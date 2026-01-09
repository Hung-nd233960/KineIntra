"""
Standalone Virtual Device Server

Runs the virtual biomechanics device as a separate process accessible over TCP.
Allows two-terminal testing: one terminal runs the device server, another runs the host client.
"""

import socket
import threading
import logging
import time
from typing import Optional

from kineintra.virtual.device import VirtualBiomechanicsDevice
from kineintra.virtual.signal_generator import SignalGenerator, RandomSignalGenerator
from kineintra.protocol.packets.packet_reader import ByteReader


class VirtualDeviceTCPServer:
    """
    TCP server hosting the virtual device.

    The server listens on a TCP port and forwards data between the host client
    and the virtual device, simulating a serial connection over the network.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8888,
        signal_generator: Optional[SignalGenerator] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize TCP server.

        Args:
            host: Server bind address (default: localhost)
            port: Server port (default: 8888)
            signal_generator: Custom signal generator for DATA frames
            logger: Logger instance
        """
        self.host = host
        self.port = port
        self._logger = logger or self._setup_logger()

        # Virtual device
        self.device = VirtualBiomechanicsDevice(
            signal_generator=signal_generator or RandomSignalGenerator(),
            logger=self._logger,
        )

        # Server state
        self._server_socket: Optional[socket.socket] = None
        self._client_socket: Optional[socket.socket] = None
        self._running = False
        self._device_thread: Optional[threading.Thread] = None

        # Byte reader for parsing commands
        self._byte_reader = ByteReader()

    def _setup_logger(self) -> logging.Logger:
        """Setup logger with timestamps."""
        logger = logging.getLogger("VirtualDeviceServer")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] %(name)s: %(message)s", datefmt="%H:%M:%S"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    def start(self) -> None:
        """Start the TCP server and begin accepting connections."""
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            self._server_socket.bind((self.host, self.port))
            self._server_socket.listen(1)
            self._running = True

            self._logger.info(
                "Virtual device server started on %s:%d", self.host, self.port
            )
            self._logger.info("Waiting for client connection...")

            # Accept one client connection
            self._client_socket, client_addr = self._server_socket.accept()
            self._logger.info(
                "Client connected from %s:%d", client_addr[0], client_addr[1]
            )

            # Start device worker thread
            self._device_thread = threading.Thread(
                target=self._device_worker, daemon=True, name="DeviceWorker"
            )
            self._device_thread.start()

            # Handle client communication in main thread
            self._handle_client()

        except KeyboardInterrupt:
            self._logger.info("Server interrupted by user")
        except Exception:
            self._logger.exception("Server error")
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the server and close all connections."""
        self._logger.info("Stopping server...")
        self._running = False

        if self._client_socket:
            try:
                self._client_socket.close()
            except Exception:
                pass

        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception:
                pass

        if self._device_thread and self._device_thread.is_alive():
            self._device_thread.join(timeout=2.0)

        self._logger.info("Server stopped")

    def _handle_client(self) -> None:
        """Handle incoming data from the connected client."""
        if not self._client_socket:
            return

        self._client_socket.settimeout(0.1)  # Non-blocking with timeout

        while self._running:
            try:
                # Receive data from client (host commands)
                data = self._client_socket.recv(4096)
                if not data:
                    self._logger.info("Client disconnected")
                    break

                self._logger.debug("Received %d bytes from client", len(data))

                # Parse command frames
                frames = self._byte_reader.process_bytes(data)

                for frame in frames:
                    if frame.crc_valid:
                        self._logger.debug("Command frame parsed successfully")
                        # Process command and send response
                        response = self.device.process_command(frame)
                        if response:
                            self._client_socket.sendall(response)
                            self._logger.debug(
                                "Sent %d bytes response to client", len(response)
                            )
                    else:
                        self._logger.error("Command frame CRC validation failed")
                        error_frame = self.device.generate_error_frame(
                            0x10, "CRC validation failed"
                        )
                        self._client_socket.sendall(error_frame)

            except socket.timeout:
                # Normal timeout, continue loop
                continue
            except (ConnectionResetError, BrokenPipeError):
                self._logger.info("Client connection lost")
                break
            except Exception:
                self._logger.exception("Error handling client data")
                break

    def _device_worker(self) -> None:
        """
        Background worker that generates periodic STATUS frames and DATA frames.

        Runs in a separate thread and sends frames to the connected client.
        """
        last_status_time = time.time()
        last_data_time = time.time()
        data_interval = 1.0 / 100.0  # 100 Hz default

        self._logger.info("Device worker started")

        while self._running and self._client_socket:
            try:
                current_time = time.time()

                # Send DATA frames when measuring
                if self.device.state == VirtualBiomechanicsDevice.STATE_MEASURING:
                    if current_time - last_data_time >= data_interval:
                        data_frame = self.device.generate_data_frame()
                        try:
                            self._client_socket.sendall(data_frame)
                            last_data_time = current_time

                            if self.device.data_frame_counter % 100 == 0:
                                self._logger.info(
                                    "Streaming DATA frames (sent %d so far)",
                                    self.device.data_frame_counter,
                                )
                        except (BrokenPipeError, ConnectionResetError):
                            self._logger.warning(
                                "Client connection lost during DATA streaming"
                            )
                            break

                # Periodic STATUS frame (heartbeat when idle)
                elif current_time - last_status_time > 0.5:
                    self._logger.debug("Sending periodic STATUS frame (heartbeat)")
                    status_frame = self.device.generate_status_frame()
                    try:
                        self._client_socket.sendall(status_frame)
                        last_status_time = current_time
                    except (BrokenPipeError, ConnectionResetError):
                        self._logger.warning(
                            "Client connection lost during STATUS heartbeat"
                        )
                        break

                time.sleep(0.001)  # 1ms polling

            except Exception:
                self._logger.exception("Device worker error")
                break

        self._logger.info("Device worker stopped")


def main(argv=None):
    """Entry point for standalone server."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="kineintra-virtual-server",
        description="Run virtual biomechanics device as TCP server",
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="Server bind address (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", type=int, default=8888, help="Server port (default: 8888)"
    )
    parser.add_argument(
        "--signal",
        choices=["random", "sine", "static"],
        default="random",
        help="Signal generator type (default: random)",
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args(argv)

    # Setup logging
    logger = logging.getLogger("VirtualDeviceServer")
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s: %(message)s", datefmt="%H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG if args.debug else logging.INFO)

    # Choose signal generator
    from kineintra.virtual.signal_generator import (
        RandomSignalGenerator,
        SineWaveGenerator,
        StaticSignalGenerator,
    )

    if args.signal == "sine":
        signal_gen = SineWaveGenerator()
    elif args.signal == "static":
        signal_gen = StaticSignalGenerator()
    else:
        signal_gen = RandomSignalGenerator()

    # Create and start server
    server = VirtualDeviceTCPServer(
        host=args.host, port=args.port, signal_generator=signal_gen, logger=logger
    )

    try:
        server.start()
    except KeyboardInterrupt:
        logger.info("Server interrupted")

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())

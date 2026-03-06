"""
Virtual Serial Port Layer

Low-level serial communication emulation that mimics pyserial.Serial interface.
Provides bidirectional communication with the virtual device.
"""

import threading
import time
import logging
from queue import Queue, Empty
from typing import Optional

from kineintra.protocol.packets.packet_reader import ByteReader
from kineintra.virtual.device import VirtualBiomechanicsDevice


class VirtualSerialPort:
    """
    Mock serial.Serial object that simulates a serial port connection.

    This class mimics the pyserial.Serial API and can be used as a drop-in
    replacement for testing. It maintains bidirectional queues and runs the
    virtual device in a background thread.

    Attributes matching pyserial:
        is_open: Port open status
        in_waiting: Number of bytes available to read
        timeout: Read timeout in seconds
        write_timeout: Write timeout in seconds
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the virtual port."""
        self._logger = logger or self._setup_logger()

        self.is_open = True
        self._in_waiting = 0  # Internal state
        self.timeout = 1.0
        self.write_timeout = 1.0

        # Queues for bidirectional communication
        self._tx_queue: Queue[bytes] = Queue()  # Host -> Device (commands)
        self._rx_queue: Queue[bytes] = Queue()  # Device -> Host (responses)

        # Virtual device with monitoring
        self._device = VirtualBiomechanicsDevice(logger=self._logger)
        self._device_thread: Optional[threading.Thread] = None
        self._running = True

        # Byte reader for parsing incoming command frames
        self._byte_reader = ByteReader()

        # Start device emulation thread
        self._start_device_thread()

        self._logger.info("Virtual serial port opened")

    @property
    def in_waiting(self) -> int:
        """Get number of bytes available to read (updates dynamically)."""
        self._in_waiting = self._rx_queue.qsize()
        return self._in_waiting

    def _setup_logger(self) -> logging.Logger:
        """Setup default logger with timestamps."""
        logger = logging.getLogger("VirtualPort")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] %(name)s: %(message)s", datefmt="%H:%M:%S"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    def close(self) -> None:
        """Close the virtual port."""
        if self.is_open:
            return

        self._logger.info("Closing virtual serial port")
        self.is_open = False
        self._running = False

        if self._device_thread and self._device_thread.is_alive():
            self._device_thread.join(timeout=2.0)

    def write(self, data: bytes) -> int:
        """
        Write data to the virtual port (host -> device).

        Args:
            data: Bytes to send to device

        Returns:
            Number of bytes written
        """
        if not self.is_open:
            raise OSError("Port is closed")

        self._tx_queue.put(bytes(data))
        self._logger.debug(f"Host sent {len(data)} bytes to device")
        return len(data)

    def read(self, size: int = 1) -> bytes:
        """
        Read data from the virtual port (device -> host).

        Args:
            size: Maximum number of bytes to read

        Returns:
            Bytes received from device (up to size bytes)
        """
        if not self.is_open:
            raise OSError("Port is closed")

        # in_waiting is now a property that updates dynamically
        if self.in_waiting == 0:
            return b""

        # Read available data
        data = bytearray()
        while len(data) < size and not self._rx_queue.empty():
            try:
                chunk = self._rx_queue.get_nowait()
                data.extend(chunk)
            except Empty:
                break

        return bytes(data)

    def flush(self) -> None:
        """Flush the output buffer (no-op for virtual port)."""
        return None

    def _start_device_thread(self) -> None:
        """Start the device emulation thread."""
        self._device_thread = threading.Thread(
            target=self._device_worker, daemon=True, name="VirtualDeviceWorker"
        )
        self._device_thread.start()

    def _device_worker(self) -> None:
        """
        Background worker that:
        1. Processes commands from host
        2. Generates periodic STATUS frames (heartbeat)
        3. Streams DATA frames when in MEASURING state
        """
        last_status_time = time.time()
        last_data_time = time.time()

        # Calculate data frame interval based on sampling rate
        data_interval = 1.0 / 100.0  # Default 100 Hz

        self._logger.info("Virtual device worker started")

        while self._running and self.is_open:
            try:
                current_time = time.time()

                # Process incoming commands from host
                if not self._tx_queue.empty():
                    try:
                        cmd_data = self._tx_queue.get_nowait()
                        self._logger.debug(
                            f"Device received {len(cmd_data)} bytes from host"
                        )

                        # Parse command frame(s)
                        frames = self._byte_reader.process_bytes(cmd_data)

                        for frame in frames:
                            if frame.crc_valid:
                                self._logger.info("Command frame parsed successfully")
                                # Generate response(s)
                                response = self._device.process_command(frame)
                                if response:
                                    self._rx_queue.put(response)
                                    self._logger.debug(
                                        f"Device queued {len(response)} bytes response"
                                    )
                            else:
                                self._logger.error(
                                    "Command frame CRC validation failed"
                                )
                                error_frame = self._device.generate_error_frame(
                                    0x10, "CRC validation failed"
                                )
                                self._rx_queue.put(error_frame)

                    except (ValueError, RuntimeError, OSError) as e:
                        self._logger.exception("Error processing command")
                        error_frame = self._device.generate_error_frame(
                            0x11, f"Command processing error: {str(e)}"
                        )
                        self._rx_queue.put(error_frame)

                # Send DATA frames when in MEASURING state
                if self._device.state == VirtualBiomechanicsDevice.STATE_MEASURING:
                    if current_time - last_data_time >= data_interval:
                        data_frame = self._device.generate_data_frame()
                        self._rx_queue.put(data_frame)
                        last_data_time = current_time

                        if self._device.data_frame_counter % 100 == 0:
                            self._logger.info(
                                "Streaming DATA frames (sent %d so far)",
                                self._device.data_frame_counter,
                            )

                # Periodic STATUS frame (heartbeat every 500ms when IDLE)
                elif current_time - last_status_time > 0.5:
                    self._logger.debug("Sending periodic STATUS frame (heartbeat)")
                    status_frame = self._device.generate_status_frame()
                    self._rx_queue.put(status_frame)
                    last_status_time = current_time

                # in_waiting is now a dynamic property, no need to set it

                time.sleep(0.001)  # 1ms polling interval

            except (ValueError, RuntimeError, OSError):
                self._logger.exception("Device worker error")
                break

        self._logger.info("Virtual device worker stopped")


class VirtualSerialModule:
    """
    Mock for serial module that patches serial.Serial() calls.

    When this module is used in place of pyserial, all Serial()
    constructor calls return VirtualSerialPort instances.
    """

    @staticmethod
    def Serial(*_args, **_kwargs):
        """Return a VirtualSerialPort instance."""
        return VirtualSerialPort()

    @staticmethod
    def SerialException(msg: str):
        """Mock SerialException."""
        return OSError(msg)


def patch_serial_for_testing():
    """
    Patch the serial module to use virtual ports for testing.

    Call this at the start of your test suite or in conftest.py:

        from kineintra.virtual import patch_serial_for_testing
        patch_serial_for_testing()

    Returns:
        VirtualSerialModule instance that was installed
    """
    import kineintra.protocol.serial.serial_connection as sc

    virtual_serial = VirtualSerialModule()
    sc.serial = virtual_serial  # type: ignore

    return virtual_serial

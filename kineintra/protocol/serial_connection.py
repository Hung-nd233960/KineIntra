"""
USB/COM Port Serial Connection Module

Handles serial communication with the biomechanics device over USB/COM ports.
Provides connection management, data transmission/reception, and error handling.
"""

import threading
import time
import platform
from typing import Optional, Callable, List
from dataclasses import dataclass
from enum import Enum
import logging
import serial
from kineintra.protocol.packet_reader import ByteReader, FrameParseResult
from kineintra.protocol.config import MAX_CONSECUTIVE_ERRORS


class ConnectionState(Enum):
    """States of the serial connection."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    CLOSING = "closing"


@dataclass
class SerialConfig:
    """Configuration for serial connection."""

    port: str
    baudrate: int = 115200
    timeout: float = 1.0
    write_timeout: float = 1.0
    bytesize: int = 8
    stopbits: int = 1
    parity: str = "N"  # None


class SerialPortConnection:
    """
    Manages USB/COM port serial communication with the biomechanics device.

    Features:
    - Automatic port detection and connection
    - Non-blocking async frame reception with callbacks
    - Error handling and reconnection support
    - Thread-safe serial communication
    """

    def __init__(
        self,
        config: Optional[SerialConfig] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize serial connection manager.

        Args:
            config: SerialConfig object with connection parameters.
                   If None, uses default USB/COM configuration.
            logger: Optional logging.Logger instance for debug output.
        """
        # Set default port based on OS
        default_port = "COM1" if platform.system() == "Windows" else "/dev/ttyUSB0"
        self.config = config or SerialConfig(port=default_port)
        self.logger = logger or self._setup_default_logger()

        self.serial_port: Optional[serial.Serial] = None
        self.state = ConnectionState.DISCONNECTED
        self.byte_reader = ByteReader()

        # Threading
        self._receive_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False

        # Thread-safe callback access
        self._callback_lock = threading.RLock()
        self._frame_callbacks: List[Callable[[FrameParseResult], None]] = []
        self._error_callbacks: List[Callable[[str], None]] = []
        self._state_callbacks: List[Callable[[ConnectionState], None]] = []

        # Statistics
        self.frames_received = 0
        self.frames_sent = 0
        self.crc_errors = 0
        self.last_error: Optional[str] = None

    def _setup_default_logger(self) -> logging.Logger:
        """Create a default logger if none provided."""
        logger = logging.getLogger("SerialPortConnection")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    def connect(self, port: Optional[str] = None, timeout: float = 5.0) -> bool:
        """
        Establish serial connection to the device.

        Args:
            port: COM/USB port name (e.g., "COM3", "/dev/ttyUSB0").
                 If None, uses configured port.
            timeout: Connection timeout in seconds.

        Returns:
            True if connection successful, False otherwise.
        """
        if port:
            self.config.port = port

        if self.state == ConnectionState.CONNECTED:
            self.logger.warning("Already connected to {}".format(self.config.port))
            return True

        self._set_state(ConnectionState.CONNECTING)

        try:
            self.serial_port = serial.Serial(
                port=self.config.port,
                baudrate=self.config.baudrate,
                timeout=self.config.timeout,
                write_timeout=self.config.write_timeout,
                bytesize=self.config.bytesize,
                stopbits=self.config.stopbits,
                parity=self.config.parity,
            )

            # Verify connection with timeout
            start_time = time.time()
            while not self.serial_port.is_open:
                if time.time() - start_time > timeout:
                    if self.serial_port:
                        self.serial_port.close()
                    raise TimeoutError(f"Connection timeout after {timeout}s")
                time.sleep(0.1)

            self.logger.info(
                "Connected to %s at %d baud", self.config.port, self.config.baudrate
            )
            self._set_state(ConnectionState.CONNECTED)

            # Start receive thread
            self._start_receive_thread()
            return True

        except (serial.SerialException, TimeoutError) as e:  # type: ignore
            error_msg = f"Failed to connect to {self.config.port}: {str(e)}"
            self.logger.error(error_msg)
            self.last_error = error_msg
            self._set_state(ConnectionState.ERROR)
            self.serial_port = None
            return False

    def disconnect(self) -> bool:
        """
        Close the serial connection.

        Returns:
            True if disconnection successful, False otherwise.
        """
        if self.state == ConnectionState.DISCONNECTED:
            self.logger.warning("Already disconnected")
            return True

        self._set_state(ConnectionState.CLOSING)

        try:
            # Stop receive thread
            self._stop_receive_thread()

            # Close serial port safely
            if self.serial_port is not None:
                try:
                    if self.serial_port.is_open:
                        self.serial_port.close()
                    self.serial_port = None
                except (OSError, AttributeError) as e:
                    self.logger.warning("Error closing port: %s", str(e))
                    self.serial_port = None

            time.sleep(0.1)  # Brief delay for OS to release port

            self.logger.info("Disconnected from %s", self.config.port)
            self._set_state(ConnectionState.DISCONNECTED)
            return True

        except Exception as e:
            error_msg = f"Error during disconnection: {str(e)}"
            self.logger.error(error_msg)
            self.last_error = error_msg
            self._set_state(ConnectionState.ERROR)
            self.serial_port = None
            return False

    def send_frame(self, frame_data: bytes) -> bool:
        """
        Send a binary frame to the device.

        Args:
            frame_data: Binary frame data to send.

        Returns:
            True if send successful, False otherwise.
        """
        if not self.is_connected():
            self.logger.error("Cannot send: not connected")
            return False

        try:
            if self.serial_port is None:
                raise RuntimeError("Serial port is None")

            bytes_sent = self.serial_port.write(frame_data)
            self.serial_port.flush()

            if bytes_sent != len(frame_data):
                self.logger.warning(
                    "Incomplete send: wrote %d/%d bytes", bytes_sent, len(frame_data)
                )
                return False

            self.frames_sent += 1
            self.logger.debug("Sent %d bytes", len(frame_data))
            return True

        except (OSError, RuntimeError) as e:
            error_msg = f"Error sending frame: {str(e)}"
            self.logger.error(error_msg)
            self.last_error = error_msg
            self._set_state(ConnectionState.ERROR)
            return False

    def is_connected(self) -> bool:
        """Check if currently connected to device."""
        return (
            self.state == ConnectionState.CONNECTED
            and self.serial_port is not None
            and self.serial_port.is_open
        )

    def get_state(self) -> ConnectionState:
        """Get current connection state."""
        return self.state

    def register_frame_callback(
        self, callback: Callable[[FrameParseResult], None]
    ) -> None:
        """
        Register callback to be invoked when a frame is received.

        Args:
            callback: Function that takes a FrameParseResult.
        """
        with self._callback_lock:
            self._frame_callbacks.append(callback)

    def register_error_callback(self, callback: Callable[[str], None]) -> None:
        """
        Register callback to be invoked when an error occurs.

        Args:
            callback: Function that takes an error message string.
        """
        with self._callback_lock:
            self._error_callbacks.append(callback)

    def register_state_callback(
        self, callback: Callable[[ConnectionState], None]
    ) -> None:
        """
        Register callback to be invoked when connection state changes.

        Args:
            callback: Function that takes a ConnectionState.
        """
        with self._callback_lock:
            self._state_callbacks.append(callback)

    def _start_receive_thread(self) -> None:
        """Start the background receive thread."""
        if self._receive_thread and self._receive_thread.is_alive():
            return

        self._stop_event.clear()
        self._running = True
        self._receive_thread = threading.Thread(
            target=self._receive_worker, daemon=True
        )
        self._receive_thread.start()
        self.logger.debug("Receive thread started")

    def _stop_receive_thread(self) -> None:
        """Stop the background receive thread."""
        if not self._running:
            return

        self._stop_event.set()
        self._running = False

        if self._receive_thread and self._receive_thread.is_alive():
            self._receive_thread.join(timeout=2.0)
            self.logger.debug("Receive thread stopped")

    def _receive_worker(self) -> None:
        """
        Background worker thread that continuously reads from serial port
        and processes frames.
        """
        self.logger.debug("Receive worker started")
        consecutive_errors = 0

        while self._running and not self._stop_event.is_set():
            try:
                if not self.is_connected():
                    time.sleep(0.1)
                    consecutive_errors = 0
                    continue

                if self.serial_port is None:
                    time.sleep(0.1)
                    continue

                if self.serial_port.in_waiting > 0:
                    new_data = self.serial_port.read(self.serial_port.in_waiting)

                    # Process bytes and extract frames
                    frames = self.byte_reader.process_bytes(new_data)

                    # Track CRC errors (safe copy to avoid race conditions)
                    crc_error_count = self.byte_reader.crc_errors
                    self.crc_errors += crc_error_count
                    self.byte_reader.crc_errors = 0

                    # Invoke callbacks for each frame
                    for frame in frames:
                        self.frames_received += 1
                        self.logger.debug(
                            "Frame received: type=0x%02X, len=%d, crc_valid=%s",
                            frame.msg_type,
                            frame.length,
                            frame.crc_valid,
                        )

                        with self._callback_lock:
                            for callback in self._frame_callbacks:
                                try:
                                    callback(frame)
                                except (ValueError, RuntimeError) as e:
                                    error_msg = f"Error in frame callback: {str(e)}"
                                    self.logger.error(error_msg)
                                    for cb in self._error_callbacks:
                                        try:
                                            cb(error_msg)
                                        except Exception as cb_err:
                                            self.logger.error(
                                                "Error in error callback: %s",
                                                str(cb_err),
                                            )

                    consecutive_errors = 0
                else:
                    time.sleep(0.01)  # Brief sleep if no data available

            except (OSError, RuntimeError) as e:
                consecutive_errors += 1
                error_msg = f"Error in receive worker: {str(e)}"
                self.logger.error(
                    "%s (consecutive errors: %d/%d)",
                    error_msg,
                    consecutive_errors,
                    MAX_CONSECUTIVE_ERRORS,
                )
                self.last_error = error_msg

                # Only transition to ERROR state once, not repeatedly
                if self.state != ConnectionState.ERROR:
                    self._set_state(ConnectionState.ERROR)

                    with self._callback_lock:
                        # Safely copy error callbacks while holding lock
                        for cb in list(self._error_callbacks):
                            try:
                                cb(error_msg)
                            except Exception as cb_err:
                                self.logger.error(
                                    "Error in error callback: %s",
                                    str(cb_err),
                                )

                # Exit if too many consecutive errors
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    self.logger.error(
                        "Too many consecutive errors, stopping receive worker"
                    )
                    self._running = False
                    break

                # Brief delay before retry
                time.sleep(0.5)

        self.logger.debug("Receive worker stopped")

    def _set_state(self, new_state: ConnectionState) -> None:
        """
        Update connection state and invoke state change callbacks.

        Args:
            new_state: The new ConnectionState.
        """
        if self.state != new_state:
            old_state = self.state
            self.state = new_state
            self.logger.info(
                "State changed: %s -> %s", old_state.value, new_state.value
            )

            with self._callback_lock:
                for callback in self._state_callbacks:
                    try:
                        callback(new_state)
                    except (ValueError, RuntimeError) as e:
                        self.logger.error("Error in state callback: %s", str(e))

    def get_statistics(self) -> dict:
        """
        Get communication statistics.

        Returns:
            Dictionary with frames sent/received, CRC errors, etc.
        """
        return {
            "frames_sent": self.frames_sent,
            "frames_received": self.frames_received,
            "crc_errors": self.crc_errors,
            "last_error": self.last_error,
            "state": self.state.value,
        }

    def reset_statistics(self) -> None:
        """Reset communication statistics."""
        self.frames_sent = 0
        self.frames_received = 0
        self.crc_errors = 0
        self.last_error = None


class PortDetector:
    """Utility class to detect available serial ports."""

    @staticmethod
    def list_ports() -> List[str]:
        """
        List all available serial ports on the system.

        Returns:
            List of port names (e.g., ["COM1", "COM3", "/dev/ttyUSB0"]).
        """
        try:
            from serial.tools.list_ports import comports  # type: ignore

            return [port.device for port in comports()]
        except ImportError:
            logging.warning("pyserial list_ports not available, returning empty list")
            return []

    @staticmethod
    def find_device_port(vid: int = 0x10C4, pid: int = 0xEA60) -> Optional[str]:
        """
        Find a specific USB device by VID/PID.

        Args:
            vid: USB Vendor ID (default: Silicon Labs CP210x).
            pid: USB Product ID (default: Silicon Labs CP210x).

        Returns:
            Port name if found, None otherwise.
        """
        try:
            from serial.tools.list_ports import comports  # type: ignore

            for port in comports():
                if hasattr(port, "vid") and hasattr(port, "pid"):
                    if port.vid == vid and port.pid == pid:  # type: ignore
                        return port.device
            return None
        except ImportError:
            logging.warning("VID/PID matching not available")
            return None

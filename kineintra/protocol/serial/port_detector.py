from typing import List, Optional
import logging
from serial.tools.list_ports import comports


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
            for port in comports():
                if hasattr(port, "vid") and hasattr(port, "pid"):
                    if port.vid == vid and port.pid == pid:  # type: ignore
                        return port.device
            return None
        except ImportError:
            logging.warning("VID/PID matching not available")
            return None

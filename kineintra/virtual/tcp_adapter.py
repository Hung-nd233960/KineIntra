"""
TCP Serial Adapter

Wraps a TCP socket to provide a Serial-like interface.
Allows DeviceClient to connect to the virtual device TCP server.
"""

import socket
import logging
from typing import Optional


class TCPSerialAdapter:
    """
    Adapter that wraps a TCP socket to mimic pyserial.Serial interface.

    This allows transparent connection to the virtual device TCP server
    using the existing SerialPortConnection infrastructure.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8888, timeout: float = 1.0):
        """
        Initialize TCP serial adapter.

        Args:
            host: Server hostname or IP
            port: Server port
            timeout: Read timeout in seconds
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.write_timeout = timeout

        self._socket: Optional[socket.socket] = None
        self.is_open = False
        self.in_waiting = 0

        self._logger = logging.getLogger("TCPSerialAdapter")

        # Connect immediately
        self._connect()

    def _connect(self) -> None:
        """Establish TCP connection to server."""
        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(self.timeout)
            self._socket.connect((self.host, self.port))
            self.is_open = True
            self._logger.info("Connected to TCP server at %s:%d", self.host, self.port)
        except Exception as e:
            self._logger.error(
                "Failed to connect to %s:%d - %s", self.host, self.port, e
            )
            raise

    def close(self) -> None:
        """Close the TCP connection."""
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
        self.is_open = False
        self._logger.info("Disconnected from TCP server")

    def write(self, data: bytes) -> int:
        """
        Write data to TCP socket.

        Args:
            data: Bytes to send

        Returns:
            Number of bytes written
        """
        if not self.is_open or not self._socket:
            raise OSError("Connection is closed")

        try:
            self._socket.sendall(data)
            return len(data)
        except Exception as e:
            self._logger.error("Write error: %s", e)
            raise

    def read(self, size: int = 1) -> bytes:
        """
        Read data from TCP socket.

        Args:
            size: Maximum bytes to read

        Returns:
            Received bytes (may be less than size)
        """
        if not self.is_open or not self._socket:
            raise OSError("Connection is closed")

        try:
            # Non-blocking receive with timeout
            data = self._socket.recv(size)
            return data
        except socket.timeout:
            return b""
        except Exception as e:
            self._logger.error("Read error: %s", e)
            raise

    def flush(self) -> None:
        """Flush output buffer (no-op for TCP)."""


class TCPSerialModule:
    """
    Mock serial module that returns TCPSerialAdapter instead of real serial ports.
    Used to patch serial connections to use TCP.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8888):
        """
        Initialize TCP serial module.

        Args:
            host: Default server host
            port: Default server port
        """
        self.default_host = host
        self.default_port = port

    def Serial(self, *args, **kwargs):
        """Return TCPSerialAdapter instead of real serial port."""
        # Ignore port argument from serial connection if it's not an integer
        # Use stored defaults for host/port
        host = self.default_host
        port = self.default_port

        # Override only if valid integer port is provided
        if "port" in kwargs and isinstance(kwargs["port"], int):
            port = kwargs["port"]
        if "host" in kwargs and isinstance(kwargs["host"], str):
            host = kwargs["host"]

        timeout = kwargs.get("timeout", 1.0)
        if not isinstance(timeout, (int, float)):
            timeout = 1.0

        return TCPSerialAdapter(host=host, port=port, timeout=timeout)

    @staticmethod
    def SerialException(msg: str):
        """Mock SerialException."""
        return OSError(msg)


def patch_serial_for_tcp(host: str = "127.0.0.1", port: int = 8888):
    """
    Patch serial module to connect to TCP virtual device server.

    Args:
        host: Virtual device server host
        port: Virtual device server port

    Returns:
        TCPSerialModule instance
    """
    import kineintra.protocol.serial.serial_connection as sc

    tcp_serial = TCPSerialModule(host=host, port=port)
    sc.serial = tcp_serial  # type: ignore

    return tcp_serial

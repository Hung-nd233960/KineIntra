"""
TCP Client Helper

Convenience helper to connect DeviceClient to TCP virtual device server.
"""

from kineintra.virtual.tcp_adapter import patch_serial_for_tcp
from kineintra.api import DeviceClient


def connect_to_tcp_server(host: str = "127.0.0.1", port: int = 8888) -> DeviceClient:
    """
    Connect to virtual device TCP server.

    Args:
        host: Server hostname/IP
        port: Server port

    Returns:
        Connected DeviceClient instance

    Example:
        # Terminal 1: Start server
        python -m kineintra.virtual.server

        # Terminal 2: Connect client
        from kineintra.virtual import connect_to_tcp_server
        client = connect_to_tcp_server()
        client.get_status(1)
    """
    # Patch serial to use TCP
    patch_serial_for_tcp(host=host, port=port)

    # Create and connect client (don't pass port - TCP adapter uses patched module)
    client = DeviceClient()

    # Connect without port argument (TCP is already patched)
    if not client.connect(timeout=5.0):
        raise ConnectionError(f"Failed to connect to TCP server at {host}:{port}")

    return client

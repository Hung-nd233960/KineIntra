"""
Virtual Device Module

One-to-one replication of the physical biomechanics device for testing and development.

Layered architecture:
- Serial layer: VirtualSerialPort (mimics pyserial interface)
- Packet layer: Frame parsing and generation
- Application layer: Device logic, command processing, data streaming

Usage:
    from kineintra.virtual import VirtualSerialPort, VirtualBiomechanicsDevice
    from kineintra.virtual import patch_serial_for_testing

    # Direct usage
    port = VirtualSerialPort()

    # Or patch for transparent testing
    patch_serial_for_testing()
"""

from kineintra.virtual.serial_layer import (
    VirtualSerialPort,
    VirtualSerialModule,
    patch_serial_for_testing,
)
from kineintra.virtual.device import VirtualBiomechanicsDevice
from kineintra.virtual.signal_generator import SignalGenerator, RandomSignalGenerator
from kineintra.virtual.tcp_adapter import TCPSerialAdapter, patch_serial_for_tcp
from kineintra.virtual.tcp_client import connect_to_tcp_server
from kineintra.virtual.server import VirtualDeviceTCPServer

__all__ = [
    "VirtualSerialPort",
    "VirtualSerialModule",
    "VirtualBiomechanicsDevice",
    "SignalGenerator",
    "RandomSignalGenerator",
    "patch_serial_for_testing",
    "TCPSerialAdapter",
    "patch_serial_for_tcp",
    "connect_to_tcp_server",
    "VirtualDeviceTCPServer",
]

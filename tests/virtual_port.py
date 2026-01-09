"""
DEPRECATED: This module has been moved to kineintra.virtual

Virtual Serial Port Emulator for Testing

Simulates a biomechanics device responding to protocol commands.
Used for unit testing without requiring actual hardware.

Use instead:
    from kineintra.virtual import VirtualSerialPort, patch_serial_for_testing
"""

# Re-export from new location for backward compatibility
from kineintra.virtual import (
    VirtualSerialPort,
    VirtualSerialModule,
    VirtualBiomechanicsDevice,
    patch_serial_for_testing,
)


# Legacy alias
def mock_serial_module():
    """DEPRECATED: Use patch_serial_for_testing() instead."""
    return patch_serial_for_testing()

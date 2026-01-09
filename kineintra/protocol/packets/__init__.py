"""
Protocol packets module.
Provides packet maker classes for both host and device communication.
"""

from kineintra.protocol.packets.config import (
    SOF,
    PROTOCOL_VER,
    MAX_PAYLOAD_SIZE,
    MAX_CONSECUTIVE_ERRORS,
    FrameType,
    CmdID,
    crc16_ccitt,
    AckResult,
    ErrorCode,
    DeviceState,
    SensorRole,
    STATUS_PAYLOAD_SIZE,
)

from kineintra.protocol.packets.packet_maker import (
    HostPacketMaker,
    DevicePacketMaker,
    UnifiedPacketMaker,
)

__all__ = [
    # Config constants
    "SOF",
    "PROTOCOL_VER",
    "MAX_PAYLOAD_SIZE",
    "MAX_CONSECUTIVE_ERRORS",
    "FrameType",
    "CmdID",
    "crc16_ccitt",
    # Packet makers
    "HostPacketMaker",
    "DevicePacketMaker",
    "UnifiedPacketMaker",
    # Constants from packet_maker
    "AckResult",
    "ErrorCode",
    "DeviceState",
    "SensorRole",
    "STATUS_PAYLOAD_SIZE",
]

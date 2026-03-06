import enum


SOF = b"\xa5\x5a"
PROTOCOL_VER = 0x01
MAX_PAYLOAD_SIZE = 0xFFFF  # 65535 bytes
MAX_CONSECUTIVE_ERRORS = 5
STATUS_PAYLOAD_SIZE = 142
# Total STATUS payload size: 10 (header) + 64 (rates) + 32 (bits) + 32 (roles) + 4 (flags)


class FrameType(enum.IntEnum):
    """
    Frame type definitions.
    Represents different types of frames in the protocol.
    """

    STATUS = 0x01
    DATA = 0x02
    COMMAND = 0x03
    ACK = 0x04
    ERROR = 0x05


class CmdID(enum.IntEnum):
    """
    Command ID definitions.
    Represents various commands that can be sent to the device."""

    GET_STATUS = 0x01
    START_MEASURE = 0x02
    STOP_MEASURE = 0x03
    SET_NSENSORS = 0x04
    SET_RATE = 0x05
    SET_BITS = 0x06
    SET_ACTIVEMAP = 0x07
    CALIBRATE = 0x08
    STOP_CALIBRATE = 0x09
    END_CALIBRATE = 0x10


# ACK Result Codes
class AckResult(enum.IntEnum):
    """
    Acknowledgment result definitions.
    Represents the outcome of command processing by the device.
    """

    OK = 0x00
    INVALID_COMMAND = 0x01
    INVALID_ARGUMENT = 0x02
    BUSY = 0x03
    FAILED = 0x04
    NOT_ALLOWED = 0x05


# Error Codes
class ErrorCode(enum.IntEnum):
    """
    Device error definitions.
    Represents various error conditions reported by the device."""

    ADC_OVERRUN = 0x01
    SENSOR_FAULT = 0x02
    FIFO_CRITICAL = 0x03
    LOW_VOLTAGE = 0x04
    I2C_ERROR = 0x05
    VENDOR_SPECIFIC = 0xFE


# Device State Codes
class DeviceState(enum.IntEnum):
    """
    Device state definitions.
    Represents the current operational state of the device.
    """

    IDLE = 0x00
    MEASURING = 0x01
    CALIBRATING = 0x02
    ERROR = 0x03


# Sensor Role Codes
class SensorRole(enum.IntEnum):
    """
    Sensor role definitions.
    Defines the functional role of each sensor in the system.
    """

    NONE = 0x00
    FSR = 0x01
    LOADCELL = 0x02
    IMU = 0x03


def crc16_ccitt(data: bytes) -> int:
    """
    CRC-16-CCITT implementation.
    Polynomial: 0x1021, Initial: 0xFFFF
    """
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc = crc << 1
            crc &= 0xFFFF
    return crc

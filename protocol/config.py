import enum


SOF = b"\xa5\x5a"
PROTOCOL_VER = 0x01


class FrameType(enum.IntEnum):
    STATUS = 0x01
    DATA = 0x02
    COMMAND = 0x03
    ACK = 0x04
    ERROR = 0x05


class CmdID(enum.IntEnum):
    GET_STATUS = 0x01
    START_MEASURE = 0x02
    STOP_MEASURE = 0x03
    SET_NSENSORS = 0x04
    SET_RATE = 0x05
    SET_BITS = 0x06
    SET_ACTIVEMAP = 0x07
    CALIBRATE = 0x08


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

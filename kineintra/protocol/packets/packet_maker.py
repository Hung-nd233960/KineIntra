import struct
from kineintra.protocol.packets.config import SOF, PROTOCOL_VER, FrameType, CmdID

# --- 1. Constants & Definitions ---


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


# --- 2. Packet Maker (Host -> Device) ---


class HostPacketMaker:
    """
    Constructs binary frames to send TO the Device (COMMAND frames).
    """

    @staticmethod
    def _pack_frame(msg_type: int, payload: bytes) -> bytes:
        # Header: SOF (2) + Ver (1) + Type (1) + Len (2)
        # Note: Len is Little-Endian (<H)
        header_inner = struct.pack("<BBH", PROTOCOL_VER, msg_type, len(payload))

        # Calculate CRC over Ver | Type | Len | Payload
        crc_val = crc16_ccitt(header_inner + payload)

        # Final assembly: SOF + HeaderInner + Payload + CRC
        return SOF + header_inner + payload + struct.pack("<H", crc_val)

    @staticmethod
    def make_command(cmd_id: int, seq: int, args: bytes = b"") -> bytes:
        """
        Generic command builder.
        Payload: CmdID (1) | Seq (1) | Args (N)
        Args:
            cmd_id: Command ID.
            seq: Sequence number.
            args: Additional command arguments as bytes.
        """
        payload = struct.pack("<BB", cmd_id, seq) + args
        return HostPacketMaker._pack_frame(FrameType.COMMAND, payload)

    # -- Specific Command Helpers (Section 7.4) --
    @staticmethod
    def cmd_get_status(seq: int) -> bytes:
        return HostPacketMaker.make_command(CmdID.GET_STATUS, seq)

    @staticmethod
    def cmd_start_measure(seq: int) -> bytes:
        return HostPacketMaker.make_command(CmdID.START_MEASURE, seq)

    @staticmethod
    def cmd_stop_measure(seq: int) -> bytes:
        return HostPacketMaker.make_command(CmdID.STOP_MEASURE, seq)

    @staticmethod
    def cmd_set_nsensors(seq: int, n_sensors: int) -> bytes:
        # Args: uint8 NSensors
        return HostPacketMaker.make_command(
            CmdID.SET_NSENSORS, seq, struct.pack("<B", n_sensors)
        )

    @staticmethod
    def cmd_set_rate(seq: int, sensor_idx: int, rate_hz: int) -> bytes:
        # Args: uint8 SensorIndex, uint16 SampRateHz
        args = struct.pack("<BH", sensor_idx, rate_hz)
        return HostPacketMaker.make_command(CmdID.SET_RATE, seq, args)

    @staticmethod
    def cmd_set_bits(seq: int, sensor_idx: int, bits_per_smp: int) -> bytes:
        # Args: uint8 SensorIndex, uint8 BitsPerSmp
        args = struct.pack("<BB", sensor_idx, bits_per_smp)
        return HostPacketMaker.make_command(CmdID.SET_BITS, seq, args)

    @staticmethod
    def cmd_set_active_map(seq: int, active_map: int) -> bytes:
        # Args: uint32 ActiveMap
        args = struct.pack("<I", active_map)
        return HostPacketMaker.make_command(CmdID.SET_ACTIVEMAP, seq, args)

    @staticmethod
    def cmd_calibrate(seq: int, mode: int) -> bytes:
        # Args: uint8 Mode
        return HostPacketMaker.make_command(
            CmdID.CALIBRATE, seq, struct.pack("<B", mode)
        )

"""
Roundtrip tests for packet maker, byte reader, and protocol parser.
Covers all frame types and host/device directions.
"""

from kineintra.protocol.packets.config import FrameType, CmdID, AckResult, ErrorCode
from kineintra.protocol.packets.packet_maker import DevicePacketMaker
from kineintra.protocol.packets.frame_maker_api import HostPacketMakerAPI
from kineintra.protocol.packets.packet_reader import ByteReader
from kineintra.protocol.packets.protocol_parser import (
    ProtocolParser,
    CommandPayload,
    StatusPayload,
    DataPayload,
    AckPayload,
    ErrorPayload,
)


def _read_single_frame(reader: ByteReader, data: bytes):
    """Feed bytes (possibly in fragments) and return the single parsed frame."""
    frames = reader.process_bytes(data[: len(data) // 2])
    frames += reader.process_bytes(data[len(data) // 2 :])
    assert len(frames) == 1, f"Expected 1 frame, got {len(frames)}"
    frame = frames[0]
    assert frame.crc_valid, "CRC check failed"
    return frame


def test_command_roundtrip_with_host_packet_maker_api():
    """COMMAND frame built by HostPacketMakerAPI should parse into CommandPayload."""
    cmd_bytes = HostPacketMakerAPI.set_frame_rate(seq=5, sensor_idx=2, rate_hz=1234)
    reader = ByteReader()
    parser = ProtocolParser()

    frame = _read_single_frame(reader, cmd_bytes)
    assert frame.msg_type == FrameType.COMMAND

    frame_type, payload = parser.parse_frame(frame)
    assert frame_type == "COMMAND"
    assert isinstance(payload, CommandPayload)
    assert payload.cmd_id == CmdID.SET_RATE
    assert payload.seq == 5
    # Args: sensor_idx (1 byte) + rate_hz (2 bytes LE)
    assert payload.args == b"\x02\xd2\x04"


def test_status_and_data_roundtrip():
    """STATUS then DATA frames parse into StatusPayload and DataPayload with correct values."""
    reader = ByteReader()
    parser = ProtocolParser()

    # Build STATUS with two active sensors (0 and 1)
    active_map = 0b11
    status_frame = DevicePacketMaker.make_status(
        state=1,  # MEASURING
        n_sensors=2,
        active_map=active_map,
        health_map=active_map,
        samp_rate_map=[1000, 500] + [0] * 30,
        bits_per_smp_map=[12, 12] + [0] * 30,
        sensor_role_map=[1, 1] + [0] * 30,
        adc_flags=0,
        reserved=0,
    )

    frame = _read_single_frame(reader, status_frame)
    ftype, payload = parser.parse_frame(frame)
    assert ftype == "STATUS"
    assert payload is not None, "payload should not be None"
    assert isinstance(payload, StatusPayload)
    assert payload.n_sensors == 2
    assert payload.active_map == active_map
    assert payload.samp_rate_map[:2] == [1000, 500]
    assert payload.bits_per_smp_map[:2] == [12, 12]

    # Build DATA for the same two sensors with 12-bit values
    data_frame = DevicePacketMaker.make_data_simple(
        timestamp=123456,
        sample_values=[0x123, 0x234],
        bits_per_sample=[12, 12],
    )

    frame = _read_single_frame(reader, data_frame)
    ftype, payload = parser.parse_frame(frame)
    assert ftype == "DATA"
    assert isinstance(payload, DataPayload)
    assert payload.timestamp == 123456
    assert payload.samples[0] == 0x123
    assert payload.samples[1] == 0x234


def test_ack_roundtrip():
    """ACK frame should parse into AckPayload with matching fields."""
    reader = ByteReader()
    parser = ProtocolParser()

    ack_frame = DevicePacketMaker.make_ack(
        cmd_id=CmdID.SET_BITS,
        seq=9,
        result=AckResult.OK,
    )

    frame = _read_single_frame(reader, ack_frame)
    ftype, payload = parser.parse_frame(frame)
    assert ftype == "ACK"
    assert isinstance(payload, AckPayload)
    assert payload.cmd_id == CmdID.SET_BITS
    assert payload.seq == 9
    assert payload.result == AckResult.OK
    assert payload.is_success()


def test_error_roundtrip():
    """ERROR frame should parse into ErrorPayload with matching fields."""
    reader = ByteReader()
    parser = ProtocolParser()

    err_frame = DevicePacketMaker.make_error(
        timestamp=42,
        err_code=ErrorCode.FIFO_CRITICAL,
        aux_data=0xBEEF,
    )

    frame = _read_single_frame(reader, err_frame)
    ftype, payload = parser.parse_frame(frame)
    assert ftype == "ERROR"
    assert isinstance(payload, ErrorPayload)
    assert payload.timestamp == 42
    assert payload.error_code == ErrorCode.FIFO_CRITICAL
    assert payload.aux_data == 0xBEEF
    assert payload.get_error_name() == "FIFO_CRITICAL"

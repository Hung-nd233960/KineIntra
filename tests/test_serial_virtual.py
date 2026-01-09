"""
Integration tests: SerialPortConnection <-> VirtualSerialPort
Verifies heartbeat STATUS reception and command ACK/STATUS responses.
"""

import time
import kineintra.protocol.serial.serial_connection as sc
from kineintra.protocol.packets.packet_maker import HostPacketMaker
from kineintra.protocol.packets.config import FrameType
from tests.virtual_port import VirtualSerialModule


def _patch_serial(monkeypatch):
    """Patch serial module used by SerialPortConnection to virtual implementation."""
    monkeypatch.setattr(sc, "serial", VirtualSerialModule())


def test_connect_and_heartbeat(monkeypatch):
    _patch_serial(monkeypatch)
    conn = sc.SerialPortConnection()
    received = []
    conn.register_frame_callback(received.append)

    try:
        assert conn.connect(timeout=1.0) is True
        # Wait for at least one unsolicited STATUS (heartbeat every ~0.5s)
        time.sleep(0.7)
    finally:
        conn.disconnect()

    assert any(
        f.msg_type == FrameType.STATUS and f.crc_valid for f in received
    ), "No STATUS heartbeat received"


def test_command_ack_and_status(monkeypatch):
    _patch_serial(monkeypatch)
    conn = sc.SerialPortConnection()
    received = []
    conn.register_frame_callback(received.append)

    try:
        assert conn.connect(timeout=1.0) is True
        # Send GET_STATUS command
        frame = HostPacketMaker.cmd_get_status(seq=1)
        assert conn.send_frame(frame) is True
        # Allow responses to arrive
        time.sleep(0.5)
    finally:
        conn.disconnect()

    has_ack = any(f.msg_type == FrameType.ACK and f.crc_valid for f in received)
    has_status = any(f.msg_type == FrameType.STATUS and f.crc_valid for f in received)
    assert has_ack, "ACK not received for GET_STATUS"
    assert has_status, "STATUS not received after GET_STATUS"


def test_disconnect_changes_state(monkeypatch):
    _patch_serial(monkeypatch)
    conn = sc.SerialPortConnection()

    assert conn.connect(timeout=1.0) is True
    assert conn.is_connected() is True
    assert conn.disconnect() is True
    assert conn.is_connected() is False

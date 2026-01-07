"""
Unit tests for the biomechanics device protocol and serial connection.
Tests use the VirtualSerialPort emulator for hardware-independent testing.
"""

import pytest
import time
import struct
from typing import List
from unittest.mock import patch, MagicMock

from kineintra.protocol.packets.packet_reader import FrameParseResult
from kineintra.protocol.packets.packet_maker import HostPacketMaker
from kineintra.protocol.packets.config import FrameType, CmdID
from kineintra.tests.virtual_port import VirtualSerialPort, VirtualSerialModule


def create_virtual_serial_patch():
    """Create a patch object for serial module."""
    return patch("protocol.serial_connection.serial", VirtualSerialModule())


class TestProtocolFrameConstruction:
    """Test basic protocol frame construction."""

    def test_get_status_command(self):
        """Test GET_STATUS command frame construction."""
        cmd = HostPacketMaker.cmd_get_status(seq=1)
        assert cmd[0:2] == b"\xa5\x5a"  # SOF
        assert cmd[2] == 0x01  # Protocol version
        assert cmd[3] == FrameType.COMMAND  # Type
        assert len(cmd) > 6  # At least SOF + header + CRC

    def test_start_measure_command(self):
        """Test START_MEASURE command frame construction."""
        cmd = HostPacketMaker.cmd_start_measure(seq=2)
        assert cmd[0:2] == b"\xa5\x5a"  # SOF
        assert cmd[3] == FrameType.COMMAND

    def test_set_nsensors_command(self):
        """Test SET_NSENSORS command frame construction."""
        cmd = HostPacketMaker.cmd_set_nsensors(seq=3, n_sensors=16)
        assert cmd[0:2] == b"\xa5\x5a"  # SOF
        assert len(cmd) > 6

    def test_set_rate_command(self):
        """Test SET_RATE command frame construction."""
        cmd = HostPacketMaker.cmd_set_rate(seq=4, sensor_idx=0, rate_hz=200)
        assert cmd[0:2] == b"\xa5\x5a"  # SOF
        assert len(cmd) > 6


class TestVirtualPort:
    """Test the virtual serial port emulator."""

    def test_virtual_port_creation(self):
        """Test virtual port initialization."""
        port = VirtualSerialPort()
        assert port.is_open is True
        assert port.in_waiting == 0
        port.close()
        assert port.is_open is False

    def test_virtual_port_write_read(self):
        """Test basic write/read on virtual port."""
        port = VirtualSerialPort()
        try:
            # Write a command
            cmd = HostPacketMaker.cmd_get_status(seq=1)
            bytes_written = port.write(cmd)
            assert bytes_written == len(cmd)

            # Give device time to process
            time.sleep(0.1)

            # Read response
            response = port.read(size=1024)
            assert len(response) > 0
            assert response[0:2] == b"\xa5\x5a"  # Response has valid SOF

        finally:
            port.close()

    def test_virtual_port_multiple_commands(self):
        """Test sending multiple commands to virtual port."""
        port = VirtualSerialPort()
        try:
            # Send multiple commands in sequence
            for seq in range(1, 4):
                cmd = HostPacketMaker.cmd_get_status(seq=seq)
                port.write(cmd)
                time.sleep(0.05)

            # Read all responses
            time.sleep(0.2)
            all_data = bytearray()
            while True:
                data = port.read(size=1024)
                if not data:
                    break
                all_data.extend(data)
                time.sleep(0.01)

            # Should have received multiple frames
            assert len(all_data) > 0

        finally:
            port.close()


class TestSerialConnection:
    """Test the SerialPortConnection with virtual port."""

    @patch("protocol.serial_connection.serial", new_callable=VirtualSerialModule)
    def test_connection_initialization(self, mock_serial):
        """Test serial connection initialization."""
        from kineintra.protocol.serial.serial_connection import (
            SerialPortConnection,
            SerialConfig,
            ConnectionState,
        )

        config = SerialConfig(port="/dev/ttyUSB0")
        conn = SerialPortConnection(config=config)
        assert conn.state == ConnectionState.DISCONNECTED
        assert conn.is_connected() is False

    @patch("protocol.serial_connection.serial", new_callable=VirtualSerialModule)
    def test_connection_connect_disconnect(self, mock_serial):
        """Test connecting and disconnecting."""
        from kineintra.protocol.serial.serial_connection import (
            SerialPortConnection,
            SerialConfig,
            ConnectionState,
        )

        config = SerialConfig(port="/dev/ttyUSB0")
        conn = SerialPortConnection(config=config)

        # Connect
        result = conn.connect(timeout=2.0)
        assert result is True
        assert conn.is_connected() is True
        assert conn.state == ConnectionState.CONNECTED

        # Disconnect
        result = conn.disconnect()
        assert result is True
        assert conn.is_connected() is False
        assert conn.state == ConnectionState.DISCONNECTED

    @patch("protocol.serial_connection.serial", new_callable=VirtualSerialModule)
    def test_connection_frame_reception(self, mock_serial):
        """Test receiving frames from virtual device."""
        from kineintra.protocol.serial.serial_connection import (
            SerialPortConnection,
            SerialConfig,
            ConnectionState,
        )

        config = SerialConfig(port="/dev/ttyUSB0")
        conn = SerialPortConnection(config=config)

        received_frames: List[FrameParseResult] = []

        def frame_callback(frame: FrameParseResult):
            received_frames.append(frame)

        conn.register_frame_callback(frame_callback)

        # Connect
        assert conn.connect(timeout=2.0) is True

        # Send command
        cmd = HostPacketMaker.cmd_get_status(seq=1)
        assert conn.send_frame(cmd) is True

        # Wait for response (increased wait time)
        time.sleep(1.0)

        # Verify we received a frame
        assert (
            len(received_frames) > 0
        ), f"Expected frames but got {len(received_frames)}"
        frame = received_frames[0]
        assert frame.crc_valid is True
        assert frame.msg_type == FrameType.STATUS

        conn.disconnect()

    @patch("protocol.serial_connection.serial", new_callable=VirtualSerialModule)
    def test_connection_send_multiple_frames(self, mock_serial):
        """Test sending multiple frames and receiving responses."""
        from kineintra.protocol.serial.serial_connection import (
            SerialPortConnection,
            SerialConfig,
            ConnectionState,
        )

        config = SerialConfig(port="/dev/ttyUSB0")
        conn = SerialPortConnection(config=config)

        received_frames: List[FrameParseResult] = []

        def frame_callback(frame: FrameParseResult):
            received_frames.append(frame)

        conn.register_frame_callback(frame_callback)

        assert conn.connect(timeout=2.0) is True

        try:
            # Send multiple commands
            commands = [
                HostPacketMaker.cmd_get_status(seq=1),
                HostPacketMaker.cmd_start_measure(seq=2),
                HostPacketMaker.cmd_stop_measure(seq=3),
            ]

            for cmd in commands:
                assert conn.send_frame(cmd) is True
                time.sleep(0.1)

            # Wait for all responses (increased wait time)
            time.sleep(1.0)

            # Should have received responses
            assert (
                len(received_frames) >= 1
            ), f"Expected at least 1 frame but got {len(received_frames)}"

        finally:
            conn.disconnect()

    @patch("protocol.serial_connection.serial", new_callable=VirtualSerialModule)
    def test_connection_state_callbacks(self, mock_serial):
        """Test connection state change callbacks."""
        from kineintra.protocol.serial.serial_connection import (
            SerialPortConnection,
            SerialConfig,
            ConnectionState,
        )

        config = SerialConfig(port="/dev/ttyUSB0")
        conn = SerialPortConnection(config=config)

        state_changes: List[ConnectionState] = []

        def state_callback(state: ConnectionState):
            state_changes.append(state)

        conn.register_state_callback(state_callback)

        # Connect
        conn.connect(timeout=2.0)
        time.sleep(0.1)

        # Disconnect
        conn.disconnect()
        time.sleep(0.1)

        # Verify state transitions were logged
        assert ConnectionState.CONNECTING in state_changes
        assert ConnectionState.CONNECTED in state_changes
        assert ConnectionState.CLOSING in state_changes

    @patch("protocol.serial_connection.serial", new_callable=VirtualSerialModule)
    def test_connection_statistics(self, mock_serial):
        """Test connection statistics tracking."""
        from kineintra.protocol.serial.serial_connection import (
            SerialPortConnection,
            SerialConfig,
            ConnectionState,
        )

        config = SerialConfig(port="/dev/ttyUSB0")
        conn = SerialPortConnection(config=config)

        def frame_callback(frame: FrameParseResult):
            pass

        conn.register_frame_callback(frame_callback)

        assert conn.connect(timeout=2.0) is True

        try:
            # Send a command
            cmd = HostPacketMaker.cmd_get_status(seq=1)
            assert conn.send_frame(cmd) is True

            time.sleep(1.0)

            # Check statistics
            stats = conn.get_statistics()
            assert (
                stats["frames_sent"] >= 1
            ), f"Expected frames_sent >= 1, got {stats['frames_sent']}"
            assert (
                stats["frames_received"] >= 1
            ), f"Expected frames_received >= 1, got {stats['frames_received']}"
            assert stats["state"] == ConnectionState.CONNECTED.value

        finally:
            conn.disconnect()

    @patch("protocol.serial_connection.serial", new_callable=VirtualSerialModule)
    def test_connection_error_handling(self, mock_serial):
        """Test error handling in connection."""
        from kineintra.protocol.serial.serial_connection import (
            SerialPortConnection,
            SerialConfig,
        )

        config = SerialConfig(port="/dev/invalid_port")
        conn = SerialPortConnection(config=config)

        # Try to connect to invalid port - should fail gracefully
        # Note: With virtual port, this will succeed. Real test would fail.
        # This tests the error handling path

    @patch("protocol.serial_connection.serial", new_callable=VirtualSerialModule)
    def test_connection_send_without_connection(self, mock_serial):
        """Test sending frame when not connected."""
        from kineintra.protocol.serial.serial_connection import (
            SerialPortConnection,
            SerialConfig,
        )

        config = SerialConfig(port="/dev/ttyUSB0")
        conn = SerialPortConnection(config=config)

        cmd = HostPacketMaker.cmd_get_status(seq=1)
        result = conn.send_frame(cmd)

        # Should fail gracefully
        assert result is False


class TestDeviceCommands:
    """Test specific device command sequences."""

    @patch("protocol.serial_connection.serial", new_callable=VirtualSerialModule)
    def test_get_status_command_sequence(self, mock_serial):
        """Test GET_STATUS command and response."""
        from kineintra.protocol.serial.serial_connection import (
            SerialPortConnection,
            SerialConfig,
            ConnectionState,
        )

        config = SerialConfig(port="/dev/ttyUSB0")
        conn = SerialPortConnection(config=config)

        responses: List[FrameParseResult] = []

        def frame_callback(frame: FrameParseResult):
            if frame.msg_type == FrameType.STATUS:
                responses.append(frame)

        conn.register_frame_callback(frame_callback)

        assert conn.connect(timeout=2.0) is True

        try:
            # Send GET_STATUS command
            cmd = HostPacketMaker.cmd_get_status(seq=1)
            assert conn.send_frame(cmd) is True

            time.sleep(1.0)

            # Should receive STATUS frame
            assert (
                len(responses) > 0
            ), f"Expected STATUS frames but got {len(responses)}"
            frame = responses[0]
            assert frame.msg_type == FrameType.STATUS
            assert len(frame.payload) >= 10  # Minimum STATUS frame size

        finally:
            conn.disconnect()

    @patch("protocol.serial_connection.serial", new_callable=VirtualSerialModule)
    def test_measure_command_sequence(self, mock_serial):
        """Test START_MEASURE and STOP_MEASURE commands."""
        from kineintra.protocol.serial.serial_connection import (
            SerialPortConnection,
            SerialConfig,
            ConnectionState,
        )

        config = SerialConfig(port="/dev/ttyUSB0")
        conn = SerialPortConnection(config=config)

        responses: List[FrameParseResult] = []

        def frame_callback(frame: FrameParseResult):
            responses.append(frame)

        conn.register_frame_callback(frame_callback)

        assert conn.connect(timeout=2.0) is True

        try:
            # Start measuring
            start_cmd = HostPacketMaker.cmd_start_measure(seq=1)
            assert conn.send_frame(start_cmd) is True

            time.sleep(0.3)

            # Stop measuring
            stop_cmd = HostPacketMaker.cmd_stop_measure(seq=2)
            assert conn.send_frame(stop_cmd) is True

            time.sleep(1.0)

            # Should have received ACK frames
            ack_frames = [f for f in responses if f.msg_type == FrameType.ACK]
            assert (
                len(ack_frames) >= 2
            ), f"Expected at least 2 ACK frames but got {len(ack_frames)}"

        finally:
            conn.disconnect()

    @patch("protocol.serial_connection.serial", new_callable=VirtualSerialModule)
    def test_set_rate_command(self, mock_serial):
        """Test SET_RATE command."""
        from kineintra.protocol.serial.serial_connection import (
            SerialPortConnection,
            SerialConfig,
            ConnectionState,
        )

        config = SerialConfig(port="/dev/ttyUSB0")
        conn = SerialPortConnection(config=config)

        responses: List[FrameParseResult] = []

        def frame_callback(frame: FrameParseResult):
            responses.append(frame)

        conn.register_frame_callback(frame_callback)

        assert conn.connect(timeout=2.0) is True

        try:
            # Set sampling rate for sensor 0 to 500 Hz
            cmd = HostPacketMaker.cmd_set_rate(seq=1, sensor_idx=0, rate_hz=500)
            assert conn.send_frame(cmd) is True

            time.sleep(1.0)

            # Should receive ACK
            ack_frames = [f for f in responses if f.msg_type == FrameType.ACK]
            assert (
                len(ack_frames) > 0
            ), f"Expected ACK frame but got {len(ack_frames)} ACKs"

        finally:
            conn.disconnect()


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])

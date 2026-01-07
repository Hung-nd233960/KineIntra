"""
Virtual Serial Port Emulator for Testing

Simulates a biomechanics device responding to protocol commands.
Used for unit testing without requiring actual hardware.
"""

import struct
import threading
import time
from queue import Queue
from typing import Optional, Callable
from kineintra.protocol.packets.config import SOF, PROTOCOL_VER, FrameType, CmdID
from kineintra.protocol.packets.packet_maker import HostPacketMaker
from kineintra.protocol.packets.packet_reader import ByteReader, FrameParseResult


class VirtualBiomechanicsDevice:
    """
    Simulates the biomechanics device MCU behavior.
    Processes commands and generates appropriate responses.
    """

    def __init__(self):
        """Initialize virtual device state."""
        self.state = 0x00  # IDLE
        self.n_sensors = 8
        self.active_map = 0xFF  # All 8 sensors active
        self.health_map = 0xFF  # All healthy
        self.samp_rate_map = [100] * 32  # Default 100 Hz for each sensor
        self.sequence_num = 0

    def generate_status_frame(self) -> bytes:
        """Generate a STATUS frame (Type 0x01) with current device state."""
        payload = struct.pack("<BB", self.state, self.n_sensors)
        payload += struct.pack("<I", self.active_map)
        payload += struct.pack("<I", self.health_map)

        # SampRateMap: 32 sensors * 2 bytes each = 64 bytes
        for i in range(32):
            payload += struct.pack("<H", self.samp_rate_map[i])

        return self._pack_frame(FrameType.STATUS, payload)

    def generate_data_frame(self, sensor_readings: bytes) -> bytes:
        """Generate a DATA frame (Type 0x02) with sensor readings."""
        payload = sensor_readings
        return self._pack_frame(FrameType.DATA, payload)

    def generate_ack_frame(self, cmd_id: int, seq: int, status: int = 0x00) -> bytes:
        """Generate an ACK frame (Type 0x04) acknowledging a command."""
        payload = struct.pack("<BBB", cmd_id, seq, status)
        return self._pack_frame(FrameType.ACK, payload)

    def generate_error_frame(self, error_code: int, error_msg: str = "") -> bytes:
        """Generate an ERROR frame (Type 0x05) reporting a device error."""
        payload = struct.pack("<B", error_code) + error_msg.encode("utf-8")[:255]
        return self._pack_frame(FrameType.ERROR, payload)

    def process_command(self, frame: FrameParseResult) -> bytes:
        """
        Process a received command and generate appropriate response.
        Returns the response frame.
        """
        if frame.msg_type != FrameType.COMMAND:
            return self.generate_error_frame(0x01, "Invalid frame type")

        if len(frame.payload) < 2:
            return self.generate_error_frame(0x02, "Payload too short")

        cmd_id = frame.payload[0]
        seq = frame.payload[1]

        # Handle different commands
        if cmd_id == CmdID.GET_STATUS:
            return self.generate_status_frame()

        elif cmd_id == CmdID.START_MEASURE:
            self.state = 0x01  # MEASURING
            return self.generate_ack_frame(cmd_id, seq)

        elif cmd_id == CmdID.STOP_MEASURE:
            self.state = 0x00  # IDLE
            return self.generate_ack_frame(cmd_id, seq)

        elif cmd_id == CmdID.SET_NSENSORS:
            if len(frame.payload) >= 3:
                self.n_sensors = frame.payload[2]
                return self.generate_ack_frame(cmd_id, seq)
            return self.generate_error_frame(0x03, "Invalid SET_NSENSORS payload")

        elif cmd_id == CmdID.SET_RATE:
            if len(frame.payload) >= 5:
                sensor_idx = frame.payload[2]
                rate_hz = struct.unpack("<H", frame.payload[3:5])[0]
                if sensor_idx < 32:
                    self.samp_rate_map[sensor_idx] = rate_hz
                    return self.generate_ack_frame(cmd_id, seq)
            return self.generate_error_frame(0x04, "Invalid SET_RATE payload")

        else:
            return self.generate_error_frame(0x05, "Unknown command ID")

    def _pack_frame(self, msg_type: int, payload: bytes) -> bytes:
        """Pack a frame with SOF, header, payload, and CRC."""
        from kineintra.protocol.packets.config import crc16_ccitt

        header_inner = struct.pack("<BBH", PROTOCOL_VER, msg_type, len(payload))
        crc_val = crc16_ccitt(header_inner + payload)
        return SOF + header_inner + payload + struct.pack("<H", crc_val)


class VirtualSerialPort:
    """
    Mock serial.Serial object that simulates a serial port connection
    to the virtual biomechanics device.
    """

    def __init__(self):
        """Initialize the virtual port."""
        self.is_open = True
        self.in_waiting = 0
        self.timeout = 1.0
        self.write_timeout = 1.0

        # Queues for bidirectional communication
        self._tx_queue = Queue()  # Data from host -> device
        self._rx_queue = Queue()  # Data from device -> host

        # Virtual device
        self._device = VirtualBiomechanicsDevice()
        self._device_thread: Optional[threading.Thread] = None
        self._running = True

        # Byte reader for parsing incoming frames
        self._byte_reader = ByteReader()

        # Start device emulation thread
        self._start_device_thread()

    def close(self) -> None:
        """Close the virtual port."""
        self.is_open = False
        self._running = False
        if self._device_thread and self._device_thread.is_alive():
            self._device_thread.join(timeout=2.0)

    def write(self, data: bytes) -> int:
        """
        Write data to the virtual port (host -> device).
        Returns number of bytes written.
        """
        if not self.is_open:
            raise OSError("Port is closed")

        self._tx_queue.put(bytes(data))
        return len(data)

    def read(self, size: int = 1) -> bytes:
        """
        Read data from the virtual port (device -> host).
        Returns up to 'size' bytes.
        """
        if not self.is_open:
            raise OSError("Port is closed")

        # Update in_waiting count
        self.in_waiting = self._rx_queue.qsize()

        if self.in_waiting == 0:
            return b""

        # Read available data
        data = bytearray()
        while len(data) < size and not self._rx_queue.empty():
            try:
                chunk = self._rx_queue.get_nowait()
                data.extend(chunk)
            except:
                break

        self.in_waiting = self._rx_queue.qsize()
        return bytes(data)

    def flush(self) -> None:
        """Flush the output buffer."""
        pass

    def _start_device_thread(self) -> None:
        """Start the device emulation thread."""
        self._device_thread = threading.Thread(target=self._device_worker, daemon=True)
        self._device_thread.start()

    def _device_worker(self) -> None:
        """
        Background worker that processes commands from the host
        and generates device responses.
        """
        last_status_time = time.time()

        while self._running and self.is_open:
            try:
                # Check for incoming host commands
                if not self._tx_queue.empty():
                    try:
                        cmd_data = self._tx_queue.get_nowait()
                        # Parse the command frame
                        frames = self._byte_reader.process_bytes(cmd_data)

                        for frame in frames:
                            if frame.crc_valid:
                                # Generate response
                                response = self._device.process_command(frame)
                                self._rx_queue.put(response)
                            else:
                                # Send error for bad CRC
                                error_frame = self._device.generate_error_frame(
                                    0x10, "CRC validation failed"
                                )
                                self._rx_queue.put(error_frame)
                    except Exception as e:
                        error_frame = self._device.generate_error_frame(
                            0x11, f"Command processing error: {str(e)}"
                        )
                        self._rx_queue.put(error_frame)

                # Periodically send unsolicited STATUS frame (every 500ms)
                current_time = time.time()
                if current_time - last_status_time > 0.5:
                    status_frame = self._device.generate_status_frame()
                    self._rx_queue.put(status_frame)
                    last_status_time = current_time

                time.sleep(0.01)

            except Exception as e:
                print(f"Device worker error: {e}")
                break


class VirtualSerialModule:
    """
    Mock for serial module that patches serial.Serial() calls.
    Used in testing to return VirtualSerialPort instead.
    """

    @staticmethod
    def Serial(*args, **kwargs):
        """Return a VirtualSerialPort instance."""
        return VirtualSerialPort()

    @staticmethod
    def SerialException(msg: str):
        """Mock SerialException."""
        return OSError(msg)


def mock_serial_module():
    """
    Patches the serial module to use virtual ports.
    Call this in test setup.
    """
    import sys
    import kineintra.protocol.serial.serial_connection as sc

    # Replace serial module with virtual implementation
    virtual_serial = VirtualSerialModule()
    sc.serial = virtual_serial  # type: ignore

    return virtual_serial

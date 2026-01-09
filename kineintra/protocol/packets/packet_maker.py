import struct
from typing import List
from kineintra.protocol.packets.config import (
    SOF,
    PROTOCOL_VER,
    FrameType,
    CmdID,
    crc16_ccitt,
)


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

    @staticmethod
    def cmd_stop_calibrate(seq: int) -> bytes:
        """Stop calibration command (from calibration protocol)."""
        return HostPacketMaker.make_command(CmdID.STOP_CALIBRATE, seq)

    @staticmethod
    def cmd_end_calibrate(seq: int) -> bytes:
        """End calibration command (from calibration protocol)."""
        return HostPacketMaker.make_command(CmdID.END_CALIBRATE, seq)


# --- 3. Device Packet Maker (Device -> Host) ---


class DevicePacketMaker:
    """
    Constructs binary frames to send FROM the Device TO the Host.
    Includes STATUS, DATA, ACK, and ERROR frames.
    """

    @staticmethod
    def _pack_frame(msg_type: int, payload: bytes) -> bytes:
        """
        Pack a frame with SOF, version, type, length, payload, and CRC.
        Args:
            msg_type: Frame type (from FrameType enum).
            payload: Payload bytes.
        Returns:
            Complete frame as bytes.
        """
        # Header: SOF (2) + Ver (1) + Type (1) + Len (2)
        # Note: Len is Little-Endian (<H)
        header_inner = struct.pack("<BBH", PROTOCOL_VER, msg_type, len(payload))

        # Calculate CRC over Ver | Type | Len | Payload
        crc_val = crc16_ccitt(header_inner + payload)

        # Final assembly: SOF + HeaderInner + Payload + CRC
        return SOF + header_inner + payload + struct.pack("<H", crc_val)

    # -- STATUS Frame (0x01) --
    @staticmethod
    def make_status(
        state: int,
        n_sensors: int,
        active_map: int,
        health_map: int,
        samp_rate_map: List[int],
        bits_per_smp_map: List[int],
        sensor_role_map: List[int],
        adc_flags: int = 0,
        reserved: int = 0,
    ) -> bytes:
        """
        Create a STATUS frame.

        Args:
            state: Device operational state (DeviceState enum).
            n_sensors: Number of active sensors (0-32).
            active_map: Bitmap of enabled sensors (32-bit).
            health_map: Bitmap of healthy sensors (32-bit).
            samp_rate_map: List of 32 uint16 values (sampling rates per sensor).
            bits_per_smp_map: List of 32 uint8 values (resolution per sensor).
            sensor_role_map: List of 32 uint8 values (sensor roles).
            adc_flags: ADC subsystem status flags (16-bit).
            reserved: Reserved field (16-bit).

        Returns:
            Complete STATUS frame as bytes.
        """
        # Validate list lengths
        if len(samp_rate_map) != 32:
            raise ValueError("samp_rate_map must contain exactly 32 elements")
        if len(bits_per_smp_map) != 32:
            raise ValueError("bits_per_smp_map must contain exactly 32 elements")
        if len(sensor_role_map) != 32:
            raise ValueError("sensor_role_map must contain exactly 32 elements")

        # Build payload according to STATUS format
        payload = struct.pack("<B", state)  # State (1 byte)
        payload += struct.pack("<B", n_sensors)  # NSensors (1 byte)
        payload += struct.pack("<I", active_map)  # ActiveMap (4 bytes)
        payload += struct.pack("<I", health_map)  # HealthMap (4 bytes)

        # SampRateMap (64 bytes = 32 * uint16)
        for rate in samp_rate_map:
            payload += struct.pack("<H", rate)

        # BitsPerSmpMap (32 bytes = 32 * uint8)
        for bits in bits_per_smp_map:
            payload += struct.pack("<B", bits)

        # SensorRoleMap (32 bytes = 32 * uint8)
        for role in sensor_role_map:
            payload += struct.pack("<B", role)

        # ADCFlags (2 bytes) + Reserved (2 bytes)
        payload += struct.pack("<HH", adc_flags, reserved)

        return DevicePacketMaker._pack_frame(FrameType.STATUS, payload)

    # -- DATA Frame (0x02) --
    @staticmethod
    def make_data(timestamp: int, samples: List[bytes]) -> bytes:
        """
        Create a DATA frame.

        Args:
            timestamp: Microseconds since device start (32-bit uint).
            samples: List of sample bytes in ascending sensor index order.
                     Each sample should be pre-encoded according to BitsPerSmp.

        Returns:
            Complete DATA frame as bytes.
        """
        # Payload: Timestamp (4 bytes) + Samples
        payload = struct.pack("<I", timestamp)
        for sample in samples:
            payload += sample

        return DevicePacketMaker._pack_frame(FrameType.DATA, payload)

    @staticmethod
    def make_data_simple(
        timestamp: int, sample_values: List[int], bits_per_sample: List[int]
    ) -> bytes:
        """
        Create a DATA frame with automatic sample encoding.

        Args:
            timestamp: Microseconds since device start (32-bit uint).
            sample_values: List of integer sample values (one per active sensor).
            bits_per_sample: List of bit resolutions for each sample.
                             Determines encoding size: 1-8→1 byte, 9-16→2 bytes, etc.

        Returns:
            Complete DATA frame as bytes.
        """
        if len(sample_values) != len(bits_per_sample):
            raise ValueError("sample_values and bits_per_sample must have same length")

        samples = []
        for value, bits in zip(sample_values, bits_per_sample):
            # Determine bytes per sample based on bits
            if bits <= 8:
                samples.append(struct.pack("<B", value & 0xFF))
            elif bits <= 16:
                samples.append(struct.pack("<H", value & 0xFFFF))
            elif bits <= 24:
                # 3 bytes for 24-bit samples
                samples.append(struct.pack("<I", value & 0xFFFFFF)[:3])
            else:  # bits <= 32
                samples.append(struct.pack("<I", value & 0xFFFFFFFF))

        return DevicePacketMaker.make_data(timestamp, samples)

    # -- ACK Frame (0x04) --
    @staticmethod
    def make_ack(cmd_id: int, seq: int, result: int) -> bytes:
        """
        Create an ACK frame.

        Args:
            cmd_id: Command ID being acknowledged.
            seq: Sequence number from the command.
            result: Result code (AckResult enum).

        Returns:
            Complete ACK frame as bytes.
        """
        payload = struct.pack("<BBB", cmd_id, seq, result)
        return DevicePacketMaker._pack_frame(FrameType.ACK, payload)

    # -- ERROR Frame (0x05) --
    @staticmethod
    def make_error(timestamp: int, err_code: int, aux_data: int = 0) -> bytes:
        """
        Create an ERROR frame.

        Args:
            timestamp: Microseconds since device start (32-bit uint).
            err_code: System error type (ErrorCode enum).
            aux_data: Context-dependent auxiliary data (16-bit).

        Returns:
            Complete ERROR frame as bytes.
        """
        payload = struct.pack("<IBH", timestamp, err_code, aux_data)
        return DevicePacketMaker._pack_frame(FrameType.ERROR, payload)


# --- 4. Unified Packet Maker (For Testing/Simulation) ---


class UnifiedPacketMaker:
    """
    Unified interface for creating any frame type from either host or device perspective.
    Useful for testing, simulation, or bidirectional communication scenarios.
    """

    # Host-side methods (delegate to HostPacketMaker)
    @staticmethod
    def command(cmd_id: int, seq: int, args: bytes = b"") -> bytes:
        """Create a COMMAND frame (host perspective)."""
        return HostPacketMaker.make_command(cmd_id, seq, args)

    @staticmethod
    def cmd_get_status(seq: int) -> bytes:
        """GET_STATUS command."""
        return HostPacketMaker.cmd_get_status(seq)

    @staticmethod
    def cmd_start_measure(seq: int) -> bytes:
        """START_MEASURE command."""
        return HostPacketMaker.cmd_start_measure(seq)

    @staticmethod
    def cmd_stop_measure(seq: int) -> bytes:
        """STOP_MEASURE command."""
        return HostPacketMaker.cmd_stop_measure(seq)

    @staticmethod
    def cmd_set_nsensors(seq: int, n_sensors: int) -> bytes:
        """SET_NSENSORS command."""
        return HostPacketMaker.cmd_set_nsensors(seq, n_sensors)

    @staticmethod
    def cmd_set_rate(seq: int, sensor_idx: int, rate_hz: int) -> bytes:
        """SET_RATE command."""
        return HostPacketMaker.cmd_set_rate(seq, sensor_idx, rate_hz)

    @staticmethod
    def cmd_set_bits(seq: int, sensor_idx: int, bits_per_smp: int) -> bytes:
        """SET_BITS command."""
        return HostPacketMaker.cmd_set_bits(seq, sensor_idx, bits_per_smp)

    @staticmethod
    def cmd_set_active_map(seq: int, active_map: int) -> bytes:
        """SET_ACTIVEMAP command."""
        return HostPacketMaker.cmd_set_active_map(seq, active_map)

    @staticmethod
    def cmd_calibrate(seq: int, mode: int) -> bytes:
        """CALIBRATE command."""
        return HostPacketMaker.cmd_calibrate(seq, mode)

    @staticmethod
    def cmd_stop_calibrate(seq: int) -> bytes:
        """STOP_CALIBRATE command."""
        return HostPacketMaker.cmd_stop_calibrate(seq)

    @staticmethod
    def cmd_end_calibrate(seq: int) -> bytes:
        """END_CALIBRATE command."""
        return HostPacketMaker.cmd_end_calibrate(seq)

    # Device-side methods (delegate to DevicePacketMaker)
    @staticmethod
    def status(
        state: int,
        n_sensors: int,
        active_map: int,
        health_map: int,
        samp_rate_map: List[int],
        bits_per_smp_map: List[int],
        sensor_role_map: List[int],
        adc_flags: int = 0,
        reserved: int = 0,
    ) -> bytes:
        """Create a STATUS frame (device perspective)."""
        return DevicePacketMaker.make_status(
            state,
            n_sensors,
            active_map,
            health_map,
            samp_rate_map,
            bits_per_smp_map,
            sensor_role_map,
            adc_flags,
            reserved,
        )

    @staticmethod
    def data(timestamp: int, samples: List[bytes]) -> bytes:
        """Create a DATA frame (device perspective)."""
        return DevicePacketMaker.make_data(timestamp, samples)

    @staticmethod
    def data_simple(
        timestamp: int, sample_values: List[int], bits_per_sample: List[int]
    ) -> bytes:
        """Create a DATA frame with automatic encoding (device perspective)."""
        return DevicePacketMaker.make_data_simple(
            timestamp, sample_values, bits_per_sample
        )

    @staticmethod
    def ack(cmd_id: int, seq: int, result: int) -> bytes:
        """Create an ACK frame (device perspective)."""
        return DevicePacketMaker.make_ack(cmd_id, seq, result)

    @staticmethod
    def error(timestamp: int, err_code: int, aux_data: int = 0) -> bytes:
        """Create an ERROR frame (device perspective)."""
        return DevicePacketMaker.make_error(timestamp, err_code, aux_data)

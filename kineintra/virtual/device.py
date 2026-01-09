"""
Virtual Device Application Layer

High-level device logic: state management, command processing, response generation.
This layer simulates the MCU firmware behavior.
"""

import struct
import logging
from typing import List, Optional

from kineintra.protocol.packets.config import (
    PROTOCOL_VER,
    FrameType,
    CmdID,
    AckResult,
    crc16_ccitt,
    SOF,
)
from kineintra.protocol.packets.packet_reader import FrameParseResult
from kineintra.virtual.signal_generator import SignalGenerator, RandomSignalGenerator


class VirtualBiomechanicsDevice:
    """
    Simulates the biomechanics device MCU behavior.

    This is a one-to-one replication of the real device firmware:
    - Maintains device state (IDLE, MEASURING, CALIBRATING)
    - Processes commands and generates appropriate responses
    - Streams DATA frames during measurement
    - Logs all activities for monitoring
    """

    # Device states (matching firmware)
    STATE_IDLE = 0x00
    STATE_MEASURING = 0x01
    STATE_CALIBRATING = 0x02

    def __init__(
        self,
        signal_generator: Optional[SignalGenerator] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize virtual device state.

        Args:
            signal_generator: Custom signal generator (default: random)
            logger: Logger for monitoring device activity
        """
        self._logger = logger or self._setup_logger()
        self.signal_generator = signal_generator or RandomSignalGenerator()

        # Device configuration state
        self.state = self.STATE_IDLE
        self.n_sensors = 8
        self.active_map = 0xFF  # first 8 sensors active
        self.health_map = 0xFF  # All healthy
        self.samp_rate_map = [100] * 32  # Default 100 Hz
        self.bits_per_smp_map = [12] * 32  # Default 12-bit
        self.sensor_role_map = [1] * 32  # Default role FSR
        self.adc_flags = 0

        # Runtime state
        self.timestamp_counter = 0
        self.data_frame_counter = 0

        self._logger.info("Virtual device initialized")

    def _setup_logger(self) -> logging.Logger:
        """Setup default logger with timestamps."""
        logger = logging.getLogger("VirtualDevice")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(asctime)s] %(levelname)s: %(message)s", datefmt="%H:%M:%S"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    def get_active_sensor_indices(self) -> List[int]:
        """Get list of active sensor indices based on active_map."""
        return [i for i in range(32) if (self.active_map >> i) & 1]

    def generate_status_frame(self) -> bytes:
        """
        Generate a STATUS frame (Type 0x01) with full 142-byte payload.

        STATUS frame structure:
        - State (1 byte)
        - NSensors (1 byte)
        - ActiveMap (4 bytes)
        - HealthMap (4 bytes)
        - SampRateMap (64 bytes = 32 * uint16)
        - BitsPerSmpMap (32 bytes)
        - SensorRoleMap (32 bytes)
        - ADCFlags (2 bytes) + Reserved (2 bytes)
        Total: 142 bytes
        """
        payload = struct.pack("<BB", self.state, self.n_sensors)
        payload += struct.pack("<I", self.active_map)
        payload += struct.pack("<I", self.health_map)

        # SampRateMap: 32 * uint16
        for rate in self.samp_rate_map:
            payload += struct.pack("<H", rate)

        # BitsPerSmpMap: 32 * uint8
        for bits in self.bits_per_smp_map:
            payload += struct.pack("<B", bits)

        # SensorRoleMap: 32 * uint8
        for role in self.sensor_role_map:
            payload += struct.pack("<B", role)

        # ADCFlags (2) + Reserved (2)
        payload += struct.pack("<HH", self.adc_flags, 0)

        self._logger.debug("Generated STATUS frame")
        return self._pack_frame(FrameType.STATUS, payload)

    def generate_data_frame(self) -> bytes:
        """
        Generate a DATA frame with timestamp and sensor samples.

        Uses the configured signal_generator to produce sample values.
        """
        active_indices = self.get_active_sensor_indices()
        n_active = len(active_indices)

        # Get bits configuration for active sensors
        active_bits = [self.bits_per_smp_map[i] for i in active_indices]

        # Generate samples using signal generator
        samples = self.signal_generator.generate_samples(n_active, active_bits)

        # Build payload: timestamp (4 bytes) + encoded samples
        payload = struct.pack("<I", self.timestamp_counter)

        for idx, value in enumerate(samples):
            sensor_idx = active_indices[idx]
            bits = self.bits_per_smp_map[sensor_idx]

            if bits <= 8:
                payload += struct.pack("<B", value & 0xFF)
            elif bits <= 16:
                payload += struct.pack("<H", value & 0xFFFF)
            elif bits <= 24:
                payload += struct.pack("<I", value & 0xFFFFFF)[:3]
            else:
                payload += struct.pack("<I", value & 0xFFFFFFFF)

        self.timestamp_counter += 1
        self.data_frame_counter += 1

        self._logger.debug(
            f"Generated DATA frame #{self.data_frame_counter} "
            f"(ts={self.timestamp_counter}, samples={n_active})"
        )
        return self._pack_frame(FrameType.DATA, payload)

    def generate_ack_frame(
        self, cmd_id: int, seq: int, status: int = AckResult.OK
    ) -> bytes:
        """
        Generate an ACK frame acknowledging a command.

        ACK payload: CmdID (1 byte) + Seq (1 byte) + Result (1 byte)
        """
        payload = struct.pack("<BBB", cmd_id, seq, status)

        result_str = "OK" if status == AckResult.OK else f"ERROR({status})"
        self._logger.info(
            f"Sending ACK: cmd={cmd_id:02X} seq={seq} result={result_str}"
        )

        return self._pack_frame(FrameType.ACK, payload)

    def generate_error_frame(self, error_code: int, error_msg: str = "") -> bytes:
        """
        Generate an ERROR frame reporting a device error.

        ERROR payload: ErrorCode (1 byte) + AuxData (variable)
        """
        payload = struct.pack("<B", error_code) + error_msg.encode("utf-8")[:255]

        self._logger.warning(f"Sending ERROR: code={error_code:02X} msg={error_msg}")

        return self._pack_frame(FrameType.ERROR, payload)

    def process_command(self, frame: FrameParseResult) -> bytes:
        """
        Process a received command frame and generate appropriate response(s).

        Returns:
            Concatenated response frames (ACK + STATUS for most commands)
        """
        if frame.msg_type != FrameType.COMMAND:
            self._logger.error(f"Received non-COMMAND frame: type={frame.msg_type:02X}")
            return self.generate_error_frame(0x01, "Invalid frame type")

        if len(frame.payload) < 2:
            self._logger.error("COMMAND payload too short")
            return self.generate_error_frame(0x02, "Payload too short")

        cmd_id = frame.payload[0]
        seq = frame.payload[1]

        cmd_name = self._get_command_name(cmd_id)
        self._logger.info(
            "Received COMMAND: %s (id=%02X seq=%d)", cmd_name, cmd_id, seq
        )

        responses = []

        def ack(ok=True, code=AckResult.OK):
            responses.append(self.generate_ack_frame(cmd_id, seq, code if ok else code))

        def push_status():
            responses.append(self.generate_status_frame())

        # Handle different commands
        try:
            if cmd_id == CmdID.GET_STATUS:
                ack()
                push_status()

            elif cmd_id == CmdID.START_MEASURE:
                self._logger.info("Starting measurement mode")
                self.state = self.STATE_MEASURING
                self.timestamp_counter = 0
                self.data_frame_counter = 0
                ack()
                push_status()

            elif cmd_id == CmdID.STOP_MEASURE:
                self._logger.info(
                    "Stopping measurement mode (sent %d frames)",
                    self.data_frame_counter,
                )
                self.state = self.STATE_IDLE
                ack()
                push_status()

            elif cmd_id == CmdID.SET_NSENSORS:
                if len(frame.payload) >= 3:
                    self.n_sensors = frame.payload[2]
                    self._logger.info("Set n_sensors = %d", self.n_sensors)
                    ack()
                    push_status()
                else:
                    return self.generate_error_frame(
                        0x03, "Invalid SET_NSENSORS payload"
                    )

            elif cmd_id == CmdID.SET_RATE:
                if len(frame.payload) >= 5:
                    sensor_idx = frame.payload[2]
                    rate_hz = struct.unpack("<H", frame.payload[3:5])[0]
                    if sensor_idx < 32:
                        self.samp_rate_map[sensor_idx] = rate_hz
                        self._logger.info(
                            "Set sensor[%d] rate = %d Hz", sensor_idx, rate_hz
                        )
                        ack()
                        push_status()
                    else:
                        return self.generate_error_frame(
                            0x04, "Sensor index out of range"
                        )
                else:
                    return self.generate_error_frame(0x04, "Invalid SET_RATE payload")

            elif cmd_id == CmdID.SET_BITS:
                if len(frame.payload) >= 4:
                    sensor_idx = frame.payload[2]
                    bits = frame.payload[3]
                    if sensor_idx < 32:
                        self.bits_per_smp_map[sensor_idx] = bits
                        self._logger.info("Set sensor[%d] bits = %d", sensor_idx, bits)
                        ack()
                        push_status()
                    else:
                        return self.generate_error_frame(
                            0x06, "Sensor index out of range"
                        )
                else:
                    return self.generate_error_frame(0x06, "Invalid SET_BITS payload")

            elif cmd_id == CmdID.SET_ACTIVEMAP:
                if len(frame.payload) >= 6:
                    self.active_map = struct.unpack("<I", frame.payload[2:6])[0]
                    self.n_sensors = bin(self.active_map).count("1")
                    self._logger.info(
                        "Set active_map = 0x%08X (%d sensors)",
                        self.active_map,
                        self.n_sensors,
                    )
                    ack()
                    push_status()
                else:
                    return self.generate_error_frame(
                        0x07, "Invalid SET_ACTIVEMAP payload"
                    )

            elif cmd_id == CmdID.CALIBRATE:
                self._logger.info("Starting calibration mode")
                self.state = self.STATE_CALIBRATING
                ack()
                push_status()

            elif cmd_id == CmdID.STOP_CALIBRATE:
                self._logger.info("Stopping calibration (returning to IDLE)")
                self.state = self.STATE_IDLE
                ack()
                push_status()

            elif cmd_id == CmdID.END_CALIBRATE:
                self._logger.info("Ending calibration (returning to IDLE)")
                self.state = self.STATE_IDLE
                ack()
                push_status()

            else:
                self._logger.warning("Unknown command ID: %02X", cmd_id)
                return self.generate_error_frame(0x05, "Unknown command ID")

        except (ValueError, struct.error, IndexError) as e:
            self._logger.exception("Error processing command")
            return self.generate_error_frame(0xFF, f"Processing error: {str(e)}")

        return b"".join(responses)

    def _pack_frame(self, msg_type: int, payload: bytes) -> bytes:
        """Pack a frame with SOF, header, payload, and CRC."""
        header_inner = struct.pack("<BBH", PROTOCOL_VER, msg_type, len(payload))
        crc_val = crc16_ccitt(header_inner + payload)
        return SOF + header_inner + payload + struct.pack("<H", crc_val)

    def _get_command_name(self, cmd_id: int) -> str:
        """Get human-readable command name."""
        cmd_names = {
            CmdID.GET_STATUS: "GET_STATUS",
            CmdID.START_MEASURE: "START_MEASURE",
            CmdID.STOP_MEASURE: "STOP_MEASURE",
            CmdID.SET_NSENSORS: "SET_NSENSORS",
            CmdID.SET_RATE: "SET_RATE",
            CmdID.SET_BITS: "SET_BITS",
            CmdID.SET_ACTIVEMAP: "SET_ACTIVEMAP",
            CmdID.CALIBRATE: "CALIBRATE",
            CmdID.STOP_CALIBRATE: "STOP_CALIBRATE",
            CmdID.END_CALIBRATE: "END_CALIBRATE",
        }
        return cmd_names.get(CmdID(cmd_id), f"UNKNOWN_{cmd_id:02X}")

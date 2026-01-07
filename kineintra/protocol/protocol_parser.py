"""
Protocol Parser Module

Parses binary frames from the device into structured, type-safe payload objects.
Handles STATUS, DATA, ACK, and ERROR frames.
"""

from dataclasses import dataclass
from typing import Dict, Union, Optional
import struct

from kineintra.protocol.config import FrameType
from kineintra.protocol.packet_reader import FrameParseResult


@dataclass
class StatusPayload:
    """Represents a decoded STATUS frame payload."""

    state: int
    n_sensors: int
    active_map: int
    health_map: int
    samp_rate_map: list[int]  # 32 uint16 values
    bits_per_smp_map: list[int]  # 32 uint8 values
    sensor_role_map: list[int]  # 32 uint8 values
    adc_flags: int
    reserved: int

    def is_measuring(self) -> bool:
        """Returns True if device is currently measuring."""
        return self.state == 0x01

    def is_idle(self) -> bool:
        """Returns True if device is idle."""
        return self.state == 0x00

    def is_calibrating(self) -> bool:
        """Returns True if device is calibrating."""
        return self.state == 0x02

    def is_error(self) -> bool:
        """Returns True if device is in error state."""
        return self.state == 0x03

    def get_active_sensors(self) -> list[int]:
        """Returns list of active sensor indices."""
        return [i for i in range(32) if (self.active_map >> i) & 1]

    def get_healthy_sensors(self) -> list[int]:
        """Returns list of healthy sensor indices."""
        return [i for i in range(32) if (self.health_map >> i) & 1]


@dataclass
class DataPayload:
    """Represents a decoded DATA frame payload."""

    timestamp: int
    samples: Dict[int, int]  # sensor_index -> raw_value

    def get_sample(self, sensor_idx: int) -> Optional[int]:
        """Get sample value for a specific sensor, or None if not present."""
        return self.samples.get(sensor_idx)


@dataclass
class AckPayload:
    """Represents a decoded ACK frame payload."""

    cmd_id: int
    seq: int
    result: int

    def is_success(self) -> bool:
        """Returns True if ACK result is OK."""
        return self.result == 0x00

    def get_result_name(self) -> str:
        """Returns human-readable result code name."""
        result_names = {
            0x00: "OK",
            0x01: "INVALID_COMMAND",
            0x02: "INVALID_ARGUMENT",
            0x03: "BUSY",
            0x04: "FAILED",
            0x05: "NOT_ALLOWED",
        }
        return result_names.get(self.result, f"UNKNOWN(0x{self.result:02X})")


@dataclass
class ErrorPayload:
    """Represents a decoded ERROR frame payload."""

    timestamp: int
    error_code: int
    aux_data: int

    def get_error_name(self) -> str:
        """Returns human-readable error code name."""
        error_names = {
            0x01: "ADC_OVERRUN",
            0x02: "SENSOR_FAULT",
            0x03: "FIFO_CRITICAL",
            0x04: "LOW_VOLTAGE",
            0x05: "I2C_ERROR",
            0xFE: "VENDOR_SPECIFIC",
        }
        return error_names.get(self.error_code, f"UNKNOWN(0x{self.error_code:02X})")


# Union type for all possible parsed payloads
ParsedPayload = Union[StatusPayload, DataPayload, AckPayload, ErrorPayload]


class ProtocolParser:
    """
    Parses binary frames into structured payload objects.
    Maintains state for decoding DATA frames based on last STATUS.
    """

    def __init__(self):
        """Initialize parser with default state."""
        self.last_active_map: int = 0
        self.last_bits_map: list[int] = [0] * 32
        self.parse_errors: list[str] = []

    def parse_frame(
        self, frame: FrameParseResult
    ) -> tuple[str, Optional[ParsedPayload]]:
        """
        Parse a FrameParseResult into a structured payload object.

        Args:
            frame: FrameParseResult from ByteReader.

        Returns:
            Tuple of (frame_type_name: str, parsed_payload: ParsedPayload or None)
            Returns (type_name, None) if payload parsing fails.
        """
        frame_type_name = FrameType(frame.msg_type).name
        payload: Optional[ParsedPayload] = None

        try:
            if frame.msg_type == FrameType.STATUS:
                payload = self._parse_status(frame.payload)
            elif frame.msg_type == FrameType.DATA:
                payload = self._parse_data(frame.payload)
            elif frame.msg_type == FrameType.ACK:
                payload = self._parse_ack(frame.payload)
            elif frame.msg_type == FrameType.ERROR:
                payload = self._parse_error(frame.payload)
            else:
                error_msg = f"Unknown frame type: 0x{frame.msg_type:02X}"
                self.parse_errors.append(error_msg)
                return frame_type_name, None

            return frame_type_name, payload

        except (ValueError, struct.error):
            error_msg = f"Error parsing {frame_type_name}: invalid payload"
            self.parse_errors.append(error_msg)
            return frame_type_name, None

    def _parse_status(self, payload: bytes) -> StatusPayload:
        """Parse STATUS frame payload (144 bytes)."""
        if len(payload) < 144:
            raise ValueError(
                f"STATUS payload too short: {len(payload)} bytes, expected 144"
            )

        # Unpack fixed fields (offset 0-10)
        state, n_sensors, active_map, health_map = struct.unpack("<BBII", payload[0:10])

        # Parse SampRateMap (offset 10-74, 64 bytes = 32 * uint16)
        samp_rate_map = list(struct.unpack("<" + "H" * 32, payload[10:74]))

        # Parse BitsPerSmpMap (offset 74-106, 32 bytes = 32 * uint8)
        bits_per_smp_map = list(struct.unpack("<" + "B" * 32, payload[74:106]))

        # Parse SensorRoleMap (offset 106-138, 32 bytes = 32 * uint8)
        sensor_role_map = list(struct.unpack("<" + "B" * 32, payload[106:138]))

        # Parse ADCFlags and Reserved (offset 138-144)
        adc_flags, reserved = struct.unpack("<HH", payload[138:144])

        # Update internal state for future DATA parsing
        self.last_active_map = active_map
        self.last_bits_map = bits_per_smp_map

        return StatusPayload(
            state=state,
            n_sensors=n_sensors,
            active_map=active_map,
            health_map=health_map,
            samp_rate_map=samp_rate_map,
            bits_per_smp_map=bits_per_smp_map,
            sensor_role_map=sensor_role_map,
            adc_flags=adc_flags,
            reserved=reserved,
        )

    def _parse_data(self, payload: bytes) -> DataPayload:
        """Parse DATA frame payload based on last STATUS configuration."""
        if len(payload) < 4:
            raise ValueError(f"DATA payload too short: {len(payload)} bytes, minimum 4")

        timestamp = struct.unpack("<I", payload[0:4])[0]
        samples: Dict[int, int] = {}
        offset = 4

        # Iterate over all 32 possible sensors
        for sensor_idx in range(32):
            # Check if sensor is active
            if (self.last_active_map >> sensor_idx) & 1:
                # Determine byte width based on resolution
                resolution = self.last_bits_map[sensor_idx]
                byte_width = self._get_byte_width(resolution)

                # Safety check
                if offset + byte_width > len(payload):
                    raise ValueError(
                        f"Payload too short for sensor {sensor_idx}: "
                        f"need {byte_width} bytes, only {len(payload) - offset} available"
                    )

                raw_bytes = payload[offset : offset + byte_width]

                # Decode Little-Endian based on width
                if byte_width == 1:
                    val = raw_bytes[0]
                elif byte_width == 2:
                    val = struct.unpack("<H", raw_bytes)[0]
                elif byte_width == 3:
                    # Manual 3-byte little-endian decode
                    val = raw_bytes[0] | (raw_bytes[1] << 8) | (raw_bytes[2] << 16)
                elif byte_width == 4:
                    val = struct.unpack("<I", raw_bytes)[0]
                else:
                    raise ValueError(f"Unexpected byte width: {byte_width}")

                samples[sensor_idx] = val
                offset += byte_width

        return DataPayload(timestamp=timestamp, samples=samples)

    def _parse_ack(self, payload: bytes) -> AckPayload:
        """Parse ACK frame payload (3 bytes)."""
        if len(payload) < 3:
            raise ValueError(f"ACK payload too short: {len(payload)} bytes, expected 3")

        cmd_id, seq, result = struct.unpack("<BBB", payload[0:3])
        return AckPayload(cmd_id=cmd_id, seq=seq, result=result)

    def _parse_error(self, payload: bytes) -> ErrorPayload:
        """Parse ERROR frame payload (7 bytes)."""
        if len(payload) < 7:
            raise ValueError(
                f"ERROR payload too short: {len(payload)} bytes, expected 7"
            )

        timestamp, error_code, aux_data = struct.unpack("<IBH", payload[0:7])
        return ErrorPayload(
            timestamp=timestamp, error_code=error_code, aux_data=aux_data
        )

    @staticmethod
    def _get_byte_width(resolution: int) -> int:
        """
        Determine the byte width for a given bit resolution.

        Args:
            resolution: Bits per sample (0-255).

        Returns:
            Byte width (1, 2, 3, or 4).
        """
        if resolution <= 8:
            return 1
        elif resolution <= 16:
            return 2
        elif resolution <= 24:
            return 3
        else:  # 25-32 or more
            return 4

    def get_errors(self) -> list[str]:
        """Get list of all parsing errors that have occurred."""
        return self.parse_errors.copy()

    def clear_errors(self) -> None:
        """Clear the parsing error log."""
        self.parse_errors.clear()

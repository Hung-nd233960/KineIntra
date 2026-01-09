import logging
from typing import List, TypeVar
from dataclasses import dataclass
import struct
from kineintra.protocol.packets.config import (
    SOF,
    crc16_ccitt,
    MAX_PAYLOAD_SIZE,
    FrameType,
)


@dataclass
class FrameParseResult:
    ver: int
    msg_type: int
    length: int
    payload: bytes
    calculated_crc: int
    received_crc: int
    raw_frame: bytes

    @property
    def crc_valid(self) -> bool:
        return self.calculated_crc == self.received_crc

    @property
    def type_enum(self) -> FrameType:
        """Frame type as FrameType enum if known, else raises ValueError."""
        return FrameType(self.msg_type)

    @property
    def type_name(self) -> str:
        """Human-friendly frame type name; falls back to hex value."""
        try:
            return self.type_enum.name
        except ValueError:
            return f"UNKNOWN_0x{self.msg_type:02X}"


T = TypeVar("T")


class ByteReader:
    """
    Parses incoming byte streams and yields validated frames.
    Direction-agnostic: works for both Device→Host and Host→Device streams.
    Handles stream fragmentation and CRC validation.
    """

    def __init__(self):
        self.buffer = bytearray()
        self.crc_errors = 0
        # Storage for configuration needed to parse DATA frames
        # These would ideally be updated whenever a STATUS frame is received

    def process_bytes(
        self, new_data: bytes, raw_return=False
    ) -> List[FrameParseResult]:
        """
        Ingest bytes and return a list of decoded frames (objects).
        Each frame is structurally valid (length & SOF checked) and CRC verified.
        """
        self.buffer.extend(new_data)
        frames: List[FrameParseResult] = []

        while True:
            # 1. Search for SOF
            sof_index = self.buffer.find(SOF)
            if sof_index == -1:
                # Keep the last byte just in case it's the first half of SOF
                if len(self.buffer) > 0:
                    self.buffer = self.buffer[-1:]
                return frames

            # Discard garbage before SOF
            if sof_index > 0:
                self.buffer = self.buffer[sof_index:]

            # 2. Check if we have enough for a Header (SOF + Ver + Type + Len) = 6 bytes
            if len(self.buffer) < 6:
                return frames

            # Unpack Header
            # SOF(2) is at 0:2
            ver, msg_type, length = struct.unpack("<BBH", self.buffer[2:6])

            if length > MAX_PAYLOAD_SIZE:
                # Invalid length, discard SOF and continue searching
                self.buffer = self.buffer[2:]
                continue

            # 3. Check full frame size availability (payload + CRC)
            total_frame_size = 6 + length + 2  # Header + Payload + CRC
            if len(self.buffer) < total_frame_size:
                # Not enough bytes yet; wait for more data
                return frames

            # 4. Extract Frame
            frame_data = self.buffer[:total_frame_size]
            payload = self.buffer[6 : 6 + length]
            crc_slice = self.buffer[6 + length : 6 + length + 2]
            if len(crc_slice) < 2:
                # Safety: should not happen due to total_frame_size check, but guard anyway
                # It poses that total_frame_size can be misleading > Issue kept for now
                return frames
            received_crc = struct.unpack("<H", crc_slice)[0]

            # Remove frame from buffer
            self.buffer = self.buffer[total_frame_size:]

            # 5. Validate CRC
            # CRC is calculated over Ver | Type | Len | Payload

            crc_check_data = frame_data[2 : 6 + length]
            calculated_crc = crc16_ccitt(crc_check_data)
            if calculated_crc != received_crc:
                self.crc_errors += 1
                logging.debug(
                    "CRC mismatch: calculated 0x%04X != received 0x%04X",
                    calculated_crc,
                    received_crc,
                )
                # CRC failed, discard this frame and continue
                continue

            frames.append(
                FrameParseResult(
                    ver=ver,
                    msg_type=msg_type,
                    length=length,
                    payload=payload,
                    calculated_crc=calculated_crc,
                    received_crc=received_crc,
                    raw_frame=frame_data if raw_return else b"",
                )
            )

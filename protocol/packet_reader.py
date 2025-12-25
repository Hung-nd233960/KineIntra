from typing import List, Dict
import struct
from protocol.config import SOF, FrameType, crc16_ccitt


class PacketReader:
    """
    Parses incoming bytes stream from the Device.
    Handles stream fragmentation and CRC validation.
    """

    def __init__(self):
        self.buffer = bytearray()
        # Storage for configuration needed to parse DATA frames
        # These would ideally be updated whenever a STATUS frame is received
        self.last_active_map = 0
        self.last_bits_map = [16] * 32  # Default to 16 bits if unknown

    def process_bytes(self, new_data: bytes) -> List[Dict]:
        """
        Ingest bytes and return a list of decoded frames (dicts).
        """
        self.buffer.extend(new_data)
        frames = []

        while True:
            # 1. Search for SOF
            sof_index = self.buffer.find(SOF)
            if sof_index == -1:
                # Keep the last byte just in case it's the first half of SOF
                if len(self.buffer) > 0:
                    self.buffer = self.buffer[-1:]
                break

            # Discard garbage before SOF
            if sof_index > 0:
                self.buffer = self.buffer[sof_index:]

            # 2. Check if we have enough for a Header (SOF + Ver + Type + Len) = 6 bytes
            if len(self.buffer) < 6:
                break

            # Unpack Header
            # SOF(2) is at 0:2
            ver, msg_type, length = struct.unpack("<BBH", self.buffer[2:6])

            # 3. Check full frame size availability
            total_frame_size = 6 + length + 2  # Header + Payload + CRC
            if len(self.buffer) < total_frame_size:
                break  # Wait for more data

            # 4. Extract Frame
            frame_data = self.buffer[:total_frame_size]
            payload = self.buffer[6 : 6 + length]
            received_crc = struct.unpack("<H", self.buffer[6 + length :])[0]

            # Remove frame from buffer
            self.buffer = self.buffer[total_frame_size:]

            # 5. Validate CRC
            # CRC is calculated over Ver | Type | Len | Payload
            crc_check_data = frame_data[2 : 6 + length]
            calculated_crc = crc16_ccitt(crc_check_data)

            if calculated_crc == received_crc:
                decoded = self._decode_payload(msg_type, payload)
                if decoded:
                    frames.append(decoded)
            else:
                print(
                    f"CRC Error: Calc {calculated_crc:04X} vs Recv {received_crc:04X}"
                )

        return frames

    def _decode_payload(self, msg_type: int, payload: bytes) -> dict:
        data = {"type": FrameType(msg_type).name, "raw_payload": payload}

        if msg_type == FrameType.STATUS:
            return self._parse_status(payload, data)
        if msg_type == FrameType.DATA:
            return self._parse_data(payload, data)
        if msg_type == FrameType.ACK:
            return self._parse_ack(payload, data)
        if msg_type == FrameType.ERROR:
            return self._parse_error(payload, data)

        return data

    def _parse_ack(self, pl: bytes, data: dict) -> dict:
        if len(pl) < 3:
            return data
        cid, seq, res = struct.unpack("<BBB", pl[:3])
        data.update({"cmd_id": cid, "seq": seq, "result": res})
        return data

    def _parse_error(self, pl: bytes, data: dict) -> dict:
        if len(pl) < 7:
            return data
        ts, code, aux = struct.unpack("<IBH", pl[:7])
        data.update({"timestamp": ts, "error_code": code, "aux_data": aux})
        return data

    def _parse_status(self, pl: bytes, data: dict) -> dict:
        if len(pl) < 144:
            return data

        # Unpack fixed fields
        state, n_sensors, active_map, health_map = struct.unpack("<BBII", pl[0:10])

        # Parse SampRateMap (64 bytes = 32 * uint16)
        samp_rates = list(struct.unpack("<" + "H" * 32, pl[10:74]))

        # Parse BitsPerSmpMap (32 bytes = 32 * uint8)
        bits_map = list(struct.unpack("<" + "B" * 32, pl[74:106]))

        # Update internal state for future DATA parsing
        self.last_active_map = active_map
        self.last_bits_map = bits_map

        data.update(
            {
                "state": state,
                "n_sensors": n_sensors,
                "active_map": f"{active_map:032b}",
                "health_map": f"{health_map:032b}",
                "rates": samp_rates,
                "resolutions": bits_map,
            }
        )
        return data

    def _parse_data(self, pl: bytes, data: dict) -> dict:
        """
        Parses complex DATA frame based on ActiveMap and BitsPerSmp.
        """
        if len(pl) < 4:
            return data
        timestamp = struct.unpack("<I", pl[0:4])[0]

        samples = {}
        offset = 4

        # Iterate over all 32 possible sensors
        for i in range(32):
            # Check if sensor i is active
            if (self.last_active_map >> i) & 1:
                # Determine byte width based on resolution
                resolution = self.last_bits_map[i]
                byte_width = 1
                if 9 <= resolution <= 16:
                    byte_width = 2
                elif 17 <= resolution <= 24:
                    byte_width = 3
                elif 25 <= resolution <= 32:
                    byte_width = 4

                # Safety check
                if offset + byte_width > len(pl):
                    data["parse_error"] = "Payload too short"
                    break

                raw_bytes = pl[offset : offset + byte_width]

                # Decode Little-Endian based on width
                val = 0
                if byte_width == 1:
                    val = raw_bytes[0]
                elif byte_width == 2:
                    val = struct.unpack("<H", raw_bytes)[0]
                elif byte_width == 3:
                    # Pad with 0 at the end for 4-byte unpack or manual shift
                    val = raw_bytes[0] | (raw_bytes[1] << 8) | (raw_bytes[2] << 16)
                elif byte_width == 4:
                    val = struct.unpack("<I", raw_bytes)[0]

                # Mask out unused bits (optional, but good for cleanliness)
                # mask = (1 << resolution) - 1
                # val &= mask

                samples[f"sensor_{i}"] = val
                offset += byte_width

        data.update({"timestamp": timestamp, "samples": samples})
        return data

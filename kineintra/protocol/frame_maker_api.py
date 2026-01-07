from typing import Mapping
from kineintra.protocol.packet_maker import HostPacketMaker

SENSOR_COUNT_LIMIT = 32  # Maximum number of sensors supported


class HostPacketMakerAPI:
    """Memoryless API wrapper around HostPacketMaker for easier command packet creation."""

    @staticmethod
    def _verify_uint8(value: int) -> bool:
        return 0 <= value <= 0xFF

    @staticmethod
    def _verify_uint16(value: int) -> bool:
        return 0 <= value <= 0xFFFF

    @staticmethod
    def _verify_uint32(value: int) -> bool:
        return 0 <= value <= 0xFFFFFFFF

    @staticmethod
    def active_map_maker(sensors: Mapping[int, bool]) -> int:
        """
        Create ActiveMap uint32 from a dictionary mapping sensor indices to active status.
        Example input: {0: True, 1: False, 2: True} -> ActiveMap with bits 0 and 2 set.
        """
        active_map = 0
        for sensor_idx, is_active in sensors.items():
            if not 0 <= sensor_idx <= SENSOR_COUNT_LIMIT - 1:
                raise ValueError(
                    f"Sensor index {sensor_idx} exceeds limit of {SENSOR_COUNT_LIMIT - 1}."
                )
            if not isinstance(is_active, bool):
                raise ValueError(
                    f"Active status for sensor {sensor_idx} must be a boolean."
                )
            if is_active:
                active_map |= 1 << sensor_idx
        return active_map

    @staticmethod
    def set_active_map(sensors: Mapping[int, bool], n_sensors: int, seq: int) -> bytes:
        """
        Create command packet to set ActiveMap based on sensor active status mapping.
        Validates input and constructs the command packet.
        Args:
            sensors: Mapping of sensor indices to their active status (True/False).
            n_sensors: Total number of sensors to consider.
            seq: Sequence number for the command.
        Returns:
            Bytes representing the command packet to set the ActiveMap.
        Raises:
            ValueError: If n_sensors exceeds limit or mapping length mismatch.
        """
        if n_sensors > SENSOR_COUNT_LIMIT:
            raise ValueError(
                f"Number of sensors {n_sensors} exceeds limit of {SENSOR_COUNT_LIMIT}."
            )
        if len(sensors) != n_sensors:
            raise ValueError(
                f"Sensor mapping length {len(sensors)} does not match n_sensors {n_sensors}."
            )
        active_map = HostPacketMakerAPI.active_map_maker(sensors)
        return HostPacketMaker.cmd_set_active_map(seq=seq, active_map=active_map)

    @staticmethod
    def set_status_request(seq: int) -> bytes:
        """
        Create command packet to request device status.
        Args:
            seq: Sequence number for the command.
        Returns:
            Bytes representing the command packet to get status.
        """
        if not HostPacketMakerAPI._verify_uint8(seq):
            raise ValueError(f"Sequence number {seq} is out of uint8 range.")
        return HostPacketMaker.cmd_get_status(seq=seq)

    @staticmethod
    def set_n_sensors(n_sensors: int, seq: int) -> bytes:
        """
        Create command packet to set the number of sensors.
        Args:
            n_sensors: Number of sensors to set.
            seq: Sequence number for the command.
        Returns:
            Bytes representing the command packet to set number of sensors.
        Raises:
            ValueError: If n_sensors exceeds limit or seq is out of range.
        """
        if n_sensors > SENSOR_COUNT_LIMIT:
            raise ValueError(
                f"Number of sensors {n_sensors} exceeds limit of {SENSOR_COUNT_LIMIT}."
            )
        if not HostPacketMakerAPI._verify_uint8(seq):
            raise ValueError(f"Sequence number {seq} is out of uint8 range.")
        return HostPacketMaker.cmd_set_nsensors(seq=seq, n_sensors=n_sensors)

    @staticmethod
    def set_start_measure(seq: int) -> bytes:
        """
        Create command packet to start measurement.
        Args:
            seq: Sequence number for the command.
        Returns:
            Bytes representing the command packet to start measurement.
        Raises:
            ValueError: If seq is out of range.
        """
        if not HostPacketMakerAPI._verify_uint8(seq):
            raise ValueError(f"Sequence number {seq} is out of uint8 range.")
        return HostPacketMaker.cmd_start_measure(seq=seq)

    @staticmethod
    def set_stop_measure(seq: int) -> bytes:
        """
        Create command packet to stop measurement.
        Args:
            seq: Sequence number for the command.
        Returns:
            Bytes representing the command packet to stop measurement.
        Raises:
            ValueError: If seq is out of range.
        """
        if not HostPacketMakerAPI._verify_uint8(seq):
            raise ValueError(f"Sequence number {seq} is out of uint8 range.")
        return HostPacketMaker.cmd_stop_measure(seq=seq)

    @staticmethod
    def set_calibrate(seq: int, mode: int) -> bytes:
        """
        Create command packet to calibrate device.
        Args:
            seq: Sequence number for the command.
            mode: Calibration mode.
        Returns:
            Bytes representing the command packet to calibrate.
        Raises:
            ValueError: If seq or mode is out of range.
        """

        if not HostPacketMakerAPI._verify_uint8(seq):
            raise ValueError(f"Sequence number {seq} is out of uint8 range.")
        if not HostPacketMakerAPI._verify_uint8(mode):
            raise ValueError(f"Calibration mode {mode} is out of uint8 range.")
        return HostPacketMaker.cmd_calibrate(seq=seq, mode=mode)

    @staticmethod
    def set_frame_rate(seq: int, sensor_idx: int, rate_hz: int) -> bytes:
        """
        Create command packet to set sensor frame rate.
        Args:
            seq: Sequence number for the command.
            sensor_idx: Index of the sensor to set.
            rate_hz: Sampling rate in Hz.
        Returns:
            Bytes representing the command packet to set frame rate.
        Raises:
            ValueError: If seq, sensor_idx, or rate_hz is out of range.
        """
        if not HostPacketMakerAPI._verify_uint8(seq):
            raise ValueError(f"Sequence number {seq} is out of uint8 range.")
        if not HostPacketMakerAPI._verify_uint8(sensor_idx):
            raise ValueError(f"Sensor index {sensor_idx} is out of uint8 range.")
        if not HostPacketMakerAPI._verify_uint16(rate_hz):
            raise ValueError(f"Rate {rate_hz} is out of uint16 range.")
        return HostPacketMaker.cmd_set_rate(
            seq=seq, sensor_idx=sensor_idx, rate_hz=rate_hz
        )

    @staticmethod
    def set_bits_per_sample(seq: int, sensor_idx: int, bits_per_smp: int) -> bytes:
        """
        Create command packet to set bits per sample for a sensor.
        Args:
            seq: Sequence number for the command.
            sensor_idx: Index of the sensor to set.
            bits_per_smp: Bits per sample.
        Returns:
            Bytes representing the command packet to set bits per sample.
        Raises:
            ValueError: If seq, sensor_idx, or bits_per_smp is out of range.
        """
        if not HostPacketMakerAPI._verify_uint8(seq):
            raise ValueError(f"Sequence number {seq} is out of uint8 range.")
        if not HostPacketMakerAPI._verify_uint8(sensor_idx):
            raise ValueError(f"Sensor index {sensor_idx} is out of uint8 range.")
        if not HostPacketMakerAPI._verify_uint8(bits_per_smp):
            raise ValueError(f"Bits per sample {bits_per_smp} is out of uint8 range.")
        return HostPacketMaker.cmd_set_bits(
            seq=seq, sensor_idx=sensor_idx, bits_per_smp=bits_per_smp
        )

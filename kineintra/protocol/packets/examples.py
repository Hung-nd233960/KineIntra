"""
Examples demonstrating usage of packet makers for both host and device.
This file shows how to create all possible frame types.
"""

from kineintra.protocol.packets import (
    HostPacketMaker,
    DevicePacketMaker,
    UnifiedPacketMaker,
    CmdID,
)
from kineintra.protocol.packets.config import (
    DeviceState,
    SensorRole,
    AckResult,
    ErrorCode,
)
from kineintra.protocol.packets.hex_formatter import hex_formatter


def example_host_commands():
    """Examples of creating COMMAND frames from host perspective."""
    print("=== Host Command Examples ===\n")

    # Basic commands
    frame = HostPacketMaker.cmd_get_status(seq=1)
    print(f"GET_STATUS: {hex_formatter(frame)}")

    frame = HostPacketMaker.cmd_start_measure(seq=2)
    print(f"START_MEASURE: {hex_formatter(frame)}")

    frame = HostPacketMaker.cmd_stop_measure(seq=3)
    print(f"STOP_MEASURE: {hex_formatter(frame)}")

    # Configuration commands
    frame = HostPacketMaker.cmd_set_nsensors(seq=4, n_sensors=8)
    print(f"SET_NSENSORS (8): {hex_formatter(frame)}")

    frame = HostPacketMaker.cmd_set_rate(seq=5, sensor_idx=0, rate_hz=1000)
    print(f"SET_RATE (sensor 0, 1000Hz): {hex_formatter(frame)}")

    frame = HostPacketMaker.cmd_set_bits(seq=6, sensor_idx=0, bits_per_smp=12)
    print(f"SET_BITS (sensor 0, 12 bits): {hex_formatter(frame)}")

    # Enable sensors 0, 1, 2 (bits 0-2 set)
    active_map = 0b111  # = 7
    frame = HostPacketMaker.cmd_set_active_map(seq=7, active_map=active_map)
    print(f"SET_ACTIVEMAP (0b111): {hex_formatter(frame)}")

    # Calibration commands
    frame = HostPacketMaker.cmd_calibrate(seq=8, mode=1)
    print(f"CALIBRATE (mode 1): {hex_formatter(frame)}")

    frame = HostPacketMaker.cmd_stop_calibrate(seq=9)
    print(f"STOP_CALIBRATE: {hex_formatter(frame)}")

    frame = HostPacketMaker.cmd_end_calibrate(seq=10)
    print(f"END_CALIBRATE: {hex_formatter(frame)}")

    print()


def example_device_status():
    """Example of creating a STATUS frame from device perspective."""
    print("=== Device STATUS Example ===\n")

    # Configure 3 active sensors (indices 0, 1, 2)
    active_map = 0b111  # Sensors 0, 1, 2 active
    health_map = 0b111  # All active sensors are healthy

    # Sampling rates: 1000 Hz for sensors 0-2, 0 for others
    samp_rate_map = [1000, 1000, 1000] + [0] * 29

    # Bit resolution: 12 bits for sensors 0-2, 0 for others
    bits_per_smp_map = [12, 12, 12] + [0] * 29

    # Sensor roles: All FSR sensors
    sensor_role_map = [
        SensorRole.FSR.value,
        SensorRole.FSR.value,
        SensorRole.FSR.value,
    ] + [SensorRole.NONE.value] * 29

    frame = DevicePacketMaker.make_status(
        state=DeviceState.MEASURING,
        n_sensors=3,
        active_map=active_map,
        health_map=health_map,
        samp_rate_map=samp_rate_map,
        bits_per_smp_map=bits_per_smp_map,
        sensor_role_map=sensor_role_map,
        adc_flags=0,
        reserved=0,
    )

    print(f"STATUS frame length: {len(frame)} bytes")
    print(f"STATUS frame (first 32 bytes): {hex_formatter(frame[:32])}")
    print()


def example_device_data():
    """Example of creating DATA frames from device perspective."""
    print("=== Device DATA Examples ===\n")

    # Example 1: Manual sample encoding
    timestamp = 1234567  # microseconds
    samples = [
        b"\x00\x01",  # 16-bit sample from sensor 0
        b"\x02\x03",  # 16-bit sample from sensor 1
        b"\x04\x05",  # 16-bit sample from sensor 2
    ]
    frame = DevicePacketMaker.make_data(timestamp, samples)
    print(f"DATA frame (manual): {hex_formatter(frame)}")

    # Example 2: Automatic sample encoding
    sample_values = [256, 770, 1284]  # Integer values
    bits_per_sample = [12, 12, 12]  # All 12-bit samples
    frame = DevicePacketMaker.make_data_simple(
        timestamp, sample_values, bits_per_sample
    )
    print(f"DATA frame (auto-encoded): {hex_formatter(frame)}")

    print()


def example_device_ack():
    """Example of creating ACK frames from device perspective."""
    print("=== Device ACK Examples ===\n")

    # Success ACK
    frame = DevicePacketMaker.make_ack(
        cmd_id=CmdID.GET_STATUS, seq=1, result=AckResult.OK
    )
    print(f"ACK OK: {hex_formatter(frame)}")

    # Error ACK
    frame = DevicePacketMaker.make_ack(
        cmd_id=CmdID.SET_RATE, seq=5, result=AckResult.INVALID_ARGUMENT
    )
    print(f"ACK INVALID_ARGUMENT: {hex_formatter(frame)}")

    frame = DevicePacketMaker.make_ack(
        cmd_id=CmdID.START_MEASURE, seq=2, result=AckResult.BUSY
    )
    print(f"ACK BUSY: {hex_formatter(frame)}")

    print()


def example_device_error():
    """Example of creating ERROR frames from device perspective."""
    print("=== Device ERROR Examples ===\n")

    timestamp = 9876543  # microseconds

    # ADC overrun error
    frame = DevicePacketMaker.make_error(
        timestamp=timestamp, err_code=ErrorCode.ADC_OVERRUN, aux_data=0
    )
    print(f"ERROR ADC_OVERRUN: {hex_formatter(frame)}")

    # Sensor fault on sensor 2
    frame = DevicePacketMaker.make_error(
        timestamp=timestamp, err_code=ErrorCode.SENSOR_FAULT, aux_data=2
    )
    print(f"ERROR SENSOR_FAULT (sensor 2): {hex_formatter(frame)}")

    # Low voltage warning
    frame = DevicePacketMaker.make_error(
        timestamp=timestamp, err_code=ErrorCode.LOW_VOLTAGE, aux_data=0
    )
    print(f"ERROR LOW_VOLTAGE: {hex_formatter(frame)}")

    print()


def example_unified_interface():
    """Example using the UnifiedPacketMaker for both host and device frames."""
    print("=== Unified Interface Examples ===\n")

    # Host commands
    frame = UnifiedPacketMaker.cmd_get_status(seq=1)
    print(f"Unified CMD: {hex_formatter(frame):}")

    # Device responses
    frame = UnifiedPacketMaker.ack(cmd_id=CmdID.GET_STATUS, seq=1, result=AckResult.OK)
    print(f"Unified ACK: {hex_formatter(frame)}")

    frame = UnifiedPacketMaker.error(
        timestamp=123456, err_code=ErrorCode.FIFO_CRITICAL, aux_data=0
    )
    print(f"Unified ERROR: {hex_formatter(frame)}")

    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Packet Maker Examples - All Frame Types")
    print("=" * 60 + "\n")

    example_host_commands()
    example_device_status()
    example_device_data()
    example_device_ack()
    example_device_error()
    example_unified_interface()

    print("=" * 60)
    print("All examples completed successfully!")
    print("=" * 60 + "\n")

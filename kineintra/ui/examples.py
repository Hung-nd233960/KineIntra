"""
Example usage and testing of the BioMechanics PyQt6 Application.

This module demonstrates:
1. Programmatic usage of DeviceCommunicationWorker
2. Testing various device commands
3. Data collection and processing
"""

import logging
import time
from datetime import datetime
from kineintra.protocol.serial_connection import SerialConfig
from kineintra.protocol.frame_maker_api import HostPacketMakerAPI
from kineintra.ui.pyqt_app import DeviceCommunicationWorker, SensorReading

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def example_basic_communication():
    """
    Example: Basic device communication without GUI.

    This demonstrates how to use the DeviceCommunicationWorker
    for programmatic control.
    """
    logger.info("=" * 60)
    logger.info("Example: Basic Device Communication")
    logger.info("=" * 60)

    # Create worker
    worker = DeviceCommunicationWorker()

    # Setup callbacks
    def on_status(status):
        logger.info(
            f"Status received: {status.n_sensors} sensors, state={status.state}"
        )

    def on_data(data):
        logger.info(f"Data received: {len(data.samples)} sensor samples")

    def on_ack(ack):
        logger.info(f"ACK received: seq={ack.seq}, result={ack.result}")

    def on_error(error_msg):
        logger.error(f"Device error: {error_msg}")

    def on_connection_state(state):
        logger.info(f"Connection state: {state.value}")

    # Register callbacks
    worker.status_received.connect(on_status)
    worker.data_received.connect(on_data)
    worker.ack_received.connect(on_ack)
    worker.error_received.connect(on_error)
    worker.connection_state_changed.connect(on_connection_state)
    worker.error_occurred.connect(on_error)

    logger.info("\nWorker created. Ready to connect to device.")
    logger.info("Usage:")
    logger.info("  worker.connect('/dev/ttyUSB0')  # or 'COM3' on Windows")
    logger.info("  worker.request_status()")
    logger.info("  worker.start_measurement()")
    logger.info("  worker.disconnect()")

    return worker


def example_command_sequence(port: str = "/dev/ttyUSB0"):
    """
    Example: Execute a sequence of commands.

    This demonstrates a typical workflow:
    1. Connect to device
    2. Request status
    3. Configure sensors
    4. Start measurement
    5. Collect data
    6. Stop measurement
    7. Disconnect
    """
    logger.info("=" * 60)
    logger.info("Example: Command Sequence")
    logger.info("=" * 60)

    worker = DeviceCommunicationWorker()

    # Track responses
    responses = {"status": None, "acks": []}

    def on_status(status):
        responses["status"] = status
        logger.info(f"✓ Status: {status.n_sensors} sensors active")

    def on_ack(ack):
        responses["acks"].append(ack)
        logger.info(f"✓ ACK: seq={ack.seq}, result={ack.result}")

    worker.status_received.connect(on_status)
    worker.ack_received.connect(on_ack)

    try:
        # Step 1: Connect
        logger.info(f"\n[1] Connecting to {port}...")
        worker.setup_connection(port)
        worker.connect(port)
        time.sleep(1)

        # Step 2: Request status
        logger.info("[2] Requesting device status...")
        worker.request_status()
        time.sleep(1)

        # Step 3: Configure sensors
        logger.info("[3] Configuring 4 sensors...")
        worker.set_n_sensors(4)
        time.sleep(0.5)

        # Step 4: Set frame rates
        logger.info("[4] Setting frame rates...")
        for sensor_idx in range(4):
            worker.set_frame_rate(sensor_idx, 100)  # 100 Hz
            time.sleep(0.3)

        # Step 5: Set bits per sample
        logger.info("[5] Setting bits per sample...")
        for sensor_idx in range(4):
            worker.set_bits_per_sample(sensor_idx, 12)  # 12-bit ADC
            time.sleep(0.3)

        # Step 6: Start measurement
        logger.info("[6] Starting measurement...")
        worker.start_measurement()
        time.sleep(1)

        # Step 7: Collect data for a few seconds
        logger.info("[7] Collecting data for 5 seconds...")
        time.sleep(5)

        # Step 8: Stop measurement
        logger.info("[8] Stopping measurement...")
        worker.stop_measurement()
        time.sleep(1)

        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("Command Sequence Complete!")
        logger.info(f"Total ACKs received: {len(responses['acks'])}")
        if responses["status"]:
            logger.info(f"Final device status: {responses['status'].n_sensors} sensors")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Error during command sequence: {e}")
    finally:
        # Step 9: Disconnect
        logger.info("[9] Disconnecting...")
        worker.disconnect()


def example_calibration(port: str = "/dev/ttyUSB0"):
    """
    Example: Perform device calibration.

    Demonstrates calibration command with different modes.
    """
    logger.info("=" * 60)
    logger.info("Example: Device Calibration")
    logger.info("=" * 60)

    worker = DeviceCommunicationWorker()

    def on_ack(ack):
        logger.info(f"Calibration ACK: seq={ack.seq}, result={ack.result}")

    worker.ack_received.connect(on_ack)

    try:
        logger.info(f"Connecting to {port}...")
        worker.setup_connection(port)
        worker.connect(port)
        time.sleep(1)

        # Calibration mode 0: Baseline calibration
        logger.info("\nPerforming baseline calibration (mode 0)...")
        worker.calibrate(mode=0)
        time.sleep(2)

        # Calibration mode 1: Full scale calibration
        logger.info("\nPerforming full-scale calibration (mode 1)...")
        worker.calibrate(mode=1)
        time.sleep(2)

        logger.info("\nCalibration complete!")

    except Exception as e:
        logger.error(f"Calibration error: {e}")
    finally:
        worker.disconnect()


def example_data_collection(port: str = "/dev/ttyUSB0", duration: int = 10):
    """
    Example: Collect and process sensor data.

    Demonstrates data collection with statistics.
    """
    logger.info("=" * 60)
    logger.info("Example: Data Collection")
    logger.info("=" * 60)

    worker = DeviceCommunicationWorker()

    # Data storage
    collected_readings = {}
    data_start_time = None

    def on_data(data):
        nonlocal data_start_time
        if data_start_time is None:
            data_start_time = datetime.now()

        timestamp = datetime.now()
        for sensor_idx, samples in enumerate(data.samples):
            if sensor_idx not in collected_readings:
                collected_readings[sensor_idx] = []

            for sample in samples:
                reading = SensorReading(
                    timestamp=timestamp,
                    sensor_idx=sensor_idx,
                    value=sample,
                    raw_value=sample,
                )
                collected_readings[sensor_idx].append(reading)

    worker.data_received.connect(on_data)

    try:
        logger.info(f"Connecting to {port}...")
        worker.setup_connection(port)
        worker.connect(port)
        time.sleep(1)

        logger.info(f"Configuring device and starting measurement...")
        worker.set_n_sensors(2)
        time.sleep(0.5)
        worker.set_frame_rate(0, 100)
        worker.set_frame_rate(1, 100)
        time.sleep(0.5)
        worker.start_measurement()

        logger.info(f"Collecting data for {duration} seconds...")
        time.sleep(duration)

        worker.stop_measurement()
        time.sleep(0.5)

        # Process collected data
        logger.info("\n" + "=" * 60)
        logger.info("Data Collection Summary")
        logger.info("=" * 60)

        total_samples = 0
        for sensor_idx in sorted(collected_readings.keys()):
            readings = collected_readings[sensor_idx]
            if not readings:
                continue

            total_samples += len(readings)
            min_val = min(r.value for r in readings)
            max_val = max(r.value for r in readings)
            avg_val = sum(r.value for r in readings) / len(readings)

            logger.info(f"\nSensor {sensor_idx}:")
            logger.info(f"  Samples: {len(readings)}")
            logger.info(f"  Min: {min_val:.4f}")
            logger.info(f"  Max: {max_val:.4f}")
            logger.info(f"  Avg: {avg_val:.4f}")
            logger.info(f"  Range: {max_val - min_val:.4f}")

            # Calculate sampling rate
            if len(readings) > 1:
                time_span = (
                    readings[-1].timestamp - readings[0].timestamp
                ).total_seconds()
                if time_span > 0:
                    sampling_rate = len(readings) / time_span
                    logger.info(f"  Sampling Rate: {sampling_rate:.1f} Hz")

        logger.info(f"\nTotal Samples: {total_samples}")
        logger.info(f"Collection Duration: {duration} seconds")
        if total_samples > 0:
            logger.info(f"Effective Rate: {total_samples / duration:.1f} samples/sec")

    except Exception as e:
        logger.error(f"Data collection error: {e}")
    finally:
        worker.disconnect()


if __name__ == "__main__":
    # Run examples (comment out as needed)

    # Example 1: Basic communication setup
    # worker = example_basic_communication()

    # Example 2: Command sequence
    # Uncomment and modify port as needed:
    # example_command_sequence(port="/dev/ttyUSB0")  # Linux/Mac
    # example_command_sequence(port="COM3")  # Windows

    # Example 3: Calibration
    # example_calibration(port="/dev/ttyUSB0")

    # Example 4: Data collection
    # example_data_collection(port="/dev/ttyUSB0", duration=10)

    logger.info("PyQt Application Examples")
    logger.info("=" * 60)
    logger.info("This module contains example code showing how to use")
    logger.info("the BioMechanics PyQt6 application programmatically.")
    logger.info("\nTo run examples, uncomment the desired function in __main__")
    logger.info("and modify the port parameter as needed.")
    logger.info("=" * 60)

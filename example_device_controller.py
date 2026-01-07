"""
Example: Using Protocol Parser and Serial Connection

This example demonstrates how to:
1. Connect to the biomechanics device via USB/COM port
2. Send commands to the device
3. Receive and parse frames from the device
4. Handle different frame types
"""

import time
import logging
from typing import Optional
from protocol.serial_connection import (
    SerialPortConnection,
    SerialConfig,
    PortDetector,
    ConnectionState,
)
from protocol.protocol_parser import (
    ProtocolParser,
    StatusPayload,
    DataPayload,
    AckPayload,
    ErrorPayload,
)
from protocol.frame_maker_api import HostPacketMakerAPI

# Setup logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DeviceController:
    """High-level device controller combining serial communication and protocol parsing."""

    def __init__(self, port: Optional[str] = None):
        """
        Initialize device controller.

        Args:
            port: Serial port name. If None, auto-detect.
        """
        # Auto-detect port if not provided
        if port is None:
            available_ports = PortDetector.list_ports()
            if available_ports:
                port = available_ports[0]
                logger.info("Auto-detected port: %s", port)
            else:
                raise RuntimeError("No serial ports found. Please specify a port.")

        # Setup serial connection
        config = SerialConfig(
            port=port,
            baudrate=115200,
            timeout=1.0,
        )
        self.connection = SerialPortConnection(config, logger)

        # Setup protocol parser
        self.parser = ProtocolParser()

        # Command sequence counter
        self.seq = 0

        # Register callbacks
        self.connection.register_frame_callback(self._on_frame_received)
        self.connection.register_error_callback(self._on_error)
        self.connection.register_state_callback(self._on_state_changed)

        # Status tracking
        self.last_status: Optional[StatusPayload] = None

    def _on_frame_received(self, frame):
        """Handle incoming frame."""
        frame_type, payload = self.parser.parse_frame(frame)
        logger.info("Frame received: %s", frame_type)

        if payload is None:
            logger.warning("Failed to parse %s frame", frame_type)
            return

        # Handle specific frame types
        if isinstance(payload, StatusPayload):
            self._handle_status(payload)
        elif isinstance(payload, DataPayload):
            self._handle_data(payload)
        elif isinstance(payload, AckPayload):
            self._handle_ack(payload)
        elif isinstance(payload, ErrorPayload):
            self._handle_error(payload)

    def _handle_status(self, status: StatusPayload):
        """Handle STATUS frame."""
        self.last_status = status
        logger.info(
            "Device Status: state=0x%02X, n_sensors=%d, active_map=0x%08X, health_map=0x%08X",
            status.state,
            status.n_sensors,
            status.active_map,
            status.health_map,
        )

        active_sensors = status.get_active_sensors()
        logger.info("Active sensors: %s", active_sensors)

        if status.is_measuring():
            logger.info("Device is MEASURING")
        elif status.is_idle():
            logger.info("Device is IDLE")
        elif status.is_calibrating():
            logger.info("Device is CALIBRATING")
        elif status.is_error():
            logger.error("Device is in ERROR state")

    def _handle_data(self, data: DataPayload):
        """Handle DATA frame."""
        logger.debug(
            "Data received: ts=%d, %d samples", data.timestamp, len(data.samples)
        )
        for sensor_idx, value in data.samples.items():
            logger.debug("  Sensor %d: %d", sensor_idx, value)

    def _handle_ack(self, ack: AckPayload):
        """Handle ACK frame."""
        logger.info(
            "ACK received: cmd_id=0x%02X, seq=%d, result=%s",
            ack.cmd_id,
            ack.seq,
            ack.get_result_name(),
        )

    def _handle_error(self, error: ErrorPayload):
        """Handle ERROR frame."""
        logger.error(
            "Device Error: %s (ts=%d, aux=0x%04X)",
            error.get_error_name(),
            error.timestamp,
            error.aux_data,
        )

    def _on_error(self, error_msg: str):
        """Handle communication error."""
        logger.error("Communication error: %s", error_msg)

    def _on_state_changed(self, state: ConnectionState):
        """Handle connection state change."""
        logger.info(f"Connection state: {state.value}")

    def _next_seq(self) -> int:
        """Get next sequence number."""
        self.seq = (self.seq + 1) % 256
        return self.seq

    def connect(self) -> bool:
        """Connect to device."""
        logger.info("Connecting to %s...", self.connection.config.port)
        return self.connection.connect()

    def disconnect(self) -> bool:
        """Disconnect from device."""
        logger.info("Disconnecting...")
        return self.connection.disconnect()

    def request_status(self) -> bool:
        """Send GET_STATUS command."""
        seq = self._next_seq()
        cmd = HostPacketMakerAPI.set_status_request(seq)
        logger.info("Requesting status (seq=%d)...", seq)
        return self.connection.send_frame(cmd)

    def start_measurement(self) -> bool:
        """Send START_MEASURE command."""
        seq = self._next_seq()
        cmd = HostPacketMakerAPI.set_start_measure(seq)
        logger.info("Starting measurement (seq=%d)...", seq)
        return self.connection.send_frame(cmd)

    def stop_measurement(self) -> bool:
        """Send STOP_MEASURE command."""
        seq = self._next_seq()
        cmd = HostPacketMakerAPI.set_stop_measure(seq)
        logger.info("Stopping measurement (seq=%d)...", seq)
        return self.connection.send_frame(cmd)

    def set_num_sensors(self, n_sensors: int) -> bool:
        """Set number of sensors."""
        seq = self._next_seq()
        cmd = HostPacketMakerAPI.set_n_sensors(n_sensors, seq)
        logger.info(f"Setting n_sensors={n_sensors} (seq={seq})...")
        return self.connection.send_frame(cmd)

    def set_sensor_rate(self, sensor_idx: int, rate_hz: int) -> bool:
        """Set sampling rate for a sensor."""
        seq = self._next_seq()
        cmd = HostPacketMakerAPI.set_frame_rate(seq, sensor_idx, rate_hz)
        logger.info(f"Setting sensor {sensor_idx} rate to {rate_hz} Hz (seq={seq})...")
        return self.connection.send_frame(cmd)

    def set_sensor_bits(self, sensor_idx: int, bits: int) -> bool:
        """Set bit resolution for a sensor."""
        seq = self._next_seq()
        cmd = HostPacketMakerAPI.set_bits_per_sample(seq, sensor_idx, bits)
        logger.info(f"Setting sensor {sensor_idx} to {bits} bits (seq={seq})...")
        return self.connection.send_frame(cmd)

    def get_statistics(self) -> dict:
        """Get communication statistics."""
        return self.connection.get_statistics()


def main():
    """Example usage."""
    logger.info("=== Biomechanics Device Controller Example ===\n")

    # Create controller
    try:
        controller = DeviceController()
    except RuntimeError as e:
        logger.error(f"Failed to initialize controller: {e}")
        return

    # Connect
    if not controller.connect():
        logger.error("Failed to connect to device")
        return

    # Allow time for connection to establish
    time.sleep(1)

    try:
        # Request device status
        controller.request_status()
        time.sleep(1)

        # Configure sensors (if desired)
        # controller.set_num_sensors(8)
        # time.sleep(0.5)

        # Start measurement
        # controller.start_measurement()
        # time.sleep(10)

        # Stop measurement
        # controller.stop_measurement()
        # time.sleep(0.5)

        # Print statistics
        stats = controller.get_statistics()
        logger.info("\n=== Communication Statistics ===")
        logger.info(f"Frames sent: {stats['frames_sent']}")
        logger.info(f"Frames received: {stats['frames_received']}")
        logger.info(f"CRC errors: {stats['crc_errors']}")

    finally:
        # Always disconnect
        controller.disconnect()


if __name__ == "__main__":
    main()

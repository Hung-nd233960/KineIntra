"""
PyQt6 Application for BioMechanics Microprocessor Control

Features:
- Connection Control: Connect/disconnect from serial device
- Command Center: Send commands to device (start/stop measurement, set parameters)
- Raw Data Display: Real-time visualization of incoming sensor data
"""

import sys
import logging
import struct
from typing import Optional, Dict, List
from datetime import datetime
from dataclasses import dataclass

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QLabel,
    QPushButton,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
    QGroupBox,
    QTableWidget,
    QTableWidgetItem,
    QLineEdit,
    QStatusBar,
    QPlainTextEdit,
    QCheckBox,
    QGridLayout,
    QFormLayout,
    QDialog,
    QMessageBox,
    QProgressBar,
    QSplitter,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread, QSize
from PyQt6.QtGui import QIcon, QColor, QFont

from kineintra.protocol.serial_connection import (
    SerialPortConnection,
    SerialConfig,
    ConnectionState,
)
from kineintra.protocol.protocol_parser import (
    ProtocolParser,
    StatusPayload,
    DataPayload,
    AckPayload,
    ErrorPayload,
)
from kineintra.protocol.frame_maker_api import HostPacketMakerAPI
from kineintra.protocol.packet_reader import FrameParseResult
import serial.tools.list_ports


# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass
class SensorReading:
    """Store a sensor reading with timestamp."""

    timestamp: datetime
    sensor_idx: int
    value: float
    raw_value: int


class DeviceCommunicationWorker(QObject):
    """Worker thread for device communication."""

    status_received = pyqtSignal(StatusPayload)
    data_received = pyqtSignal(DataPayload)
    ack_received = pyqtSignal(AckPayload)
    error_received = pyqtSignal(ErrorPayload)
    connection_state_changed = pyqtSignal(ConnectionState)
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.connection: Optional[SerialPortConnection] = None
        self.protocol_parser = ProtocolParser()
        self.seq_counter = 0
        self.is_connected = False

    def setup_connection(self, port: str, baudrate: int = 115200):
        """Setup serial connection."""
        try:
            config = SerialConfig(port=port, baudrate=baudrate)
            self.connection = SerialPortConnection(config=config)

            # Register callbacks
            self.connection.register_frame_callback(self._on_frame_received)
            self.connection.register_error_callback(self._on_error)
            self.connection.register_state_callback(self._on_state_changed)

            self.seq_counter = 0
            self.is_connected = True
        except Exception as e:
            self.error_occurred.emit(f"Failed to setup connection: {str(e)}")
            self.is_connected = False

    def connect(self, port: str):
        """Connect to device."""
        try:
            if not self.connection:
                self.setup_connection(port)
            if self.connection.connect(port):
                self.is_connected = True
            else:
                self.is_connected = False
                self.error_occurred.emit("Failed to connect to device")
        except Exception as e:
            self.is_connected = False
            self.error_occurred.emit(f"Connection error: {str(e)}")

    def disconnect(self):
        """Disconnect from device."""
        try:
            if self.connection:
                self.connection.disconnect()
            self.is_connected = False
        except Exception as e:
            self.error_occurred.emit(f"Disconnection error: {str(e)}")

    def send_command(self, command_bytes: bytes):
        """Send command to device."""
        try:
            if not self.connection:
                self.error_occurred.emit("Not connected to device")
                return False
            self.connection.send_frame(command_bytes)
            return True
        except Exception as e:
            self.error_occurred.emit(f"Failed to send command: {str(e)}")
            return False

    def request_status(self):
        """Request device status."""
        try:
            self.seq_counter = (self.seq_counter + 1) % 256
            cmd = HostPacketMakerAPI.set_status_request(seq=self.seq_counter)
            return self.send_command(cmd)
        except Exception as e:
            self.error_occurred.emit(f"Failed to request status: {str(e)}")
            return False

    def start_measurement(self):
        """Start measurement."""
        try:
            self.seq_counter = (self.seq_counter + 1) % 256
            cmd = HostPacketMakerAPI.set_start_measure(seq=self.seq_counter)
            return self.send_command(cmd)
        except Exception as e:
            self.error_occurred.emit(f"Failed to start measurement: {str(e)}")
            return False

    def stop_measurement(self):
        """Stop measurement."""
        try:
            self.seq_counter = (self.seq_counter + 1) % 256
            cmd = HostPacketMakerAPI.set_stop_measure(seq=self.seq_counter)
            return self.send_command(cmd)
        except Exception as e:
            self.error_occurred.emit(f"Failed to stop measurement: {str(e)}")
            return False

    def set_n_sensors(self, n_sensors: int):
        """Set number of sensors."""
        try:
            self.seq_counter = (self.seq_counter + 1) % 256
            cmd = HostPacketMakerAPI.set_n_sensors(
                n_sensors=n_sensors, seq=self.seq_counter
            )
            return self.send_command(cmd)
        except Exception as e:
            self.error_occurred.emit(f"Failed to set n_sensors: {str(e)}")
            return False

    def set_frame_rate(self, sensor_idx: int, rate_hz: int):
        """Set frame rate for sensor."""
        try:
            self.seq_counter = (self.seq_counter + 1) % 256
            cmd = HostPacketMakerAPI.set_frame_rate(
                seq=self.seq_counter, sensor_idx=sensor_idx, rate_hz=rate_hz
            )
            return self.send_command(cmd)
        except Exception as e:
            self.error_occurred.emit(f"Failed to set frame rate: {str(e)}")
            return False

    def set_bits_per_sample(self, sensor_idx: int, bits: int):
        """Set bits per sample for sensor."""
        try:
            self.seq_counter = (self.seq_counter + 1) % 256
            cmd = HostPacketMakerAPI.set_bits_per_sample(
                seq=self.seq_counter, sensor_idx=sensor_idx, bits_per_smp=bits
            )
            return self.send_command(cmd)
        except Exception as e:
            self.error_occurred.emit(f"Failed to set bits: {str(e)}")
            return False

    def calibrate(self, mode: int):
        """Calibrate device."""
        try:
            self.seq_counter = (self.seq_counter + 1) % 256
            cmd = HostPacketMakerAPI.set_calibrate(seq=self.seq_counter, mode=mode)
            return self.send_command(cmd)
        except Exception as e:
            self.error_occurred.emit(f"Failed to calibrate: {str(e)}")
            return False

    def _on_frame_received(self, frame: FrameParseResult):
        """Handle received frame."""
        try:
            parsed = self.protocol_parser.parse(frame)
            if isinstance(parsed, StatusPayload):
                self.status_received.emit(parsed)
            elif isinstance(parsed, DataPayload):
                self.data_received.emit(parsed)
            elif isinstance(parsed, AckPayload):
                self.ack_received.emit(parsed)
            elif isinstance(parsed, ErrorPayload):
                self.error_received.emit(parsed)
        except Exception as e:
            logger.error(f"Frame parsing error: {e}")

    def _on_error(self, error_msg: str):
        """Handle error."""
        self.error_occurred.emit(error_msg)

    def _on_state_changed(self, state: ConnectionState):
        """Handle connection state change."""
        self.connection_state_changed.emit(state)


class ConnectionControlWidget(QWidget):
    """Widget for controlling device connection."""

    def __init__(self, worker: DeviceCommunicationWorker):
        super().__init__()
        self.worker = worker
        self.init_ui()
        self.worker.connection_state_changed.connect(self._on_connection_state_changed)

    def init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout()

        # Port selection group
        port_group = QGroupBox("Port Selection")
        port_layout = QFormLayout()

        self.port_combo = QComboBox()
        self._refresh_ports()
        port_layout.addRow("Port:", self.port_combo)

        refresh_btn = QPushButton("Refresh Ports")
        refresh_btn.clicked.connect(self._refresh_ports)
        port_layout.addRow("", refresh_btn)

        self.baudrate_spin = QSpinBox()
        self.baudrate_spin.setMinimum(9600)
        self.baudrate_spin.setMaximum(921600)
        self.baudrate_spin.setValue(115200)
        self.baudrate_spin.setSingleStep(9600)
        port_layout.addRow("Baud Rate:", self.baudrate_spin)

        port_group.setLayout(port_layout)
        layout.addWidget(port_group)

        # Connection status group
        status_group = QGroupBox("Connection Status")
        status_layout = QVBoxLayout()

        self.status_label = QLabel("Status: Disconnected")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        status_layout.addWidget(self.status_label)

        self.connection_info_label = QLabel("")
        status_layout.addWidget(self.connection_info_label)

        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        # Connection buttons group
        button_group = QGroupBox("Connection Controls")
        button_layout = QHBoxLayout()

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self._on_connect)
        self.connect_btn.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold;"
        )
        button_layout.addWidget(self.connect_btn)

        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.clicked.connect(self._on_disconnect)
        self.disconnect_btn.setEnabled(False)
        self.disconnect_btn.setStyleSheet(
            "background-color: #f44336; color: white; font-weight: bold;"
        )
        button_layout.addWidget(self.disconnect_btn)

        button_group.setLayout(button_layout)
        layout.addWidget(button_group)

        layout.addStretch()
        self.setLayout(layout)

    def _refresh_ports(self):
        """Refresh available COM ports."""
        self.port_combo.clear()
        ports = serial.tools.list_ports.comports()
        for port in ports:
            self.port_combo.addItem(port.device)
        if not ports:
            self.port_combo.addItem("No ports available")

    def _on_connect(self):
        """Handle connect button click."""
        port = self.port_combo.currentText()
        if port == "No ports available":
            QMessageBox.warning(self, "Error", "No serial ports available")
            return
        self.worker.connect(port)

    def _on_disconnect(self):
        """Handle disconnect button click."""
        self.worker.disconnect()

    def _on_connection_state_changed(self, state: ConnectionState):
        """Handle connection state change."""
        if state == ConnectionState.CONNECTED:
            self.status_label.setText("Status: Connected")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
            self.port_combo.setEnabled(False)
            self.baudrate_spin.setEnabled(False)
            self.connection_info_label.setText(
                f"Connected to {self.port_combo.currentText()} at {self.baudrate_spin.value()} baud"
            )
        elif state == ConnectionState.DISCONNECTED:
            self.status_label.setText("Status: Disconnected")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            self.connect_btn.setEnabled(True)
            self.disconnect_btn.setEnabled(False)
            self.port_combo.setEnabled(True)
            self.baudrate_spin.setEnabled(True)
            self.connection_info_label.setText("")
        elif state == ConnectionState.CONNECTING:
            self.status_label.setText("Status: Connecting...")
            self.status_label.setStyleSheet("color: orange; font-weight: bold;")
        elif state == ConnectionState.ERROR:
            self.status_label.setText("Status: Error")
            self.status_label.setStyleSheet("color: darkred; font-weight: bold;")


class CommandCenterWidget(QWidget):
    """Widget for sending commands to device."""

    def __init__(self, worker: DeviceCommunicationWorker):
        super().__init__()
        self.worker = worker
        self.init_ui()
        self.worker.connection_state_changed.connect(self._on_connection_changed)
        self.worker.ack_received.connect(self._on_ack_received)

    def init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout()

        # Status command group
        status_group = QGroupBox("Status Commands")
        status_layout = QVBoxLayout()

        self.request_status_btn = QPushButton("Request Status")
        self.request_status_btn.clicked.connect(self._on_request_status)
        self.request_status_btn.setEnabled(False)
        status_layout.addWidget(self.request_status_btn)

        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        # Measurement control group
        measure_group = QGroupBox("Measurement Control")
        measure_layout = QHBoxLayout()

        self.start_measure_btn = QPushButton("Start Measurement")
        self.start_measure_btn.clicked.connect(self._on_start_measure)
        self.start_measure_btn.setEnabled(False)
        self.start_measure_btn.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold;"
        )
        measure_layout.addWidget(self.start_measure_btn)

        self.stop_measure_btn = QPushButton("Stop Measurement")
        self.stop_measure_btn.clicked.connect(self._on_stop_measure)
        self.stop_measure_btn.setEnabled(False)
        self.stop_measure_btn.setStyleSheet(
            "background-color: #f44336; color: white; font-weight: bold;"
        )
        measure_layout.addWidget(self.stop_measure_btn)

        measure_group.setLayout(measure_layout)
        layout.addWidget(measure_group)

        # Sensor configuration group
        sensor_group = QGroupBox("Sensor Configuration")
        sensor_layout = QFormLayout()

        self.n_sensors_spin = QSpinBox()
        self.n_sensors_spin.setMinimum(1)
        self.n_sensors_spin.setMaximum(32)
        self.n_sensors_spin.setValue(1)
        sensor_layout.addRow("Number of Sensors:", self.n_sensors_spin)

        set_n_sensors_btn = QPushButton("Set Number of Sensors")
        set_n_sensors_btn.clicked.connect(self._on_set_n_sensors)
        set_n_sensors_btn.setEnabled(False)
        self.set_n_sensors_btn = set_n_sensors_btn
        sensor_layout.addRow("", set_n_sensors_btn)

        sensor_group.setLayout(sensor_layout)
        layout.addWidget(sensor_group)

        # Frame rate configuration group
        framerate_group = QGroupBox("Sensor Frame Rate")
        framerate_layout = QFormLayout()

        self.rate_sensor_idx_spin = QSpinBox()
        self.rate_sensor_idx_spin.setMinimum(0)
        self.rate_sensor_idx_spin.setMaximum(31)
        framerate_layout.addRow("Sensor Index:", self.rate_sensor_idx_spin)

        self.frame_rate_spin = QSpinBox()
        self.frame_rate_spin.setMinimum(1)
        self.frame_rate_spin.setMaximum(10000)
        self.frame_rate_spin.setValue(100)
        framerate_layout.addRow("Frame Rate (Hz):", self.frame_rate_spin)

        set_rate_btn = QPushButton("Set Frame Rate")
        set_rate_btn.clicked.connect(self._on_set_frame_rate)
        set_rate_btn.setEnabled(False)
        self.set_rate_btn = set_rate_btn
        framerate_layout.addRow("", set_rate_btn)

        framerate_group.setLayout(framerate_layout)
        layout.addWidget(framerate_group)

        # Bits per sample configuration group
        bits_group = QGroupBox("Bits Per Sample")
        bits_layout = QFormLayout()

        self.bits_sensor_idx_spin = QSpinBox()
        self.bits_sensor_idx_spin.setMinimum(0)
        self.bits_sensor_idx_spin.setMaximum(31)
        bits_layout.addRow("Sensor Index:", self.bits_sensor_idx_spin)

        self.bits_per_sample_spin = QSpinBox()
        self.bits_per_sample_spin.setMinimum(8)
        self.bits_per_sample_spin.setMaximum(32)
        self.bits_per_sample_spin.setValue(12)
        bits_layout.addRow("Bits Per Sample:", self.bits_per_sample_spin)

        set_bits_btn = QPushButton("Set Bits Per Sample")
        set_bits_btn.clicked.connect(self._on_set_bits)
        set_bits_btn.setEnabled(False)
        self.set_bits_btn = set_bits_btn
        bits_layout.addRow("", set_bits_btn)

        bits_group.setLayout(bits_layout)
        layout.addWidget(bits_group)

        # Calibration group
        calib_group = QGroupBox("Calibration")
        calib_layout = QFormLayout()

        self.calib_mode_spin = QSpinBox()
        self.calib_mode_spin.setMinimum(0)
        self.calib_mode_spin.setMaximum(255)
        calib_layout.addRow("Calibration Mode:", self.calib_mode_spin)

        calib_btn = QPushButton("Calibrate")
        calib_btn.clicked.connect(self._on_calibrate)
        calib_btn.setEnabled(False)
        self.calib_btn = calib_btn
        calib_layout.addRow("", calib_btn)

        calib_group.setLayout(calib_layout)
        layout.addWidget(calib_group)

        # Response log
        log_group = QGroupBox("Command Response Log")
        log_layout = QVBoxLayout()

        self.response_log = QPlainTextEdit()
        self.response_log.setReadOnly(True)
        self.response_log.setMaximumHeight(150)
        log_layout.addWidget(self.response_log)

        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        layout.addStretch()
        self.setLayout(layout)

    def _set_all_buttons_enabled(self, enabled: bool):
        """Enable/disable all command buttons."""
        self.request_status_btn.setEnabled(enabled)
        self.start_measure_btn.setEnabled(enabled)
        self.stop_measure_btn.setEnabled(enabled)
        self.set_n_sensors_btn.setEnabled(enabled)
        self.set_rate_btn.setEnabled(enabled)
        self.set_bits_btn.setEnabled(enabled)
        self.calib_btn.setEnabled(enabled)

    def _on_connection_changed(self, state: ConnectionState):
        """Handle connection state change."""
        self._set_all_buttons_enabled(state == ConnectionState.CONNECTED)

    def _on_request_status(self):
        """Request device status."""
        self.worker.request_status()
        self.response_log.appendPlainText(
            f"[{datetime.now().strftime('%H:%M:%S')}] Status request sent"
        )

    def _on_start_measure(self):
        """Start measurement."""
        self.worker.start_measurement()
        self.response_log.appendPlainText(
            f"[{datetime.now().strftime('%H:%M:%S')}] Start measurement command sent"
        )

    def _on_stop_measure(self):
        """Stop measurement."""
        self.worker.stop_measurement()
        self.response_log.appendPlainText(
            f"[{datetime.now().strftime('%H:%M:%S')}] Stop measurement command sent"
        )

    def _on_set_n_sensors(self):
        """Set number of sensors."""
        n_sensors = self.n_sensors_spin.value()
        self.worker.set_n_sensors(n_sensors)
        self.response_log.appendPlainText(
            f"[{datetime.now().strftime('%H:%M:%S')}] Set n_sensors to {n_sensors}"
        )

    def _on_set_frame_rate(self):
        """Set frame rate."""
        sensor_idx = self.rate_sensor_idx_spin.value()
        rate_hz = self.frame_rate_spin.value()
        self.worker.set_frame_rate(sensor_idx, rate_hz)
        self.response_log.appendPlainText(
            f"[{datetime.now().strftime('%H:%M:%S')}] Set frame rate for sensor {sensor_idx} to {rate_hz} Hz"
        )

    def _on_set_bits(self):
        """Set bits per sample."""
        sensor_idx = self.bits_sensor_idx_spin.value()
        bits = self.bits_per_sample_spin.value()
        self.worker.set_bits_per_sample(sensor_idx, bits)
        self.response_log.appendPlainText(
            f"[{datetime.now().strftime('%H:%M:%S')}] Set bits for sensor {sensor_idx} to {bits}"
        )

    def _on_calibrate(self):
        """Calibrate device."""
        mode = self.calib_mode_spin.value()
        self.worker.calibrate(mode)
        self.response_log.appendPlainText(
            f"[{datetime.now().strftime('%H:%M:%S')}] Calibration command sent (mode {mode})"
        )

    def _on_ack_received(self, ack: AckPayload):
        """Handle ACK response."""
        self.response_log.appendPlainText(
            f"[{datetime.now().strftime('%H:%M:%S')}] ACK received - Seq: {ack.seq}, Result: {ack.result}"
        )


class RawDataDisplayWidget(QWidget):
    """Widget for displaying raw sensor data."""

    def __init__(self, worker: DeviceCommunicationWorker):
        super().__init__()
        self.worker = worker
        self.sensor_readings: Dict[int, List[SensorReading]] = {}
        self.max_readings_per_sensor = 1000
        self.init_ui()
        self.worker.data_received.connect(self._on_data_received)
        self.worker.status_received.connect(self._on_status_received)

    def init_ui(self):
        """Initialize UI."""
        layout = QVBoxLayout()

        # Statistics group
        stats_group = QGroupBox("Data Statistics")
        stats_layout = QFormLayout()

        self.total_readings_label = QLabel("0")
        stats_layout.addRow("Total Readings:", self.total_readings_label)

        self.active_sensors_label = QLabel("0")
        stats_layout.addRow("Active Sensors:", self.active_sensors_label)

        self.last_update_label = QLabel("Never")
        stats_layout.addRow("Last Update:", self.last_update_label)

        self.fps_label = QLabel("0 FPS")
        stats_layout.addRow("Data Rate:", self.fps_label)

        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        # Data table
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(4)
        self.data_table.setHorizontalHeaderLabels(
            ["Timestamp", "Sensor ID", "Raw Value", "Formatted Value"]
        )
        self.data_table.setMaximumHeight(300)
        layout.addWidget(self.data_table)

        # Sensor details group
        details_group = QGroupBox("Sensor Details")
        details_layout = QVBoxLayout()

        self.sensor_details_text = QPlainTextEdit()
        self.sensor_details_text.setReadOnly(True)
        details_layout.addWidget(self.sensor_details_text)

        details_group.setLayout(details_layout)
        layout.addWidget(details_group)

        # Data log
        log_group = QGroupBox("Raw Data Log")
        log_layout = QVBoxLayout()

        self.data_log = QPlainTextEdit()
        self.data_log.setReadOnly(True)
        log_layout.addWidget(self.data_log)

        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        # Setup update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_display)
        self.update_timer.start(500)  # Update every 500ms

        self.setLayout(layout)

    def _on_status_received(self, status: StatusPayload):
        """Handle status payload."""
        details = f"Device State: {status.state}\n"
        details += f"Number of Sensors: {status.n_sensors}\n"
        details += f"Active Map: 0x{status.active_map:08x}\n"
        details += f"Health Map: 0x{status.health_map:08x}\n\n"

        details += "Sampling Rates:\n"
        for i, rate in enumerate(status.samp_rates):
            if rate > 0:
                details += f"  Sensor {i}: {rate} Hz\n"

        details += "\nBits Per Sample:\n"
        for i, bits in enumerate(status.bits_map):
            if bits > 0:
                details += f"  Sensor {i}: {bits} bits\n"

        self.sensor_details_text.setPlainText(details)

    def _on_data_received(self, data: DataPayload):
        """Handle data payload."""
        timestamp = datetime.now()

        # Extract readings
        for sensor_idx, samples in enumerate(data.samples):
            if sensor_idx not in self.sensor_readings:
                self.sensor_readings[sensor_idx] = []

            for sample in samples:
                reading = SensorReading(
                    timestamp=timestamp,
                    sensor_idx=sensor_idx,
                    value=sample,
                    raw_value=sample,
                )
                self.sensor_readings[sensor_idx].append(reading)

                # Limit storage
                if len(self.sensor_readings[sensor_idx]) > self.max_readings_per_sensor:
                    self.sensor_readings[sensor_idx].pop(0)

                # Log
                self.data_log.appendPlainText(
                    f"[{timestamp.strftime('%H:%M:%S.%f')[:-3]}] Sensor {sensor_idx}: {sample}"
                )

        # Update last update time
        self.last_update_label.setText(timestamp.strftime("%H:%M:%S"))

    def _update_display(self):
        """Update display with latest readings."""
        # Update statistics
        total_readings = sum(len(v) for v in self.sensor_readings.values())
        self.total_readings_label.setText(str(total_readings))
        self.active_sensors_label.setText(str(len(self.sensor_readings)))

        # Calculate FPS
        fps = 0
        if self.sensor_readings:
            latest_readings = [v[-1] for v in self.sensor_readings.values() if v]
            if latest_readings and len(latest_readings) > 1:
                time_span = (
                    latest_readings[-1].timestamp - latest_readings[0].timestamp
                ).total_seconds()
                if time_span > 0:
                    fps = len(latest_readings) / time_span
        self.fps_label.setText(f"{fps:.1f} FPS")

        # Update table with latest readings
        self.data_table.setRowCount(0)
        for sensor_idx in sorted(self.sensor_readings.keys()):
            if self.sensor_readings[sensor_idx]:
                reading = self.sensor_readings[sensor_idx][-1]
                row = self.data_table.rowCount()
                self.data_table.insertRow(row)

                self.data_table.setItem(
                    row,
                    0,
                    QTableWidgetItem(reading.timestamp.strftime("%H:%M:%S.%f")[:-3]),
                )
                self.data_table.setItem(row, 1, QTableWidgetItem(str(sensor_idx)))
                self.data_table.setItem(
                    row, 2, QTableWidgetItem(str(reading.raw_value))
                )
                self.data_table.setItem(
                    row,
                    3,
                    QTableWidgetItem(f"{reading.value:.4f}"),
                )


class BioMechanicsApp(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("BioMechanics Microprocessor Control - PyQt6")
        self.setGeometry(100, 100, 1200, 900)

        # Create worker
        self.worker = DeviceCommunicationWorker()

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Create tab widget
        tabs = QTabWidget()

        # Add tabs
        self.connection_widget = ConnectionControlWidget(self.worker)
        tabs.addTab(self.connection_widget, "Connection Control")

        self.command_widget = CommandCenterWidget(self.worker)
        tabs.addTab(self.command_widget, "Command Center")

        self.data_widget = RawDataDisplayWidget(self.worker)
        tabs.addTab(self.data_widget, "Raw Data Display")

        layout = QVBoxLayout()
        layout.addWidget(tabs)
        central_widget.setLayout(layout)

        # Create status bar
        self.statusBar().showMessage("Ready")

        # Connect worker error signal
        self.worker.error_occurred.connect(self._on_error)

    def _on_error(self, error_msg: str):
        """Handle error."""
        logger.error(error_msg)
        QMessageBox.critical(self, "Error", error_msg)
        self.statusBar().showMessage(f"Error: {error_msg}")


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    window = BioMechanicsApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

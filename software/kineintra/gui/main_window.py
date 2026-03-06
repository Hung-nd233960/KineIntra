"""
KineIntra Main Window

Main application window with connection management, status monitor, and command center.
"""

from __future__ import annotations

import sys
from typing import Optional
from PyQt6.QtWidgets import (  # type: ignore[import-untyped]
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QComboBox,
    QLineEdit,
    QSpinBox,
    QTextEdit,
    QGridLayout,
    QSplitter,
    QCheckBox,
    QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread  # type: ignore[import-untyped]
from PyQt6.QtGui import QFont, QAction  # type: ignore[import-untyped]

from kineintra.api import DeviceClient, list_ports
from kineintra.protocol.packets.protocol_parser import (
    StatusPayload,
    DataPayload,
    AckPayload,
    ErrorPayload,
)


class EventPollerThread(QThread):
    """Background thread that polls for device events."""

    status_received = pyqtSignal(object)  # StatusPayload
    data_received = pyqtSignal(object)  # DataPayload
    ack_received = pyqtSignal(object)  # AckPayload
    error_received = pyqtSignal(object)  # ErrorPayload

    def __init__(self, client: DeviceClient, parent=None):
        super().__init__(parent)
        self.client = client
        self._running = False

    def run(self):
        self._running = True
        while self._running:
            evt = self.client.poll_event(timeout=0.1)
            if evt:
                etype, payload = evt
                if etype == "STATUS":
                    self.status_received.emit(payload)
                elif etype == "DATA":
                    self.data_received.emit(payload)
                elif etype == "ACK":
                    self.ack_received.emit(payload)
                elif etype == "ERROR":
                    self.error_received.emit(payload)

    def stop(self):
        self._running = False
        self.wait(2000)


class ConnectionPanel(QGroupBox):
    """Panel for connection management."""

    connection_changed = pyqtSignal(bool)  # True = connected

    def __init__(self, parent=None):
        super().__init__("Connection", parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QGridLayout(self)

        # Port selection
        layout.addWidget(QLabel("Port:"), 0, 0)
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(150)
        layout.addWidget(self.port_combo, 0, 1)

        self.refresh_btn = QPushButton("↻")
        self.refresh_btn.setFixedWidth(30)
        self.refresh_btn.setToolTip("Refresh port list")
        self.refresh_btn.clicked.connect(self.refresh_ports)
        layout.addWidget(self.refresh_btn, 0, 2)

        # TCP mode
        self.tcp_checkbox = QCheckBox("TCP Mode")
        self.tcp_checkbox.toggled.connect(self._on_tcp_toggled)
        layout.addWidget(self.tcp_checkbox, 1, 0)

        self.tcp_host = QLineEdit("127.0.0.1")
        self.tcp_host.setPlaceholderText("Host")
        self.tcp_host.setEnabled(False)
        layout.addWidget(self.tcp_host, 1, 1)

        self.tcp_port = QSpinBox()
        self.tcp_port.setRange(1, 65535)
        self.tcp_port.setValue(8888)
        self.tcp_port.setEnabled(False)
        layout.addWidget(self.tcp_port, 1, 2)

        # Connect/Disconnect buttons
        btn_layout = QHBoxLayout()
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        btn_layout.addWidget(self.connect_btn)

        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.setStyleSheet("background-color: #f44336; color: white;")
        self.disconnect_btn.setEnabled(False)
        btn_layout.addWidget(self.disconnect_btn)

        layout.addLayout(btn_layout, 2, 0, 1, 3)

        # Status indicator
        self.status_label = QLabel("● Disconnected")
        self.status_label.setStyleSheet("color: #f44336; font-weight: bold;")
        layout.addWidget(self.status_label, 3, 0, 1, 3)

        self.refresh_ports()

    def _on_tcp_toggled(self, checked: bool):
        self.tcp_host.setEnabled(checked)
        self.tcp_port.setEnabled(checked)
        self.port_combo.setEnabled(not checked)

    def refresh_ports(self):
        self.port_combo.clear()
        ports = list_ports(include_virtual=True)
        self.port_combo.addItems(ports)

    def set_connected(self, connected: bool):
        self.connect_btn.setEnabled(not connected)
        self.disconnect_btn.setEnabled(connected)
        self.port_combo.setEnabled(not connected and not self.tcp_checkbox.isChecked())
        self.tcp_checkbox.setEnabled(not connected)
        self.tcp_host.setEnabled(not connected and self.tcp_checkbox.isChecked())
        self.tcp_port.setEnabled(not connected and self.tcp_checkbox.isChecked())

        if connected:
            self.status_label.setText("● Connected")
            self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        else:
            self.status_label.setText("● Disconnected")
            self.status_label.setStyleSheet("color: #f44336; font-weight: bold;")

        self.connection_changed.emit(connected)

    def get_connection_params(self) -> dict:
        """Get connection parameters."""
        return {
            "use_tcp": self.tcp_checkbox.isChecked(),
            "tcp_host": self.tcp_host.text(),
            "tcp_port": self.tcp_port.value(),
            "port": self.port_combo.currentText(),
        }


class StatusPanel(QGroupBox):
    """Panel for displaying device status."""

    def __init__(self, parent=None):
        super().__init__("Device Status", parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QGridLayout(self)

        # State indicator
        layout.addWidget(QLabel("State:"), 0, 0)
        self.state_label = QLabel("Unknown")
        self.state_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.state_label, 0, 1)

        # Number of sensors
        layout.addWidget(QLabel("Sensors:"), 1, 0)
        self.sensors_label = QLabel("-")
        layout.addWidget(self.sensors_label, 1, 1)

        # Active sensors
        layout.addWidget(QLabel("Active:"), 2, 0)
        self.active_label = QLabel("-")
        layout.addWidget(self.active_label, 2, 1)

        # Healthy sensors
        layout.addWidget(QLabel("Healthy:"), 3, 0)
        self.healthy_label = QLabel("-")
        layout.addWidget(self.healthy_label, 3, 1)

        # Sample rates (first 4)
        layout.addWidget(QLabel("Rates (Hz):"), 4, 0)
        self.rates_label = QLabel("-")
        layout.addWidget(self.rates_label, 4, 1)

        # Bits per sample (first 4)
        layout.addWidget(QLabel("Bits:"), 5, 0)
        self.bits_label = QLabel("-")
        layout.addWidget(self.bits_label, 5, 1)

        # Last update time
        layout.addWidget(QLabel("Updated:"), 6, 0)
        self.updated_label = QLabel("-")
        self.updated_label.setStyleSheet("color: #666;")
        layout.addWidget(self.updated_label, 6, 1)

    def update_status(self, status: StatusPayload):
        """Update display with new status."""
        import time

        state_map = {
            0x00: ("IDLE", "#2196F3"),
            0x01: ("MEASURING", "#4CAF50"),
            0x02: ("CALIBRATING", "#FF9800"),
            0x03: ("ERROR", "#f44336"),
        }
        state_name, color = state_map.get(
            status.state, (f"0x{status.state:02X}", "#666")
        )
        self.state_label.setText(state_name)
        self.state_label.setStyleSheet(f"font-weight: bold; color: {color};")

        self.sensors_label.setText(str(status.n_sensors))

        active = status.get_active_sensors()
        self.active_label.setText(str(active) if active else "None")

        healthy = status.get_healthy_sensors()
        self.healthy_label.setText(str(healthy) if healthy else "None")

        rates = status.samp_rate_map[: min(4, status.n_sensors)]
        self.rates_label.setText(str(rates) if rates else "-")

        bits = status.bits_per_smp_map[: min(4, status.n_sensors)]
        self.bits_label.setText(str(bits) if bits else "-")

        self.updated_label.setText(time.strftime("%H:%M:%S"))

    def clear(self):
        """Clear status display."""
        self.state_label.setText("Unknown")
        self.state_label.setStyleSheet("font-weight: bold;")
        self.sensors_label.setText("-")
        self.active_label.setText("-")
        self.healthy_label.setText("-")
        self.rates_label.setText("-")
        self.bits_label.setText("-")
        self.updated_label.setText("-")


class CommandPanel(QGroupBox):
    """Panel for sending commands."""

    command_requested = pyqtSignal(str, dict)  # command_name, params

    def __init__(self, parent=None):
        super().__init__("Command Center", parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Basic commands
        basic_group = QGroupBox("Basic Commands")
        basic_layout = QGridLayout(basic_group)

        self.status_btn = QPushButton("Get Status")
        self.status_btn.clicked.connect(
            lambda: self.command_requested.emit("status", {})
        )
        basic_layout.addWidget(self.status_btn, 0, 0)

        self.start_btn = QPushButton("▶ Start Measure")
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        self.start_btn.clicked.connect(lambda: self.command_requested.emit("start", {}))
        basic_layout.addWidget(self.start_btn, 0, 1)

        self.stop_btn = QPushButton("■ Stop Measure")
        self.stop_btn.setStyleSheet("background-color: #f44336; color: white;")
        self.stop_btn.clicked.connect(lambda: self.command_requested.emit("stop", {}))
        basic_layout.addWidget(self.stop_btn, 0, 2)

        layout.addWidget(basic_group)

        # Configuration commands
        config_group = QGroupBox("Configuration")
        config_layout = QGridLayout(config_group)

        # Number of sensors
        config_layout.addWidget(QLabel("N Sensors:"), 0, 0)
        self.nsensors_spin = QSpinBox()
        self.nsensors_spin.setRange(1, 32)
        self.nsensors_spin.setValue(8)
        config_layout.addWidget(self.nsensors_spin, 0, 1)

        self.set_nsensors_btn = QPushButton("Set")
        self.set_nsensors_btn.clicked.connect(
            lambda: self.command_requested.emit(
                "set_nsensors", {"n": self.nsensors_spin.value()}
            )
        )
        config_layout.addWidget(self.set_nsensors_btn, 0, 2)

        # Sample rate
        config_layout.addWidget(QLabel("Rate (Hz):"), 1, 0)
        self.rate_spin = QSpinBox()
        self.rate_spin.setRange(1, 1000)
        self.rate_spin.setValue(100)
        config_layout.addWidget(self.rate_spin, 1, 1)

        self.sensor_idx_spin = QSpinBox()
        self.sensor_idx_spin.setRange(0, 31)
        self.sensor_idx_spin.setPrefix("Sensor ")
        config_layout.addWidget(self.sensor_idx_spin, 1, 2)

        self.set_rate_btn = QPushButton("Set Rate")
        self.set_rate_btn.clicked.connect(
            lambda: self.command_requested.emit(
                "set_rate",
                {
                    "sensor_idx": self.sensor_idx_spin.value(),
                    "rate": self.rate_spin.value(),
                },
            )
        )
        config_layout.addWidget(self.set_rate_btn, 1, 3)

        layout.addWidget(config_group)

        # Calibration commands
        cal_group = QGroupBox("Calibration")
        cal_layout = QHBoxLayout(cal_group)

        self.cal_mode_spin = QSpinBox()
        self.cal_mode_spin.setRange(0, 255)
        self.cal_mode_spin.setPrefix("Mode ")
        cal_layout.addWidget(self.cal_mode_spin)

        self.calibrate_btn = QPushButton("Calibrate")
        self.calibrate_btn.setStyleSheet("background-color: #FF9800; color: white;")
        self.calibrate_btn.clicked.connect(
            lambda: self.command_requested.emit(
                "calibrate", {"mode": self.cal_mode_spin.value()}
            )
        )
        cal_layout.addWidget(self.calibrate_btn)

        self.stop_cal_btn = QPushButton("Stop Cal")
        self.stop_cal_btn.clicked.connect(
            lambda: self.command_requested.emit("stop_cal", {})
        )
        cal_layout.addWidget(self.stop_cal_btn)

        self.end_cal_btn = QPushButton("End Cal")
        self.end_cal_btn.clicked.connect(
            lambda: self.command_requested.emit("end_cal", {})
        )
        cal_layout.addWidget(self.end_cal_btn)

        layout.addWidget(cal_group)

        layout.addStretch()

    def set_enabled(self, enabled: bool):
        """Enable/disable all command buttons."""
        for btn in [
            self.status_btn,
            self.start_btn,
            self.stop_btn,
            self.set_nsensors_btn,
            self.set_rate_btn,
            self.calibrate_btn,
            self.stop_cal_btn,
            self.end_cal_btn,
        ]:
            btn.setEnabled(enabled)


class EventLogPanel(QGroupBox):
    """Panel for displaying event log."""

    def __init__(self, parent=None):
        super().__init__("Event Log", parent)
        self._setup_ui()
        self._data_count = 0
        self._max_lines = 1000

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Controls
        ctrl_layout = QHBoxLayout()

        self.show_data_cb = QCheckBox("Show DATA")
        self.show_data_cb.setChecked(False)
        ctrl_layout.addWidget(self.show_data_cb)

        self.show_status_cb = QCheckBox("Show STATUS")
        self.show_status_cb.setChecked(True)
        ctrl_layout.addWidget(self.show_status_cb)

        self.show_ack_cb = QCheckBox("Show ACK")
        self.show_ack_cb.setChecked(True)
        ctrl_layout.addWidget(self.show_ack_cb)

        ctrl_layout.addStretch()

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear)
        ctrl_layout.addWidget(self.clear_btn)

        layout.addLayout(ctrl_layout)

        # Stats
        self.stats_label = QLabel("DATA frames: 0")
        layout.addWidget(self.stats_label)

        # Log text
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Monospace", 9))
        layout.addWidget(self.log_text)

    def log_status(self, status: StatusPayload):
        if not self.show_status_cb.isChecked():
            return
        active = status.get_active_sensors()
        healthy = status.get_healthy_sensors()
        msg = f"STATUS state={status.state} n={status.n_sensors} active={active} healthy={healthy}"
        self._append_log(msg, "#2196F3")

    def log_data(self, data: DataPayload):
        self._data_count += 1
        self.stats_label.setText(f"DATA frames: {self._data_count}")

        if not self.show_data_cb.isChecked():
            return
        sensors = list(data.samples.keys()) if data.samples else []
        msg = f"DATA ts={data.timestamp} samples={len(sensors)} sensors={sensors} data ={data.samples}"
        self._append_log(msg, "#4CAF50")

    def log_ack(self, ack: AckPayload):
        if not self.show_ack_cb.isChecked():
            return
        result = "OK" if ack.result == 0 else f"ERR({ack.result})"
        msg = f"ACK cmd=0x{ack.cmd_id:02X} seq={ack.seq} result={result}"
        self._append_log(msg, "#9C27B0")

    def log_error(self, error: ErrorPayload):
        msg = f"ERROR code=0x{error.error_code:02X} aux={error.aux_data}"
        self._append_log(msg, "#f44336")

    def _append_log(self, msg: str, color: str = "#000"):
        import time

        timestamp = time.strftime("%H:%M:%S")
        html = f'<span style="color: #666;">[{timestamp}]</span> <span style="color: {color};">{msg}</span>'
        self.log_text.append(html)

        # Limit lines
        doc = self.log_text.document()
        if doc.blockCount() > self._max_lines:
            cursor = self.log_text.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            cursor.movePosition(
                cursor.MoveOperation.Down, cursor.MoveMode.KeepAnchor, 100
            )
            cursor.removeSelectedText()

    def clear(self):
        self.log_text.clear()
        self._data_count = 0
        self.stats_label.setText("DATA frames: 0")


class KineIntraMainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.client: Optional[DeviceClient] = None
        self.poller: Optional[EventPollerThread] = None
        self._setup_ui()
        self._setup_menu()
        self._connect_signals()

    def _setup_ui(self):
        self.setWindowTitle("KineIntra - Biomechanics Device Control")
        self.setMinimumSize(900, 700)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        # Left panel - Connection and Status
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.connection_panel = ConnectionPanel()
        left_layout.addWidget(self.connection_panel)

        self.status_panel = StatusPanel()
        left_layout.addWidget(self.status_panel)

        self.command_panel = CommandPanel()
        self.command_panel.set_enabled(False)
        left_layout.addWidget(self.command_panel)

        left_layout.addStretch()

        # Right panel - Event Log
        self.event_log = EventLogPanel()

        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(self.event_log)
        splitter.setSizes([350, 550])

        main_layout.addWidget(splitter)

        # Status bar
        self.statusBar().showMessage("Ready")

    def _setup_menu(self):
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _connect_signals(self):
        self.connection_panel.connect_btn.clicked.connect(self._on_connect)
        self.connection_panel.disconnect_btn.clicked.connect(self._on_disconnect)
        self.command_panel.command_requested.connect(self._on_command)

    def _on_connect(self):
        params = self.connection_panel.get_connection_params()

        # Create client
        use_virtual = params["port"] == "virtual" and not params["use_tcp"]

        if params["use_tcp"]:
            # Patch for TCP mode
            from kineintra.virtual import patch_serial_for_tcp

            patch_serial_for_tcp(host=params["tcp_host"], port=params["tcp_port"])
            self.client = DeviceClient(use_virtual=False)
            port = "tcp"
        else:
            self.client = DeviceClient(use_virtual=use_virtual)
            port = None if use_virtual else params["port"]

        self.statusBar().showMessage("Connecting...")

        if not self.client.connect(port=port, timeout=5.0):
            QMessageBox.critical(
                self, "Connection Failed", "Failed to connect to device."
            )
            self.statusBar().showMessage("Connection failed")
            self.client = None
            return

        # Start event poller
        self.poller = EventPollerThread(self.client, self)
        self.poller.status_received.connect(self._on_status)
        self.poller.data_received.connect(self._on_data)
        self.poller.ack_received.connect(self._on_ack)
        self.poller.error_received.connect(self._on_error)
        self.poller.start()

        self.connection_panel.set_connected(True)
        self.command_panel.set_enabled(True)
        self.statusBar().showMessage("Connected")

        # Request initial status
        self.client.get_status(seq=1)

    def _on_disconnect(self):
        if self.poller:
            self.poller.stop()
            self.poller = None

        if self.client:
            self.client.disconnect()
            self.client = None

        self.connection_panel.set_connected(False)
        self.command_panel.set_enabled(False)
        self.status_panel.clear()
        self.statusBar().showMessage("Disconnected")

    def _on_command(self, cmd: str, params: dict):
        if not self.client:
            return

        seq = 1
        success = False

        if cmd == "status":
            success = self.client.get_status(seq)
        elif cmd == "start":
            success = self.client.start_measure(seq)
        elif cmd == "stop":
            success = self.client.stop_measure(seq)
        elif cmd == "set_nsensors":
            success = self.client.set_nsensors(seq, params["n"])
        elif cmd == "set_rate":
            success = self.client.set_rate(seq, params["sensor_idx"], params["rate"])
        elif cmd == "calibrate":
            success = self.client.calibrate(seq, params["mode"])
        elif cmd == "stop_cal":
            success = self.client.stop_calibrate(seq)
        elif cmd == "end_cal":
            success = self.client.end_calibrate(seq)

        if success:
            self.statusBar().showMessage(f"Command sent: {cmd}")
        else:
            self.statusBar().showMessage(f"Command failed: {cmd}")

    def _on_status(self, status: StatusPayload):
        self.status_panel.update_status(status)
        self.event_log.log_status(status)

    def _on_data(self, data: DataPayload):
        self.event_log.log_data(data)

    def _on_ack(self, ack: AckPayload):
        self.event_log.log_ack(ack)

    def _on_error(self, error: ErrorPayload):
        self.event_log.log_error(error)

    def _show_about(self):
        QMessageBox.about(
            self,
            "About KineIntra",
            "KineIntra Biomechanics Device Control\n\n"
            "A GUI application for controlling and monitoring\n"
            "biomechanics measurement devices.\n\n"
            "Version 1.0.0",
        )

    def closeEvent(self, event):
        self._on_disconnect()
        event.accept()


def main():
    """Entry point for GUI application."""
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Dark theme option
    # palette = QPalette()
    # palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
    # palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    # app.setPalette(palette)

    window = KineIntraMainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

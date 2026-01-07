# BioMechanics Microprocessor PyQt6 Application

A professional PyQt6-based GUI application for controlling and monitoring the BioMechanics Microprocessor device.

## Features

### 1. **Connection Control Tab**

- **Port Selection**: Dynamically detect and select available COM/USB ports
- **Baud Rate Configuration**: Configurable communication speed (9600-921600)
- **Connection Status**: Real-time connection state display
- **Auto-Refresh**: Refresh available ports without restarting

**UI Components:**

- Port dropdown with auto-detection
- Baud rate spinner
- Connect/Disconnect buttons
- Status indicator with connection info

### 2. **Command Center Tab**

- **Status Requests**: Query device status and configuration
- **Measurement Control**: Start/stop data acquisition
- **Sensor Configuration**: Set number of active sensors
- **Frame Rate Control**: Configure sampling rates per sensor
- **Bits Per Sample**: Set ADC resolution per sensor
- **Calibration**: Perform device calibration with selectable modes
- **Command Logging**: View all sent commands and device responses

**UI Components:**

- Request status button
- Start/Stop measurement buttons
- Sensor count spinner
- Frame rate configuration (sensor index + Hz)
- Bits per sample configuration
- Calibration mode selector
- Response log with timestamps

### 3. **Raw Data Display Tab**

- **Real-time Data Visualization**: Monitor incoming sensor readings
- **Data Statistics**: Track total readings, active sensors, data rate
- **Sensor Details**: View device status information
- **Data Table**: Display latest readings from each sensor
- **Raw Data Log**: Complete log of all received data points

**UI Components:**

- Statistics panel (total readings, active sensors, last update, FPS)
- Data table with timestamp, sensor ID, raw value, formatted value
- Sensor details text area
- Raw data log with scrollable history

## Installation

### Prerequisites

- Python 3.10+
- pip or poetry

### Install Dependencies

```bash
pip install pyserial PyQt6>=6.6.0
```

Or using poetry (if using pyproject.toml):

```bash
poetry install
```

## Usage

### Launch the Application

```bash
python run_app.py
```

Or directly:

```bash
python -m ui.pyqt_app
```

### Quick Start Guide

#### Step 1: Connect to Device

1. Click the "Connection Control" tab
2. Select your device's COM port from the dropdown
3. Verify baud rate (default: 115200)
4. Click "Connect"
5. Status should change to "Connected" (green)

#### Step 2: Configure Device

1. Click the "Command Center" tab
2. Click "Request Status" to query device configuration
3. Set the number of sensors using "Set Number of Sensors"
4. Configure individual sensor frame rates and bit depths
5. Check the response log for confirmations

#### Step 3: Start Measurement

1. Click "Start Measurement" to begin data acquisition
2. Switch to "Raw Data Display" tab to view incoming data
3. Monitor statistics and sensor readings in real-time
4. Click "Stop Measurement" to pause acquisition

## Architecture

### DeviceCommunicationWorker

Thread-safe worker class that manages:

- Serial port connection and lifecycle
- Command generation and transmission
- Frame parsing and signal emission
- Connection state management

**Key Methods:**

- `connect(port)`: Establish connection
- `disconnect()`: Close connection
- `send_command(command_bytes)`: Send raw command
- `request_status()`: Query device status
- `start_measurement()`: Begin data acquisition
- `stop_measurement()`: Stop data acquisition
- `set_n_sensors(n_sensors)`: Configure sensor count
- `set_frame_rate(sensor_idx, rate_hz)`: Set sampling rate
- `set_bits_per_sample(sensor_idx, bits)`: Set ADC resolution
- `calibrate(mode)`: Perform calibration

**Signals Emitted:**

- `status_received`: Device status update
- `data_received`: Sensor data frame
- `ack_received`: Command acknowledgment
- `error_received`: Error message from device
- `connection_state_changed`: Connection status change
- `error_occurred`: Communication error

### ConnectionControlWidget

Manages the connection interface:

- Port discovery and selection
- Connection lifecycle
- Visual status feedback

### CommandCenterWidget

Provides command interface:

- All device commands accessible via buttons/spinners
- Command validation and error handling
- Response logging with timestamps

### RawDataDisplayWidget

Displays sensor data:

- Real-time data table updates
- Statistics calculation
- Data history management (max 1000 readings per sensor)
- Status information display

## Protocol Details

The application integrates with the BioMechanics protocol which defines:

### Frame Structure

```
SOF (2 bytes) | Version (1) | Type (1) | Length (2) | Payload (N) | CRC (2)
```

### Frame Types

- **STATUS (0x01)**: Device state and configuration
- **DATA (0x02)**: Sensor readings
- **COMMAND (0x03)**: Host to device commands
- **ACK (0x04)**: Command acknowledgment
- **ERROR (0x05)**: Error notification

### Command IDs

- `GET_STATUS (0x01)`: Query device status
- `START_MEASURE (0x02)`: Start measurement
- `STOP_MEASURE (0x03)`: Stop measurement
- `SET_NSENSORS (0x04)`: Set number of sensors
- `SET_RATE (0x05)`: Set sampling rate
- `SET_BITS (0x06)`: Set bits per sample
- `SET_ACTIVEMAP (0x07)`: Set active sensor map
- `CALIBRATE (0x08)`: Calibrate device

## Configuration

### Serial Connection Parameters

Default configuration in `SerialConfig`:

- **Baudrate**: 115200
- **Timeout**: 1.0 second
- **Write Timeout**: 1.0 second
- **Data Bits**: 8
- **Stop Bits**: 1
- **Parity**: None

These can be modified in the Connection Control tab.

## Data Display

### Statistics

- **Total Readings**: Cumulative count of all sensor readings received
- **Active Sensors**: Number of sensors currently transmitting data
- **Last Update**: Timestamp of most recent data reception
- **Data Rate**: Frames per second (FPS) of incoming data

### Data Table

Shows the most recent reading from each active sensor:

- Timestamp (HH:MM:SS.mmm format)
- Sensor ID (0-31)
- Raw ADC value
- Formatted value (with decimal precision)

### Sensor Details

Displays full status information including:

- Device state
- Number of sensors
- Active map (bitmask)
- Health map (bitmask)
- Sampling rates per sensor
- Bits per sample per sensor

## Error Handling

The application includes robust error handling:

- Connection timeouts with user notification
- CRC validation and error counting
- Command validation before transmission
- Graceful disconnection on errors
- Error logging with timestamps
- User-friendly error messages in status bar and dialogs

## Logging

Console logging is configured at INFO level by default. Increase verbosity by modifying:

```python
logging.basicConfig(level=logging.DEBUG)
```

Logs include:

- Connection state changes
- Command transmission
- Frame reception and parsing
- CRC errors
- Timing information

## Limitations

- Maximum 32 sensors (protocol limitation)
- UI updates every 500ms (configurable via `update_timer`)
- Data history limited to 1000 readings per sensor
- Single device connection at a time

## Troubleshooting

### No ports appear in dropdown

- Verify USB/Serial cable connection
- Check device drivers are installed
- Refresh ports using "Refresh Ports" button

### "Connection timeout" error

- Verify correct COM port selected
- Check baud rate matches device configuration
- Ensure device is powered on
- Try different baud rate (common: 115200, 9600)

### No data appearing in Raw Data Display

- Ensure device is connected (status should be "Connected")
- Click "Start Measurement" in Command Center
- Check that at least one sensor is configured
- Verify sampling rate is set > 0

### Commands not responding

- Verify connection status is "Connected"
- Check device log for error messages
- Try requesting status to verify communication
- Disconnect and reconnect

## Future Enhancements

Potential features for future versions:

- Data export to CSV/HDF5
- Real-time plotting with matplotlib/pyqtgraph
- Sensor calibration wizard
- Configuration profiles save/load
- Multi-device support
- Data filtering and averaging
- Trend analysis and anomaly detection
- Recording to file with playback
- Advanced sensor visualization (heatmaps, 3D plots)

## License

Part of the BioMechanics Microprocessor project.

## Support

For issues or questions:

1. Check the command response log for error messages
2. Verify serial connection with different baud rates
3. Review protocol documentation in `protocol/docs/`
4. Check application logs for detailed error information

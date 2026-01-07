# PyQt Application - Quick Reference Card

## Connection Control - Quick Reference

| Task | Steps |
|------|-------|
| **Connect to Device** | 1. Select port from dropdown<br>2. Verify baud rate (default 115200)<br>3. Click "Connect"<br>4. Wait for green "Connected" status |
| **Disconnect** | Click "Disconnect" button |
| **Find Your Port** | Click "Refresh Ports" button |
| **Change Baud Rate** | 1. Disconnect if connected<br>2. Change baud rate spinner<br>3. Reconnect |
| **Unknown Port?** | Check device manager or `ls /dev/tty*` |

## Command Center - Quick Reference

| Command | Purpose | Steps |
|---------|---------|-------|
| **Request Status** | Query device | Click "Request Status" |
| **Start Measurement** | Begin data collection | Click "Start Measurement" |
| **Stop Measurement** | End data collection | Click "Stop Measurement" |
| **Set Sensors** | Configure sensor count | Set spinner to N, click button |
| **Set Frame Rate** | Set sampling rate | Set sensor index & Hz, click button |
| **Set Bit Depth** | Configure ADC resolution | Set sensor index & bits, click button |
| **Calibrate** | Calibrate device | Set mode, click "Calibrate" |

## Raw Data Display - Quick Reference

| Feature | What It Shows |
|---------|---------------|
| **Total Readings** | Cumulative count of all data points received |
| **Active Sensors** | Number of sensors currently sending data |
| **Last Update** | Timestamp of most recent data reception |
| **Data Rate (FPS)** | Frames per second being received |
| **Data Table** | Latest reading from each sensor |
| **Sensor Details** | Full device status and configuration |
| **Data Log** | Complete history of all readings |

## Common Workflows

### Setup & Start Measurement

```
1. Connect Tab: Select port → Click Connect ✓
2. Command Tab: Request Status (to verify device) ✓
3. Command Tab: Set Number of Sensors ✓
4. Command Tab: Set Frame Rate for each sensor ✓
5. Command Tab: Click "Start Measurement" ✓
6. Data Tab: Monitor incoming data ✓
7. Command Tab: Click "Stop Measurement" (when done)
8. Connect Tab: Click Disconnect ✓
```

### Troubleshooting Connection

```
Problem: No ports showing
→ Check physical USB connection
→ Click "Refresh Ports"
→ Check Device Manager (Windows) or dmesg (Linux)

Problem: Connection timeout
→ Try different baud rate (9600, 57600, 115200)
→ Check device is powered on
→ Try different USB port/cable

Problem: Connected but no data
→ Click "Request Status" to verify device
→ Check "Number of Sensors" is set > 0
→ Verify frame rate is set > 0 Hz
→ Click "Start Measurement"
```

## Key Buttons & Controls

### Connection Tab

```
┌──────────────────────────────────────────┐
│ Port Dropdown        [port selection]    │
│ Refresh Ports Btn    [reload port list]  │
│ Baud Rate Spinner    [9600-921600]       │
│ Status Label         [green/red/orange]  │
│ Connect Button       [blue when ready]   │
│ Disconnect Button    [red when active]   │
└──────────────────────────────────────────┘
```

### Command Center Tab

```
┌──────────────────────────────────────────┐
│ Request Status Btn   [get device config] │
│ Start Measurement    [green button]      │
│ Stop Measurement     [red button]        │
│ Set N Sensors        [configure count]   │
│ Set Frame Rate       [configure Hz]      │
│ Set Bits Per Sample  [configure depth]   │
│ Calibrate Button     [run calibration]   │
│ Response Log         [command history]   │
└──────────────────────────────────────────┘
```

### Raw Data Display Tab

```
┌──────────────────────────────────────────┐
│ Statistics Panel     [live metrics]      │
│ Data Table          [latest readings]    │
│ Sensor Details      [device status]      │
│ Data Log            [data history]       │
└──────────────────────────────────────────┘
```

## Parameter Ranges

| Parameter | Min | Max | Common |
|-----------|-----|-----|--------|
| Baud Rate | 9600 | 921600 | 115200 |
| N Sensors | 1 | 32 | 4 |
| Sensor Index | 0 | 31 | 0-3 |
| Frame Rate | 1 Hz | 10000 Hz | 100 Hz |
| Bits/Sample | 8 | 32 | 12 |
| Calib Mode | 0 | 255 | 0 |

## Status Indicators

| Status | Color | Meaning |
|--------|-------|---------|
| Connected | 🟢 Green | Device ready |
| Disconnected | 🔴 Red | No device |
| Connecting | 🟠 Orange | Connection in progress |
| Error | 🔴 Dark Red | Communication error |

## Common Port Names

| OS | Common Ports |
|----|--------------|
| **Windows** | COM1, COM3, COM4 |
| **Linux** | /dev/ttyUSB0, /dev/ttyACM0 |
| **macOS** | /dev/cu.usbserial-* |

## Data Interpretation

### Data Table Columns

- **Timestamp**: When data was received (HH:MM:SS.mmm)
- **Sensor ID**: Which sensor (0-31)
- **Raw Value**: ADC value
- **Formatted Value**: Converted/scaled value

### Statistics Explained

- **Total Readings**: Sum of all data points received
- **Active Sensors**: Sensors that have sent data
- **Last Update**: Timestamp of most recent data
- **FPS**: Data frames arriving per second

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| **Tab** | Next field |
| **Shift+Tab** | Previous field |
| **Enter** | Activate button |
| **Space** | Toggle button |

## Memory & Performance

| Setting | Default | Impact |
|---------|---------|--------|
| Max readings/sensor | 1000 | Lower = less memory |
| UI update interval | 500ms | Higher = smoother |
| Port refresh | Manual | Can be slow |

## File Locations

```
Main Application:   ui/pyqt_app.py
Launcher:          run_app.py
Examples:          ui/examples.py
Docs:              ui/README.md, SETUP.md, ARCHITECTURE.md
Quick Start:       QUICKSTART.md
```

## Dependencies

```
PyQt6 ≥ 6.6.0       [GUI framework]
pyserial ≥ 3.5      [Serial communication]
```

## Typical Data Flow

```
User Action (button click)
        ↓
UI Signal Slot (_on_connect)
        ↓
Call Worker Method (worker.connect)
        ↓
Command Generated (HostPacketMakerAPI)
        ↓
Data Sent to Device (serial port)
        ↓
Device Responds (frame received)
        ↓
Frame Parsed (ProtocolParser)
        ↓
Signal Emitted (Qt signal)
        ↓
UI Updated (slot connected to signal)
        ↓
User Sees Result
```

## Error Messages - Quick Fix

| Error | Fix |
|-------|-----|
| "No ports available" | Check USB, refresh ports |
| "Connection timeout" | Try different baud rate |
| "Permission denied" | Linux: `sudo usermod -a -G dialout $USER` |
| "ModuleNotFoundError: PyQt6" | `pip install PyQt6` |
| "ModuleNotFoundError: protocol" | Ensure you're in project root |
| "No data appearing" | Click "Start Measurement" |
| "Command doesn't respond" | Verify "Connected" status |

## Performance Tips

1. **Slow UI?** → Increase UI update interval (500ms → 1000ms)
2. **High memory?** → Reduce max readings per sensor
3. **Lost commands?** → Reduce command frequency
4. **Lag?** → Reduce number of active sensors or frame rates

## Advanced Usage

### Change Update Frequency

In `ui/pyqt_app.py`, line ~850:

```python
self.update_timer.start(500)  # Change 500 to desired milliseconds
```

### Change Data Buffer Size

In `ui/pyqt_app.py`, line ~120:

```python
self.max_readings_per_sensor = 1000  # Change as needed
```

### Enable Debug Logging

In `ui/pyqt_app.py`, line ~65:

```python
logging.basicConfig(level=logging.DEBUG)  # Changed from INFO
```

## Getting Help

1. **5-minute setup?** → Read QUICKSTART.md
2. **Installation issues?** → Read SETUP.md Troubleshooting
3. **Feature details?** → Read ui/README.md
4. **Architecture?** → Read ARCHITECTURE.md
5. **Code examples?** → Check ui/examples.py

---

## Cheat Sheet

**Connect Device:**

```
1. Select port
2. Click Connect
3. Wait for green
```

**Collect Data:**

```
1. Request Status
2. Set N Sensors
3. Set Frame Rate
4. Start Measurement
5. Monitor on Data tab
6. Stop Measurement
```

**Disconnect:**

```
Click Disconnect
```

**Troubleshoot:**

```
Check SETUP.md → Troubleshooting section
```

---

**Last Updated**: 2024
**Version**: 1.0
**Status**: Production Ready

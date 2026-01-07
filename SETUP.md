# BioMechanics Microprocessor - PyQt6 GUI Application Setup Guide

## Overview

This guide will walk you through setting up and running the PyQt6 GUI application for the BioMechanics Microprocessor project.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Installation](#installation)
3. [Running the Application](#running-the-application)
4. [Troubleshooting](#troubleshooting)
5. [Project Structure](#project-structure)

## System Requirements

### Operating System

- **Windows 10+** (tested on Windows 10/11)
- **macOS 10.14+** (tested on Monterey+)
- **Linux** (Ubuntu 20.04+, Fedora, Debian)

### Python

- Python 3.10 or higher
- pip (Python package manager)
- Virtual environment support (venv or conda)

### Hardware

- USB/Serial connection to BioMechanics device
- Minimum 4GB RAM
- Display resolution 1024x768 or higher

## Installation

### Step 1: Clone/Navigate to Project

```bash
cd /path/to/BioMechanics_Microprocessor
```

### Step 2: Create Virtual Environment (Recommended)

#### Using venv

```bash
# Linux/macOS
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

#### Using conda

```bash
conda create -n biomechanics python=3.10
conda activate biomechanics
```

### Step 3: Install Dependencies

#### Option A: Using requirements.txt

```bash
pip install -r requirements.txt
```

#### Option B: Using pyproject.toml with pip

```bash
pip install -e .
```

#### Option C: Using poetry

```bash
pip install poetry
poetry install
```

#### Option D: Manual Installation

```bash
pip install pyserial>=3.5 PyQt6>=6.6.0
```

### Step 4: Verify Installation

```bash
# Verify PyQt6 installation
python -c "from PyQt6 import QtWidgets; print('PyQt6 OK')"

# Verify pyserial installation
python -c "import serial; print('pyserial OK')"
```

## Running the Application

### Method 1: Using run_app.py (Recommended)

```bash
python run_app.py
```

### Method 2: Using module execution

```bash
python -m ui.pyqt_app
```

### Method 3: Using Python directly

```bash
python -c "from ui.pyqt_app import main; main()"
```

### Expected Startup Output

When you run the application, you should see:

1. PyQt6 window opens with 1200x900 resolution
2. Three tabs: "Connection Control", "Command Center", "Raw Data Display"
3. Ports dropdown populated with available COM ports
4. Status bar at bottom showing "Ready"

## Application Usage

### Step 1: Connect to Device

1. **Open Connection Control tab**
2. **Select COM Port**: Choose your device's port from dropdown
   - On Windows: Usually "COM3" or "COM4"
   - On Linux: Usually "/dev/ttyUSB0" or "/dev/ttyACM0"
   - On macOS: Usually "/dev/cu.usbserial-*"
3. **Set Baud Rate**: Default 115200 (usually correct)
4. **Click "Connect"**
5. **Verify Status**: Should turn green and say "Connected"

### Step 2: Configure Device

1. **Open Command Center tab**
2. **Click "Request Status"** to query device
3. **Set Number of Sensors**: Configure how many sensors are active
4. **Configure Frame Rates**: Set sampling rate for each sensor
5. **Set Bit Depth**: Choose ADC resolution (8-32 bits)
6. **Check Response Log** for command confirmations

### Step 3: Collect Data

1. **Click "Start Measurement"** to begin data acquisition
2. **Switch to "Raw Data Display"** tab
3. **Monitor Incoming Data**:
   - Watch statistics update
   - View latest readings in table
   - Check sensor details
4. **Click "Stop Measurement"** to pause

## Troubleshooting

### Issue: "No ports available"

**Cause**: Device not connected or drivers missing

**Solutions**:

- Physically verify USB cable connection
- On Windows: Check Device Manager for unknown devices
- On Linux: Run `lsusb` to verify device detection
- On macOS: Check System Report > USB
- Try different USB ports
- Restart computer

**Verify connection:**

```bash
# Linux/macOS
ls /dev/tty*

# Windows
mode COM:  # or use Device Manager
```

### Issue: "Connection timeout"

**Cause**: Wrong baud rate or port

**Solutions**:

1. Try common baud rates:
   - 115200 (default)
   - 9600
   - 57600
2. Verify port in system settings
3. Try disconnecting/reconnecting cable
4. Check device logs for baud rate setting

### Issue: "Port dropdown empty"

**Cause**: No serial ports detected

**Solutions**:

1. Click "Refresh Ports" button
2. Check USB drivers installed
3. Physically verify connection
4. Try different USB hub/port
5. Restart computer

**Debug on Linux:**

```bash
# Check device
dmesg | tail -20

# Check permissions
ls -l /dev/ttyUSB0

# Add user to dialout group
sudo usermod -a -G dialout $USER
# Log out and back in
```

### Issue: "No data appearing in Raw Data Display"

**Cause**: Device not measuring or not sending data

**Solutions**:

1. Verify "Connected" status (green)
2. Click "Start Measurement" in Command Center
3. Check "Request Status" - should show active sensors
4. Verify at least one sensor has non-zero frame rate
5. Check device health/error status

### Issue: "Permission denied" on Linux

**Cause**: User doesn't have permission to access serial port

**Solutions**:

```bash
# Add current user to dialout group
sudo usermod -a -G dialout $USER

# Apply group changes
newgrp dialout

# Or logout and back in
```

### Issue: "ModuleNotFoundError: No module named 'PyQt6'"

**Cause**: PyQt6 not installed

**Solutions**:

```bash
# Verify virtual environment is activated
# Then reinstall:
pip install PyQt6>=6.6.0

# Or upgrade pip first
pip install --upgrade pip
pip install PyQt6>=6.6.0
```

### Issue: "ModuleNotFoundError: No module named 'protocol'"

**Cause**: Running script from wrong directory

**Solutions**:

```bash
# Make sure you're in project root
cd /path/to/BioMechanics_Microprocessor

# Then run
python run_app.py
```

### Issue: Application crashes on startup

**Cause**: Missing dependencies or display issues

**Solutions**:

```bash
# Reinstall all dependencies
pip install --force-reinstall -r requirements.txt

# Check Python version
python --version  # Should be 3.10+

# Try verbose startup
python -u run_app.py
```

## Project Structure

```
BioMechanics_Microprocessor/
├── ui/                           # GUI application package
│   ├── __init__.py              # Package init
│   ├── pyqt_app.py              # Main application
│   ├── examples.py              # Example usage
│   └── README.md                # Detailed documentation
├── protocol/                     # Protocol implementation
│   ├── __init__.py
│   ├── config.py               # Protocol constants
│   ├── packet_maker.py         # Command packet creation
│   ├── packet_reader.py        # Response parsing
│   ├── serial_connection.py    # Serial communication
│   ├── protocol_parser.py      # Frame type parsing
│   ├── frame_maker_api.py      # High-level API
│   └── docs/                   # Protocol documentation
├── pyproject.toml              # Project metadata
├── requirements.txt            # Python dependencies
├── run_app.py                  # Application launcher
└── README.md                   # Project overview
```

## File Descriptions

### Core GUI Files

- **ui/pyqt_app.py**: Main application containing:
  - `DeviceCommunicationWorker`: Thread-safe device interface
  - `ConnectionControlWidget`: Connection management UI
  - `CommandCenterWidget`: Command interface UI
  - `RawDataDisplayWidget`: Data visualization UI
  - `BioMechanicsApp`: Main window

- **ui/examples.py**: Programmatic usage examples
- **run_app.py**: Simple launcher script

### Key Classes

#### DeviceCommunicationWorker

Manages device communication in separate thread:

```python
worker = DeviceCommunicationWorker()
worker.connect("/dev/ttyUSB0")
worker.request_status()
worker.start_measurement()
```

#### ConnectionControlWidget

Handles connection UI:

- Port selection and detection
- Baud rate configuration
- Real-time status display

#### CommandCenterWidget

Provides command interface:

- Status requests
- Measurement control
- Sensor configuration
- Calibration
- Response logging

#### RawDataDisplayWidget

Displays sensor data:

- Real-time updates
- Statistics
- Data table
- Device info

## Advanced Configuration

### Changing Update Frequency

In `RawDataDisplayWidget.__init__`:

```python
self.update_timer.start(500)  # Change 500 to desired ms
```

### Changing Data Buffer Size

In `RawDataDisplayWidget.init_ui`:

```python
self.max_readings_per_sensor = 1000  # Change as needed
```

### Modifying Default Baud Rate

In `ConnectionControlWidget.init_ui`:

```python
self.baudrate_spin.setValue(115200)  # Change as needed
```

## Performance Tips

1. **Data Display**: For high-frequency sensors, reduce update timer frequency
2. **Memory**: Decrease `max_readings_per_sensor` if memory is constrained
3. **Port Detection**: Click refresh sparingly, it can be slow on some systems
4. **Multiple Sensors**: Reduce frame rates if experiencing lag

## Getting Help

### Check Logs

Enable debug logging:

```python
# In pyqt_app.py, change:
logging.basicConfig(level=logging.DEBUG)
```

### Verify Hardware Connection

```bash
# List available serial ports
python -c "import serial.tools.list_ports; print(list(serial.tools.list_ports.comports()))"
```

### Test Serial Connection

```bash
# Using miniterm (included with pyserial)
python -m serial.tools.miniterm /dev/ttyUSB0 115200
# (Press Ctrl-] to exit)
```

## Next Steps

1. Review [ui/README.md](ui/README.md) for detailed feature documentation
2. Check [ui/examples.py](ui/examples.py) for programmatic usage
3. Explore protocol documentation in [protocol/docs/](protocol/docs/)
4. Examine protocol implementation in [protocol/](protocol/)

## Support Resources

- **Protocol Details**: See `protocol/docs/PROTOCOL_PARSER_README.md`
- **Example Usage**: See `ui/examples.py`
- **API Reference**: See `protocol/frame_maker_api.py`
- **Configuration**: See `protocol/config.py`

## Version Information

- **PyQt6**: 6.6.0+
- **pyserial**: 3.5+
- **Python**: 3.10+

---

**Last Updated**: 2024
**Tested On**: Windows 11, Ubuntu 22.04, macOS 13.0

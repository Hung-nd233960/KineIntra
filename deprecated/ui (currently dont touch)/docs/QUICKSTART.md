# Quick Start Guide - BioMechanics PyQt6 Application

Get up and running in 5 minutes!

## Installation (2 minutes)

```bash
# 1. Navigate to project directory
cd /path/to/BioMechanics_Microprocessor

# 2. Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

## Launch (30 seconds)

```bash
python run_app.py
```

The PyQt6 application window will open!

## First Time Setup (2 minutes)

### 1. Connect to Device

- Click **"Connection Control"** tab
- Select your COM port (e.g., "COM3" or "/dev/ttyUSB0")
- Click **"Connect"** button
- Status should turn green: "Connected"

### 2. Configure Device

- Click **"Command Center"** tab
- Click **"Request Status"** button (see device config)
- Set **"Number of Sensors"** to your device's sensor count (e.g., 4)
- Click **"Set Number of Sensors"**
- For each sensor, set **"Frame Rate"** to desired Hz (e.g., 100 Hz)

### 3. Start Collecting Data

- Click **"Start Measurement"** button
- Switch to **"Raw Data Display"** tab
- Watch the data table update in real-time!
- Click **"Stop Measurement"** to pause

## What You Can Do

### Connection Tab

- ✓ Connect/disconnect from device
- ✓ Auto-detect COM ports
- ✓ Change baud rate
- ✓ View connection status

### Command Center Tab

- ✓ Request device status
- ✓ Start/stop measurement
- ✓ Configure sensors
- ✓ Set sampling rates
- ✓ Set ADC bit depth
- ✓ Calibrate device
- ✓ View command responses

### Raw Data Display Tab

- ✓ View sensor readings in real-time
- ✓ See data statistics (total readings, active sensors, FPS)
- ✓ Check sensor configuration
- ✓ Monitor complete data history

## Common Tasks

### Find Your COM Port

**Windows:**

- Device Manager → Ports (COM & LPT)
- Look for "USB Serial Device" or similar

**Linux:**

- Open terminal: `ls /dev/tty*`
- Usually `/dev/ttyUSB0` or `/dev/ttyACM0`

**macOS:**

- Terminal: `ls /dev/cu.*`
- Usually `/dev/cu.usbserial-*`

### Check If It's Connected

```bash
# Windows
mode COM3:  # Replace COM3 with your port

# Linux/Mac
stty -f /dev/ttyUSB0  # Replace with your port
```

### No Ports Showing?

1. Try different USB port/cable
2. Install drivers for your device
3. Restart computer
4. Click "Refresh Ports" button in app

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "No ports available" | Check USB connection, refresh ports |
| "Connection timeout" | Try different baud rate (9600, 57600, 115200) |
| No data appearing | Click "Start Measurement", check sensor count |
| "Permission denied" (Linux) | Run: `sudo usermod -a -G dialout $USER` then logout/login |
| "ModuleNotFoundError" | Activate virtual environment, reinstall requirements |

## Next Steps

1. Read **[SETUP.md](SETUP.md)** for detailed setup instructions
2. Check **[ui/README.md](ui/README.md)** for full documentation
3. Run examples in **[ui/examples.py](ui/examples.py)** for programmatic usage
4. Review protocol in **[protocol/docs/](protocol/docs/)**

## Tips & Tricks

- **Slow updates?** Reduce number of sensors or frame rates
- **Memory issues?** Reduce data buffer (decrease max readings per sensor)
- **Want to test without hardware?** Use `protocol/virtual_port.py` simulator
- **Need more control?** Check `ui/examples.py` for programmatic API

## Key Features at a Glance

| Feature | Location | Purpose |
|---------|----------|---------|
| Connect/Disconnect | Connection Tab | Manage serial connection |
| Request Status | Command Tab | Query device config |
| Start Measurement | Command Tab | Begin data acquisition |
| Configure Sensors | Command Tab | Set sample rate, bit depth |
| View Data | Raw Data Tab | Real-time sensor readings |
| Data Stats | Raw Data Tab | Readings count, FPS rate |
| Device Info | Raw Data Tab | Full status information |
| Command Log | Command Tab | All responses timestamped |

## Keyboard Shortcuts

- **F5**: Refresh ports (Connection tab)
- **Alt+F4**: Close application
- **Tab key**: Navigate between fields

## Getting More Help

- See **[ui/README.md](ui/README.md)** for detailed features
- Check **[SETUP.md](SETUP.md)** for troubleshooting
- Review **[protocol/docs/](protocol/docs/)** for protocol details
- Run `python -m ui.examples` for example code

---

**You're ready to go!** 🚀

If you have issues, cvheck [SETUP.md](SETUP.md) for comprehensive troubleshooting.

# Virtual Device Module

One-to-one replication of the physical biomechanics device for testing and development.

## Architecture

The virtual device is structured in three layers:

### 1. Serial Layer (`serial_layer.py`)

- **VirtualSerialPort**: Mimics pyserial.Serial interface
- Maintains bidirectional communication queues (host ↔ device)
- Runs device emulation in background thread
- Monitors and logs all serial traffic

### 2. Application Layer (`device.py`)

- **VirtualBiomechanicsDevice**: Simulates MCU firmware behavior
- State management (IDLE, MEASURING, CALIBRATING)
- Command processing with protocol-compliant responses
- Generates STATUS, DATA, ACK, ERROR frames
- Comprehensive logging with timestamps

### 3. Signal Generation (`signal_generator.py`)

- **SignalGenerator**: Abstract base for custom signal patterns
- **RandomSignalGenerator**: Default random data within protocol ranges
- **SineWaveGenerator**: Sinusoidal patterns for DSP testing
- **StaticSignalGenerator**: Constant values for calibration

## Usage

### Single-Process Mode (In-Memory)

The default mode runs the device in a background thread within your process.

```python
from kineintra.virtual import patch_serial_for_testing

# Patch pyserial for transparent testing
patch_serial_for_testing()

# Now all SerialPortConnection calls use virtual device
from kineintra.api import DeviceClient
client = DeviceClient()
client.connect()  # Automatically uses virtual port
```

### Two-Terminal Mode (TCP Server)

For realistic testing with separate device and host processes.

**Terminal 1: Start Virtual Device Server**

```bash
# Start server on localhost:8888 (default)
uv run python -m kineintra.virtual.server

# Or customize
uv run python -m kineintra.virtual.server --host 127.0.0.1 --port 9999 --signal sine

# Options:
#   --host HOST          Server bind address (default: 127.0.0.1)
#   --port PORT          Server port (default: 8888)
#   --signal TYPE        Signal generator: random, sine, static (default: random)
#   --debug              Enable debug logging
```

**Terminal 2: Connect Host Client**

```python
# Python script or REPL
from kineintra.virtual import connect_to_tcp_server

client = connect_to_tcp_server(host="127.0.0.1", port=8888)

# Use normally
client.get_status(1)
client.start_measure(2)

# Subscribe to events
client.on_data(lambda d: print(f"DATA: {d.samples}"))
```

### Custom Signal Generation

```python
from kineintra.virtual import VirtualSerialPort, SineWaveGenerator

# Create virtual port with sine wave generator
generator = SineWaveGenerator(frequencies=[1.0, 2.0, 5.0])
# Note: Custom signal injection requires direct device access
```

### CLI with Virtual Device

```bash
# List ports (includes 'virtual')
python -m kineintra.cli ports

# Connect to virtual device with monitoring
python -m kineintra.cli connect --port virtual --monitor
```

## Monitoring Output

The virtual device logs all activities with timestamps:

```text
[22:47:39] VirtualDevice: Virtual device initialized
[22:47:39] VirtualPort: Virtual serial port opened
[22:47:39] VirtualDevice: Virtual device worker started
[22:47:39] VirtualDevice: Received COMMAND: START_MEASURE (id=02 seq=01)
[22:47:39] VirtualDevice: Starting measurement mode
[22:47:39] VirtualDevice: Sending ACK: cmd=02 seq=1 result=OK
[22:47:40] VirtualDevice: Streaming DATA frames (sent 100 so far)
[22:47:41] VirtualDevice: Received COMMAND: STOP_MEASURE (id=03 seq=02)
[22:47:41] VirtualDevice: Stopping measurement mode (sent 234 frames)
```

## Extending Signal Generation

Create custom signal generators for your testing needs:

```python
from kineintra.virtual import SignalGenerator

class CustomSignalGenerator(SignalGenerator):
    def __init__(self):
        self.step = 0
        
    def generate_samples(self, n_sensors, bits_per_sensor):
        samples = []
        for i in range(n_sensors):
            # Your custom logic here
            value = (self.step * 10 + i * 100) % (2**bits_per_sensor[i])
            samples.append(value)
        self.step += 1
        return samples

# Use it in tests or custom virtual device instances
```

## File Structure

```text
kineintra/virtual/
├── __init__.py           # Public API exports
├── serial_layer.py       # VirtualSerialPort, VirtualSerialModule
├── device.py             # VirtualBiomechanicsDevice
└── signal_generator.py   # SignalGenerator classes
```

## Backward Compatibility

The old `tests/virtual_port.py` now re-exports from `kineintra.virtual` for compatibility:

```python
# Old import (still works)
from tests.virtual_port import VirtualSerialPort

# New import (preferred)
from kineintra.virtual import VirtualSerialPort
```

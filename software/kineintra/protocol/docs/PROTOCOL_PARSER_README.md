# Protocol Parser & Serial Connection Module

Comprehensive Python modules for communicating with the Biomechanics device over USB/COM ports.

## Overview

This package provides two main components:

1. **Protocol Parser** (`protocol_parser.py`) - Parses binary frames into structured, type-safe Python objects
2. **Serial Connection** (`serial_connection.py`) - Manages USB/COM port communication with async frame reception

## Installation

Required dependencies:

```bash
pip install pyserial
```

## Quick Start

```python
from protocol.serial_connection import SerialPortConnection, SerialConfig
from protocol.protocol_parser import ProtocolParser

# Setup connection
config = SerialConfig(port="/dev/ttyUSB0", baudrate=115200)
connection = SerialPortConnection(config)
parser = ProtocolParser()

# Connect and start receiving
connection.connect()

# Register frame callback
def on_frame(frame):
    frame_type, payload = parser.parse_frame(frame)
    print(f"Received {frame_type}: {payload}")

connection.register_frame_callback(on_frame)

# Send a command
from protocol.frame_maker_api import HostPacketMakerAPI
cmd = HostPacketMakerAPI.set_status_request(seq=1)
connection.send_frame(cmd)

# Keep receiving for a while
import time
time.sleep(5)

# Cleanup
connection.disconnect()
```

## Protocol Parser Module

### Overview

The protocol parser converts binary frames from the device into structured Python dataclasses:

- **`StatusPayload`** - Device status and configuration
- **`DataPayload`** - Sensor measurements
- **`AckPayload`** - Command acknowledgment
- **`ErrorPayload`** - Device error reports

### Key Classes

#### `ProtocolParser`

Main parser class that converts `FrameParseResult` objects into structured payloads.

```python
parser = ProtocolParser()

# Parse a frame
frame_type, payload = parser.parse_frame(frame)

# payload can be StatusPayload, DataPayload, AckPayload, or ErrorPayload
if isinstance(payload, StatusPayload):
    print(f"Device state: {payload.state}")
    print(f"Active sensors: {payload.get_active_sensors()}")
    print(f"Is measuring: {payload.is_measuring()}")
```

#### `StatusPayload`

Represents device status and configuration.

```python
@dataclass
class StatusPayload:
    state: int                      # 0=IDLE, 1=MEASURING, 2=CALIBRATING, 3=ERROR
    n_sensors: int                  # Number of active sensors
    active_map: int                 # Bitmap of active sensors
    health_map: int                 # Bitmap of healthy sensors
    samp_rate_map: list[int]        # 32 uint16 values (Hz per sensor)
    bits_per_smp_map: list[int]     # 32 uint8 values (bits per sensor)
    sensor_role_map: list[int]      # 32 uint8 values (role per sensor)
    adc_flags: int                  # ADC subsystem status
    reserved: int                   # Reserved field

# Methods:
payload.is_measuring()              # Check if device is measuring
payload.is_idle()                   # Check if device is idle
payload.get_active_sensors()        # Get list of active sensor indices
payload.get_healthy_sensors()       # Get list of healthy sensor indices
```

#### `DataPayload`

Represents sensor measurement samples.

```python
@dataclass
class DataPayload:
    timestamp: int                  # Microseconds since device start
    samples: Dict[int, int]         # sensor_index -> raw_value

# Methods:
value = payload.get_sample(0)       # Get value for sensor 0
for idx, val in payload.samples.items():
    print(f"Sensor {idx}: {val}")
```

#### `AckPayload`

Represents command acknowledgment.

```python
@dataclass
class AckPayload:
    cmd_id: int                     # Command ID being acknowledged
    seq: int                        # Sequence number
    result: int                     # Result code (0=OK)

# Methods:
if payload.is_success():
    print("Command succeeded")
else:
    print(f"Error: {payload.get_result_name()}")
```

#### `ErrorPayload`

Represents device error.

```python
@dataclass
class ErrorPayload:
    timestamp: int                  # Microseconds since device start
    error_code: int                 # Error type code
    aux_data: int                   # Context-dependent auxiliary data

# Methods:
print(f"Error: {payload.get_error_name()}")
```

### Parsing Errors

The parser tracks parsing errors for debugging:

```python
parser = ProtocolParser()

# Parse frames...
errors = parser.get_errors()
for error in errors:
    print(f"Parse error: {error}")

parser.clear_errors()  # Clear error log
```

## Serial Connection Module

### Overview

The serial connection module provides thread-safe, non-blocking serial communication with async frame reception.

### Key Classes

#### `SerialConfig`

Configuration for serial connection.

```python
config = SerialConfig(
    port="/dev/ttyUSB0",            # COM port name
    baudrate=115200,                # Baud rate
    timeout=1.0,                    # Read timeout (seconds)
    write_timeout=1.0,              # Write timeout (seconds)
    bytesize=8,                     # Data bits
    stopbits=1,                     # Stop bits
    parity="N"                      # Parity: N(one), E(ven), O(dd)
)
```

#### `SerialPortConnection`

Main connection class for serial communication.

```python
config = SerialConfig(port="COM3")
conn = SerialPortConnection(config)

# Connection management:
if conn.connect():
    print("Connected!")

conn.send_frame(command_bytes)      # Send frame

conn.is_connected()                 # Check connection status
conn.get_state()                    # Get ConnectionState

conn.disconnect()
```

#### Connection States

```python
from protocol.serial_connection import ConnectionState

# States:
ConnectionState.DISCONNECTED        # Not connected
ConnectionState.CONNECTING          # Connection in progress
ConnectionState.CONNECTED           # Successfully connected
ConnectionState.ERROR               # Error state
ConnectionState.CLOSING             # Disconnection in progress
```

#### Callbacks

Register callbacks for frame reception, errors, and state changes:

```python
def on_frame_received(frame):
    print(f"Frame type: {frame.msg_type}")

def on_error(error_msg):
    print(f"Error: {error_msg}")

def on_state_changed(state):
    print(f"State: {state.value}")

conn.register_frame_callback(on_frame_received)
conn.register_error_callback(on_error)
conn.register_state_callback(on_state_changed)
```

#### Statistics

Track communication statistics:

```python
stats = conn.get_statistics()
print(f"Frames sent: {stats['frames_sent']}")
print(f"Frames received: {stats['frames_received']}")
print(f"CRC errors: {stats['crc_errors']}")

conn.reset_statistics()  # Reset counters
```

#### Port Detection

```python
from protocol.serial_connection import PortDetector

# List all available ports
ports = PortDetector.list_ports()
print(ports)  # e.g., ['/dev/ttyUSB0', '/dev/ttyUSB1']

# Find device by USB VID/PID (defaults to Silicon Labs CP210x)
port = PortDetector.find_device_port()
if port:
    print(f"Device found at: {port}")
```

## Example: DeviceController

See `example_device_controller.py` for a complete example of using both modules together.

### High-level controller

```python
from example_device_controller import DeviceController

# Create and connect
controller = DeviceController()  # Auto-detects port
if not controller.connect():
    print("Connection failed")
    return

# Send commands
controller.request_status()
controller.set_num_sensors(8)
controller.start_measurement()

# Frames are automatically parsed and logged
# Statistics are available
stats = controller.get_statistics()

# Cleanup
controller.disconnect()
```

## Protocol Frame Structure

All frames follow this structure:

```
| SOF (2B) | Ver (1B) | Type (1B) | Len (2B) | Payload (N) | CRC16 (2B) |
```

- **SOF**: Start of frame marker (`0xA5 0x5A`)
- **Ver**: Protocol version (`0x01`)
- **Type**: Frame type (0x01=STATUS, 0x02=DATA, 0x03=COMMAND, 0x04=ACK, 0x05=ERROR)
- **Len**: Payload length (little-endian, max 65535)
- **Payload**: Frame-specific data
- **CRC16**: CRC-16-CCITT checksum (polynomial 0x1021, init 0xFFFF)

### Frame Types

| Type | Name | Direction | Purpose |
|------|------|-----------|---------|
| 0x01 | STATUS | Device → Host | Device status and configuration |
| 0x02 | DATA | Device → Host | Sensor measurements |
| 0x03 | COMMAND | Host → Device | Commands to device |
| 0x04 | ACK | Device → Host | Command acknowledgment |
| 0x05 | ERROR | Device → Host | Device error report |

## Threading Model

The serial connection uses a background receive thread:

- **Non-blocking**: `connect()`, `send_frame()`, and callback registration are non-blocking
- **Thread-safe**: All serial port access is protected
- **Async frame reception**: Frames are parsed and callbacks invoked in background thread
- **Graceful shutdown**: `disconnect()` waits for receive thread to stop

## Error Handling

The module handles several error conditions:

```python
# Connection errors
if not conn.connect():
    error = conn.last_error
    print(f"Connection failed: {error}")

# Parse errors
errors = parser.get_errors()
for error in errors:
    print(f"Parse error: {error}")

# CRC errors
stats = conn.get_statistics()
print(f"CRC errors: {stats['crc_errors']}")
```

## Advanced Usage

### Custom Logging

```python
import logging
logger = logging.getLogger("MyApp")

conn = SerialPortConnection(config, logger=logger)
```

### Multiple Parsers

Create multiple parsers to track different device states:

```python
parser1 = ProtocolParser()  # For data parsing
parser2 = ProtocolParser()  # Separate parser for stats
```

### Port Management

```python
# Try multiple ports
for port in PortDetector.list_ports():
    config = SerialConfig(port=port)
    conn = SerialPortConnection(config)
    if conn.connect():
        print(f"Connected to {port}")
        break
```

## Performance Notes

- **Frame rate**: Handles up to ~1000 frames/sec typical
- **Latency**: ~10-50ms typical round-trip
- **Memory**: Minimal overhead, no frame buffering
- **CPU**: Background thread uses <1% CPU when idle

## Troubleshooting

### Port not found

```python
ports = PortDetector.list_ports()
if not ports:
    print("No serial ports detected")
    # Check device connections, drivers
```

### CRC errors

```python
if stats['crc_errors'] > 0:
    print("CRC errors detected - check USB cable/connection quality")
```

### Parse errors

```python
errors = parser.get_errors()
if errors:
    print(f"Parse failures: {errors}")
    # May indicate protocol version mismatch
```

### Connection drops

```python
def on_state_changed(state):
    if state == ConnectionState.ERROR:
        print("Connection lost - attempting reconnect")
        # Implement reconnection logic
```

## See Also

- [PROTOCOL.md](PROTOCOL.md) - Complete protocol specification
- [example_device_controller.py](example_device_controller.py) - Full usage example
- [protocol/frame_maker_api.py](protocol/frame_maker_api.py) - Command construction
- [protocol/packet_reader.py](protocol/packet_reader.py) - Low-level frame parsing

## License

[Your License Here]

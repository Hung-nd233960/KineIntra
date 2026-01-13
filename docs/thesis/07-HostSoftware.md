# Host Software (CLI, GUI, API)

## 7.1 Software Architecture Overview

### 7.1.1 Design Principles

1. **Separation of Concerns**: UI, API, protocol, and transport in distinct layers
2. **Testability**: Virtual serial enables testing without hardware
3. **Flexibility**: Multiple consumption models (callbacks, polling, sync)
4. **Extensibility**: Clear extension points for new commands and transports

### 7.1.2 Layer Diagram

```
┌─────────────────────────────────────────────────────────┐
│                   Application Layer                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │    CLI      │  │    GUI      │  │  User Scripts   │  │
│  │ (argparse)  │  │  (PyQt6)    │  │   (custom)      │  │
│  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘  │
└─────────┼────────────────┼──────────────────┼───────────┘
          │                │                  │
          ▼                ▼                  ▼
┌─────────────────────────────────────────────────────────┐
│                      API Layer                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │                DeviceClient                      │    │
│  │  • connect() / disconnect()                      │    │
│  │  • get_status() / start_measure() / stop_...     │    │
│  │  • on_status() / on_data() / on_ack() / on_error()   │
│  │  • poll_event() → (type, payload)                │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
          │                │                  │
          ▼                ▼                  ▼
┌─────────────────────────────────────────────────────────┐
│                    Protocol Layer                        │
│  ┌───────────────┐  ┌──────────────┐  ┌─────────────┐   │
│  │HostPacketMaker│  │ProtocolParser│  │ ByteReader  │   │
│  │  (build cmds) │  │ (parse resp) │  │ (frame CRC) │   │
│  └───────────────┘  └──────────────┘  └─────────────┘   │
└─────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────┐
│                   Transport Layer                        │
│  ┌─────────────────────────────────────────────────┐    │
│  │             SerialPortConnection                 │    │
│  │  • Physical serial (pyserial)                    │    │
│  │  • Virtual serial (testing)                      │    │
│  │  • TCP bridge (remote)                           │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

## 7.2 DeviceClient API

### 7.2.1 Class Interface

```python
class DeviceClient:
    """High-level device communication facade."""

    def __init__(
        self,
        config: Optional[SerialConfig] = None,
        use_virtual: bool = False,
        logger: Optional[logging.Logger] = None
    ) -> None: ...

    # Connection management
    def connect(self, port: Optional[str] = None, timeout: float = 5.0) -> bool: ...
    def disconnect(self) -> bool: ...
    def is_connected(self) -> bool: ...

    # Commands
    def get_status(self, seq: int) -> bool: ...
    def start_measure(self, seq: int) -> bool: ...
    def stop_measure(self, seq: int) -> bool: ...
    def set_nsensors(self, seq: int, n: int) -> bool: ...
    def set_rate(self, seq: int, sensor_idx: int, rate_hz: int) -> bool: ...
    def set_bits(self, seq: int, sensor_idx: int, bits: int) -> bool: ...
    def set_active_map(self, seq: int, sensors: Dict[int, bool], n_sensors: int) -> bool: ...
    def calibrate(self, seq: int, mode: int) -> bool: ...
    def stop_calibrate(self, seq: int) -> bool: ...
    def end_calibrate(self, seq: int) -> bool: ...

    # Event subscription (callbacks)
    def on_status(self, cb: Callable[[StatusPayload], None]) -> None: ...
    def on_data(self, cb: Callable[[DataPayload], None]) -> None: ...
    def on_ack(self, cb: Callable[[AckPayload], None]) -> None: ...
    def on_error(self, cb: Callable[[ErrorPayload], None]) -> None: ...
    def on_raw_frame(self, cb: Callable[[FrameParseResult], None]) -> None: ...

    # Event polling (alternative to callbacks)
    def poll_event(self, timeout: float = 0.1) -> Optional[Tuple[str, Any]]: ...
    def get_last_status(self) -> Optional[StatusPayload]: ...
    def get_statistics(self) -> dict: ...
```

### 7.2.2 Event Dispatch Flow

```python
def _handle_frame(self, frame: FrameParseResult) -> None:
    """Internal frame handler called by SerialPortConnection."""
    # 1. Dispatch to raw frame callbacks
    for cb in self._raw_cbs:
        cb(frame)

    # 2. Parse frame to typed payload
    msg_type, payload = self.parser.parse_frame(frame)
    if payload is None:
        return

    # 3. Route based on message type
    if msg_type == "STATUS":
        self._last_status = payload
        self._event_queue.put(("STATUS", payload))
        for cb in self._status_cbs:
            cb(payload)
    elif msg_type == "DATA":
        self._event_queue.put(("DATA", payload))
        for cb in self._data_cbs:
            cb(payload)
    # ... ACK, ERROR similarly
```

### 7.2.3 Usage Examples

```python
# Example 1: Simple status check
from kineintra.api import DeviceClient

client = DeviceClient()
if client.connect(port="/dev/ttyUSB0"):
    client.get_status(seq=1)
    event = client.poll_event(timeout=1.0)
    if event and event[0] == "STATUS":
        print(f"Sensors: {event[1].n_sensors}")
    client.disconnect()

# Example 2: Callback-based streaming
def on_data(payload):
    print(f"[{payload.timestamp}] {payload.samples}")

client = DeviceClient(use_virtual=True)
client.connect()
client.on_data(on_data)
client.start_measure(seq=1)
time.sleep(10)  # Stream for 10 seconds
client.stop_measure(seq=2)
client.disconnect()
```

## 7.3 Command-Line Interface (CLI)

### 7.3.1 Subcommand Overview

| Command | Description | Key Options |
|---------|-------------|-------------|
| `ports` | List available serial ports | `--include-virtual` |
| `connect` | Connect and optionally monitor | `--monitor`, `--raw`, `--types` |
| `status` | Send GET_STATUS | `--seq` |
| `start` | Begin measurement | `--seq` |
| `stop` | Stop measurement | `--seq` |
| `set-nsensors` | Configure sensor count | `N` |
| `set-rate` | Configure sample rate | `SENSOR_IDX`, `HZ` |
| `set-bits` | Configure bit resolution | `SENSOR_IDX`, `BITS` |
| `set-active` | Configure active map | `MAP` (JSON or int) |
| `calibrate` | Start calibration | `--mode` |
| `stop-calibrate` | Abort calibration | `--seq` |
| `end-calibrate` | Finalize calibration | `--seq` |
| `monitor` | Live event stream | `--raw`, `--types`, `--start` |
| `stats` | Show connection statistics | — |

### 7.3.2 Common Options

```
Connection Options (all subcommands except 'ports'):
  --port PORT         Serial port or 'virtual' (default: /dev/ttyUSB0)
  --timeout SECONDS   Connection timeout (default: 2.0)
  --tcp-host HOST     Connect via TCP bridge
  --tcp-port PORT     TCP port (default: 8888)
```

### 7.3.3 Usage Examples

```bash
# List ports
python -m kineintra.cli ports

# Connect and monitor all events
python -m kineintra.cli connect --port /dev/ttyUSB0 --monitor

# Monitor only DATA events
python -m kineintra.cli monitor --port virtual --types DATA

# Configure and start
python -m kineintra.cli set-nsensors 8 --port /dev/ttyUSB0
python -m kineintra.cli set-rate 0 100 --port /dev/ttyUSB0
python -m kineintra.cli start --port /dev/ttyUSB0

# Connect via TCP bridge
python -m kineintra.cli connect --tcp-host 192.168.1.100 --tcp-port 8888 --monitor
```

### 7.3.4 Event Output Formatting

```python
def _print_event(etype: str, payload):
    if etype == "STATUS":
        active = payload.get_active_sensors()
        print(f"STATUS state={payload.state} n={payload.n_sensors} active={active}")
    elif etype == "DATA":
        print(f"DATA ts={payload.timestamp} samples={payload.samples}")
    elif etype == "ACK":
        print(f"ACK cmd={payload.cmd_id} seq={payload.seq} result={payload.result}")
    elif etype == "ERROR":
        print(f"ERROR code={payload.error_code} aux={payload.aux_data}")
```

## 7.4 Graphical User Interface (GUI)

### 7.4.1 Main Window Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  KineIntra                                              [─] [□] [×] │
├─────────────────────────────────────────────────────────────────────┤
│ ┌─Connection──────────────────┐ ┌─Device Status─────────────────┐  │
│ │ Port: [/dev/ttyUSB0    ▼] ↻ │ │ State:   ● MEASURING          │  │
│ │ □ TCP Mode                  │ │ Sensors: 8                     │  │
│ │   Host: [127.0.0.1      ]   │ │ Active:  [0, 1, 2, 3, 4, 5, 6, 7]│
│ │   Port: [8888           ]   │ │ Healthy: [0, 1, 2, 3, 4, 5, 6, 7]│
│ │ [  Connect  ] [Disconnect]  │ │ Rates:   [100, 100, 100, 100]  │  │
│ │ ● Connected                 │ │ Bits:    [12, 12, 12, 12]      │  │
│ └─────────────────────────────┘ │ Updated: 14:32:05              │  │
│                                 └────────────────────────────────┘  │
│ ┌─Command Center───────────────────────────────────────────────┐    │
│ │ Basic Commands                                               │    │
│ │ [Get Status] [▶ Start Measure] [■ Stop Measure]              │    │
│ │                                                              │    │
│ │ Configuration                                                │    │
│ │ N Sensors: [8  ▲▼] [Set]   Rate: [100 ▲▼] Sensor [0▲▼] [Set] │    │
│ │                                                              │    │
│ │ Calibration                                                  │    │
│ │ Mode [0▲▼] [Calibrate] [Stop Cal] [End Cal]                  │    │
│ └──────────────────────────────────────────────────────────────┘    │
│ ┌─Event Log────────────────────────────────────────────────────┐    │
│ │ [14:32:00] STATUS state=MEASURING n=8 active=[0..7]          │    │
│ │ [14:32:01] DATA ts=1234567 samples={0:1234, 1:2345, ...}     │    │
│ │ [14:32:01] DATA ts=1234667 samples={0:1235, 1:2346, ...}     │    │
│ │ [14:32:01] DATA ts=1234767 samples={0:1236, 1:2347, ...}     │    │
│ │                                                              │    │
│ │ DATA count: 3 | [Clear Log]                                  │    │
│ └──────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

### 7.4.2 Panel Classes

| Class | Responsibility | Key Widgets |
|-------|----------------|-------------|
| `ConnectionPanel` | Port selection, TCP mode, connect/disconnect | `QComboBox`, `QCheckBox`, `QPushButton` |
| `StatusPanel` | Display device state, sensor info | `QLabel` grid |
| `CommandPanel` | Send commands, configure sensors | `QPushButton`, `QSpinBox` |
| `EventLogPanel` | Display event stream | `QTextEdit` |

### 7.4.3 Threading Model

```python
class EventPollerThread(QThread):
    """Background thread for non-blocking event polling."""

    status_received = pyqtSignal(object)
    data_received = pyqtSignal(object)
    ack_received = pyqtSignal(object)
    error_received = pyqtSignal(object)

    def __init__(self, client: DeviceClient):
        super().__init__()
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
                # ... etc

    def stop(self):
        self._running = False
        self.wait(2000)
```

### 7.4.4 Signal-Slot Connections

```python
# In MainWindow.__init__
self.poller.status_received.connect(self._on_status_received)
self.poller.data_received.connect(self._on_data_received)
self.cmd_panel.command_requested.connect(self._on_command)
self.conn_panel.connect_btn.clicked.connect(self._on_connect)

# Slot implementations
def _on_status_received(self, payload: StatusPayload):
    self.status_panel.update_status(payload)
    self.log_panel.log_status(payload)

def _on_connect(self):
    params = self.conn_panel.get_connection_params()
    # ... connection logic
```

## 7.5 Transport Abstraction

### 7.5.1 SerialPortConnection Interface

```python
class SerialPortConnection:
    def connect(self, port: Optional[str] = None, timeout: float = 5.0) -> bool: ...
    def disconnect(self) -> bool: ...
    def is_connected(self) -> bool: ...
    def send_frame(self, frame_bytes: bytes) -> bool: ...
    def register_frame_callback(self, cb: Callable[[FrameParseResult], None]) -> None: ...
    def get_statistics(self) -> dict: ...
```

### 7.5.2 Transport Implementations

| Transport | Use Case | Activation |
|-----------|----------|------------|
| **Physical serial** | Production devices | Default (pyserial) |
| **Virtual serial** | Unit/integration tests | `use_virtual=True` |
| **TCP bridge** | Remote devices | `--tcp-host` CLI option |

### 7.5.3 Virtual Serial Patching

```python
def patch_serial_for_testing():
    """Replace serial module with virtual implementation."""
    import kineintra.protocol.serial.serial_connection as sc
    from kineintra.virtual import VirtualSerialModule
    sc.serial = VirtualSerialModule()
```

## 7.6 Protocol Layer Components

### 7.6.1 HostPacketMakerAPI

```python
class HostPacketMakerAPI:
    """Static methods to build COMMAND frames."""

    @staticmethod
    def set_status_request(seq: int) -> bytes: ...

    @staticmethod
    def set_start_measure(seq: int) -> bytes: ...

    @staticmethod
    def set_stop_measure(seq: int) -> bytes: ...

    @staticmethod
    def set_n_sensors(n: int, seq: int) -> bytes: ...

    @staticmethod
    def set_frame_rate(seq: int, sensor_idx: int, rate_hz: int) -> bytes: ...

    @staticmethod
    def set_bits_per_sample(seq: int, sensor_idx: int, bits: int) -> bytes: ...

    @staticmethod
    def set_active_map(sensors: Dict[int, bool], n_sensors: int, seq: int) -> bytes: ...

    @staticmethod
    def set_calibrate(seq: int, mode: int) -> bytes: ...
```

### 7.6.2 ProtocolParser

```python
class ProtocolParser:
    """Parse FrameParseResult into typed payloads."""

    def parse_frame(self, frame: FrameParseResult) -> Tuple[str, Optional[Payload]]:
        if frame.msg_type == FrameType.STATUS:
            return ("STATUS", self._parse_status(frame.payload))
        elif frame.msg_type == FrameType.DATA:
            return ("DATA", self._parse_data(frame.payload))
        elif frame.msg_type == FrameType.ACK:
            return ("ACK", self._parse_ack(frame.payload))
        elif frame.msg_type == FrameType.ERROR:
            return ("ERROR", self._parse_error(frame.payload))
        elif frame.msg_type == FrameType.COMMAND:
            return ("COMMAND", self._parse_command(frame.payload))
        return ("UNKNOWN", None)
```

### 7.6.3 Payload Dataclasses

```python
@dataclass
class StatusPayload:
    state: int
    n_sensors: int
    active_map: int
    health_map: int
    samp_rate_map: List[int]      # 32 entries
    bits_per_smp_map: List[int]   # 32 entries
    sensor_role_map: List[int]    # 32 entries
    adc_flags: int
    reserved: int

    def get_active_sensors(self) -> List[int]:
        return [i for i in range(32) if (self.active_map >> i) & 1]

    def get_healthy_sensors(self) -> List[int]:
        return [i for i in range(32) if (self.health_map >> i) & 1]

@dataclass
class DataPayload:
    timestamp: int
    samples: Dict[int, int]  # sensor_idx -> value

@dataclass
class AckPayload:
    cmd_id: CmdID
    seq: int
    result: AckResult

    def is_success(self) -> bool:
        return self.result == AckResult.OK

@dataclass
class ErrorPayload:
    timestamp: int
    error_code: ErrorCode
    aux_data: int

    def get_error_name(self) -> str:
        return self.error_code.name
```

## 7.7 File References

| Component | File | Lines |
|-----------|------|-------|
| CLI | [kineintra/cli.py](../../kineintra/cli.py) | ~300 |
| DeviceClient | [kineintra/api/device_client.py](../../kineintra/api/device_client.py) | ~200 |
| GUI | [kineintra/gui/main_window.py](../../kineintra/gui/main_window.py) | ~700 |
| Parser | [kineintra/protocol/packets/protocol_parser.py](../../kineintra/protocol/packets/protocol_parser.py) | ~250 |
| Maker | [kineintra/protocol/packets/frame_maker_api.py](../../kineintra/protocol/packets/frame_maker_api.py) | ~200 |
| Reader | [kineintra/protocol/packets/packet_reader.py](../../kineintra/protocol/packets/packet_reader.py) | ~150 |
| Transport | [kineintra/protocol/serial/serial_connection.py](../../kineintra/protocol/serial/serial_connection.py) | ~200 |

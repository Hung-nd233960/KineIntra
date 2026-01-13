# KineIntra System Architecture and Testing Guide

This document provides a detailed overview of the KineIntra system: design goals, key components, data flow, and how the testing infrastructure validates correctness. It is meant for contributors and integrators who need a deep understanding of how the host side communicates with the device and how to reason about each layer.

## Overview

KineIntra is organized into layered modules that separate concerns:

- Application layer: Command-line interface and optional GUI.
- Host API layer: High-level device client with an event model.
- Protocol layer: Packet framing, parsing, and configuration enums.
- Transport layer: Serial port connection (physical or virtual) and TCP bridge.
- Sensor signal utilities: FSR signal conversions and calibrator examples.
- Tests: Roundtrip protocol tests and virtual serial integration tests.

## Architecture Diagram

```
+------------------+       +------------------+       +------------------+
|   CLI / GUI      |  -->  |  Host API        |  -->  |  Protocol Packets |
|  (User Commands) |       |  (DeviceClient)  |       |  + Parser/Reader  |
+------------------+       +------------------+       +------------------+
         |                             |                          |
         v                             v                          v
   User events /                 Command bytes                 Framed bytes
   display updates                 (HostPacketMakerAPI)        (CRC, FrameType)
         |                             |                          |
         +---------------------------->|                          |
                                       v                          v
                               +------------------+       +------------------+
                               | Transport Layer  |  <--> |  Serial / TCP    |
                               | (SerialPortConn) |       |  Physical or     |
                               +------------------+       |  Virtual adapter |
                                                            +------------------+

Device responses (STATUS/DATA/ACK/ERROR) bubble back up -> ByteReader -> ProtocolParser -> DeviceClient callbacks/event queue -> CLI/GUI display.
```

## Components

### CLI

- File: [kineintra/cli.py](kineintra/cli.py)
- Purpose: A user-facing command-line tool built on the high-level `DeviceClient`. It supports listing ports, connecting (real, virtual, or TCP bridged), sending commands, and monitoring events.
- Key capabilities:
  - List ports including virtual: `ports`
  - Connect and monitor: `connect`, `monitor`
  - Device control: `status`, `start`, `stop`, `calibrate`, `stop-calibrate`, `end-calibrate`
  - Configuration: `set-nsensors`, `set-rate`, `set-bits`, `set-active`
  - Statistics: `stats`
- Highlights:
  - Uses `list_ports()` from the API to include physical and virtual ports.
  - Can enable TCP mode by patching the serial layer (see Virtual/TCP below).
  - Monitors events via `DeviceClient.poll_event()` and prints formatted payloads.

Usage examples:

```bash
# List available ports (includes 'virtual')
python -m kineintra.cli ports

# Connect to virtual and monitor STATUS/DATA/ACK/ERROR
python -m kineintra.cli connect --port virtual --monitor

# Send GET_STATUS to a physical port, then monitor
python -m kineintra.cli connect --port /dev/ttyUSB0 --send-status --monitor

# Bridge via TCP virtual server
python -m kineintra.cli connect --tcp-host 127.0.0.1 --tcp-port 8888 --monitor

# Configure sensors
python -m kineintra.cli set-nsensors 8
python -m kineintra.cli set-rate 0 100
python -m kineintra.cli set-bits 0 12
python -m kineintra.cli set-active 0x3
```

### GUI

- File: [kineintra/gui/main_window.py](kineintra/gui/main_window.py)
- Purpose: A PyQt6 main window that wraps connection management, status display, command center, and event logging.
- Key classes:
  - `EventPollerThread`: polls `DeviceClient.poll_event()` and emits signals for `STATUS`, `DATA`, `ACK`, `ERROR`.
  - `ConnectionPanel`: port selection, TCP mode toggling, connect/disconnect, visual status.
  - `StatusPanel`: renders device state, sensor counts, active/healthy maps, sample rates, bits per sample.
  - `CommandPanel`: buttons for status, start/stop measure, sensor count, per-sensor rate, and calibration.
  - `EventLogPanel`: textual log of events, with truncation management.
- Reasoning:
  - GUI decouples UI updates via signals from the polling thread, keeping the main thread responsive.
  - Panels encapsulate responsibilities (connection, status, commands, logs) for clarity and testability.

### Host API (`DeviceClient`)

- File: [kineintra/api/device_client.py](kineintra/api/device_client.py)
- Purpose: A high-level convenience wrapper that:
  - Manages connection via `SerialPortConnection`.
  - Sends commands using `HostPacketMakerAPI`.
  - Parses frames using `ProtocolParser`.
  - Dispatches events via callbacks and a small event queue.
- Interface highlights:
  - Connection: `connect()`, `disconnect()`, `is_connected()`.
  - Commands: `get_status()`, `start_measure()`, `stop_measure()`, `set_nsensors()`, `set_rate()`, `set_bits()`, `set_active_map()`, `calibrate()`, `stop_calibrate()`, `end_calibrate()`.
  - Events: `on_status()`, `on_data()`, `on_ack()`, `on_error()`, `on_raw_frame()`.
  - Monitoring: `poll_event()` returns `(etype, payload)` tuples for use by CLI/GUI.
  - Utilities: `list_ports()`, `format_status()`.
- Reasoning:
  - Centralizes protocol details and transport concerns, presenting a simple host-side API.
  - Event callbacks plus polling allow both reactive and imperative consumption models.

### Protocol Layer

- Directory: [kineintra/protocol](kineintra/protocol)
- Purpose: Defines frame structures, config enums, makers/readers/parsers, and serial configuration.
- Key elements (from `packets` submodule):
  - `FrameType`, `CmdID`, `AckResult`, `ErrorCode` enums.
  - `HostPacketMakerAPI` and `DevicePacketMaker` to construct frames.
  - `ByteReader` to consume streaming bytes into frames with CRC validation.
  - `ProtocolParser` to translate frames into typed payloads: `CommandPayload`, `StatusPayload`, `DataPayload`, `AckPayload`, `ErrorPayload`.
- Reasoning:
  - By separating byte-level concerns from host logic, the system remains testable and maintainable.
  - Roundtrip tests ensure builders and parsers remain in sync across changes.

### Transport Layer (Serial/TCP)

- Serial connection implementation resides under [kineintra/protocol/serial](kineintra/protocol/serial).
- `SerialPortConnection` exposes:
  - `connect(port, timeout)`, `disconnect()`, `is_connected()`
  - `send_frame(bytes)`
  - `register_frame_callback(cb)` delivering `FrameParseResult` instances
  - `get_statistics()` for session-level metrics
- TCP bridge and virtual adapters are available under the `system` and `virtual` namespaces:
  - Virtual serial for tests: [tests/virtual_port.py](tests/virtual_port.py)
  - Patching helpers referenced by the API/CLI for testing/remote operation via TCP.
- Reasoning:
  - A single connection abstraction allows swapping real serial, virtual serial, or TCP bridged transports without changing higher layers.

### System Helpers (Device/Server/Signal/TCP)

- Directory: [kineintra/system](kineintra/system)
- Purpose: Utility modules for device abstraction, a TCP server/adapter to expose/bridge serial over TCP, synthetic signal generation, and layering helpers.
- Typical roles:
  - `device.py`: device-side abstractions for state and operations.
  - `serial_layer.py`: orchestration and lifecycle of serial/TCP adapters.
  - `server.py`: a lightweight TCP server exposing the device to remote clients.
  - `signal_generator.py`: build synthetic sensor signals for demos/tests.
  - `tcp_adapter.py`: translate TCP messages to serial protocol frames and back.
  - `tcp_client.py`: client helpers to connect to remote server.
- Note: Exact implementations can vary across versions; this section captures their intended responsibilities and interactions.

### Sensor Signal Utilities (FSR)

- File: [kineintra/FSR_signal/adc_signal.py](kineintra/FSR_signal/adc_signal.py)
- Purpose: Convert ADC signals to voltages and resistances based on voltage divider principles.
- Functions:
  - `adc_signal_to_voltage(adc_signal, max_voltage=1.024, resolution=1024) -> float`
  - `voltage_to_resistance(source_voltage, known_resistance, measured_voltage, measuring_resistance) -> float`
  - `adc_signal_to_resistance(adc_signal, source_voltage, known_resistance, ...) -> float`
- Reasoning:
  - Encapsulates electrical math with clear enums (`MeasuringResistor`) to avoid mistakes when deriving resistances from readings.

## Data Flow

1. A user action in CLI/GUI triggers a high-level call on `DeviceClient`.
2. `DeviceClient` uses `HostPacketMakerAPI` to build a command frame (bytes).
3. `SerialPortConnection` writes the frame to the serial/TCP transport.
4. The device responds with framed bytes (`STATUS`, `DATA`, `ACK`, `ERROR`).
5. `SerialPortConnection` feeds bytes into `ByteReader`, producing `FrameParseResult`s.
6. `ProtocolParser` converts frames to typed payloads.
7. `DeviceClient` dispatches callbacks and queues events for the CLI/GUI to consume.

## Event Model and Reasoning

- `DeviceClient` combines callback lists with a simple queue:
  - Callbacks (`on_status/on_data/on_ack/on_error`) are ideal for streaming consumers and background processing.
  - `poll_event()` provides a bounded-wait queue for UI loops and CLIs without threading complexity.
- Exception-safe dispatching:
  - Each callback execution is wrapped to avoid crashing due to consumer errors; exceptions are logged.
- Status caching:
  - `get_last_status()` allows synchronous access to the most recent `STATUS` payload.

## Testing

### Protocol Roundtrip Tests

- File: [tests/test_packet_parser_roundtrip.py](tests/test_packet_parser_roundtrip.py)
- Validates that all key frame types can be constructed, read, parsed, and inspected correctly:
  - COMMAND via `HostPacketMakerAPI` parses into `CommandPayload` with correct `cmd_id`, `seq`, `args`.
  - STATUS frames set `n_sensors`, active/healthy maps, rates, bits.
  - DATA frames carry `timestamp` and per-sensor values, respecting bit widths.
  - ACK frames match command ids, sequence numbers, and success results.
  - ERROR frames include codes, aux data, and names.
- Reasoning:
  - Ensures byte-level changes don’t break semantic parsing and payload typing.

### Virtual Serial Integration Tests

- File: [tests/test_serial_virtual.py](tests/test_serial_virtual.py)
- Patches the serial dependency of `SerialPortConnection` to a virtual implementation ([tests/virtual_port.py](tests/virtual_port.py)).
- Verifies:
  - Connect/disconnect lifecycle changes state correctly.
  - Heartbeat `STATUS` frames arrive unsolicited while connected.
  - Sending `GET_STATUS` yields an `ACK` and subsequent `STATUS` from the virtual device.
- Reasoning:
  - Confirms end-to-end path from host API to transport and back under controlled conditions.

### How to Run Tests

```bash
# From the workspace root
python -m pytest -q

# Or, pick a specific test module
python -m pytest tests/test_packet_parser_roundtrip.py -q
python -m pytest tests/test_serial_virtual.py -q
```

## Practical Usage

### Using `DeviceClient` directly

```python
from kineintra.api import DeviceClient

client = DeviceClient(use_virtual=True)
assert client.connect(timeout=1.0)

# Subscribe to status updates
client.on_status(lambda s: print("STATUS", s.n_sensors, s.get_active_sensors()))

# Send a command
client.get_status(seq=1)

# Poll events (CLI-style)
for _ in range(10):
    evt = client.poll_event(timeout=0.2)
    if evt:
        etype, payload = evt
        print(etype, payload)

client.disconnect()
```

### CLI Quick Reference

- List ports: `ports`
- Connect: `connect [--port /dev/ttyUSB0 | --port virtual | --tcp-host HOST --tcp-port N]`
- Monitor: `connect --monitor` or `monitor`
- Status: `status --seq N`
- Control: `start`, `stop`
- Configure: `set-nsensors N`, `set-rate IDX HZ`, `set-bits IDX BITS`, `set-active MAP`

## Extensibility

- Adding a new command:
  - Implement frame builder in `HostPacketMakerAPI` (protocol/packets).
  - Add a convenience wrapper in `DeviceClient`.
  - Expose via CLI subcommand or GUI button.
  - Extend parser and tests if new frame or payload types are introduced.

## Notes

- TCP mode in the CLI enables a remote virtual server; ensure the server is running and reachable. The API marks TCP usage and adjusts how the port is interpreted.
- GUI relies on PyQt6; install required dependencies listed in the project’s `requirements.txt` before attempting to run a UI harness.

---

This guide reflects the structure observed in the provided workspace and attachments. If modules evolve (especially under `system` or transport adapters), update this document to keep component responsibilities and data flow accurate.

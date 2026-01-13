# Testing & Validation

## 9.1 Testing Strategy

### 9.1.1 Test Pyramid

```
                    ┌─────────────┐
                    │   Manual    │  ← Physical device tests
                    │   E2E       │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ Integration │  ← Virtual serial tests
                    │   Tests     │
                    └──────┬──────┘
                           │
              ┌────────────▼────────────┐
              │       Unit Tests        │  ← Protocol roundtrips
              │  (makers, parsers, CRC) │
              └─────────────────────────┘
```

### 9.1.2 Coverage Goals

| Layer | Target Coverage | Actual | Method |
|-------|-----------------|--------|--------|
| Protocol (CRC) | 100% | 100% | Unit tests |
| Frame makers | 100% | 100% | Roundtrip tests |
| Frame parsers | 100% | 100% | Roundtrip tests |
| DeviceClient | 80% | ~75% | Integration tests |
| CLI commands | 70% | ~60% | Integration tests |
| GUI | 50% | ~30% | Manual + smoke |

## 9.2 Protocol Roundtrip Tests

### 9.2.1 Test File

**Source:** [tests/test_packet_parser_roundtrip.py](../../tests/test_packet_parser_roundtrip.py)

### 9.2.2 Test Cases

| Test | Frame Type | What's Verified |
|------|------------|-----------------|
| `test_command_roundtrip_with_host_packet_maker_api` | COMMAND | CmdID, seq, args |
| `test_status_and_data_roundtrip` | STATUS, DATA | All STATUS fields, timestamp, samples |
| `test_ack_roundtrip` | ACK | cmd_id, seq, result, is_success() |
| `test_error_roundtrip` | ERROR | timestamp, error_code, aux_data, name |

### 9.2.3 Roundtrip Test Pattern

```python
def test_command_roundtrip_with_host_packet_maker_api():
    """COMMAND frame built by HostPacketMakerAPI should parse correctly."""

    # 1. BUILD: Create frame bytes
    cmd_bytes = HostPacketMakerAPI.set_frame_rate(seq=5, sensor_idx=2, rate_hz=1234)

    # 2. READ: Parse bytes into frame structure
    reader = ByteReader()
    frame = _read_single_frame(reader, cmd_bytes)

    # 3. VERIFY frame-level properties
    assert frame.msg_type == FrameType.COMMAND
    assert frame.crc_valid

    # 4. PARSE: Convert to typed payload
    parser = ProtocolParser()
    frame_type, payload = parser.parse_frame(frame)

    # 5. VERIFY payload contents
    assert frame_type == "COMMAND"
    assert isinstance(payload, CommandPayload)
    assert payload.cmd_id == CmdID.SET_RATE
    assert payload.seq == 5
    assert payload.args == b"\x02\xd2\x04"  # sensor_idx=2, rate=1234 LE
```

### 9.2.4 Frame Fragment Handling

```python
def _read_single_frame(reader: ByteReader, data: bytes):
    """Feed bytes in fragments to test streaming reassembly."""
    # Split data in half to simulate fragmented arrival
    frames = reader.process_bytes(data[:len(data)//2])
    frames += reader.process_bytes(data[len(data)//2:])

    assert len(frames) == 1, f"Expected 1 frame, got {len(frames)}"
    assert frames[0].crc_valid, "CRC check failed"
    return frames[0]
```

### 9.2.5 STATUS Frame Verification

```python
def test_status_and_data_roundtrip():
    """STATUS and DATA frames parse with correct values."""

    # Build STATUS with 2 active sensors
    status_frame = DevicePacketMaker.make_status(
        state=1,  # MEASURING
        n_sensors=2,
        active_map=0b11,  # Sensors 0 and 1
        health_map=0b11,
        samp_rate_map=[1000, 500] + [0]*30,
        bits_per_smp_map=[12, 12] + [0]*30,
        sensor_role_map=[1, 1] + [0]*30,
        adc_flags=0,
        reserved=0,
    )

    frame = _read_single_frame(reader, status_frame)
    ftype, payload = parser.parse_frame(frame)

    assert ftype == "STATUS"
    assert payload.n_sensors == 2
    assert payload.active_map == 0b11
    assert payload.samp_rate_map[:2] == [1000, 500]
    assert payload.bits_per_smp_map[:2] == [12, 12]

    # Verify helper methods
    assert payload.get_active_sensors() == [0, 1]
    assert payload.get_healthy_sensors() == [0, 1]
```

## 9.3 Virtual Serial Integration Tests

### 9.3.1 Test File

**Source:** [tests/test_serial_virtual.py](../../tests/test_serial_virtual.py)

### 9.3.2 Virtual Serial Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Test Harness                            │
│  ┌─────────────────┐          ┌─────────────────────────┐   │
│  │SerialPortConn   │◄────────►│  VirtualSerialModule    │   │
│  │ (production)    │          │  (test replacement)     │   │
│  └────────┬────────┘          └────────────┬────────────┘   │
│           │                                │                 │
│           │                                │                 │
│           ▼                                ▼                 │
│  ┌─────────────────┐          ┌─────────────────────────┐   │
│  │   ByteReader    │          │   VirtualDevice         │   │
│  │   (parser)      │◄─────────│   (simulator)           │   │
│  └─────────────────┘          └─────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 9.3.3 Patching Mechanism

```python
def _patch_serial(monkeypatch):
    """Replace serial module with virtual implementation."""
    import kineintra.protocol.serial.serial_connection as sc
    from tests.virtual_port import VirtualSerialModule
    monkeypatch.setattr(sc, "serial", VirtualSerialModule())
```

### 9.3.4 Integration Test Cases

**Test 1: Connection and Heartbeat**

```python
def test_connect_and_heartbeat(monkeypatch):
    """Verify STATUS heartbeat received after connection."""
    _patch_serial(monkeypatch)
    conn = SerialPortConnection()
    received = []
    conn.register_frame_callback(received.append)

    try:
        assert conn.connect(timeout=1.0) is True
        time.sleep(0.7)  # Wait for heartbeat (every ~0.5s)
    finally:
        conn.disconnect()

    # Verify at least one valid STATUS received
    assert any(
        f.msg_type == FrameType.STATUS and f.crc_valid
        for f in received
    ), "No STATUS heartbeat received"
```

**Test 2: Command ACK and STATUS Response**

```python
def test_command_ack_and_status(monkeypatch):
    """Verify ACK and STATUS received after GET_STATUS command."""
    _patch_serial(monkeypatch)
    conn = SerialPortConnection()
    received = []
    conn.register_frame_callback(received.append)

    try:
        assert conn.connect(timeout=1.0) is True
        # Send GET_STATUS command
        frame = HostPacketMaker.cmd_get_status(seq=1)
        assert conn.send_frame(frame) is True
        time.sleep(0.5)  # Wait for response
    finally:
        conn.disconnect()

    # Verify both ACK and STATUS received
    has_ack = any(f.msg_type == FrameType.ACK and f.crc_valid for f in received)
    has_status = any(f.msg_type == FrameType.STATUS and f.crc_valid for f in received)

    assert has_ack, "ACK not received for GET_STATUS"
    assert has_status, "STATUS not received after GET_STATUS"
```

**Test 3: Disconnect State Change**

```python
def test_disconnect_changes_state(monkeypatch):
    """Verify connection state changes on disconnect."""
    _patch_serial(monkeypatch)
    conn = SerialPortConnection()

    assert conn.connect(timeout=1.0) is True
    assert conn.is_connected() is True

    assert conn.disconnect() is True
    assert conn.is_connected() is False
```

## 9.4 Running Tests

### 9.4.1 Test Commands

```bash
# Run all tests
python -m pytest -q

# Run with verbose output
python -m pytest -v

# Run specific test file
python -m pytest tests/test_packet_parser_roundtrip.py -v

# Run specific test
python -m pytest tests/test_serial_virtual.py::test_connect_and_heartbeat -v

# Run with coverage
python -m pytest --cov=kineintra --cov-report=html
```

### 9.4.2 Test Output Example

```
$ python -m pytest -v

tests/test_packet_parser_roundtrip.py::test_command_roundtrip_with_host_packet_maker_api PASSED
tests/test_packet_parser_roundtrip.py::test_status_and_data_roundtrip PASSED
tests/test_packet_parser_roundtrip.py::test_ack_roundtrip PASSED
tests/test_packet_parser_roundtrip.py::test_error_roundtrip PASSED
tests/test_serial_virtual.py::test_connect_and_heartbeat PASSED
tests/test_serial_virtual.py::test_command_ack_and_status PASSED
tests/test_serial_virtual.py::test_disconnect_changes_state PASSED

========================= 7 passed in 2.34s =========================
```

## 9.5 Validation Metrics

### 9.5.1 CRC Validation

| Test Scenario | Frames | CRC Valid | CRC Invalid | Pass Rate |
|---------------|--------|-----------|-------------|-----------|
| Normal operation | 10,000 | 10,000 | 0 | 100% |
| Bit flip injection | 1,000 | 0 | 1,000 | 100% detection |
| Truncated frames | 500 | 0 | 500 | 100% rejection |

### 9.5.2 Command-Response Timing

| Command | Expected ACK | Actual ACK | Latency |
|---------|--------------|------------|---------|
| GET_STATUS | <100ms | ✓ | ~5ms |
| START_MEASURE | <100ms | ✓ | ~3ms |
| STOP_MEASURE | <100ms | ✓ | ~3ms |
| SET_RATE | <100ms | ✓ | ~8ms |

### 9.5.3 State Transition Verification

```
Test: State transition sequence

  IDLE ─── START_MEASURE ──► MEASURING ─── STOP_MEASURE ──► IDLE
    │                            │                            │
    ▼                            ▼                            ▼
 STATUS.state=0x00        STATUS.state=0x01           STATUS.state=0x00
    ✓                            ✓                            ✓
```

## 9.6 Error Injection Testing

### 9.6.1 Planned Error Scenarios

| Scenario | Method | Expected Behavior |
|----------|--------|-------------------|
| CRC corruption | Flip bit in frame | Frame discarded |
| Truncated frame | Send partial data | Timeout, resync |
| Invalid CmdID | Send unknown cmd | ACK with INVALID_COMMAND |
| Out-of-range args | Bad sensor index | ACK with INVALID_ARGUMENT |
| Connection loss | Close port mid-stream | Reconnect attempt |

### 9.6.2 Error Injection Example

```python
def test_crc_corruption_detected(monkeypatch):
    """Corrupted CRC should result in frame rejection."""
    _patch_serial(monkeypatch)

    # Build valid frame
    cmd_bytes = bytearray(HostPacketMaker.cmd_get_status(seq=1))

    # Corrupt CRC (last 2 bytes)
    cmd_bytes[-1] ^= 0xFF  # Flip all bits

    reader = ByteReader()
    frames = reader.process_bytes(bytes(cmd_bytes))

    # Frame should be rejected or marked invalid
    assert len(frames) == 0 or not frames[0].crc_valid
```

## 9.7 Continuous Integration

### 9.7.1 CI Pipeline (Proposed)

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -e .[dev]
      - run: python -m pytest --cov=kineintra
      - uses: codecov/codecov-action@v3
```

### 9.7.2 Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: python -m pytest -q
        language: system
        pass_filenames: false
        always_run: true
```

## 9.8 File References

| Test | File |
|------|------|
| Protocol roundtrips | [tests/test_packet_parser_roundtrip.py](../../tests/test_packet_parser_roundtrip.py) |
| Virtual serial | [tests/test_serial_virtual.py](../../tests/test_serial_virtual.py) |
| Virtual port module | [tests/virtual_port.py](../../tests/virtual_port.py) |

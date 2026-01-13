# Communication Protocol

## 5.1 Protocol Design Goals

### 5.1.1 Primary Objectives

1. **Reliability**: Detect transmission errors with high probability (CRC-16)
2. **Efficiency**: Minimize overhead for high-frequency streaming (8-byte envelope)
3. **Simplicity**: Enable implementation on resource-constrained MCUs
4. **Extensibility**: Support future message types without breaking changes
5. **Debuggability**: Fixed structure aids hex dump analysis

### 5.1.2 Design Constraints

- MCU RAM: ~320KB (ESP32) — must support fixed buffers
- Serial bandwidth: 115200 baud → ~11.5 KB/s effective
- Latency target: <10ms for command-response cycle
- Sensor count: Up to 32 channels with independent configuration

## 5.2 Frame Envelope Structure

### 5.2.1 Overall Frame Format

```
┌─────┬─────┬──────┬──────┬─────────────┬───────┐
│ SOF │ Ver │ Type │ Len  │   Payload   │ CRC16 │
│ 2B  │ 1B  │ 1B   │ 2B   │   N bytes   │  2B   │
└─────┴─────┴──────┴──────┴─────────────┴───────┘
       │◄────────── CRC coverage ─────────────►│
```

### 5.2.2 Field Specifications

| Field | Offset | Size | Value/Range | Description |
|-------|--------|------|-------------|-------------|
| **SOF** | 0 | 2 | `0xA5 0x5A` | Start-of-Frame marker (not in CRC) |
| **Ver** | 2 | 1 | `0x01` | Protocol version |
| **Type** | 3 | 1 | `0x01–0x05` | Message type identifier |
| **Len** | 4 | 2 | `0–65535` | Payload length (little-endian) |
| **Payload** | 6 | N | Variable | Type-specific data |
| **CRC16** | 6+N | 2 | Calculated | CRC-16-CCITT (little-endian) |

### 5.2.3 CRC Calculation

```
Polynomial: 0x1021 (CRC-16-CCITT)
Initial value: 0xFFFF
Input reflection: No
Output reflection: No
Final XOR: None

Coverage: Ver | Type | Len | Payload
```

**Python implementation:**

```python
def calculate_crc16(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
        crc &= 0xFFFF
    return crc
```

## 5.3 Message Types

### 5.3.1 Type Enumeration

| Type | Value | Direction | Description |
|------|-------|-----------|-------------|
| `STATUS` | `0x01` | Device → Host | Device state and configuration |
| `DATA` | `0x02` | Device → Host | Sensor readings with timestamp |
| `COMMAND` | `0x03` | Host → Device | Control and configuration commands |
| `ACK` | `0x04` | Device → Host | Command acknowledgment |
| `ERROR` | `0x05` | Device → Host | Asynchronous error notification |

### 5.3.2 Message Flow Patterns

```
Pattern 1: Status Request
    Host ──COMMAND(GET_STATUS)──► Device
    Host ◄──ACK(OK)────────────── Device
    Host ◄──STATUS─────────────── Device

Pattern 2: Start Measurement
    Host ──COMMAND(START)────────► Device
    Host ◄──ACK(OK)────────────── Device
    Host ◄──DATA───────────────── Device (continuous)
    Host ◄──DATA───────────────── Device
    ...

Pattern 3: Unsolicited Events
    Host ◄──STATUS (heartbeat)─── Device (periodic)
    Host ◄──ERROR (fault)──────── Device (async)
```

## 5.4 STATUS Frame (0x01)

### 5.4.1 Payload Layout (144 bytes)

```
Offset  Size   Field           Description
──────  ────   ─────           ───────────
0       1      State           Device operational state
1       1      NSensors        Number of active sensors
2       4      ActiveMap       Bitmap of enabled sensors (LE)
6       4      HealthMap       Bitmap of healthy sensors (LE)
10      64     SampRateMap     Per-sensor sample rates (32 × uint16 LE)
74      32     BitsPerSmpMap   Per-sensor bit resolutions (32 × uint8)
106     32     SensorRoleMap   Per-sensor semantic roles (32 × uint8)
138     2      ADCFlags        ADC subsystem status flags
140     2      Reserved        Future use (set to 0)
142     2      (padding)       Alignment padding
──────────────────────────────────────────────────────────
Total: 144 bytes
```

### 5.4.2 State Values

| Value | Name | Description |
|-------|------|-------------|
| `0x00` | IDLE | Ready, not acquiring |
| `0x01` | MEASURING | Actively streaming DATA |
| `0x02` | CALIBRATING | Calibration in progress |
| `0x03` | ERROR | Fault condition |

### 5.4.3 Bitmap Interpretation

```python
# Example: ActiveMap = 0x00000007 (sensors 0, 1, 2 enabled)
active_sensors = [i for i in range(32) if (active_map >> i) & 1]
# Result: [0, 1, 2]
```

### 5.4.4 SampRateMap Semantics

- Index `i` corresponds to sensor `i` (0–31)
- Value is sample rate in Hz (0–65535)
- Example: `SampRateMap[0] = 100` → Sensor 0 samples at 100 Hz

## 5.5 DATA Frame (0x02)

### 5.5.1 Payload Layout

```
Offset  Size        Field       Description
──────  ────        ─────       ───────────
0       4           Timestamp   Microseconds since device start (LE)
4       Variable    Samples     Packed sensor values
```

### 5.5.2 Sample Encoding Rules

| BitsPerSmp | Bytes/Sample | Padding | Example |
|------------|--------------|---------|---------|
| 1–8 | 1 | To 8 bits | 10-bit → stored in 2 bytes |
| 9–16 | 2 | To 16 bits | 12-bit ADC → 2 bytes LE |
| 17–24 | 3 | To 24 bits | 24-bit ADC → 3 bytes LE |
| 25–32 | 4 | To 32 bits | 32-bit value → 4 bytes LE |

### 5.5.3 Sample Ordering

- Samples appear in ascending sensor index order
- Only active sensors (per ActiveMap) are included
- Example with `ActiveMap = 0b0101` (sensors 0 and 2):

  ```
  Payload: [Timestamp(4)] [Sample0(2)] [Sample2(2)]
  ```

### 5.5.4 Payload Size Calculation

```python
def calc_data_payload_size(active_map: int, bits_map: list) -> int:
    size = 4  # Timestamp
    for i in range(32):
        if (active_map >> i) & 1:
            bits = bits_map[i]
            size += (bits + 7) // 8  # Round up to bytes
    return size
```

## 5.6 COMMAND Frame (0x03)

### 5.6.1 Payload Layout

```
Offset  Size   Field    Description
──────  ────   ─────    ───────────
0       1      CmdID    Command identifier
1       1      Seq      Sequence number (0–255)
2       N      Args     Command-specific arguments
```

### 5.6.2 Command Identifiers

| CmdID | Name | Args | Description |
|-------|------|------|-------------|
| `0x01` | GET_STATUS | None | Request STATUS frame |
| `0x02` | START_MEASURE | None | Begin data acquisition |
| `0x03` | STOP_MEASURE | None | Stop data acquisition |
| `0x04` | SET_NSENSORS | `uint8 n` | Set active sensor count |
| `0x05` | SET_RATE | `uint8 idx, uint16 hz` | Set sensor sample rate |
| `0x06` | SET_BITS | `uint8 idx, uint8 bits` | Set sensor resolution |
| `0x07` | SET_ACTIVEMAP | `uint32 map` | Set enabled sensors bitmap |
| `0x08` | CALIBRATE | `uint8 mode` | Start calibration |
| `0x09` | STOP_CALIBRATE | None | Abort calibration |
| `0x0A` | END_CALIBRATE | None | Finalize calibration |

### 5.6.3 Sequence Number Usage

- Monotonically incrementing (wraps at 255)
- Echoed in ACK for request-response correlation
- Host can detect missed/reordered ACKs

## 5.7 ACK Frame (0x04)

### 5.7.1 Payload Layout (3 bytes)

```
Offset  Size   Field    Description
──────  ────   ─────    ───────────
0       1      CmdID    Command being acknowledged
1       1      Seq      Sequence from original command
2       1      Result   Result code
```

### 5.7.2 Result Codes

| Value | Name | Description |
|-------|------|-------------|
| `0x00` | OK | Command executed successfully |
| `0x01` | INVALID_COMMAND | Unknown CmdID |
| `0x02` | INVALID_ARGUMENT | Argument out of range |
| `0x03` | BUSY | Device busy, try later |
| `0x04` | FAILED | Execution failed |
| `0x05` | NOT_ALLOWED | Command not permitted in current state |

## 5.8 ERROR Frame (0x05)

### 5.8.1 Payload Layout (7 bytes)

```
Offset  Size   Field      Description
──────  ────   ─────      ───────────
0       4      Timestamp  Microseconds since device start (LE)
4       1      ErrCode    Error type
5       2      AuxData    Context-dependent data (LE)
```

### 5.8.2 Error Codes

| Value | Name | AuxData | Trigger |
|-------|------|---------|---------|
| `0x01` | ADC_OVERRUN | Channel mask | ADC data lost |
| `0x02` | SENSOR_FAULT | Sensor index | Sensor disconnected |
| `0x03` | FIFO_CRITICAL | Fill level | Buffer overflow |
| `0x04` | LOW_VOLTAGE | Voltage × 100 | Power below threshold |
| `0xFE` | VENDOR_SPECIFIC | Vendor-defined | Custom error |

## 5.9 Protocol State Machine

### 5.9.1 Host States

```
                    ┌──────────────┐
                    │ Disconnected │
                    └──────┬───────┘
                           │ connect()
                           ▼
                    ┌──────────────┐
              ┌────►│   Connected  │◄────┐
              │     └──────┬───────┘     │
              │            │             │
     disconnect()    ┌─────┴─────┐      poll
              │      │           │       │
              │      ▼           ▼       │
              │ ┌─────────┐ ┌─────────┐  │
              └─│ Command │ │ Monitor │──┘
                │  Mode   │ │  Mode   │
                └─────────┘ └─────────┘
```

### 5.9.2 Device States

```
                    ┌───────┐
            ┌──────►│ IDLE  │◄──────┐
            │       └───┬───┘       │
            │           │           │
       STOP_MEASURE   START    END_CALIBRATE
            │           │           │
            │           ▼           │
            │    ┌────────────┐     │
            └────│ MEASURING  │     │
                 └────────────┘     │
                                    │
                    CALIBRATE       │
                        │           │
                        ▼           │
                 ┌────────────┐     │
                 │CALIBRATING │─────┘
                 └────────────┘
```

## 5.10 Implementation Notes

### 5.10.1 Frame Synchronization

- On sync loss, scan for SOF bytes (0xA5 0x5A)
- Validate CRC before processing
- Discard partial frames on timeout (e.g., 100ms)

### 5.10.2 Bandwidth Calculations

| Scenario | Sensors | Rate | Bits | Payload | Frame | Bandwidth |
|----------|---------|------|------|---------|-------|-----------|
| Single sensor | 1 | 100 Hz | 16 | 6 B | 14 B | 1.4 KB/s |
| 8 sensors | 8 | 100 Hz | 16 | 20 B | 28 B | 2.8 KB/s |
| 32 sensors | 32 | 100 Hz | 16 | 68 B | 76 B | 7.6 KB/s |
| 32 sensors | 32 | 1000 Hz | 12 | 68 B | 76 B | 76 KB/s ⚠️ |

⚠️ Exceeds 115200 baud capacity (~11.5 KB/s); requires higher baud or reduced config.

### 5.10.3 Reference Implementation

- Specification: [Communication_Stack/PROTOCOL.md](../../Communication_Stack/PROTOCOL.md)
- Host maker: [kineintra/protocol/packets/frame_maker_api.py](../../kineintra/protocol/packets/frame_maker_api.py)
- Host parser: [kineintra/protocol/packets/protocol_parser.py](../../kineintra/protocol/packets/protocol_parser.py)
- Device firmware: [Communication_Stack/for_mcu/client_device.ino](../../Communication_Stack/for_mcu/client_device.ino)

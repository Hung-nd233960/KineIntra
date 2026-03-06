# Device Firmware (MCU)

## 6.1 Hardware Platform

### 6.1.1 Microcontroller Selection

| Feature | ESP32 | Requirement | Notes |
|---------|-------|-------------|-------|
| CPU | Dual-core 240 MHz | ✓ | Non-blocking RX/TX |
| RAM | 320 KB | ✓ | Fixed buffers for 32 sensors |
| Flash | 4 MB | ✓ | Firmware + calibration storage |
| UART | 3 interfaces | ✓ | Dedicated serial |
| I2C | 2 buses | ✓ | ADS1115 ADC connection |
| GPIO | 34 pins | ✓ | Status LED, expansion |

### 6.1.2 ADC Module (ADS1115)

| Specification | Value | Application |
|---------------|-------|-------------|
| Resolution | 16-bit | High-precision FSR readings |
| Channels | 4 (multiplexed) | Single-ended or differential |
| Sample rate | 8–860 SPS | Configurable per application |
| PGA gain | ±0.256V to ±6.144V | GAIN_FOUR (±1.024V) selected |
| Interface | I2C (400 kHz) | Address 0x48–0x4B |

### 6.1.3 Schematic Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         ESP32                                │
│                                                              │
│   GPIO2 ────────────► LED (Status indicator)                │
│                                                              │
│   TX (GPIO1) ────────► USB-Serial ────► Host Computer       │
│   RX (GPIO3) ◄──────── (115200 baud)                        │
│                                                              │
│   SDA (GPIO21) ◄────┬────► ADS1115 #1 (0x48) ◄── FSR 0-3   │
│   SCL (GPIO22) ◄────┘     ADS1115 #2 (0x49) ◄── FSR 4-7   │
│                           ...                                │
│                                                              │
│   VCC ──────────────────► 3.3V ──────────────► Sensor VCC   │
│   GND ──────────────────► Common Ground                      │
└─────────────────────────────────────────────────────────────┘
```

## 6.2 Firmware Architecture

### 6.2.1 Module Organization

```
client_device.ino
├── Configuration Constants
│   ├── SOF_1, SOF_2 (0xA5, 0x5A)
│   ├── PROTOCOL_VER (0x01)
│   └── Message type enums
├── Hardware Configuration
│   ├── LED_PIN, R_FIX, VCC
│   └── ADC object (ads)
├── State Variables
│   ├── deviceState (IDLE/MEASURING/CALIBRATING/ERROR)
│   ├── rxBuffer[], rxIndex
│   └── lastHeartbeat, lastSampleTime
├── CRC Functions
│   └── calculateCRC16()
├── TX Functions
│   ├── sendRawFrame()
│   ├── sendAck()
│   └── sendStatusFrame()
├── RX State Machine
│   ├── RxState enum
│   └── processIncomingByte()
├── Command Handler
│   └── handleFrame()
└── Main Loop
    ├── setup()
    └── loop()
```

### 6.2.2 Memory Layout

| Buffer | Size | Purpose |
|--------|------|---------|
| `rxBuffer` | 256 B | Incoming frame assembly |
| `headerBytes` | 4 B | Saved header for CRC |
| `statusPayload` | 144 B | Pre-built STATUS payload |
| `dataPayload` | 6–132 B | DATA frame (dynamic) |
| `crcBuf` | Allocated | CRC calculation buffer |

## 6.3 RX State Machine

### 6.3.1 State Definitions

```c
enum RxState {
    WAIT_SOF1,    // Waiting for first SOF byte (0xA5)
    WAIT_SOF2,    // Waiting for second SOF byte (0x5A)
    READ_HEADER,  // Reading Ver, Type, Len (4 bytes)
    READ_PAYLOAD, // Reading payload bytes
    READ_CRC      // Reading CRC (2 bytes)
};
```

### 6.3.2 State Transition Logic

```
                    ┌─────────────────────────────────────┐
                    │                                     │
                    ▼                                     │
              ┌──────────┐                                │
              │WAIT_SOF1 │◄──────┐                        │
              └────┬─────┘       │                        │
                   │ 0xA5        │ !0x5A                  │
                   ▼             │                        │
              ┌──────────┐       │                        │
              │WAIT_SOF2 │───────┘                        │
              └────┬─────┘                                │
                   │ 0x5A                                 │
                   ▼                                      │
              ┌───────────┐                               │
              │READ_HEADER│                               │
              │ (4 bytes) │                               │
              └────┬──────┘                               │
                   │ complete                             │
                   ▼                                      │
              ┌───────────┐  len==0   ┌───────────┐       │
              │READ_PAYLOAD├─────────►│ READ_CRC  │       │
              │ (N bytes)  │          │ (2 bytes) │       │
              └────┬───────┘          └─────┬─────┘       │
                   │ complete               │ complete    │
                   │                        ▼             │
                   │                   ┌─────────┐        │
                   └──────────────────►│ VERIFY  │────────┘
                                       │  CRC    │
                                       └────┬────┘
                                            │ valid
                                            ▼
                                       handleFrame()
```

### 6.3.3 Implementation Details

```c
void processIncomingByte(uint8_t byte) {
    switch (currentState) {
        case WAIT_SOF1:
            if (byte == SOF_1) currentState = WAIT_SOF2;
            break;

        case WAIT_SOF2:
            if (byte == SOF_2) {
                rxIndex = 0;
                currentState = READ_HEADER;
            } else {
                currentState = WAIT_SOF1;  // Resync
            }
            break;

        case READ_HEADER:
            rxBuffer[rxIndex++] = byte;
            if (rxIndex == 4) {
                // Parse Len (little-endian)
                expectedPayloadLen = rxBuffer[2] | (rxBuffer[3] << 8);
                memcpy(headerBytes, rxBuffer, 4);
                rxIndex = 0;
                currentState = (expectedPayloadLen > 0) 
                    ? READ_PAYLOAD : READ_CRC;
            }
            break;

        case READ_PAYLOAD:
            rxBuffer[rxIndex++] = byte;
            if (rxIndex == expectedPayloadLen) {
                currentState = READ_CRC;
                rxIndex = 0;
            }
            break;

        case READ_CRC:
            crcBytes[rxIndex++] = byte;
            if (rxIndex == 2) {
                uint16_t receivedCRC = crcBytes[0] | (crcBytes[1] << 8);
                // Verify CRC...
                if (receivedCRC == calcCRC) {
                    handleFrame(headerBytes[1], rxBuffer, expectedPayloadLen);
                }
                currentState = WAIT_SOF1;
            }
            break;
    }
}
```

## 6.4 Command Handler

### 6.4.1 Command Dispatch

```c
void handleFrame(uint8_t type, uint8_t *payload, uint16_t len) {
    if (type != TYPE_COMMAND) return;
    if (len < 2) return;  // Minimum: CmdID + Seq

    uint8_t cmdID = payload[0];
    uint8_t seq   = payload[1];
    uint8_t *args = &payload[2];

    switch (cmdID) {
        case CMD_GET_STATUS:
            sendAck(cmdID, seq, 0x00);  // OK
            sendStatusFrame();
            break;

        case CMD_START_MEASURE:
            deviceState = 0x01;           // MEASURING
            digitalWrite(LED_PIN, HIGH);
            sendAck(cmdID, seq, 0x00);
            break;

        case CMD_STOP_MEASURE:
            deviceState = 0x00;           // IDLE
            digitalWrite(LED_PIN, LOW);
            sendAck(cmdID, seq, 0x00);
            break;

        case CMD_SET_NSENSORS:
            if (len < 3) {
                sendAck(cmdID, seq, 0x02);  // INVALID_ARGUMENT
            } else {
                n_sensors = args[0];
                sendAck(cmdID, seq, 0x00);
                sendStatusFrame();
            }
            break;

        case CMD_SET_RATE:
            if (len < 5) {
                sendAck(cmdID, seq, 0x02);
            } else {
                uint8_t idx = args[0];
                uint16_t rate = args[1] | (args[2] << 8);
                samp_rate_map[idx] = rate;
                sendAck(cmdID, seq, 0x00);
                sendStatusFrame();
            }
            break;

        // ... other commands ...

        default:
            sendAck(cmdID, seq, 0x01);  // INVALID_COMMAND
            break;
    }
}
```

### 6.4.2 Response Timing

| Command | ACK Delay | Additional Response |
|---------|-----------|---------------------|
| GET_STATUS | <1ms | STATUS frame |
| START_MEASURE | <1ms | None (DATA starts streaming) |
| STOP_MEASURE | <1ms | None |
| SET_* | <5ms | STATUS frame (confirmation) |
| CALIBRATE | <10ms | STATUS during calibration |

## 6.5 TX Frame Building

### 6.5.1 Generic Frame Sender

```c
void sendRawFrame(uint8_t type, uint8_t *payload, uint16_t len) {
    // 1. Send SOF
    Serial.write(SOF_1);
    Serial.write(SOF_2);

    // 2. Build CRC input buffer
    uint8_t *crcBuf = (uint8_t*)malloc(4 + len);
    crcBuf[0] = PROTOCOL_VER;
    crcBuf[1] = type;
    crcBuf[2] = len & 0xFF;         // Len LSB
    crcBuf[3] = (len >> 8) & 0xFF;  // Len MSB
    memcpy(crcBuf + 4, payload, len);

    // 3. Calculate CRC
    uint16_t crc = calculateCRC16(crcBuf, 4 + len);

    // 4. Send header
    Serial.write(crcBuf, 4);

    // 5. Send payload
    if (len > 0) Serial.write(payload, len);

    // 6. Send CRC (little-endian)
    Serial.write(crc & 0xFF);
    Serial.write((crc >> 8) & 0xFF);

    free(crcBuf);
}
```

### 6.5.2 STATUS Frame Construction

```c
void sendStatusFrame() {
    const uint16_t STATUS_LEN = 144;
    static uint8_t statusPayload[STATUS_LEN];
    memset(statusPayload, 0, STATUS_LEN);

    // Offset 0: State
    statusPayload[0] = deviceState;

    // Offset 1: NSensors
    statusPayload[1] = n_sensors;

    // Offset 2-5: ActiveMap (4 bytes LE)
    statusPayload[2] = active_map & 0xFF;
    statusPayload[3] = (active_map >> 8) & 0xFF;
    statusPayload[4] = (active_map >> 16) & 0xFF;
    statusPayload[5] = (active_map >> 24) & 0xFF;

    // Offset 6-9: HealthMap (4 bytes LE)
    // ... similar pattern ...

    // Offset 10-73: SampRateMap (32 × uint16 LE)
    for (int i = 0; i < 32; i++) {
        statusPayload[10 + i*2] = samp_rate_map[i] & 0xFF;
        statusPayload[11 + i*2] = (samp_rate_map[i] >> 8) & 0xFF;
    }

    // Offset 74-105: BitsPerSmpMap (32 × uint8)
    memcpy(&statusPayload[74], bits_per_smp_map, 32);

    // ... remaining fields ...

    sendRawFrame(TYPE_STATUS, statusPayload, STATUS_LEN);
}
```

### 6.5.3 DATA Frame Construction

```c
void sendDataFrame() {
    uint8_t dataPayload[132];  // Max: 4 + 32*4
    uint32_t ts = millis();

    // Timestamp (4 bytes LE)
    dataPayload[0] = ts & 0xFF;
    dataPayload[1] = (ts >> 8) & 0xFF;
    dataPayload[2] = (ts >> 16) & 0xFF;
    dataPayload[3] = (ts >> 24) & 0xFF;

    uint16_t offset = 4;
    for (int i = 0; i < 32; i++) {
        if (!((active_map >> i) & 1)) continue;

        int16_t adc = readSensor(i);
        uint8_t bits = bits_per_smp_map[i];
        uint8_t bytes = (bits + 7) / 8;

        // Pack sample (LE)
        for (int b = 0; b < bytes; b++) {
            dataPayload[offset++] = (adc >> (b * 8)) & 0xFF;
        }
    }

    sendRawFrame(TYPE_DATA, dataPayload, offset);
}
```

## 6.6 Main Loop

### 6.6.1 Non-Blocking Architecture

```c
void loop() {
    unsigned long currentMillis = millis();

    // A. Process incoming bytes (non-blocking)
    while (Serial.available()) {
        processIncomingByte(Serial.read());
    }

    // B. State-dependent behavior
    if (deviceState == 0x01) {  // MEASURING
        // Send DATA at configured rate
        if (currentMillis - lastSampleTime > sampleInterval) {
            lastSampleTime = currentMillis;
            sendDataFrame();
        }
    } else {  // IDLE or other
        // Send heartbeat STATUS periodically
        if (currentMillis - lastHeartbeat > 3000) {
            lastHeartbeat = currentMillis;
            sendStatusFrame();
        }
    }
}
```

### 6.6.2 Timing Diagram

```
Time ─────────────────────────────────────────────────────►
     │                                                    │
IDLE │  STATUS  │         │  STATUS  │         │  STATUS │
     │    ↓     │         │    ↓     │         │    ↓    │
     ├──────────┼─────────┼──────────┼─────────┼─────────┤
     0         3s        6s         9s       12s       15s

MEASURING
     │ DATA │ DATA │ DATA │ DATA │ DATA │ DATA │ DATA │
     │  ↓   │  ↓   │  ↓   │  ↓   │  ↓   │  ↓   │  ↓   │
     ├──────┼──────┼──────┼──────┼──────┼──────┼──────┤
     0    100ms 200ms 300ms 400ms 500ms 600ms 700ms
```

## 6.7 Performance Considerations

### 6.7.1 Memory Optimization

| Technique | Savings | Trade-off |
|-----------|---------|-----------|
| Static status buffer | ~144 B RAM | None |
| Nibble-based CRC | ~480 B ROM | Slightly slower |
| Avoid malloc in hot path | Predictable | Code complexity |

### 6.7.2 Timing Constraints

| Operation | Max Time | Measured |
|-----------|----------|----------|
| CRC-16 (144 bytes) | <500 µs | ~200 µs |
| ADC read (single) | <10 ms | ~1.2 ms |
| Frame TX (20 bytes) | <2 ms | ~1.7 ms |

### 6.7.3 Error Handling

```c
// Guard against allocation failures
uint8_t *crcBuf = (uint8_t*)malloc(4 + len);
if (crcBuf == NULL) {
    // Log error, skip frame
    return;
}

// Validate command arguments
if (sensor_idx >= 32) {
    sendAck(cmdID, seq, 0x02);  // INVALID_ARGUMENT
    return;
}
```

## 6.8 Reference Implementation

- Source: [Communication_Stack/for_mcu/client_device.ino](../../Communication_Stack/for_mcu/client_device.ino)
- Dependencies: `Wire.h`, `Adafruit_ADS1X15.h`
- Flash usage: ~50 KB
- RAM usage: ~20 KB (with 256-byte RX buffer)

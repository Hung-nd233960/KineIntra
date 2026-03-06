# Sequence Diagrams

Message sequence diagrams showing interactions between components.

## Connection and Status Request

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant DeviceClient
    participant SerialConn
    participant MCU

    User->>CLI: python -m kineintra.cli connect --port /dev/ttyUSB0
    CLI->>DeviceClient: DeviceClient(use_virtual=False)
    CLI->>DeviceClient: connect(port, timeout)
    DeviceClient->>SerialConn: connect(port, timeout)
    SerialConn->>MCU: Open serial connection
    MCU-->>SerialConn: Connection established
    SerialConn-->>DeviceClient: True
    DeviceClient-->>CLI: True
    
    Note over MCU: MCU sends periodic STATUS heartbeat
    MCU->>SerialConn: STATUS frame (heartbeat)
    SerialConn->>DeviceClient: frame callback
    DeviceClient->>DeviceClient: parse -> StatusPayload
    DeviceClient-->>CLI: poll_event() -> ("STATUS", payload)
    CLI->>User: Print status info
```

## Start Measurement Sequence

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant DeviceClient
    participant HostPacketMaker
    participant SerialConn
    participant MCU

    User->>CLI: start --seq 1
    CLI->>DeviceClient: start_measure(seq=1)
    DeviceClient->>HostPacketMaker: set_start_measure(seq=1)
    HostPacketMaker-->>DeviceClient: COMMAND frame bytes
    DeviceClient->>SerialConn: send_frame(bytes)
    SerialConn->>MCU: COMMAND (START_MEASURE)
    
    MCU->>MCU: state = MEASURING
    MCU->>MCU: LED ON
    MCU->>SerialConn: ACK (OK)
    SerialConn->>DeviceClient: frame callback
    DeviceClient->>DeviceClient: parse -> AckPayload
    DeviceClient-->>CLI: poll_event() -> ("ACK", payload)
    CLI->>User: Print "ACK OK"
    
    loop Every 100ms (10 Hz)
        MCU->>MCU: Read ADC
        MCU->>SerialConn: DATA frame
        SerialConn->>DeviceClient: frame callback
        DeviceClient->>DeviceClient: parse -> DataPayload
        DeviceClient-->>CLI: poll_event() -> ("DATA", payload)
        CLI->>User: Print sensor values
    end
```

## Configuration Sequence

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant DeviceClient
    participant MCU

    User->>CLI: set-nsensors 8 --seq 1
    CLI->>DeviceClient: set_nsensors(seq=1, n=8)
    DeviceClient->>MCU: COMMAND (SET_NSENSORS, args=[8])
    MCU->>MCU: n_sensors = 8
    MCU-->>DeviceClient: ACK (OK)
    DeviceClient-->>CLI: ("ACK", AckPayload)
    MCU-->>DeviceClient: STATUS (updated)
    DeviceClient-->>CLI: ("STATUS", StatusPayload)
    CLI->>User: Print updated status
    
    User->>CLI: set-rate 0 100 --seq 2
    CLI->>DeviceClient: set_rate(seq=2, sensor_idx=0, rate_hz=100)
    DeviceClient->>MCU: COMMAND (SET_RATE, args=[0, 100])
    MCU->>MCU: samp_rate[0] = 100
    MCU-->>DeviceClient: ACK (OK)
    MCU-->>DeviceClient: STATUS (updated)
    CLI->>User: Print updated status
```

## Error Handling Sequence

```mermaid
sequenceDiagram
    participant MCU
    participant SerialConn
    participant DeviceClient
    participant CLI
    participant User

    Note over MCU: Sensor fault detected
    MCU->>MCU: health_map &= ~(1 << sensor_idx)
    MCU->>SerialConn: ERROR frame (SENSOR_FAULT)
    SerialConn->>DeviceClient: frame callback
    DeviceClient->>DeviceClient: parse -> ErrorPayload
    DeviceClient-->>CLI: poll_event() -> ("ERROR", payload)
    CLI->>User: Print "ERROR: SENSOR_FAULT"
    
    Note over MCU: FIFO overflow
    MCU->>SerialConn: ERROR frame (FIFO_CRITICAL)
    SerialConn->>DeviceClient: frame callback
    DeviceClient-->>CLI: ("ERROR", payload)
    CLI->>User: Print "ERROR: FIFO_CRITICAL"
```

## GUI Event Polling

```mermaid
sequenceDiagram
    participant MainWindow
    participant EventPollerThread
    participant DeviceClient
    participant MCU

    MainWindow->>DeviceClient: connect()
    DeviceClient-->>MainWindow: True
    MainWindow->>EventPollerThread: start()
    
    loop Polling Loop
        EventPollerThread->>DeviceClient: poll_event(timeout=0.1)
        
        alt Event available
            DeviceClient-->>EventPollerThread: ("STATUS", payload)
            EventPollerThread->>MainWindow: status_received.emit(payload)
            MainWindow->>MainWindow: update StatusPanel
        else No event
            DeviceClient-->>EventPollerThread: None
        end
    end
    
    MCU->>DeviceClient: DATA frame
    DeviceClient-->>EventPollerThread: ("DATA", payload)
    EventPollerThread->>MainWindow: data_received.emit(payload)
    MainWindow->>MainWindow: update EventLogPanel
    
    MainWindow->>EventPollerThread: stop()
    MainWindow->>DeviceClient: disconnect()
```

## Protocol Parser Flow

```mermaid
sequenceDiagram
    participant SerialConn
    participant ByteReader
    participant ProtocolParser
    participant DeviceClient

    SerialConn->>ByteReader: process_bytes(raw_data)
    
    loop For each complete frame
        ByteReader->>ByteReader: Find SOF (0xA5 0x5A)
        ByteReader->>ByteReader: Read header (Ver, Type, Len)
        ByteReader->>ByteReader: Read payload
        ByteReader->>ByteReader: Verify CRC
        
        alt CRC Valid
            ByteReader-->>SerialConn: FrameParseResult
            SerialConn->>DeviceClient: frame_callback(frame)
            DeviceClient->>ProtocolParser: parse_frame(frame)
            
            alt STATUS frame
                ProtocolParser-->>DeviceClient: ("STATUS", StatusPayload)
            else DATA frame
                ProtocolParser-->>DeviceClient: ("DATA", DataPayload)
            else ACK frame
                ProtocolParser-->>DeviceClient: ("ACK", AckPayload)
            else ERROR frame
                ProtocolParser-->>DeviceClient: ("ERROR", ErrorPayload)
            end
            
            DeviceClient->>DeviceClient: dispatch callbacks
            DeviceClient->>DeviceClient: queue.put(event)
        else CRC Invalid
            ByteReader->>ByteReader: Discard frame
        end
    end
```

## Virtual Serial Test Sequence

```mermaid
sequenceDiagram
    participant Test
    participant SerialPortConnection
    participant VirtualSerialModule
    participant VirtualDevice

    Test->>Test: monkeypatch serial module
    Test->>SerialPortConnection: new()
    Test->>SerialPortConnection: connect(timeout=1.0)
    SerialPortConnection->>VirtualSerialModule: Serial(port, baud)
    VirtualSerialModule->>VirtualDevice: create virtual device
    VirtualDevice-->>SerialPortConnection: connection ready
    
    Note over VirtualDevice: Heartbeat every 0.5s
    VirtualDevice->>SerialPortConnection: STATUS frame
    SerialPortConnection->>Test: frame_callback
    Test->>Test: assert STATUS received
    
    Test->>SerialPortConnection: send_frame(GET_STATUS)
    SerialPortConnection->>VirtualDevice: COMMAND frame
    VirtualDevice->>VirtualDevice: process command
    VirtualDevice->>SerialPortConnection: ACK frame
    VirtualDevice->>SerialPortConnection: STATUS frame
    SerialPortConnection->>Test: frame_callbacks
    Test->>Test: assert ACK and STATUS received
    
    Test->>SerialPortConnection: disconnect()
```

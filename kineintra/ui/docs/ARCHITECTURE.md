# PyQt6 Application Architecture

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    BioMechanics PyQt6 Application                │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │               BioMechanicsApp (QMainWindow)              │   │
│  │  - Main application window (1200x900)                   │   │
│  │  - Tab widget coordination                              │   │
│  │  - Error handling & status bar                          │   │
│  └──────────────────────┬───────────────────────────────────┘   │
│                         │                                        │
│     ┌───────────────────┼───────────────────┐                   │
│     │                   │                   │                   │
│     ▼                   ▼                   ▼                   │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐   │
│  │ Connection      │ │ Command         │ │ Raw Data        │   │
│  │ Control Widget  │ │ Center Widget   │ │ Display Widget  │   │
│  ├─────────────────┤ ├─────────────────┤ ├─────────────────┤   │
│  │ • Port select   │ │ • Status req    │ │ • Live table    │   │
│  │ • Baud rate     │ │ • Start/Stop    │ │ • Statistics    │   │
│  │ • Connect/DC    │ │ • Configure     │ │ • Device info   │   │
│  │ • Status disp   │ │ • Calibrate     │ │ • Data log      │   │
│  └────────┬────────┘ └────────┬────────┘ └────────┬────────┘   │
│           │                    │                   │            │
│           └────────────────────┼───────────────────┘            │
│                                │                                │
│                                ▼                                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │    DeviceCommunicationWorker (QObject in Thread)         │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ Responsibilities:                                        │   │
│  │ • Serial port management                                │   │
│  │ • Command generation (via HostPacketMakerAPI)           │   │
│  │ • Frame parsing (via ProtocolParser)                    │   │
│  │ • Signal emission (status, data, ack, error)            │   │
│  │ • Thread-safe callbacks                                 │   │
│  └────────────────────┬──────────────────────────────────┬──┘   │
│                       │                                  │       │
│          ┌────────────┴─────────────┐                   │       │
│          │                          │                   │       │
│          ▼                          ▼                   │       │
│  ┌──────────────────────┐   ┌────────────────────────┐  │       │
│  │ SerialPort           │   │ ProtocolParser         │  │       │
│  │ Connection           │   │ (Parse Frames)         │  │       │
│  └──────────┬───────────┘   └────────┬───────────────┘  │       │
│             │                        │                  │       │
│             ▼                        ▼                  │       │
│  ┌──────────────────────┐   ┌────────────────────────┐  │       │
│  │ PacketMaker (send)   │   │ PacketReader (recv)    │  │       │
│  │ HostPacketMakerAPI   │   │ ByteReader             │  │       │
│  └──────────────────────┘   └────────────────────────┘  │       │
│                                                          │       │
│                        Serial Port                       │       │
│                            ║                             │       │
└────────────────────────────╫─────────────────────────────┘       │
                             ║                                      │
                    ┌────────▼────────┐                            │
                    │   BioMechanics   │                           │
                    │   Microprocessor │                           │
                    │      Device      │                           │
                    └─────────────────┘                            │
```

## Class Hierarchy

```
QMainWindow
    └── BioMechanicsApp
        ├── ConnectionControlWidget (QWidget)
        ├── CommandCenterWidget (QWidget)
        ├── RawDataDisplayWidget (QWidget)
        └── DeviceCommunicationWorker (QObject)
            └── Runs in QThread

QWidget
    ├── ConnectionControlWidget
    │   ├── QGroupBox
    │   │   ├── QComboBox (port_combo)
    │   │   ├── QSpinBox (baudrate_spin)
    │   │   └── QPushButton (connect/disconnect)
    │   └── QLabel (status_label)
    │
    ├── CommandCenterWidget
    │   ├── QGroupBox (Status, Measurement, Sensor, Frame Rate, Bits, Calib)
    │   ├── QPushButton (various commands)
    │   ├── QSpinBox (parameters)
    │   └── QPlainTextEdit (response_log)
    │
    └── RawDataDisplayWidget
        ├── QTableWidget (data_table)
        ├── QPlainTextEdit (sensor_details_text)
        ├── QPlainTextEdit (data_log)
        └── QTimer (update_timer)

QObject
    └── DeviceCommunicationWorker
        ├── pyqtSignal: status_received(StatusPayload)
        ├── pyqtSignal: data_received(DataPayload)
        ├── pyqtSignal: ack_received(AckPayload)
        ├── pyqtSignal: error_received(ErrorPayload)
        ├── pyqtSignal: connection_state_changed(ConnectionState)
        └── pyqtSignal: error_occurred(str)
```

## Signal Flow Diagram

```
┌────────────────────────────────────────────────────────────────┐
│                     Signal Flow Architecture                    │
├────────────────────────────────────────────────────────────────┤
│                                                                  │
│  User UI Event          Worker Method      Device Response      │
│  ──────────────────────────────────────────────────────────────│
│                                                                  │
│  Connect Button     →   worker.connect()   →   Connected       │
│                         (serial.connect)      (emits signal)    │
│                                                  ↓              │
│                              ConnectionControlWidget            │
│                              updates status (green)             │
│                                                                  │
│  ─────────────────────────────────────────────────────────────  │
│                                                                  │
│  Request Status     →   worker.           →   STATUS frame     │
│  Button                 request_status()      arrives           │
│                         (sends CMD)           (parser runs)     │
│                                                  ↓              │
│                              RawDataDisplayWidget               │
│                              updates sensor info                │
│                                                                  │
│  ─────────────────────────────────────────────────────────────  │
│                                                                  │
│  Start Measurement  →   worker.           →   ACK frame        │
│  Button                 start_measurement()   arrives           │
│                         (sends CMD)           (parser runs)     │
│                                                  ↓              │
│                              CommandCenterWidget                │
│                              logs response                      │
│                                                                  │
│  ─────────────────────────────────────────────────────────────  │
│                                                                  │
│  (Continuous)           (Polling RX)        DATA frames        │
│                                              arriving           │
│                                              continuously       │
│                                                  ↓              │
│                              RawDataDisplayWidget               │
│                              updates table & statistics         │
│                                                                  │
└────────────────────────────────────────────────────────────────┘
```

## Data Flow for Measurement

```
┌─────────────────────────────────────────────────────────────────┐
│              Data Collection and Display Pipeline                │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  1. Device                                                       │
│     Sends DATA Frame (Sensor Samples)                           │
│           ↓                                                      │
│  2. SerialConnection._receive_thread()                          │
│     Reads bytes from port                                       │
│           ↓                                                      │
│  3. ByteReader.process_bytes()                                  │
│     Parses frame structure                                      │
│     Validates CRC                                               │
│           ↓                                                      │
│  4. DeviceCommunicationWorker._on_frame_received()              │
│     Callback from SerialConnection                              │
│           ↓                                                      │
│  5. ProtocolParser.parse()                                      │
│     Converts FrameParseResult → DataPayload                    │
│           ↓                                                      │
│  6. Worker.data_received.emit(DataPayload)                      │
│     Qt Signal emitted                                           │
│           ↓                                                      │
│  7. RawDataDisplayWidget._on_data_received()                    │
│     Slot connected to signal                                    │
│           ↓                                                      │
│  8. Data Storage                                                │
│     self.sensor_readings[sensor_idx].append(reading)            │
│           ↓                                                      │
│  9. QTimer (every 500ms)                                        │
│     Triggers _update_display()                                  │
│           ↓                                                      │
│  10. UI Update                                                   │
│      • Update table with latest readings                        │
│      • Recalculate statistics                                   │
│      • Update FPS counter                                       │
│      • Append to log                                            │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Threading Model

```
Main Thread (UI)                 Worker Thread
────────────────────────────────────────────────────────────

PyQt Event Loop
    │
    ├─ User clicks button
    │
    ├─ signal: worker.request_status()
    │                                    → Background Thread
    │                                      │
    │                                      ├─ Send command
    │                                      │
    │                                      ├─ Wait for response
    │                                      │
    │                                      └─ worker.status_received.emit()
    │
    ◄─ Qt Signal arrives
    │
    ├─ Slot: _on_status_received()
    │
    └─ Update UI


Key Points:
• Worker runs in separate QThread
• All signals are thread-safe (Qt handles marshalling)
• No blocking calls in main thread
• UI remains responsive during communication
• Multiple commands can queue
```

## Communication Protocol Integration

```
┌─────────────────────────────────────────────────────────────┐
│         PyQt App Integration with Protocol Layer             │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  UI Layer (PyQt6)                                           │
│  ├── BioMechanicsApp (UI orchestration)                     │
│  ├── ConnectionControlWidget (connection UI)                │
│  ├── CommandCenterWidget (command UI)                       │
│  └── RawDataDisplayWidget (data visualization)              │
│         ▲                                                    │
│         │ Signals/Slots (Qt mechanism)                      │
│         │                                                    │
│  ┌──────▼──────────────────────────────────────────────┐   │
│  │  Application Layer (DeviceCommunicationWorker)      │   │
│  │  • High-level device interface                      │   │
│  │  • Command/response correlation                     │   │
│  │  • State management                                 │   │
│  └──────▲──────────────────────────────────────────────┘   │
│         │ API calls                                         │
│         │                                                    │
│  ┌──────▼──────────────────────────────────────────────┐   │
│  │  Protocol/API Layer                                 │   │
│  │  ├── frame_maker_api.py (Command generation)        │   │
│  │  ├── protocol_parser.py (Response parsing)          │   │
│  │  ├── serial_connection.py (Rx/Tx)                   │   │
│  │  ├── packet_maker.py (Frame assembly)               │   │
│  │  └── packet_reader.py (Frame disassembly)           │   │
│  └──────▲──────────────────────────────────────────────┘   │
│         │ Bytes                                             │
│         │                                                    │
│  ┌──────▼──────────────────────────────────────────────┐   │
│  │  Serial Connection (pyserial)                       │   │
│  │  • COM/USB port I/O                                 │   │
│  │  • Baud rate control                                │   │
│  └──────▲──────────────────────────────────────────────┘   │
│         │ Binary data                                       │
│         │                                                    │
│  ┌──────▼──────────────────────────────────────────────┐   │
│  │  BioMechanics Device (Hardware)                     │   │
│  │  • Sensor interface                                 │   │
│  │  • ADC processing                                   │   │
│  │  • Protocol implementation                          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## State Machine

```
Connection States:
─────────────────

┌─────────────────┐
│  DISCONNECTED   │ (Initial state)
└────────┬────────┘
         │
         │ connect()
         ▼
┌─────────────────┐
│   CONNECTING    │
└────────┬────────┘
         │
         ├─ Success ──→ ┌─────────────┐
         │              │  CONNECTED  │
         │              └────────┬────┘
         │                       │
         │                       │ disconnect()
         │                       ▼
         │              ┌─────────────────┐
         │              │  DISCONNECTED   │
         │              └─────────────────┘
         │
         └─ Failure ──→ ┌──────────┐
                        │  ERROR   │
                        └────┬─────┘
                             │
                             │ User action (retry/close)
                             ▼
                        ┌─────────────────┐
                        │  DISCONNECTED   │
                        └─────────────────┘

Measurement States:
───────────────────
• Idle (not measuring)
• Measuring (collecting data)
• Error (communication issue)

Frame Types Received:
────────────────────
• STATUS: Device configuration
• DATA: Sensor readings
• ACK: Command confirmation
• ERROR: Device error message
```

## Component Interaction Example

### Scenario: User starts measurement

```
1. User clicks "Start Measurement"
   ↓
2. CommandCenterWidget._on_start_measure()
   ↓
3. worker.start_measurement()
   ↓
4. (In worker thread) HostPacketMakerAPI.set_start_measure()
   ↓
5. worker.send_command(cmd_bytes)
   ↓
6. SerialPortConnection.send_frame(cmd_bytes)
   ↓
7. serial_port.write(cmd_bytes)
   ↓
8. Device receives command, processes it
   ↓
9. Device sends ACK frame
   ↓
10. SerialPortConnection._receive_thread() reads ACK
    ↓
11. ByteReader.process_bytes() parses ACK frame
    ↓
12. worker._on_frame_received(frame)
    ↓
13. ProtocolParser.parse(frame) → AckPayload
    ↓
14. worker.ack_received.emit(ack_payload)
    ↓
15. (Qt signal emitted to main thread)
    ↓
16. CommandCenterWidget._on_ack_received(ack)
    ↓
17. response_log.appendPlainText("[HH:MM:SS] ACK received...")
    ↓
18. User sees response in command log
```

---

## Key Design Principles

1. **Separation of Concerns**
   - UI layer (Qt widgets) separate from communication logic
   - Worker class encapsulates device communication
   - Protocol layer independent of application

2. **Thread Safety**
   - Worker runs in separate thread
   - Qt signals automatically marshal between threads
   - No blocking operations in main thread

3. **Responsiveness**
   - Non-blocking serial communication
   - Callback-based frame reception
   - Periodic UI updates via QTimer

4. **Extensibility**
   - Easy to add new command buttons
   - Data display can be extended
   - Protocol updates don't affect UI

5. **Error Handling**
   - User-friendly error messages
   - Graceful degradation
   - Connection recovery options

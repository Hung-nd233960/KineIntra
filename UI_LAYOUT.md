# PyQt6 Application - UI Layout & Workflow

## Main Window Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ BioMechanics Microprocessor Control - PyQt6                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌─ Connection Control ─┬─ Command Center ─┬─ Raw Data Display ─┐           │
│  │                      │                  │                    │           │
│  │  Port Selection      │  Status Commands │  Data Statistics   │           │
│  │  ├─ Port Combo       │  ├─ Request      │  ├─ Total Reading  │           │
│  │  ├─ Refresh Btn      │  │   Status      │  ├─ Active Sensors │           │
│  │  ├─ Baud Rate        │  │               │  ├─ Last Update    │           │
│  │  │                   │  Measurement     │  ├─ Data Rate FPS  │           │
│  │  Connection Status   │  ├─ Start        │  │                 │           │
│  │  ├─ Status Label     │  │   Measurement │  Data Table        │           │
│  │  ├─ Connection Info  │  ├─ Stop         │  ├─ Timestamp      │           │
│  │  │                   │  │   Measurement │  ├─ Sensor ID      │           │
│  │  Connection Controls │  │               │  ├─ Raw Value      │           │
│  │  ├─ Connect Btn      │  Sensor Config   │  └─ Formatted Val  │           │
│  │  └─ Disconnect Btn   │  ├─ Set N Sensors│                   │           │
│  │                      │  ├─ Set Rate    │  Sensor Details    │           │
│  │                      │  └─ Set Bits    │  (Status Display)   │           │
│  │                      │                 │  ├─ Device State    │           │
│  │                      │  Calibration    │  ├─ N Sensors       │           │
│  │                      │  ├─ Mode Sel    │  ├─ Active Map      │           │
│  │                      │  └─ Calibrate   │  ├─ Health Map      │           │
│  │                      │  Btn            │  ├─ Sample Rates    │           │
│  │                      │                 │  └─ Bits Per Smp    │           │
│  │                      │  Response Log   │  │                 │           │
│  │                      │  (Timestamped) │  Raw Data Log       │           │
│  │                      │                 │  (Scrollable)       │           │
│  │                      │                 │                    │           │
│  └──────────────────────┴─────────────────┴────────────────────┘           │
│                                                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│ Status Bar: Ready                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Tab 1: Connection Control

```
┌─────────────────────────────────────────┐
│      Connection Control Tab             │
├─────────────────────────────────────────┤
│                                         │
│  Port Selection                         │
│  ┌─────────────────────────────────┐   │
│  │ Port: [COM3            ▼]       │   │
│  │ [Refresh Ports]                 │   │
│  │ Baud Rate: [115200    ]         │   │
│  └─────────────────────────────────┘   │
│                                         │
│  Connection Status                      │
│  ┌─────────────────────────────────┐   │
│  │ Status: Connected               │   │ (Green)
│  │ Connected to COM3 at 115200 baud│   │
│  └─────────────────────────────────┘   │
│                                         │
│  Connection Controls                    │
│  ┌─────────────────────────────────┐   │
│  │ [  Connect  ]  [Disconnect]     │   │
│  │   (Green)        (Disabled)     │   │
│  └─────────────────────────────────┘   │
│                                         │
└─────────────────────────────────────────┘
```

## Tab 2: Command Center

```
┌──────────────────────────────────────────────────────┐
│         Command Center Tab                           │
├──────────────────────────────────────────────────────┤
│                                                      │
│  Status Commands                                    │
│  ┌────────────────────────────────────────────┐    │
│  │ [Request Status]                           │    │
│  └────────────────────────────────────────────┘    │
│                                                      │
│  Measurement Control                                │
│  ┌────────────────────────────────────────────┐    │
│  │ [Start Measurement] [Stop Measurement]     │    │
│  │     (Green)           (Red)                │    │
│  └────────────────────────────────────────────┘    │
│                                                      │
│  Sensor Configuration                               │
│  ┌────────────────────────────────────────────┐    │
│  │ Number of Sensors: [4    ]                 │    │
│  │ [Set Number of Sensors]                    │    │
│  └────────────────────────────────────────────┘    │
│                                                      │
│  Sensor Frame Rate                                  │
│  ┌────────────────────────────────────────────┐    │
│  │ Sensor Index: [0    ]                      │    │
│  │ Frame Rate (Hz): [100  ]                   │    │
│  │ [Set Frame Rate]                           │    │
│  └────────────────────────────────────────────┘    │
│                                                      │
│  Bits Per Sample                                    │
│  ┌────────────────────────────────────────────┐    │
│  │ Sensor Index: [0    ]                      │    │
│  │ Bits Per Sample: [12   ]                   │    │
│  │ [Set Bits Per Sample]                      │    │
│  └────────────────────────────────────────────┘    │
│                                                      │
│  Calibration                                        │
│  ┌────────────────────────────────────────────┐    │
│  │ Calibration Mode: [0    ]                  │    │
│  │ [Calibrate]                                │    │
│  └────────────────────────────────────────────┘    │
│                                                      │
│  Command Response Log                               │
│  ┌────────────────────────────────────────────┐    │
│  │ [14:32:15] Status request sent              │    │
│  │ [14:32:16] ACK received - Seq: 1, Result: 0│    │
│  │ [14:32:20] Start measurement command sent  │    │
│  │ [14:32:21] ACK received - Seq: 2, Result: 0│    │
│  │                                            │    │
│  │                                            │    │
│  └────────────────────────────────────────────┘    │
│                                                      │
└──────────────────────────────────────────────────────┘
```

## Tab 3: Raw Data Display

```
┌────────────────────────────────────────────────────────────┐
│          Raw Data Display Tab                              │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Data Statistics                                          │
│  ┌──────────────────────────────────────────────────┐    │
│  │ Total Readings: 1234        Last Update: 14:32:45│    │
│  │ Active Sensors: 4           Data Rate: 102.3 FPS │    │
│  └──────────────────────────────────────────────────┘    │
│                                                            │
│  Data Table (Latest Readings)                             │
│  ┌──────────────────────────────────────────────────┐    │
│  │ Timestamp     │ Sensor ID │ Raw Value  │ Formatted   │    │
│  ├───────────────┼───────────┼────────────┼───────────┤    │
│  │ 14:32:45.123 │ 0         │ 2048       │ 0.5000     │    │
│  │ 14:32:45.112 │ 1         │ 2156       │ 0.5267     │    │
│  │ 14:32:45.101 │ 2         │ 1923       │ 0.4697     │    │
│  │ 14:32:45.089 │ 3         │ 2341       │ 0.5713     │    │
│  │ 14:32:45.078 │ 4         │ 2089       │ 0.5100     │    │
│  └──────────────────────────────────────────────────┘    │
│                                                            │
│  Sensor Details                                           │
│  ┌──────────────────────────────────────────────────┐    │
│  │ Device State: RUNNING                            │    │
│  │ Number of Sensors: 4                             │    │
│  │ Active Map: 0x0000000F                           │    │
│  │ Health Map: 0x0000000F                           │    │
│  │                                                  │    │
│  │ Sampling Rates:                                  │    │
│  │   Sensor 0: 100 Hz                              │    │
│  │   Sensor 1: 100 Hz                              │    │
│  │   Sensor 2: 50 Hz                               │    │
│  │   Sensor 3: 100 Hz                              │    │
│  │                                                  │    │
│  │ Bits Per Sample:                                 │    │
│  │   Sensor 0: 12 bits                             │    │
│  │   Sensor 1: 12 bits                             │    │
│  │   Sensor 2: 16 bits                             │    │
│  │   Sensor 3: 12 bits                             │    │
│  └──────────────────────────────────────────────────┘    │
│                                                            │
│  Raw Data Log (Scrollable)                                │
│  ┌──────────────────────────────────────────────────┐    │
│  │ [14:32:00.000] Sensor 0: 2048                   │    │
│  │ [14:32:00.010] Sensor 1: 2156                   │    │
│  │ [14:32:00.020] Sensor 2: 1923                   │    │
│  │ [14:32:00.030] Sensor 3: 2341                   │    │
│  │ [14:32:00.040] Sensor 0: 2089                   │    │
│  │ [14:32:00.050] Sensor 1: 2200                   │    │
│  │ [14:32:00.060] Sensor 2: 1876                   │    │
│  │ ... (scrollable)                                │    │
│  │                                                  │    │
│  └──────────────────────────────────────────────────┘    │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

## User Workflow

```
Start Application
    ↓
┌─ Connection Control Tab ─────────────┐
│ 1. Select COM port                   │
│ 2. Verify baud rate (115200)         │
│ 3. Click "Connect"                   │
│ 4. Status changes to green "Connected"
└──────────────────────────────────────┘
    ↓
┌─ Command Center Tab ──────────────────┐
│ 5. Click "Request Status"              │
│ 6. Set "Number of Sensors" (e.g., 4)  │
│ 7. Set frame rate for each sensor      │
│ 8. Click "Start Measurement"           │
└───────────────────────────────────────┘
    ↓
┌─ Raw Data Display Tab ─────────────────┐
│ 9. Monitor incoming sensor data        │
│ 10. View statistics (readings, FPS)    │
│ 11. Check device status information    │
│ 12. Review data log                    │
└───────────────────────────────────────┘
    ↓
┌─ Command Center Tab ──────────────────┐
│ 13. When done, Click "Stop Measurement"│
└───────────────────────────────────────┘
    ↓
┌─ Connection Control Tab ─────────────┐
│ 14. Click "Disconnect"                │
│ 15. Status changes to red "Disconnected"
└──────────────────────────────────────┘
    ↓
End Application
```

## Color Scheme

| Element | Color | Meaning |
|---------|-------|---------|
| Status: Connected | Green | Device is connected and ready |
| Status: Connecting | Orange | Connection in progress |
| Status: Disconnected | Red | Device not connected |
| Status: Error | Dark Red | Connection error |
| Connect Button | Green | Ready to connect |
| Disconnect Button | Red | Ready to disconnect |
| Start Measurement | Green | Start data collection |
| Stop Measurement | Red | Stop data collection |

## UI Dimensions

- **Main Window**: 1200 x 900 pixels
- **Minimum Width**: 800 pixels
- **Minimum Height**: 600 pixels
- **Tab Height**: ~40 pixels
- **Status Bar Height**: ~25 pixels

## Responsive Features

- All text fields auto-resize with window
- Scroll bars appear when content exceeds space
- Tables and text areas are scrollable
- Buttons maintain minimum width

## Keyboard Navigation

- **Tab**: Move to next field
- **Shift+Tab**: Move to previous field
- **Enter**: Activate button
- **Spacebar**: Toggle checkbox/button

## Input Validation

| Input | Min | Max | Default |
|-------|-----|-----|---------|
| Baud Rate | 9600 | 921600 | 115200 |
| Number of Sensors | 1 | 32 | 1 |
| Sensor Index | 0 | 31 | 0 |
| Frame Rate (Hz) | 1 | 10000 | 100 |
| Bits Per Sample | 8 | 32 | 12 |
| Calibration Mode | 0 | 255 | 0 |

---

This layout provides an intuitive, organized interface for complete device control and monitoring.

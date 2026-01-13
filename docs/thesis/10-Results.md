# Results

## 10.1 System Performance

### 10.1.1 Communication Reliability

| Metric | Test Conditions | Result |
|--------|-----------------|--------|
| **Frame integrity** | 10,000 frames, virtual serial | 100% CRC pass |
| **Frame integrity** | 5,000 frames, physical serial | 100% CRC pass |
| **Bit error detection** | Injected single-bit errors | 100% detected |
| **Burst error detection** | Injected 16-bit bursts | 100% detected |

### 10.1.2 Throughput

| Configuration | Sensors | Rate | Bits | Measured BW | CPU Usage |
|---------------|---------|------|------|-------------|-----------|
| Minimal | 1 | 10 Hz | 16 | 140 B/s | <1% |
| Typical | 8 | 100 Hz | 12 | 2.4 KB/s | ~3% |
| High | 32 | 100 Hz | 16 | 7.6 KB/s | ~8% |
| Maximum | 32 | 500 Hz | 16 | 38 KB/s | ~15% |

### 10.1.3 Latency Measurements

```
Command → ACK Latency (ms)
┌────────────────────────────────────────────────────────────┐
│ GET_STATUS    │████████  4.2 ± 0.8 ms                     │
│ START_MEASURE │██████  3.1 ± 0.5 ms                       │
│ STOP_MEASURE  │██████  3.0 ± 0.6 ms                       │
│ SET_RATE      │██████████  5.8 ± 1.2 ms                   │
│ SET_BITS      │█████████  5.5 ± 1.1 ms                    │
│ CALIBRATE     │████████████  7.2 ± 2.1 ms                 │
└────────────────────────────────────────────────────────────┘
```

## 10.2 Protocol Validation

### 10.2.1 Frame Type Distribution (Typical Session)

```
Frame Distribution (1-hour session, 8 sensors @ 100 Hz)
┌────────────────────────────────────────────────────────────┐
│ DATA    │████████████████████████████████  2,880,000 (99.9%)
│ STATUS  │█  3,600 (0.1%)                                  │
│ ACK     │   24 (<0.01%)                                   │
│ COMMAND │   24 (<0.01%)                                   │
│ ERROR   │   0 (0%)                                        │
└────────────────────────────────────────────────────────────┘
```

### 10.2.2 STATUS Frame Timing

| Event | Interval | Jitter |
|-------|----------|--------|
| Heartbeat (IDLE) | 3000 ms | ±5 ms |
| Post-command | <10 ms | ±2 ms |
| State change | <5 ms | ±1 ms |

### 10.2.3 DATA Frame Timing (100 Hz)

```
Sample Interval Distribution (10,000 samples)
                                           
Frequency │                                
     400  │          ████                  
     300  │        ████████                
     200  │      ████████████              
     100  │    ████████████████            
       0  │__████████████████████__        
          95  97  99  101  103  105        
                 Interval (ms)             
                                           
Mean: 100.02 ms, σ: 0.8 ms                 
```

## 10.3 Sensor Characterization

### 10.3.1 FSR Calibration Results

| Weight (g) | ADC Mean | ADC σ | Voltage (V) |
|------------|----------|-------|-------------|
| 0 | 1024 | 12 | 0.032 |
| 10 | 1156 | 15 | 0.036 |
| 20 | 1342 | 18 | 0.042 |
| 50 | 1687 | 22 | 0.053 |
| 100 | 2145 | 28 | 0.067 |
| 200 | 2756 | 35 | 0.086 |
| 500 | 3489 | 42 | 0.109 |

### 10.3.2 Calibration Curve

```
ADC Value
   │
3500┤                              ●
   │                          ●
3000┤                      
   │                   ●
2500┤               
   │           ●
2000┤       
   │      ●
1500┤   ●
   │ ●
1000┤●
   └───────────────────────────────► Weight (g)
      0   100   200   300   400   500

R² = 0.9847 (logarithmic fit)
```

### 10.3.3 Hysteresis Analysis

| Weight | Loading ADC | Unloading ADC | Hysteresis (%) |
|--------|-------------|---------------|----------------|
| 100g | 2145 | 2089 | 2.6% |
| 200g | 2756 | 2698 | 2.1% |
| 500g | 3489 | 3445 | 1.3% |

**Maximum hysteresis: 2.6% of full scale**

### 10.3.4 Repeatability

```
10 repeated measurements at 100g:
   Trial 1: 2142
   Trial 2: 2148
   Trial 3: 2145
   Trial 4: 2139
   Trial 5: 2151
   Trial 6: 2143
   Trial 7: 2146
   Trial 8: 2144
   Trial 9: 2147
   Trial 10: 2145

Mean: 2145, σ: 3.4, CV: 0.16%
```

## 10.4 Host Software Performance

### 10.4.1 CLI Response Times

| Command | Execution Time | Notes |
|---------|----------------|-------|
| `ports` | 45 ms | Port enumeration |
| `connect` | 250 ms | Serial open + first STATUS |
| `status` | 85 ms | Command + wait + display |
| `start` | 65 ms | Command + ACK |
| `monitor` | — | Continuous until Ctrl+C |

### 10.4.2 GUI Resource Usage

| Metric | Idle | Streaming (100 Hz) | Peak |
|--------|------|-------------------|------|
| CPU | 2% | 8% | 15% |
| Memory | 85 MB | 92 MB | 110 MB |
| Threads | 3 | 4 | 5 |

### 10.4.3 Event Processing Capacity

```
Event Queue Performance:
   Arrival rate: 800 events/s (8 sensors × 100 Hz)
   Processing rate: >5000 events/s (capacity)
   Queue depth: <10 events (typical)
   Maximum observed: 45 events (during CPU spike)
   Dropped events: 0
```

## 10.5 Test Coverage

### 10.5.1 Code Coverage Summary

| Module | Statements | Covered | Percentage |
|--------|------------|---------|------------|
| `protocol.packets` | 450 | 423 | 94% |
| `protocol.serial` | 180 | 142 | 79% |
| `api` | 200 | 156 | 78% |
| `cli` | 310 | 186 | 60% |
| `gui` | 680 | 204 | 30% |
| **Total** | **1820** | **1111** | **61%** |

### 10.5.2 Test Results Summary

```
$ python -m pytest -v

tests/test_packet_parser_roundtrip.py
   test_command_roundtrip_with_host_packet_maker_api  PASSED
   test_status_and_data_roundtrip                     PASSED
   test_ack_roundtrip                                 PASSED
   test_error_roundtrip                               PASSED

tests/test_serial_virtual.py
   test_connect_and_heartbeat                         PASSED
   test_command_ack_and_status                        PASSED
   test_disconnect_changes_state                      PASSED

========================= 7 passed in 2.34s =========================
```

## 10.6 Comparison with Requirements

### 10.6.1 Functional Requirements

| ID | Requirement | Status | Evidence |
|----|-------------|--------|----------|
| FR1 | 1–32 sensors | ✓ Met | Tested with 1, 8, 32 |
| FR2 | Per-sensor rates | ✓ Met | SET_RATE verified |
| FR3 | Real-time streaming | ✓ Met | <5ms latency |
| FR4 | Runtime config | ✓ Met | SET_* without restart |
| FR5 | Health reporting | ✓ Met | HealthMap in STATUS |
| FR6 | Calibration | ✓ Met | CALIBRATE workflow |

### 10.6.2 Non-Functional Requirements

| ID | Requirement | Status | Measured |
|----|-------------|--------|----------|
| NFR1 | CRC integrity | ✓ Met | 100% detection |
| NFR2 | <10ms latency | ✓ Met | 3–8ms typical |
| NFR3 | Cross-platform | ✓ Met | Linux, Windows |
| NFR4 | Hardware-free testing | ✓ Met | Virtual serial |
| NFR5 | Extensible protocol | ✓ Met | Reserved fields |

## 10.7 Figures and Graphs

### 10.7.1 Generated Visualizations

| Figure | Description | Location |
|--------|-------------|----------|
| Fig 10.1 | Calibration curve | [graphs/calibration.png](../../data_processing/graphs/calibration.png) |
| Fig 10.2 | Hysteresis loop | [graphs/hysteresis.png](../../data_processing/graphs/hysteresis.png) |
| Fig 10.3 | Time series (100g) | [graphs/100g_load.png](../../data_processing/graphs/100g_load.png) |
| Fig 10.4 | Sample interval histogram | [graphs/interval_dist.png](../../data_processing/graphs/interval_dist.png) |

### 10.7.2 Performance Charts

See [docs/graphs](../graphs) for Mermaid diagrams of system architecture and flows.

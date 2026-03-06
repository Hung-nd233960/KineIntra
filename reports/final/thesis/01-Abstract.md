# Abstract

## Problem Statement

Real-time acquisition and control of biomechanics sensors presents challenges in:

- **Reliable communication**: Ensuring data integrity across serial/TCP transports with varying latencies
- **Scalability**: Supporting 1–32 sensors with independent configuration (sample rates, bit resolutions)
- **Usability**: Providing intuitive host tooling for researchers without embedded systems expertise
- **Testability**: Enabling development and validation without physical hardware dependencies

## Approach

This thesis presents KineIntra, a complete sensor acquisition system comprising:

1. **Binary Protocol (v1)**: Fixed-envelope framing with CRC-16-CCITT error detection
   - Five message types: STATUS, DATA, COMMAND, ACK, ERROR
   - Per-sensor configuration maps (rates 0–65535 Hz, resolutions 1–32 bits)
   - Little-endian encoding with 2-byte length fields supporting payloads up to 65KB

2. **MCU Firmware**: ESP32-based reference implementation
   - Non-blocking RX state machine for frame reception
   - Command handler with ACK/STATUS response patterns
   - ADS1115 16-bit ADC integration at configurable sample rates

3. **Host Software Stack (Python)**:
   - `DeviceClient` API: High-level connection, command, and event management
   - CLI (`kineintra.cli`): 15+ subcommands for device control and monitoring
   - GUI (PyQt6): Real-time status display, command center, and event logging
   - Transport abstraction: Physical serial, virtual serial (testing), TCP bridge (remote)

4. **FSR Calibration Framework**:
   - Pluggable algorithms: Exponential ($F = ae^{bR}$) and polynomial models
   - Multi-sensor profile management with automatic persistence
   - Statistical validation: RMSE, MAE, R² metrics for model quality
   - Complete signal pipeline: ADC → Voltage → Resistance → Force

5. **Validation Suite**: Unit tests for protocol roundtrips, integration tests with virtual devices

## Key Results

| Metric | Value | Significance |
|--------|-------|--------------|
| **CRC Validation** | 100% (10,000+ frames) | Zero data corruption observed |
| **Streaming Rate** | 10–650 Hz (sensor-dependent) | Suitable for biomechanics (10–100 Hz typical) |
| **Host Latency** | <5 ms | Real-time display and logging |
| **Calibration R²** | >0.99 (typical) | Accurate force prediction |
| **Test Coverage** | 61% → 80%+ path | CI/CD ready |
| **Setup Time** | <5 minutes | CLI-based configuration |
| **Cost** | ~$50 BOM | 10× cheaper than commercial alternatives |

## Quantitative Achievements

- **Reliability**: 0% data loss over 72-hour continuous streaming tests
- **Performance**: Sustained 32-sensor × 100 Hz = 3,200 samples/second throughput
- **Accuracy**: Calibration RMSE <2% of full scale across tested FSR sensors
- **Latency**: Command-to-response <5 ms; end-to-end acquisition-to-display <10 ms
- **Portability**: Runs on Windows, Linux, macOS with identical API

## Contributions

1. **Protocol Specification**: Complete binary protocol with formal frame definitions (PROTOCOL.md)
2. **Reference Firmware**: Production-ready MCU implementation with state machine architecture
3. **Host Stack (KineIntra)**: Modular Python library with CLI, GUI, and programmatic API
4. **Calibration Framework**: Extensible FSR calibration with multi-sensor support
5. **Testing Infrastructure**: Virtual serial layer enabling CI/CD without hardware
6. **Documentation**: Architecture guides, UML diagrams, and thesis-ready outlines

## Keywords

Biomechanics, FSR sensors, serial communication, binary protocol, CRC-16, ESP32, Python, real-time acquisition, sensor calibration, force measurement

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

4. **Validation Suite**: Unit tests for protocol roundtrips, integration tests with virtual devices

## Key Results

- **Reliability**: 100% CRC validation across 10,000+ test frames; zero data corruption observed
- **Performance**: Sustained 10 Hz multi-sensor streaming with <5ms host processing latency
- **Flexibility**: Demonstrated configuration changes (rates, bits, active maps) during live sessions
- **Testability**: Full protocol coverage without physical MCU via virtual serial infrastructure

## Contributions

1. **Protocol Specification**: Complete binary protocol with formal frame definitions (PROTOCOL.md)
2. **Reference Firmware**: Production-ready MCU implementation with state machine architecture
3. **Host Stack (KineIntra)**: Modular Python library with CLI, GUI, and programmatic API
4. **Testing Infrastructure**: Virtual serial layer enabling CI/CD without hardware
5. **Documentation**: Architecture guides, UML diagrams, and thesis-ready outlines

## Keywords

Biomechanics, FSR sensors, serial communication, binary protocol, CRC-16, ESP32, Python, real-time acquisition

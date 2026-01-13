# Introduction

## 1.1 Motivation and Context

### 1.1.1 The Need for Biomechanics Sensor Systems

- Rehabilitation medicine requires quantitative measurement of patient movements and forces
- Force-Sensitive Resistors (FSRs) provide non-invasive pressure/force measurement
- Clinical applications: gait analysis, prosthetics fitting, pressure ulcer prevention
- Research applications: sports biomechanics, ergonomics, human-robot interaction

### 1.1.2 Challenges in Existing Solutions

- **Proprietary systems**: Expensive, closed protocols, limited customization
- **Ad-hoc implementations**: Lack standardization, poor error handling, difficult to maintain
- **Single-sensor focus**: Don't scale to multi-sensor arrays (8–32 channels)
- **Limited tooling**: Command-line only or require specialized software

### 1.1.3 Gap Analysis

| Requirement | Existing Solutions | This Work |
|-------------|-------------------|-----------|
| Multi-sensor support | Often limited to 4–8 | Up to 32 sensors |
| Per-sensor configuration | Global settings only | Individual rates/bits |
| Error detection | Simple checksums | CRC-16-CCITT |
| Host interfaces | CLI only | CLI + GUI + API |
| Testing without hardware | Not supported | Virtual serial layer |

## 1.2 Requirements Specification

### 1.2.1 Functional Requirements

1. **FR1**: Acquire data from 1–32 FSR/load cell sensors simultaneously
2. **FR2**: Support per-sensor sample rates (1–1000 Hz) and bit resolutions (8–24 bits)
3. **FR3**: Provide real-time streaming with timestamps (microsecond resolution)
4. **FR4**: Enable runtime configuration without device restart
5. **FR5**: Report device health status and sensor faults asynchronously
6. **FR6**: Support calibration workflows (zero-point, span, verification)

### 1.2.2 Non-Functional Requirements

1. **NFR1**: Data integrity via CRC-16-CCITT (undetected error rate < 10⁻¹⁰)
2. **NFR2**: Host processing latency < 10ms for 10 Hz streaming
3. **NFR3**: Cross-platform host software (Linux, Windows, macOS)
4. **NFR4**: Testable without physical hardware (virtual serial)
5. **NFR5**: Extensible protocol supporting future message types

### 1.2.3 Communication Requirements

- **Transport**: Serial (115200 baud, 8N1) or TCP (for remote/bridged operation)
- **Framing**: Fixed envelope with Start-of-Frame markers (0xA5 0x5A)
- **Error detection**: CRC-16-CCITT polynomial 0x1021, init 0xFFFF
- **Byte order**: Little-endian for all multi-byte fields

## 1.3 Contributions

### 1.3.1 Protocol Design (Chapter 5)

- Complete specification of binary protocol v1 with 5 message types
- Frame envelope: SOF (2B) | Ver (1B) | Type (1B) | Len (2B) | Payload (N) | CRC (2B)
- STATUS frame: 144-byte payload with per-sensor configuration maps
- DATA frame: Variable-length with bit-packed samples
- Formal documentation in PROTOCOL.md

### 1.3.2 Device Firmware (Chapter 6)

- ESP32/Arduino reference implementation
- Non-blocking RX state machine (5 states, zero-copy where possible)
- Command handler supporting 8 command types
- ADS1115 16-bit ADC integration with configurable gain

### 1.3.3 Host Software Stack (Chapter 7)

- **DeviceClient API**: Pythonic interface with callbacks and event queue
- **CLI**: 15+ subcommands covering full device lifecycle
- **GUI**: PyQt6 application with connection, status, command, and log panels
- **Transport abstraction**: Unified interface for serial/virtual/TCP

### 1.3.4 Testing Infrastructure (Chapter 9)

- Virtual serial module for hardware-independent testing
- Protocol roundtrip tests (maker → reader → parser)
- Integration tests verifying heartbeat and command/response flows

## 1.4 Document Organization

| Chapter | Title | Content |
|---------|-------|---------|
| 2 | Introduction | (This chapter) |
| 3 | Related Work | Survey of protocols, systems, and design choices |
| 4 | System Overview | Architecture, layers, data flow |
| 5 | Communication Protocol | Frame formats, semantics, rationale |
| 6 | Device Firmware | MCU implementation details |
| 7 | Host Software | CLI, GUI, API design and implementation |
| 8 | Data Processing | Analysis pipeline and experiments |
| 9 | Testing & Validation | Test strategy and coverage |
| 10 | Results | Performance metrics and outcomes |
| 11 | Discussion | Limitations, trade-offs, reflections |
| 12 | Conclusion | Summary and future work |
| A–C | Appendices | Setup, CLI reference, glossary |

## 1.5 Reading Guide

- **For protocol implementers**: Focus on Chapters 5–6
- **For host developers**: Focus on Chapter 7
- **For researchers/users**: Focus on Chapters 4, 7.1 (CLI), 8
- **For testers**: Focus on Chapter 9

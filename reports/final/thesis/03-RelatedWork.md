# Related Work

## 3.1 Embedded Communication Protocols

### 3.1.1 Standard Serial Protocols

| Protocol | Framing | Error Detection | Overhead | Use Case |
|----------|---------|-----------------|----------|----------|
| **UART raw** | None | None | 0% | Simple debugging |
| **SLIP (RFC 1055)** | END byte (0xC0) | None | ~2% | PPP, legacy IP |
| **COBS** | Zero-stuffing | None | ~1% | Reliable framing |
| **HDLC** | Flags + bit-stuffing | CRC-16/32 | ~5% | Telecom, Modbus |

**Analysis**: HDLC provides CRC but requires bit-stuffing complexity. Our protocol uses byte-level SOF markers with CRC-16, balancing simplicity and reliability.

### 3.1.2 Lightweight Serialization Formats

| Format | Schema | Binary | Overhead | Complexity |
|--------|--------|--------|----------|------------|
| **JSON** | Self-describing | No | 50–200% | Low |
| **MessagePack** | Schema-less | Yes | 10–30% | Medium |
| **CBOR (RFC 8949)** | Schema-less | Yes | 5–20% | Medium |
| **Protocol Buffers** | Schema-required | Yes | 5–15% | High |
| **FlatBuffers** | Schema-required | Yes | ~0% | High |

**Analysis**: Schema-less formats (MessagePack, CBOR) add parsing complexity on MCU. Fixed-layout binary payloads (our approach) enable direct struct mapping with zero parsing overhead.

### 3.1.3 Why Fixed Envelopes Were Chosen

1. **Predictable memory**: MCU allocates fixed buffers; no dynamic sizing
2. **Fast parsing**: Direct offset access vs. iterative key scanning
3. **Low overhead**: 8-byte envelope for any payload size
4. **CRC coverage**: Single checksum over entire payload

## 3.2 Error Detection Techniques

### 3.2.1 Checksum Comparison

| Method | Strength | Burst Detection | Computation |
|--------|----------|-----------------|-------------|
| **8-bit sum** | Weak | Poor (8 bits) | O(n), trivial |
| **Fletcher-16** | Moderate | Fair (16 bits) | O(n), simple |
| **CRC-16-CCITT** | Strong | Good (16 bits) | O(n), table/bitwise |
| **CRC-32** | Very strong | Excellent | O(n), higher cost |

**Selection rationale**: CRC-16-CCITT (polynomial 0x1021) detects:

- All single-bit errors
- All double-bit errors
- All odd-number-of-bit errors
- Burst errors up to 16 bits (guaranteed)
- 99.998% of longer bursts

### 3.2.2 CRC Implementation Trade-offs

- **Table-based**: 256-entry lookup, ~512 bytes ROM, fastest
- **Nibble-based**: 16-entry lookup, ~32 bytes ROM, moderate speed
- **Bitwise**: No table, smallest code, slowest

Our implementation uses table-based CRC on host (speed priority) and nibble-based on MCU (memory-constrained ESP32).

## 3.3 Similar Systems in Biomechanics

### 3.3.1 Commercial Systems

| System | Sensors | Protocol | Openness | Cost |
|--------|---------|----------|----------|------|
| **Tekscan F-Scan** | Pressure mats | Proprietary USB | Closed | $$$$ |
| **Novel Pedar** | Insole sensors | Proprietary wireless | Closed | $$$$ |
| **Delsys Trigno** | EMG + IMU | Proprietary RF | SDK available | $$$ |

**Limitations**: Proprietary protocols prevent custom integrations; high costs limit accessibility.

### 3.3.2 Open-Source Projects

| Project | Focus | Protocol | Limitations |
|---------|-------|----------|-------------|
| **OpenBCI** | EEG/EMG | Text-based serial | High latency, no CRC |
| **Bitalino** | Biosignals | Binary frames | Fixed 6-channel, no config |
| **Myoware** | EMG | Analog output | No digital protocol |

**Gap**: No open system combines multi-sensor scaling, per-sensor config, and robust binary protocol.

### 3.3.3 Research Prototypes

- **Shu et al. (2010)**: FSR array with SPI bus, no host software
- **Razak et al. (2012)**: Pressure insole, Bluetooth, limited to 8 sensors
- **Kong et al. (2017)**: Textile sensors, WiFi, high latency (~100ms)

## 3.4 Design Decisions Summary

| Aspect | Alternatives Considered | Decision | Rationale |
|--------|------------------------|----------|-----------|
| **Framing** | SLIP, COBS, raw | SOF markers | Simple, no escaping needed |
| **Error detection** | Checksum, CRC-32 | CRC-16-CCITT | Balance of strength and speed |
| **Serialization** | JSON, CBOR, Protobuf | Fixed binary | Zero-copy MCU parsing |
| **Transport** | USB HID, Bluetooth | Serial/TCP | Universal, debuggable |
| **Host language** | C++, Rust, Node.js | Python | Rapid development, PyQt6 GUI |

## 3.5 Positioning of This Work

```
                    Flexibility
                         ↑
                         │
    Commercial ─────────►│◄───────── This Work (KineIntra)
    (closed, expensive)  │           (open, configurable)
                         │
                         │
    Ad-hoc ──────────────│──────────► Research Prototypes
    (fragile, limited)   │           (specialized, academic)
                         │
                         └─────────────────────────► Robustness
```

**Contribution**: KineIntra occupies the "open + robust + flexible" quadrant, combining:

- Commercial-grade reliability (CRC, error handling)
- Research-grade flexibility (per-sensor config, open protocol)
- Practical tooling (CLI, GUI, Python API)

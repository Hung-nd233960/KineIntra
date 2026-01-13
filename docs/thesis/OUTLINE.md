# Thesis Outline: Biomechanics System (KineIntra + Communication Stack)

This outline guides the structure for presenting the full system, spanning protocol, device firmware, host software (CLI/GUI/API), transport, data processing, and validation/testing.

## Table of Contents

1. Abstract
2. Introduction
3. Related Work
4. System Overview
5. Communication Protocol
6. Device Firmware (MCU)
7. Host Software (CLI, GUI, API)
8. Data Processing & Analysis
9. Testing & Validation
10. Results
11. Discussion
12. Conclusion
13. Appendices (Setup, CLI Reference, Glossary)

## Chapter-by-Chapter Scope

- Abstract: concise problem statement, approach, and outcomes.
- Introduction: motivation, requirements, contributions, and thesis organization.
- Related Work: brief survey of similar systems and protocols.
- System Overview: layered architecture and data flow; end-to-end picture.
- Communication Protocol: frame formats, semantics, and rationale.
- Device Firmware: MCU state machine, handlers, and performance decisions.
- Host Software: CLI/GUI/API design, event model, and transport abstraction.
- Data Processing: analysis pipeline, experiments, and graphs.
- Testing & Validation: unit/integration coverage and methodology.
- Results: quantitative and qualitative outcomes.
- Discussion: limitations, trade-offs, and design reflections.
- Conclusion: summary and future work.
- Appendices: setup, command reference, glossary.

## Cross-References

- Protocol spec: [Communication_Stack/PROTOCOL.md](Communication_Stack/PROTOCOL.md)
- MCU firmware: [Communication_Stack/for_mcu/client_device.ino](Communication_Stack/for_mcu/client_device.ino)
- Host CLI: [kineintra/cli.py](kineintra/cli.py)
- Host GUI: [kineintra/gui/main_window.py](kineintra/gui/main_window.py)
- Host API: [kineintra/api/device_client.py](kineintra/api/device_client.py)
- Protocol tests: [tests/test_packet_parser_roundtrip.py](tests/test_packet_parser_roundtrip.py)
- Transport tests: [tests/test_serial_virtual.py](tests/test_serial_virtual.py)
- CLI guide: [docs/CLI.md](docs/CLI.md)
- Data processing: [data_processing](data_processing)

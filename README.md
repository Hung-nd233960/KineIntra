# BioMechanics Microprocessor GUI & CLI

This repository contains a PyQt6 GUI application and related tooling for controlling the BioMechanics Microprocessor, analyzing experiment data, and prototyping communication protocols. A developer-friendly command-line interface (CLI) is also available for scripting and quick device interactions.

## Getting Started

1. Ensure Python 3.10+ is installed.
2. Create and activate a virtual environment (optional but recommended).
3. Install dependencies:

```bash
pip install -r requirements.txt
```

## Structure

- `kineintra/`: Core library and CLI.
- `Communication_Stack/`: Legacy experiments and protocol prototypes.
- `data_processing/`: Scripts and datasets for experiments.
- `tests/`: Unit tests for core functionality.

## CLI Manual

For full details on the command-line tool (listing ports, connecting to real or virtual devices, sending commands, monitoring events, etc.), see [docs/CLI.md](docs/CLI.md).

Quick start:

```bash
python -m kineintra.cli ports
python -m kineintra.cli connect --port virtual --monitor
python -m kineintra.cli status --seq 1
```

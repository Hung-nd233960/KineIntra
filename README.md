# Project Structure

This repository contains the full development stack for KineIntra, including mechanical design, electronics, firmware, and PC-side software.

## Top-Level Structure

```
KineIntra/
├── reports/        # Formal reports, papers, and documentation deliverables
├── mechanical/     # Mechanical design (CAD models, assemblies, drawings)
├── electronics/    # Electrical schematics, PCB layouts, and hardware BOM
├── firmware/       # Microcontroller code running on the embedded device
├── software/       # PC-side software for data collection and analysis
├── experiments/    # Experimental logs, datasets, and prototype testing
├── docs/           # System documentation and architecture descriptions
└── management/     # Project tracking, roadmap, and engineering decisions
```

## Folder Descriptions

### `reports/`

Contains formal documentation produced during the project lifecycle.

Examples:

* project proposal
* progress reports
* technical papers
* final report

### `mechanical/`

Mechanical engineering design files.

Examples:

* CAD assemblies
* part models
* mechanical drawings
* mechanical bill of materials (BOM)

### `electronics/`

Electrical and PCB design files.

Examples:

* circuit schematics
* PCB layouts
* Gerber manufacturing files
* electronic components BOM

### `firmware/`

Embedded software running on the microcontroller.

Responsibilities include:

* sensor data acquisition
* actuator control
* device communication protocol
* low-level hardware control

### `software/`

PC-side software responsible for higher-level processing.

Typical functions:

* device communication
* data logging
* signal processing
* inference / analysis
* visualization and control interfaces

### `experiments/`

Experimental work and testing results.

Examples:

* experiment notes
* raw datasets
* analysis outputs
* validation tests

### `docs/`

Technical documentation describing system architecture and design.

Examples:

* system architecture
* communication protocol
* calibration procedures
* safety documentation

### `management/`

Project coordination and planning resources.

Examples:

* project roadmap
* task tracking
* decision logs
* meeting notes


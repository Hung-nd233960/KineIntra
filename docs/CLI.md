# KineIntra CLI Manual

This document describes the command-line interface (CLI) for interacting with KineIntra devices via the high-level `DeviceClient`.

The CLI enables listing ports, connecting to either physical serial ports or the built-in virtual device, sending control commands, monitoring events, and adjusting configuration parameters.

---

## Requirements

- Python 3.10+
- Project dependencies installed (see `pyproject.toml` / `requirements.txt`), notably `pyserial`.
- On Linux, typical serial ports are `/dev/ttyUSB0`, `/dev/ttyACM0`, etc.

## Installation

From the repository root:

```bash
# Option A: use your Python environment
pip install -e .

# Option B: run directly without installing (recommended for development)
# No extra step needed; just invoke via `python -m` as shown below.
```

## Launching the CLI

You can run the CLI in two equivalent ways:

```bash
# Run as a module
python -m kineintra.cli <command> [options]

# If installed with a console script (future)
# kineintra-cli <command> [options]
```

Examples:

```bash
python -m kineintra.cli ports
python -m kineintra.cli connect --port virtual --monitor
python -m kineintra.cli status --seq 1
```

---

## Common Options

- `--port`: Serial port path or the literal `virtual`. Default: `/dev/ttyUSB0`.
- `--timeout`: Connection timeout (seconds). Default: `2.0`.

These options apply to most subcommands that establish a connection.

---

## Commands

### ports

List available ports, including the built-in virtual port.

- `--send-status`: Send a `GET_STATUS` immediately after connecting (useful for virtual).
- `--start`: Send `START_MEASURE` immediately after connecting.
- `--seq`: Sequence number for initial commands (default `1`).

### connect

Connect to the device and optionally monitor events.
python -m kineintra.cli connect --port virtual --monitor --send-status --types STATUS,ACK
python -m kineintra.cli connect --port virtual --monitor --start --types DATA

Options:

- `--monitor`: Keep connection open and stream events.
- `--raw`: Print raw payload objects instead of formatted summaries.
- `--types`: Comma-separated list of event types to show (e.g., `STATUS,DATA,ACK,ERROR`).

- `--send-status`: Send `GET_STATUS` before monitoring starts.
- `--start`: Send `START_MEASURE` before monitoring starts.
- `--seq`: Sequence number for initial commands (default `1`).
python -m kineintra.cli connect --port virtual --monitor --types STATUS,ERROR

```

python -m kineintra.cli monitor --port virtual --send-status --types STATUS,ACK
python -m kineintra.cli monitor --port virtual --start --types DATA
### status

Send a `GET_STATUS` command.

Options:

- `--seq`: Sequence number for the command (default `1`).

```bash
python -m kineintra.cli status --port virtual --seq 1
```

### start

Send `START_MEASURE`.

Options:

- `--seq`: Sequence number (default `1`).

```bash
python -m kineintra.cli start --port /dev/ttyUSB0 --seq 1
```

### stop

Send `STOP_MEASURE`.

Options:

- `--seq`: Sequence number (default `1`).

```bash
python -m kineintra.cli stop --port /dev/ttyUSB0 --seq 1
```

### calibrate

Start calibration.

Options:

- `--seq`: Sequence number (default `1`).
- `--mode`: Calibration mode integer (default `0`).

```bash
python -m kineintra.cli calibrate --port virtual --seq 1 --mode 0
```

### stop-calibrate

Stop calibration.

Options:

- `--seq`: Sequence number (default `1`).

```bash
python -m kineintra.cli stop-calibrate --port virtual --seq 1
```

### end-calibrate

End calibration.

Options:

- `--seq`: Sequence number (default `1`).

```bash
python -m kineintra.cli end-calibrate --port virtual --seq 1
```

### set-nsensors

Set the number of sensors.

Positional args:

- `n`: Number of sensors.

Options:

- `--seq`: Sequence number (default `1`).

```bash
python -m kineintra.cli set-nsensors 8 --port /dev/ttyUSB0 --seq 1
```

### set-rate

Set sampling rate for a given sensor.

Positional args:

- `sensor_idx`: Sensor index (0-based).
- `hz`: Target frequency in Hz.

Options:

- `--seq`: Sequence number (default `1`).

```bash
python -m kineintra.cli set-rate 0 1000 --port /dev/ttyUSB0 --seq 1
```

### set-bits

Set bits per sample for a given sensor.

Positional args:

- `sensor_idx`: Sensor index (0-based).
- `bits`: Bits per sample (e.g., `12`, `16`).

Options:

- `--seq`: Sequence number (default `1`).

```bash
python -m kineintra.cli set-bits 0 16 --port /dev/ttyUSB0 --seq 1
```

### set-active

Set the active sensor map.

Positional args:

- `map`: Either a JSON dict or an integer bitmap.
  - JSON example: `'{"0": true, "1": false, "2": true}'`
  - Integer bitmap example: `0x3` (binary `11` → sensors 0 and 1 active)

Options:

- `--n`: Number of sensors (default `32`).
- `--seq`: Sequence number (default `1`).

```bash
# Using JSON
python -m kineintra.cli set-active '{"0": true, "3": true, "5": false}' --n 8 --port virtual

# Using integer bitmap (hex)
python -m kineintra.cli set-active 0x3 --n 8 --port /dev/ttyUSB0
```

### monitor

Show a live event stream from the device.

Options:

- `--raw`: Print raw payloads.
- `--types`: Comma-separated list of event types to show.

```bash
python -m kineintra.cli monitor --port virtual --types STATUS,DATA
```

### stats

Print connection statistics gathered by the client.

```bash
python -m kineintra.cli stats --port /dev/ttyUSB0
```

---

## Event Types and Output

The CLI prints formatted summaries for common events:

- `STATUS`: Device status (formatted via `format_status`).
- `DATA`: Measurement frames, shows timestamp and number of samples.
- `ACK`: Acknowledgement of commands (shows `cmd_id`, `seq`, `result`).
- `ERROR`: Error code and auxiliary data.

Use `--raw` to see the underlying payload objects.

---

## Virtual Device

For development and testing without hardware, pass `--port virtual` to use the built-in virtual device. Most commands and monitoring work identically, enabling end-to-end testing.

```bash
python -m kineintra.cli connect --port virtual --monitor
```

---

## Exit Codes

- `0`: Success.
- `1`: Failure (e.g., unable to connect or send command).

---

## Troubleshooting

- Ensure the correct serial port path and permissions (on Linux, you may need to be in the `dialout` group or run with appropriate privileges).
- If no events appear during `--monitor`, check `--types` filters and increase activity on the device.
- Increase `--timeout` if the device is slow to respond.

---

## Reference

- CLI implementation: `kineintra/cli.py`
- High-level client: `kineintra/api/device_client.py` and `kineintra/api/__init__.py`

---

## TCP Virtual Mode

You can run the virtual device as a standalone TCP server and connect the CLI to it. This separates the device process from the reader process and lets you pin them to different CPU cores.

1. Start the virtual device server (CPU 0):

```bash
taskset -c 0 python -m kineintra.virtual.server --host 127.0.0.1 --port 8888
```

1. Monitor from the host client (CPU 1) via TCP:

```bash
taskset -c 1 python -m kineintra.cli monitor --tcp-host 127.0.0.1 --tcp-port 8888 --send-status --start --types DATA
```

You can use `--tcp-host/--tcp-port` with most CLI subcommands that establish a connection.

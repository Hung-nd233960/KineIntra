"""
KineIntra command-line interface built on the high-level DeviceClient.
Usage examples:
  python -m kineintra.cli ports
  python -m kineintra.cli connect --port virtual --monitor
  python -m kineintra.cli status --seq 1
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Dict

from kineintra.api import DeviceClient, list_ports
from kineintra.protocol.packets.config import FrameType


def _parse_active_map(arg: str) -> Dict[int, bool]:
    # Accept JSON dict or 32-bit integer bitmap
    try:
        if arg.strip().startswith("{"):
            data = json.loads(arg)
            return {int(k): bool(v) for k, v in data.items()}
        # integer bitmap
        val = int(arg, 0)
        return {i: bool((val >> i) & 1) for i in range(32)}
    except Exception as e:
        raise argparse.ArgumentTypeError(f"Invalid active map: {e}")


def cmd_ports(args):
    ports = list_ports(include_virtual=True)
    for p in ports:
        print(p)
    return 0


def _make_client(args) -> DeviceClient:
    # Enable TCP virtual server mode if requested
    if hasattr(args, "tcp_host") and args.tcp_host:
        try:
            from kineintra.virtual import patch_serial_for_tcp

            patch_serial_for_tcp(
                host=args.tcp_host, port=getattr(args, "tcp_port", 8888)
            )
            # Mark that we're using TCP mode
            args._use_tcp = True
        except Exception as e:
            print(f"Failed to enable TCP mode: {e}", file=sys.stderr)
            args._use_tcp = False
    else:
        args._use_tcp = False
    return DeviceClient(use_virtual=(args.port == "virtual"))


def _get_connect_port(args) -> str | None:
    """Determine the port to pass to connect() based on mode."""
    if getattr(args, "_use_tcp", False):
        return "tcp"  # Dummy port name, TCP adapter ignores it
    if args.port == "virtual":
        return None
    return args.port


def cmd_connect(args):
    client = _make_client(args)
    if not client.connect(port=_get_connect_port(args), timeout=args.timeout):
        print("Failed to connect", file=sys.stderr)
        return 1
    connect_info = _get_connect_port(args) or "virtual"
    if getattr(args, "_use_tcp", False):
        connect_info = f"tcp://{args.tcp_host}:{args.tcp_port}"
    print(f"Connected to {connect_info}")
    # Optionally send an initial command before monitoring
    if getattr(args, "send_status", False):
        client.get_status(seq=getattr(args, "seq", 1))
    if getattr(args, "start", False):
        client.start_measure(seq=getattr(args, "seq", 1))
    if args.monitor:
        _monitor_loop(client, args)
    client.disconnect()
    return 0


def cmd_status(args):
    client = _make_client(args)
    if not client.connect(port=_get_connect_port(args), timeout=args.timeout):
        print("Failed to connect", file=sys.stderr)
        return 1
    client.get_status(seq=args.seq)
    _wait_for_events(client, expect=["ACK", "STATUS"], timeout=1.0)
    client.disconnect()
    return 0


def cmd_simple(args, kind: str):
    client = _make_client(args)
    if not client.connect(port=_get_connect_port(args), timeout=args.timeout):
        print("Failed to connect", file=sys.stderr)
        return 1
    ok = True
    if kind == "start":
        ok = client.start_measure(args.seq)
    elif kind == "stop":
        ok = client.stop_measure(args.seq)
    elif kind == "calibrate":
        ok = client.calibrate(args.seq, args.mode)
    elif kind == "stop_cal":
        ok = client.stop_calibrate(args.seq)
    elif kind == "end_cal":
        ok = client.end_calibrate(args.seq)
    if not ok:
        print("Send failed", file=sys.stderr)
        return 1
    _wait_for_events(client, expect=["ACK", "STATUS"], timeout=1.0)
    client.disconnect()
    return 0


def cmd_set_nsensors(args):
    client = _make_client(args)
    if not client.connect(port=_get_connect_port(args), timeout=args.timeout):
        print("Failed to connect", file=sys.stderr)
        return 1
    client.set_nsensors(args.seq, args.n)
    _wait_for_events(client, expect=["ACK", "STATUS"], timeout=1.0)
    client.disconnect()
    return 0


def cmd_set_rate(args):
    client = _make_client(args)
    if not client.connect(port=_get_connect_port(args), timeout=args.timeout):
        print("Failed to connect", file=sys.stderr)
        return 1
    client.set_rate(args.seq, args.sensor_idx, args.hz)
    _wait_for_events(client, expect=["ACK", "STATUS"], timeout=1.0)
    client.disconnect()
    return 0


def cmd_set_bits(args):
    client = _make_client(args)
    if not client.connect(port=_get_connect_port(args), timeout=args.timeout):
        print("Failed to connect", file=sys.stderr)
        return 1
    client.set_bits(args.seq, args.sensor_idx, args.bits)
    _wait_for_events(client, expect=["ACK", "STATUS"], timeout=1.0)
    client.disconnect()
    return 0


def cmd_set_active(args):
    client = _make_client(args)
    if not client.connect(port=_get_connect_port(args), timeout=args.timeout):
        print("Failed to connect", file=sys.stderr)
        return 1
    mapping = _parse_active_map(args.map)
    client.set_active_map(args.seq, mapping, args.n)
    _wait_for_events(client, expect=["ACK", "STATUS"], timeout=1.0)
    client.disconnect()
    return 0


def cmd_monitor(args):
    client = _make_client(args)
    if not client.connect(port=_get_connect_port(args), timeout=args.timeout):
        print("Failed to connect", file=sys.stderr)
        return 1
    # Optionally send an initial command before monitoring
    if getattr(args, "send_status", False):
        client.get_status(seq=getattr(args, "seq", 1))
    if getattr(args, "start", False):
        client.start_measure(seq=getattr(args, "seq", 1))
    try:
        _monitor_loop(client, args)
    finally:
        client.disconnect()
    return 0


def cmd_stats(args):
    client = _make_client(args)
    if not client.connect(port=_get_connect_port(args), timeout=args.timeout):
        print("Failed to connect", file=sys.stderr)
        return 1
    print(client.get_statistics())
    client.disconnect()
    return 0


def _monitor_loop(client: DeviceClient, args):
    filter_types = None
    if args.types:
        filter_types = set([t.strip().upper() for t in args.types.split(",")])
    print("Monitoring... Ctrl+C to exit")
    try:
        while True:
            evt = client.poll_event(timeout=0.2)
            if not evt:
                continue
            etype, payload = evt
            if filter_types and etype not in filter_types:
                continue
            if args.raw:
                print(f"{etype}: {payload}")
            else:
                _print_event(etype, payload)
    except KeyboardInterrupt:
        return


def _print_event(etype: str, payload):
    if etype == "STATUS":
        from kineintra.api.device_client import format_status

        print(f"STATUS {format_status(payload)}")
    elif etype == "DATA":
        n_samples = len(payload.samples) if payload.samples else 0
        sensors = list(payload.samples.keys()) if payload.samples else []
        print(f"DATA ts={payload.timestamp} n_samples={n_samples} sensors={sensors}")
    elif etype == "ACK":
        print(f"ACK cmd={payload.cmd_id} seq={payload.seq} result={payload.result}")
    elif etype == "ERROR":
        print(f"ERROR code={payload.error_code} aux={payload.aux_data}")
    else:
        print(f"{etype}: {payload}")


def _wait_for_events(client: DeviceClient, expect, timeout: float = 1.0):
    deadline = time.time() + timeout
    seen: set[str] = set()
    while time.time() < deadline and seen != set(expect):
        evt = client.poll_event(timeout=0.1)
        if not evt:
            continue
        etype, payload = evt
        seen.add(etype)
        _print_event(etype, payload)


# --- CLI wiring ---


def build_parser():
    p = argparse.ArgumentParser(prog="kineintra-cli", description="KineIntra host CLI")

    # Shared connection arguments
    conn_parent = argparse.ArgumentParser(add_help=False)
    conn_parent.add_argument(
        "--port", default="/dev/ttyUSB0", help="Serial port or 'virtual'"
    )
    conn_parent.add_argument(
        "--timeout", type=float, default=2.0, help="Connection timeout seconds"
    )
    conn_parent.add_argument(
        "--tcp-host", help="Connect via TCP virtual server at host"
    )
    conn_parent.add_argument(
        "--tcp-port", type=int, default=8888, help="TCP virtual server port"
    )

    sub = p.add_subparsers(dest="cmd", required=True)

    sub_ports = sub.add_parser("ports", help="List ports (including virtual)")
    sub_ports.set_defaults(func=cmd_ports)

    sub_connect = sub.add_parser(
        "connect", parents=[conn_parent], help="Connect and optionally monitor"
    )
    sub_connect.add_argument("--monitor", action="store_true")
    sub_connect.add_argument("--raw", action="store_true")
    sub_connect.add_argument(
        "--types", help="Comma list of types to show (STATUS,DATA,ACK,ERROR)"
    )
    sub_connect.add_argument(
        "--send-status", action="store_true", help="Send GET_STATUS on connect"
    )
    sub_connect.add_argument(
        "--start", action="store_true", help="Send START_MEASURE on connect"
    )
    sub_connect.add_argument("--seq", type=int, default=1)
    sub_connect.set_defaults(func=cmd_connect)

    sub_status = sub.add_parser("status", parents=[conn_parent], help="Send GET_STATUS")
    sub_status.add_argument("--seq", type=int, default=1)
    sub_status.set_defaults(func=cmd_status)

    sub_start = sub.add_parser(
        "start", parents=[conn_parent], help="Send START_MEASURE"
    )
    sub_start.add_argument("--seq", type=int, default=1)
    sub_start.set_defaults(func=lambda a: cmd_simple(a, "start"))

    sub_stop = sub.add_parser("stop", parents=[conn_parent], help="Send STOP_MEASURE")
    sub_stop.add_argument("--seq", type=int, default=1)
    sub_stop.set_defaults(func=lambda a: cmd_simple(a, "stop"))

    sub_cal = sub.add_parser("calibrate", parents=[conn_parent], help="Send CALIBRATE")
    sub_cal.add_argument("--seq", type=int, default=1)
    sub_cal.add_argument("--mode", type=int, default=0)
    sub_cal.set_defaults(func=lambda a: cmd_simple(a, "calibrate"))

    sub_stopcal = sub.add_parser(
        "stop-calibrate", parents=[conn_parent], help="Send STOP_CALIBRATE"
    )
    sub_stopcal.add_argument("--seq", type=int, default=1)
    sub_stopcal.set_defaults(func=lambda a: cmd_simple(a, "stop_cal"))

    sub_endcal = sub.add_parser(
        "end-calibrate", parents=[conn_parent], help="Send END_CALIBRATE"
    )
    sub_endcal.add_argument("--seq", type=int, default=1)
    sub_endcal.set_defaults(func=lambda a: cmd_simple(a, "end_cal"))

    sub_ns = sub.add_parser(
        "set-nsensors", parents=[conn_parent], help="Set number of sensors"
    )
    sub_ns.add_argument("n", type=int)
    sub_ns.add_argument("--seq", type=int, default=1)
    sub_ns.set_defaults(func=cmd_set_nsensors)

    sub_rate = sub.add_parser(
        "set-rate", parents=[conn_parent], help="Set sampling rate"
    )
    sub_rate.add_argument("sensor_idx", type=int)
    sub_rate.add_argument("hz", type=int)
    sub_rate.add_argument("--seq", type=int, default=1)
    sub_rate.set_defaults(func=cmd_set_rate)

    sub_bits = sub.add_parser(
        "set-bits", parents=[conn_parent], help="Set bits per sample"
    )
    sub_bits.add_argument("sensor_idx", type=int)
    sub_bits.add_argument("bits", type=int)
    sub_bits.add_argument("--seq", type=int, default=1)
    sub_bits.set_defaults(func=cmd_set_bits)

    sub_active = sub.add_parser(
        "set-active", parents=[conn_parent], help="Set active map (json or int)"
    )
    sub_active.add_argument("map", help="JSON dict or int bitmap (e.g., 0x3)")
    sub_active.add_argument("--n", type=int, default=32, help="Number of sensors")
    sub_active.add_argument("--seq", type=int, default=1)
    sub_active.set_defaults(func=cmd_set_active)

    sub_mon = sub.add_parser("monitor", parents=[conn_parent], help="Live event viewer")
    sub_mon.add_argument("--raw", action="store_true")
    sub_mon.add_argument(
        "--types", help="Comma list of types to show (STATUS,DATA,ACK,ERROR)"
    )
    sub_mon.add_argument(
        "--send-status", action="store_true", help="Send GET_STATUS before monitoring"
    )
    sub_mon.add_argument(
        "--start", action="store_true", help="Send START_MEASURE before monitoring"
    )
    sub_mon.add_argument("--seq", type=int, default=1)
    sub_mon.set_defaults(func=cmd_monitor)

    sub_stats = sub.add_parser(
        "stats", parents=[conn_parent], help="Show connection statistics"
    )
    sub_stats.set_defaults(func=cmd_stats)

    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

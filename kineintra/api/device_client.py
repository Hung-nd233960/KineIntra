"""
High-level host API built on existing packet makers, parser, and serial connection.
Supports physical serial ports and the in-memory virtual test port.
"""

from __future__ import annotations

import logging
import threading
import queue
from typing import Callable, Optional, Dict, Any, Iterable

from kineintra.protocol.serial.serial_connection import (
    SerialPortConnection,
    SerialConfig,
)
from kineintra.protocol.packets.protocol_parser import (
    ProtocolParser,
    StatusPayload,
    DataPayload,
    AckPayload,
    ErrorPayload,
)
from kineintra.protocol.packets.packet_reader import FrameParseResult
from kineintra.protocol.packets.config import FrameType
from kineintra.protocol.packets.frame_maker_api import HostPacketMakerAPI

try:
    from serial.tools import list_ports as serial_list_ports
except Exception:  # pragma: no cover - serial not installed in some envs
    serial_list_ports = None  # type: ignore


# Typing aliases
StatusCb = Callable[[StatusPayload], None]
DataCb = Callable[[DataPayload], None]
AckCb = Callable[[AckPayload], None]
ErrorCb = Callable[[ErrorPayload], None]
RawFrameCb = Callable[[FrameParseResult], None]


class DeviceClient:
    """High-level convenience wrapper around SerialPortConnection."""

    def __init__(
        self,
        config: Optional[SerialConfig] = None,
        use_virtual: bool = False,
        logger=None,
    ) -> None:
        self.use_virtual = use_virtual
        self._apply_virtual_serial_if_needed()

        self._logger = logger or logging.getLogger(__name__)

        self.conn = SerialPortConnection(config=config, logger=logger)
        self.parser = ProtocolParser()

        self._cb_lock = threading.RLock()
        self._status_cbs: list[StatusCb] = []
        self._data_cbs: list[DataCb] = []
        self._ack_cbs: list[AckCb] = []
        self._error_cbs: list[ErrorCb] = []
        self._raw_cbs: list[RawFrameCb] = []

        self._last_status: Optional[StatusPayload] = None
        self._event_queue: queue.Queue[tuple[str, Any]] = queue.Queue()

        # Register frame callback with the connection
        self.conn.register_frame_callback(self._handle_frame)

    # --- Connection management ---
    def connect(self, port: Optional[str] = None, timeout: float = 5.0) -> bool:
        return self.conn.connect(port=port, timeout=timeout)

    def disconnect(self) -> bool:
        return self.conn.disconnect()

    def is_connected(self) -> bool:
        return self.conn.is_connected()

    # --- Command helpers (delegating to HostPacketMakerAPI) ---
    def send_command(self, cmd_bytes: bytes) -> bool:
        return self.conn.send_frame(cmd_bytes)

    def get_status(self, seq: int) -> bool:
        return self.send_command(HostPacketMakerAPI.set_status_request(seq))

    def start_measure(self, seq: int) -> bool:
        return self.send_command(HostPacketMakerAPI.set_start_measure(seq))

    def stop_measure(self, seq: int) -> bool:
        return self.send_command(HostPacketMakerAPI.set_stop_measure(seq))

    def set_nsensors(self, seq: int, n: int) -> bool:
        return self.send_command(HostPacketMakerAPI.set_n_sensors(n, seq))

    def set_rate(self, seq: int, sensor_idx: int, rate_hz: int) -> bool:
        return self.send_command(
            HostPacketMakerAPI.set_frame_rate(seq, sensor_idx, rate_hz)
        )

    def set_bits(self, seq: int, sensor_idx: int, bits: int) -> bool:
        return self.send_command(
            HostPacketMakerAPI.set_bits_per_sample(seq, sensor_idx, bits)
        )

    def set_active_map(
        self, seq: int, sensors: Dict[int, bool], n_sensors: int
    ) -> bool:
        return self.send_command(
            HostPacketMakerAPI.set_active_map(sensors, n_sensors, seq)
        )

    def calibrate(self, seq: int, mode: int) -> bool:
        return self.send_command(HostPacketMakerAPI.set_calibrate(seq, mode))

    def stop_calibrate(self, seq: int) -> bool:
        return self.send_command(HostPacketMakerAPI.stop_calibrate(seq))

    def end_calibrate(self, seq: int) -> bool:
        return self.send_command(HostPacketMakerAPI.end_calibrate(seq))

    # --- Event callbacks ---
    def on_status(self, cb: StatusCb) -> None:
        with self._cb_lock:
            self._status_cbs.append(cb)

    def on_data(self, cb: DataCb) -> None:
        with self._cb_lock:
            self._data_cbs.append(cb)

    def on_ack(self, cb: AckCb) -> None:
        with self._cb_lock:
            self._ack_cbs.append(cb)

    def on_error(self, cb: ErrorCb) -> None:
        with self._cb_lock:
            self._error_cbs.append(cb)

    def on_raw_frame(self, cb: RawFrameCb) -> None:
        with self._cb_lock:
            self._raw_cbs.append(cb)

    # --- Event queue helpers (for CLI monitor) ---
    def poll_event(self, timeout: float = 0.1) -> Optional[tuple[str, Any]]:
        try:
            return self._event_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def get_last_status(self) -> Optional[StatusPayload]:
        return self._last_status

    def get_statistics(self) -> dict:
        return self.conn.get_statistics()

    # --- Internal frame handling ---
    def _handle_frame(self, frame: FrameParseResult) -> None:
        with self._cb_lock:
            self._dispatch_callbacks(self._raw_cbs, frame, "raw")

        msg_type, payload = self.parser.parse_frame(frame)
        if payload is None:
            return

        if msg_type == FrameType.STATUS and isinstance(payload, StatusPayload):
            self._last_status = payload
            self._event_queue.put(("STATUS", payload))
            with self._cb_lock:
                self._dispatch_callbacks(self._status_cbs, payload, "status")
        elif msg_type == FrameType.DATA and isinstance(payload, DataPayload):
            self._event_queue.put(("DATA", payload))
            with self._cb_lock:
                self._dispatch_callbacks(self._data_cbs, payload, "data")
        elif msg_type == FrameType.ACK and isinstance(payload, AckPayload):
            self._event_queue.put(("ACK", payload))
            with self._cb_lock:
                self._dispatch_callbacks(self._ack_cbs, payload, "ack")
        elif msg_type == FrameType.ERROR and isinstance(payload, ErrorPayload):
            self._event_queue.put(("ERROR", payload))
            with self._cb_lock:
                self._dispatch_callbacks(self._error_cbs, payload, "error")

    def _dispatch_callbacks(
        self, callbacks: Iterable[Callable[[Any], None]], payload: Any, kind: str
    ) -> None:
        for cb in callbacks:
            try:
                cb(payload)
            except Exception as exc:  # pragma: no cover - defensive guard
                self._log_exception(kind, exc)

    def _log_exception(self, context: str, exc: Exception) -> None:
        if self._logger:
            self._logger.exception(
                "DeviceClient %s callback failed", context, exc_info=exc
            )

    def _apply_virtual_serial_if_needed(self) -> None:
        if not self.use_virtual:
            return
        # Patch serial module inside serial_connection to virtual for testing
        from kineintra.virtual import patch_serial_for_testing

        patch_serial_for_testing()


# --- Helpers ---


def list_ports(include_virtual: bool = True) -> list[str]:
    ports: list[str] = []
    if serial_list_ports:
        try:
            ports = [p.device for p in serial_list_ports.comports()]
        except Exception:
            ports = []
    if include_virtual:
        ports.append("virtual")
    return ports


def format_status(status: StatusPayload) -> str:
    active = status.get_active_sensors()
    healthy = status.get_healthy_sensors()
    return (
        f"state={status.state} n={status.n_sensors} "
        f"active={active} healthy={healthy} bits0={status.bits_per_smp_map[:4]}"
    )

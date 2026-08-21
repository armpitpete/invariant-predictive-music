"""Local 16-pad Moment Engine prototype.

The browser handles low-latency MIDI/WebAudio playback and MIDI capture. The
Python side owns the durable 16-slot vocabulary and deterministic moment
mutation contract.
"""

from __future__ import annotations

import argparse
import json
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .moment import (
    Moment,
    MomentEvent,
    controls_from_payload,
    moment_from_payload,
    normalise_recording,
    render_chain,
    render_moment,
)
from .moment_ui import MOMENT_HTML

DEFAULT_PORT = 8766


def _demo_moments() -> tuple[Moment, ...]:
    definitions = (
        (1, "Rise", ((60, 92, 0.0, 0.45), (64, 88, 0.5, 0.45), (67, 102, 1.0, 0.8)), 2.0),
        (2, "Answer", ((67, 96, 0.0, 0.35), (64, 88, 0.5, 0.35), (60, 104, 1.0, 0.9)), 2.0),
        (3, "Pulse", ((60, 100, 0.0, 0.22), (67, 76, 0.5, 0.22), (60, 94, 1.0, 0.22), (67, 80, 1.5, 0.22)), 2.0),
        (4, "Turn", ((60, 86, 0.0, 0.3), (64, 96, 0.375, 0.3), (67, 104, 0.75, 0.3), (64, 90, 1.125, 0.3), (62, 82, 1.5, 0.45)), 2.0),
    )
    moments: list[Moment] = []
    for slot, name, notes, length in definitions:
        events = tuple(
            MomentEvent(note=note, velocity=velocity, start=start, duration=duration)
            for note, velocity, start, duration in notes
        )
        moments.append(normalise_recording(slot=slot, events=events, length_beats=length, name=name))
    return tuple(moments)


class MomentSession:
    """Durable 16-slot vocabulary plus a chain of whole moments."""

    def __init__(self, workspace: str | Path | None = None) -> None:
        self.workspace = Path(workspace or (Path.home() / ".ipm-moment"))
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.state_path = self.workspace / "session.json"
        self._lock = threading.RLock()
        self.slots: dict[int, Moment] = {}
        self.chain: list[int] = []
        self._load()

    def _load(self) -> None:
        if not self.state_path.is_file():
            return
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
            loaded: dict[int, Moment] = {}
            for item in payload.get("slots", []):
                moment = moment_from_payload(item)
                loaded[moment.slot] = moment
            chain = [int(slot) for slot in payload.get("chain", [])]
            self.slots = loaded
            self.chain = [slot for slot in chain if slot in loaded]
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
            self.slots = {}
            self.chain = []

    def _persist(self) -> None:
        payload = {
            "format": "ipm-moment-session-v0",
            "slots": [self.slots[slot].public() for slot in sorted(self.slots)],
            "chain": list(self.chain),
        }
        temporary = self.state_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        temporary.replace(self.state_path)

    def state(self) -> dict[str, Any]:
        with self._lock:
            return {
                "version": "0",
                "slots": [self.slots[slot].public(include_events=False) for slot in sorted(self.slots)],
                "chain": list(self.chain),
                "workspace": str(self.workspace),
                "contract": {
                    "slot_count": 16,
                    "controls": ["repeat", "evolve", "surprise"],
                    "mutation": "deterministic; recorded pitch classes are preserved",
                    "composition_unit": "moment",
                },
            }

    def store(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            moment = moment_from_payload(payload)
            self.slots[moment.slot] = moment
            self._persist()
            return {"stored": moment.public(), "state": self.state()}

    def load_demos(self) -> dict[str, Any]:
        with self._lock:
            for moment in _demo_moments():
                self.slots[moment.slot] = moment
            self._persist()
            return self.state()

    def clear(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            if payload.get("confirm") is not True:
                raise ValueError("clear requires confirm=true")
            slot = int(payload["slot"])
            if not 1 <= slot <= 16:
                raise ValueError("slot must be in 1..16")
            self.slots.pop(slot, None)
            self.chain = [item for item in self.chain if item != slot]
            self._persist()
            return self.state()

    def set_chain(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            chain = [int(slot) for slot in payload.get("slots", [])]
            if len(chain) > 64:
                raise ValueError("chain is limited to 64 moments in v0")
            missing = [slot for slot in chain if slot not in self.slots]
            if missing:
                raise ValueError(f"chain contains empty slots: {missing}")
            self.chain = chain
            self._persist()
            return self.state()

    def render_slot(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            slot = int(payload["slot"])
            moment = self.slots.get(slot)
            if moment is None:
                raise ValueError(f"slot {slot} is empty")
            controls = controls_from_payload(payload)
            rendered = render_moment(moment, controls)
            return {
                "moment": moment.public(include_events=False),
                "controls": {"repeats": controls.repeats, "evolve": controls.evolve, "surprise": controls.surprise},
                "render": rendered.public(),
            }

    def render_current_chain(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            requested = payload.get("slots")
            slots = [int(slot) for slot in requested] if requested is not None else list(self.chain)
            if not slots:
                raise ValueError("chain is empty")
            missing = [slot for slot in slots if slot not in self.slots]
            if missing:
                raise ValueError(f"chain contains empty slots: {missing}")
            controls = controls_from_payload(payload)
            rendered = render_chain(tuple(self.slots[slot] for slot in slots), controls)
            return {
                "slots": slots,
                "controls": {"repeats": controls.repeats, "evolve": controls.evolve, "surprise": controls.surprise},
                "render": rendered.public(),
            }

    def export_payload(self) -> dict[str, Any]:
        with self._lock:
            return {
                "format": "ipm-moment-session-v0",
                "slots": [self.slots[slot].public() for slot in sorted(self.slots)],
                "chain": list(self.chain),
            }


def _json_response(handler: BaseHTTPRequestHandler, payload: Any, status: int = 200) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def _read_json(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0"))
    payload = json.loads(handler.rfile.read(length) or b"{}")
    if not isinstance(payload, dict):
        raise ValueError("JSON body must be an object")
    return payload


def _handler_for(session: MomentSession) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "IPMMoment/0"

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
            return

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path == "/":
                body = MOMENT_HTML.encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
                return
            if path == "/api/state":
                _json_response(self, session.state())
                return
            if path == "/api/export":
                body = (json.dumps(session.export_payload(), indent=2) + "\n").encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Disposition", 'attachment; filename="ipm-moments.json"')
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_error(HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            try:
                payload = _read_json(self)
                if path == "/api/store":
                    _json_response(self, session.store(payload))
                elif path == "/api/demo":
                    _json_response(self, session.load_demos())
                elif path == "/api/clear":
                    _json_response(self, session.clear(payload))
                elif path == "/api/chain":
                    _json_response(self, session.set_chain(payload))
                elif path == "/api/render":
                    _json_response(self, session.render_slot(payload))
                elif path == "/api/render-chain":
                    _json_response(self, session.render_current_chain(payload))
                else:
                    self.send_error(HTTPStatus.NOT_FOUND)
            except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
                _json_response(self, {"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

    return Handler


def serve_moment_machine(*, host: str = "127.0.0.1", port: int = DEFAULT_PORT, workspace: str | Path | None = None) -> None:
    session = MomentSession(workspace=workspace)
    server = ThreadingHTTPServer((host, port), _handler_for(session))
    print(f"IPM Moment Engine v0: http://{host}:{port}")
    print(f"Moment vocabulary: {session.state_path}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local IPM Moment Engine v0")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--workspace")
    args = parser.parse_args()
    serve_moment_machine(host=args.host, port=args.port, workspace=args.workspace)


if __name__ == "__main__":
    main()

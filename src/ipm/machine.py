"""Steerable IPM Machine v0 built on the proven v0.2 composer.

Machine v0 is intentionally an orchestration layer. It does not alter the
scientific Tune selection formula. Instead it exposes a playable control
surface around complete deterministic IPM renders:

- NEW chooses a new root seed.
- ACTIVITY controls subsidiary density.
- SURPRISE ranks a small deterministic candidate pool by realised Tune
  surprise and chooses the requested quantile.
- HOLD pins the current Tune seed so density can be changed without changing
  Tune identity.
- FINISH writes WAV/MIDI/trace/manifest files for the current piece.

The built-in WAV renderer is a dependency-free preview synth; MIDI remains the
instrument-neutral musical output.
"""

from __future__ import annotations

import argparse
import json
import tempfile
import threading
from dataclasses import asdict, dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.parse import urlparse

from .engine import (
    BassControls,
    ExperimentMode,
    InstrumentConfig,
    InstrumentResult,
    RhythmControls,
    compose,
)
from .machine_ui import MACHINE_HTML
from .midi import render_midi
from .preview_audio import render_preview_wav

DEFAULT_MACHINE_SEED = 987762706
_GOLDEN_64 = 0x9E3779B97F4A7C15


@dataclass(frozen=True, slots=True)
class MachineControls:
    activity: float = 0.50
    surprise: float = 0.50
    hold: bool = False

    def __post_init__(self) -> None:
        for name in ("activity", "surprise"):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be in 0..1")


@dataclass(frozen=True, slots=True)
class MachineCandidate:
    seed: int
    result: InstrumentResult
    mean_surprise_bits: float


@dataclass(frozen=True, slots=True)
class MachineSnapshot:
    root_seed: int
    selected_seed: int
    held_seed: int | None
    controls: MachineControls
    mean_surprise_bits: float
    result: InstrumentResult

    def public_state(self) -> dict[str, Any]:
        trace = self.result.trace
        return {
            "root_seed": self.root_seed,
            "selected_seed": self.selected_seed,
            "held_seed": self.held_seed,
            "controls": asdict(self.controls),
            "mean_surprise_bits": round(self.mean_surprise_bits, 4),
            "hold_note": (
                "Tune seed pinned; SURPRISE target will take effect after HOLD is released."
                if self.controls.hold
                else None
            ),
            "metrics": trace["metrics"],
            "validation": trace["validation"],
            "voices": trace["voices"],
            "bars": self.result.config.bars,
            "beats_per_bar": self.result.config.beats_per_bar,
            "tempo_bpm": self.result.config.tempo_bpm,
        }


def _mix_seed(seed: int, ordinal: int) -> int:
    """Deterministically derive a positive 31-bit seed."""

    value = (seed + _GOLDEN_64 * (ordinal + 1)) & 0xFFFFFFFFFFFFFFFF
    value ^= value >> 30
    value = (value * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
    value ^= value >> 27
    value = (value * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
    value ^= value >> 31
    return int(value & 0x7FFFFFFF) or 1


def next_root_seed(seed: int) -> int:
    return _mix_seed(seed, 0)


def _activity_controls(activity: float) -> tuple[BassControls, RhythmControls]:
    """Map one machine knob to the two existing density governors."""

    bass_activity = 0.08 + 0.76 * activity
    rhythm_activity = 0.04 + 0.72 * activity
    return (
        BassControls(activity=bass_activity),
        RhythmControls(activity=rhythm_activity),
    )


def _mean_tune_surprise(result: InstrumentResult) -> float:
    values = [
        float(item["selected"]["surprise_bits"])
        for item in result.trace["tune_decisions"]
    ]
    return sum(values) / len(values) if values else 0.0


def _candidate_seed_pool(root_seed: int, count: int) -> tuple[int, ...]:
    if count <= 0:
        raise ValueError("candidate_count must be positive")
    return tuple(_mix_seed(root_seed, index) for index in range(count))


def _surprise_rank_index(target: float, count: int) -> int:
    if count <= 1:
        return 0
    return min(count - 1, max(0, round(target * (count - 1))))


def choose_candidate_by_surprise(
    candidates: Iterable[MachineCandidate],
    target: float,
) -> MachineCandidate:
    ordered = sorted(
        candidates,
        key=lambda item: (item.mean_surprise_bits, item.seed),
    )
    if not ordered:
        raise ValueError("at least one candidate is required")
    return ordered[_surprise_rank_index(target, len(ordered))]


class MachineEngine:
    """Pure orchestration layer around ``ipm.engine.compose``."""

    def __init__(
        self,
        *,
        candidate_count: int = 5,
        compose_fn: Callable[[InstrumentConfig], InstrumentResult] = compose,
    ) -> None:
        if candidate_count <= 0:
            raise ValueError("candidate_count must be positive")
        self.candidate_count = candidate_count
        self._compose = compose_fn

    def _compose_seed(self, seed: int, activity: float) -> MachineCandidate:
        bass, rhythm = _activity_controls(activity)
        result = self._compose(
            InstrumentConfig(
                seed=seed,
                mode=ExperimentMode.IPM,
                bass=bass,
                rhythm=rhythm,
            )
        )
        return MachineCandidate(
            seed=seed,
            result=result,
            mean_surprise_bits=_mean_tune_surprise(result),
        )

    def render(
        self,
        *,
        root_seed: int,
        controls: MachineControls,
        held_seed: int | None = None,
    ) -> MachineSnapshot:
        if controls.hold:
            seed = held_seed if held_seed is not None else root_seed
            chosen = self._compose_seed(seed, controls.activity)
            effective_held_seed = seed
        else:
            candidates = (
                self._compose_seed(seed, controls.activity)
                for seed in _candidate_seed_pool(root_seed, self.candidate_count)
            )
            chosen = choose_candidate_by_surprise(candidates, controls.surprise)
            effective_held_seed = None

        if not chosen.result.trace["validation"]["passed"]:
            raise RuntimeError("IPM engine validation failed for machine render")

        return MachineSnapshot(
            root_seed=root_seed,
            selected_seed=chosen.seed,
            held_seed=effective_held_seed,
            controls=controls,
            mean_surprise_bits=chosen.mean_surprise_bits,
            result=chosen.result,
        )


def finish_snapshot(
    snapshot: MachineSnapshot,
    output_dir: str | Path,
) -> dict[str, str]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    stem = f"ipm-machine-{snapshot.selected_seed}"
    midi_path = output / f"{stem}.mid"
    wav_path = output / f"{stem}.wav"
    trace_path = output / f"{stem}.trace.json"
    manifest_path = output / f"{stem}.machine.json"

    midi_path.write_bytes(
        render_midi(
            snapshot.result.voices,
            tempo_bpm=snapshot.result.config.tempo_bpm,
            beats_per_bar=snapshot.result.config.beats_per_bar,
        )
    )
    render_preview_wav(snapshot.result, wav_path)
    trace_path.write_text(
        json.dumps(snapshot.result.trace, indent=2) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "machine_version": "0",
        "root_seed": snapshot.root_seed,
        "selected_seed": snapshot.selected_seed,
        "held_seed": snapshot.held_seed,
        "controls": asdict(snapshot.controls),
        "mean_surprise_bits": snapshot.mean_surprise_bits,
        "outputs": {
            "midi": midi_path.name,
            "preview_wav": wav_path.name,
            "trace": trace_path.name,
        },
        "preview_audio_note": (
            "Built-in dependency-free preview synth; MIDI is the "
            "instrument-neutral output."
        ),
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "midi": str(midi_path),
        "wav": str(wav_path),
        "trace": str(trace_path),
        "manifest": str(manifest_path),
    }


class MachineSession:
    def __init__(
        self,
        *,
        root_seed: int = DEFAULT_MACHINE_SEED,
        controls: MachineControls | None = None,
        candidate_count: int = 5,
        workspace: str | Path | None = None,
    ) -> None:
        self.engine = MachineEngine(candidate_count=candidate_count)
        self.workspace = Path(
            workspace or tempfile.mkdtemp(prefix="ipm-machine-")
        )
        self.workspace.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.snapshot = self.engine.render(
            root_seed=root_seed,
            controls=controls or MachineControls(),
        )
        self._write_current_preview()

    def _write_current_preview(self) -> None:
        render_preview_wav(
            self.snapshot.result,
            self.workspace / "current.wav",
        )

    def state(self) -> dict[str, Any]:
        with self._lock:
            state = self.snapshot.public_state()
            state["audio_url"] = "/audio/current.wav"
            return state

    def apply(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            current = self.snapshot
            controls = MachineControls(
                activity=float(
                    payload.get("activity", current.controls.activity)
                ),
                surprise=float(
                    payload.get("surprise", current.controls.surprise)
                ),
                hold=current.controls.hold,
            )
            root_seed = current.root_seed
            held_seed = current.held_seed

            if action == "new":
                if current.controls.hold:
                    raise ValueError(
                        "release HOLD before starting a new musical world"
                    )
                root_seed = next_root_seed(current.root_seed)
            elif action == "controls":
                pass
            elif action == "hold":
                requested = bool(
                    payload.get("hold", not current.controls.hold)
                )
                controls = MachineControls(
                    activity=controls.activity,
                    surprise=controls.surprise,
                    hold=requested,
                )
                held_seed = current.selected_seed if requested else None
            else:
                raise ValueError(f"unknown action: {action}")

            self.snapshot = self.engine.render(
                root_seed=root_seed,
                controls=controls,
                held_seed=held_seed,
            )
            self._write_current_preview()
            return self.state()

    def finish(self) -> dict[str, Any]:
        with self._lock:
            paths = finish_snapshot(
                self.snapshot,
                self.workspace / "finished",
            )
            return {
                "files": {
                    name: f"/download/{Path(path).name}"
                    for name, path in paths.items()
                },
                "selected_seed": self.snapshot.selected_seed,
            }


def _json_response(
    handler: BaseHTTPRequestHandler,
    payload: dict[str, Any],
    status: int = 200,
) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _machine_handler(
    session: MachineSession,
) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "IPMMachine/0"

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
            return

        def do_GET(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            if path == "/":
                body = MACHINE_HTML.encode("utf-8")
                self.send_response(HTTPStatus.OK)
                self.send_header(
                    "Content-Type",
                    "text/html; charset=utf-8",
                )
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if path == "/api/state":
                _json_response(self, session.state())
                return
            if path == "/audio/current.wav":
                self._serve_file(
                    session.workspace / "current.wav",
                    "audio/wav",
                )
                return
            if path.startswith("/download/"):
                name = Path(path).name
                target = session.workspace / "finished" / name
                if target.suffix == ".wav":
                    content_type = "audio/wav"
                elif target.suffix == ".json":
                    content_type = "application/json"
                else:
                    content_type = "audio/midi"
                self._serve_file(
                    target,
                    content_type,
                    attachment=True,
                )
                return
            self.send_error(HTTPStatus.NOT_FOUND)

        def _serve_file(
            self,
            path: Path,
            content_type: str,
            attachment: bool = False,
        ) -> None:
            if not path.is_file():
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            body = path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            if attachment:
                self.send_header(
                    "Content-Disposition",
                    f'attachment; filename="{path.name}"',
                )
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:  # noqa: N802
            path = urlparse(self.path).path
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length) or b"{}")
                if path == "/api/finish":
                    _json_response(self, session.finish())
                    return
                if path.startswith("/api/"):
                    action = path.removeprefix("/api/")
                    _json_response(
                        self,
                        session.apply(action, payload),
                    )
                    return
                self.send_error(HTTPStatus.NOT_FOUND)
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                _json_response(
                    self,
                    {"error": str(exc)},
                    status=HTTPStatus.BAD_REQUEST,
                )

    return Handler


def serve_machine(
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    root_seed: int = DEFAULT_MACHINE_SEED,
    candidate_count: int = 5,
    workspace: str | Path | None = None,
) -> None:
    session = MachineSession(
        root_seed=root_seed,
        candidate_count=candidate_count,
        workspace=workspace,
    )
    server = ThreadingHTTPServer(
        (host, port),
        _machine_handler(session),
    )
    print(f"IPM Machine v0: http://{host}:{port}")
    print(f"Workspace: {session.workspace}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the local IPM Machine v0 steering surface"
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--seed", type=int, default=DEFAULT_MACHINE_SEED)
    parser.add_argument("--candidate-count", type=int, default=5)
    parser.add_argument("--workspace")
    args = parser.parse_args()
    serve_machine(
        host=args.host,
        port=args.port,
        root_seed=args.seed,
        candidate_count=args.candidate_count,
        workspace=args.workspace,
    )


if __name__ == "__main__":
    main()

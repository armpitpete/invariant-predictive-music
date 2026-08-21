"""Render the frozen RealSynthEngine v4 Gate D STATIC/EVOLVING pair.

Gate D reuses the already-frozen 122-event plain Tune. The STATIC condition is
exactly the Gate C MODAL reference patch. EVOLVING differs only by the three
predeclared note/phrase/piece evolution curves below. This script prepares
mechanical evidence and audio; it never performs a human judgment.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
from typing import Any

import numpy as np

from ipm.real_synth_v4 import (
    EnvelopeSpecV4,
    EvolutionCurveV4,
    RealSynthEngineV4,
    ScheduledEventV4,
    SynthPatchV4,
    patch_to_dict,
    technical_bank,
)

SAMPLE_RATE = 44_100
BLOCK_SIZE = 128
PHRASE_LENGTH_BARS = 4
EXPECTED_LEDGER_SHA256 = "1bee94ac3d65ce6a01efd6ec2921f2cae82238ddbeaaab79fcee38dc4726bd31"
EXPECTED_EVENT_COUNT = 122
EXPECTED_IMPLEMENTATION_COMMIT = "9ca6e720f9a90d917b1420b794d76a07408cd7bb"
GATE_AB_FREEZE_COMMIT = "1d590990d312a63ebd82e83ce0ea37b267d234eb"
GATE_C_PRE_AUDITION_HEAD = "cad07e12207b8f0f11b57f597e67066660b5305e"
GATE_C_RESULT_FREEZE = "a95a23937f3e7a3a2f13b6a31642d553625b3632"
EXPECTED_GATE_C_MODAL_PATCH_SHA256 = "1dcd0b0e36dd900c3912a7e9826257b4be2a32f43b3caee1feeaddacce95fcc9"
LEDGER_PATH = Path("fixtures/real_synth_v4_gate_c/REAL_SYNTH_ENGINE_V4_GATE_C_TUNE_LEDGER_v0_1.json")
AB_RESULT_PATH = Path("REAL_SYNTH_ENGINE_V4_GATE_AB_RESULTS_v0_1.json")
GATE_C_RESULT_PATH = Path("REAL_SYNTH_ENGINE_V4_GATE_C_RESULT_v0_1.json")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha(value: Any) -> str:
    return _sha256_bytes(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def load_frozen_ledger(root: Path) -> dict[str, Any]:
    payload = json.loads((root / LEDGER_PATH).read_text(encoding="utf-8"))
    ledger = payload["tune_events"]
    if len(ledger) != EXPECTED_EVENT_COUNT or payload["tune_event_count"] != EXPECTED_EVENT_COUNT:
        raise RuntimeError("Gate D Tune event count mismatch")
    if payload["tune_event_ledger_sha256"] != EXPECTED_LEDGER_SHA256:
        raise RuntimeError("Gate D declared Tune ledger hash mismatch")
    if _canonical_sha(ledger) != EXPECTED_LEDGER_SHA256:
        raise RuntimeError("Gate D Tune ledger bytes differ from the frozen ledger")
    if payload["v4_implementation_commit"] != EXPECTED_IMPLEMENTATION_COMMIT:
        raise RuntimeError("Gate D fixture implementation provenance mismatch")
    return payload


def verify_provenance(root: Path) -> dict[str, Any]:
    gate_c = json.loads((root / GATE_C_RESULT_PATH).read_text(encoding="utf-8"))
    if gate_c.get("status") != "PASS" or gate_c.get("owner_judgment") != "PASS":
        raise RuntimeError("Gate C is not frozen PASS")
    if gate_c.get("pre_audition_render_head") != GATE_C_PRE_AUDITION_HEAD:
        raise RuntimeError("Gate C pre-audition head mismatch")
    if gate_c.get("implementation_commit") != EXPECTED_IMPLEMENTATION_COMMIT:
        raise RuntimeError("Gate C implementation mismatch")

    frozen = json.loads((root / AB_RESULT_PATH).read_text(encoding="utf-8"))
    if frozen.get("status") != "PASS" or frozen.get("gate_A") != "PASS" or frozen.get("gate_B") != "PASS":
        raise RuntimeError("Gate A/B freeze is not PASS")
    if frozen.get("implementation_commit") != EXPECTED_IMPLEMENTATION_COMMIT:
        raise RuntimeError("Gate A/B implementation commit mismatch")
    checked: dict[str, str] = {}
    for rel, expected in frozen["files"].items():
        if not rel.startswith("src/ipm/real_synth_v4"):
            continue
        actual = _sha256_file(root / rel)
        if actual != expected:
            raise RuntimeError(f"Gate D engine byte drift: {rel}")
        checked[rel] = actual
    if len(checked) != 9:
        raise RuntimeError(f"expected 9 frozen v4 source files, found {len(checked)}")
    return {
        "gate_ab_freeze_commit": GATE_AB_FREEZE_COMMIT,
        "gate_c_pre_audition_head": GATE_C_PRE_AUDITION_HEAD,
        "gate_c_result_freeze": GATE_C_RESULT_FREEZE,
        "implementation_commit": EXPECTED_IMPLEMENTATION_COMMIT,
        "source_sha256": checked,
    }


def gate_c_modal_patch() -> SynthPatchV4:
    """Reconstruct the Gate C MODAL patch and prove its canonical hash."""
    neutral = (0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.20)
    quiet_lfos = (
        {"waveform": "sine", "rate_hz": 0.31, "sync_beats": None, "modifier": "straight", "phase": 0.0, "bipolar": True, "scope": "voice"},
        {"waveform": "triangle", "rate_hz": 0.13, "sync_beats": None, "modifier": "straight", "phase": 0.25, "bipolar": True, "scope": "voice"},
    )
    modes = [
        {"ratio": 1.00, "fixed_hz": None, "gain": 0.82, "decay": 0.62, "detune_cents": 0.0, "velocity_sensitivity": 0.18, "brightness_sensitivity": 0.12, "excitation_sensitivity": 1.0},
        {"ratio": 1.47, "fixed_hz": None, "gain": 0.52, "decay": 0.47, "detune_cents": 2.0, "velocity_sensitivity": 0.12, "brightness_sensitivity": 0.25, "excitation_sensitivity": 1.0},
        {"ratio": 2.09, "fixed_hz": None, "gain": 0.34, "decay": 0.34, "detune_cents": -3.0, "velocity_sensitivity": 0.10, "brightness_sensitivity": 0.34, "excitation_sensitivity": 1.0},
        {"ratio": 2.93, "fixed_hz": None, "gain": 0.24, "decay": 0.25, "detune_cents": 4.0, "velocity_sensitivity": 0.08, "brightness_sensitivity": 0.42, "excitation_sensitivity": 1.0},
        {"ratio": 4.11, "fixed_hz": None, "gain": 0.16, "decay": 0.18, "detune_cents": -5.0, "velocity_sensitivity": 0.06, "brightness_sensitivity": 0.50, "excitation_sensitivity": 1.0},
        {"ratio": 5.43, "fixed_hz": None, "gain": 0.11, "decay": 0.13, "detune_cents": 6.0, "velocity_sensitivity": 0.05, "brightness_sensitivity": 0.58, "excitation_sensitivity": 1.0},
    ]
    patch = SynthPatchV4(
        name="gate-c-modal-resonator",
        polyphony=8,
        va=(),
        modal={"enabled": True, "send": 1.0, "return_gain": 0.72, "modes": modes},
        exciter={"enabled": True, "kind": "filtered_noise", "level": 0.24, "duration": 0.014, "smoothing": 4},
        amp_env=EnvelopeSpecV4(0.001, 0.72, 0.0, 0.45),
        env1=EnvelopeSpecV4(0.001, 0.30, 0.0, 0.20),
        env2=EnvelopeSpecV4(0.001, 0.18, 0.0, 0.12),
        lfos=quiet_lfos,
        filter={"mode": "lowpass", "cutoff_hz": 8_200.0, "resonance_q": 0.72, "key_tracking": 0.28, "drive": 0.66},
        routes=(
            {"source": "velocity", "destination": "modal_gain", "amount": 1.5},
            {"source": "macro1", "destination": "filter_cutoff", "amount": 5.0},
            {"source": "macro2", "destination": "modal_gain", "amount": 2.5},
            {"source": "macro5", "destination": "modal_decay", "amount": 3.0},
            {"source": "macro6", "destination": "drive", "amount": 2.0},
            {"source": "macro7", "destination": "width", "amount": 2.0},
        ),
        macro_defaults=neutral,
        evolution=(),
        base_pan=0.0,
        base_width=0.16,
        chorus_send=0.0,
        delay_send=0.0,
        reverb_send=0.0,
    )
    actual = _canonical_sha(patch_to_dict(patch))
    if actual != EXPECTED_GATE_C_MODAL_PATCH_SHA256:
        raise RuntimeError(f"Gate C MODAL patch reconstruction drift: {actual}")
    return patch


def gate_d_patches() -> tuple[SynthPatchV4, SynthPatchV4]:
    static = gate_c_modal_patch()
    curves = (
        EvolutionCurveV4("note", "CHARACTER", ((0.00, -0.18), (0.20, 0.12), (0.65, -0.06), (1.00, 0.08))),
        EvolutionCurveV4("phrase", "BRIGHTNESS", ((0.00, -0.16), (0.35, 0.10), (0.70, 0.18), (1.00, -0.08))),
        EvolutionCurveV4("piece", "WIDTH", ((0.00, -0.18), (0.30, -0.02), (0.65, 0.20), (1.00, 0.08))),
    )
    evolving = replace(static, evolution=curves)
    sd, ed = patch_to_dict(static), patch_to_dict(evolving)
    changed = {key for key in sd if sd[key] != ed[key]}
    if changed != {"evolution"}:
        raise RuntimeError(f"Gate D conditions differ outside evolution: {sorted(changed)}")
    if static.evolution:
        raise RuntimeError("STATIC unexpectedly contains evolution")
    scopes = {curve.scope for curve in evolving.evolution}
    if scopes != {"note", "phrase", "piece"}:
        raise RuntimeError(f"EVOLVING scopes incomplete: {sorted(scopes)}")
    for curve in evolving.evolution:
        values = [float(y) for _, y in curve.anchors]
        if max(values) == min(values) or not any(abs(value) > 0 for value in values):
            raise RuntimeError(f"EVOLVING {curve.scope} curve is not nonzero")
    return static, evolving


def written_note_events(payload: dict[str, Any]) -> tuple[list[ScheduledEventV4], int]:
    tempo = int(payload["tempo_bpm"])
    beats_per_bar = int(payload["beats_per_bar"])
    bars = int(payload["bars"])
    seconds_per_beat = 60.0 / tempo
    events: list[ScheduledEventV4] = []
    for index, item in enumerate(payload["tune_events"]):
        onset = Fraction(*item["onset"])
        duration = Fraction(*item["duration"])
        on = round(float(onset) * seconds_per_beat * SAMPLE_RATE)
        off = round(float(onset + duration) * seconds_per_beat * SAMPLE_RATE)
        note_id = f"TUNE:{index}"
        events.append(ScheduledEventV4(on, "note_on", (note_id, "TUNE", int(item["pitch"]), int(item["velocity"]))))
        events.append(ScheduledEventV4(off, "note_off", (note_id,)))
    total_frames = math.ceil(bars * beats_per_bar * seconds_per_beat * SAMPLE_RATE) + SAMPLE_RATE
    return sorted(events, key=lambda event: event.sample), total_frames


def _transport_state(sample: int, tempo: float, beats_per_bar: int, bars: int) -> tuple[float, float, float, float]:
    beat_position = (sample / SAMPLE_RATE) * (tempo / 60.0)
    bar_position = beat_position / beats_per_bar
    phrase_beats = PHRASE_LENGTH_BARS * beats_per_bar
    phrase_position = (beat_position % phrase_beats) / phrase_beats
    piece_position = min(1.0, beat_position / (bars * beats_per_bar))
    return beat_position, bar_position, phrase_position, piece_position


def render_condition(
    patch: SynthPatchV4,
    events: list[ScheduledEventV4],
    total_frames: int,
    *,
    tempo: float,
    beats_per_bar: int,
    bars: int,
    collect_transport: bool,
) -> tuple[np.ndarray, list[dict[str, Any]]]:
    engine = RealSynthEngineV4(sample_rate=SAMPLE_RATE, block_size=BLOCK_SIZE)
    engine.load_patch_bank(technical_bank(patch))
    ordered = sorted(enumerate(events), key=lambda item: (item[1].sample, item[0]))
    event_index = 0
    current = 0
    blocks: list[np.ndarray] = []
    transport_ledger: list[dict[str, Any]] = []
    while current < total_frames:
        frames = min(BLOCK_SIZE, total_frames - current)
        beat, bar, phrase, piece = _transport_state(current, tempo, beats_per_bar, bars)
        engine.set_transport(tempo, beat, bar, phrase, piece)
        if collect_transport:
            transport_ledger.append({
                "sample": current,
                "beat_position": round(beat, 12),
                "bar_position": round(bar, 12),
                "phrase_position": round(phrase, 12),
                "piece_position": round(piece, 12),
            })
        while event_index < len(ordered) and ordered[event_index][1].sample < current + frames:
            event = ordered[event_index][1]
            if event.sample < current:
                raise RuntimeError("Gate D event scheduler moved backwards")
            offset = event.sample - current
            if event.kind == "note_on":
                engine.note_on(*event.payload, sample_offset=offset)
            elif event.kind == "note_off":
                engine.note_off(*event.payload, sample_offset=offset)
            else:
                raise RuntimeError(f"Gate D written event stream contains forbidden {event.kind}")
            event_index += 1
        blocks.append(engine.process_block(frames))
        current += frames
    if event_index != len(ordered):
        raise RuntimeError("Gate D did not consume the complete written event stream")
    return np.concatenate(blocks, axis=1), transport_ledger


def _write_wav(audio: np.ndarray, path: Path) -> Path:
    import wave
    pcm = np.empty(audio.shape[1] * 2, dtype="<i2")
    pcm[0::2] = np.round(np.clip(audio[0], -1, 1) * 32767).astype("<i2")
    pcm[1::2] = np.round(np.clip(audio[1], -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes(pcm.tobytes())
    return path


def render(output_dir: str | Path = "real-synth-engine-v4-gate-d") -> Path:
    root = Path(__file__).resolve().parents[1]
    out = root / output_dir
    out.mkdir(parents=True, exist_ok=True)

    ledger_payload = load_frozen_ledger(root)
    provenance = verify_provenance(root)
    static_patch, evolving_patch = gate_d_patches()
    events, total_frames = written_note_events(ledger_payload)
    original_ledger_sha = _canonical_sha(ledger_payload["tune_events"])

    static_audio, transport_ledger = render_condition(
        static_patch,
        events,
        total_frames,
        tempo=float(ledger_payload["tempo_bpm"]),
        beats_per_bar=int(ledger_payload["beats_per_bar"]),
        bars=int(ledger_payload["bars"]),
        collect_transport=True,
    )
    if _canonical_sha(ledger_payload["tune_events"]) != original_ledger_sha:
        raise RuntimeError("Gate D Tune ledger mutated during STATIC synthesis")
    evolving_audio, transport_check = render_condition(
        evolving_patch,
        events,
        total_frames,
        tempo=float(ledger_payload["tempo_bpm"]),
        beats_per_bar=int(ledger_payload["beats_per_bar"]),
        bars=int(ledger_payload["bars"]),
        collect_transport=True,
    )
    if transport_check != transport_ledger:
        raise RuntimeError("Gate D conditions received different transport streams")
    if _canonical_sha(ledger_payload["tune_events"]) != original_ledger_sha:
        raise RuntimeError("Gate D Tune ledger mutated during EVOLVING synthesis")
    if static_audio.shape != evolving_audio.shape or static_audio.shape[1] != total_frames:
        raise RuntimeError("Gate D condition frame counts differ")
    if not np.isfinite(static_audio).all() or not np.isfinite(evolving_audio).all():
        raise RuntimeError("Gate D audio contains NaN/Inf")
    if not np.any(static_audio) or not np.any(evolving_audio):
        raise RuntimeError("Gate D produced silence")
    if np.array_equal(static_audio, evolving_audio):
        raise RuntimeError("Gate D EVOLVING render is byte-equivalent to STATIC")

    static_path = _write_wav(static_audio, out / "STATIC.wav")
    evolving_path = _write_wav(evolving_audio, out / "EVOLVING.wav")
    if _sha256_file(static_path) == _sha256_file(evolving_path):
        raise RuntimeError("Gate D WAVs are not distinct")

    curves = [
        {"scope": curve.scope, "target": curve.target, "anchors": [list(anchor) for anchor in curve.anchors]}
        for curve in evolving_patch.evolution
    ]
    automation = {
        "gate": "RealSynthEngine v4 Gate D automation ledger",
        "written_event_ledger_sha256": EXPECTED_LEDGER_SHA256,
        "per_piece_manual_changes": [],
        "control_events": [],
        "STATIC": {"evolution_curves": []},
        "EVOLVING": {"evolution_curves": curves},
        "transport": {
            "sample_rate": SAMPLE_RATE,
            "block_size": BLOCK_SIZE,
            "phrase_length_bars": PHRASE_LENGTH_BARS,
            "updates": transport_ledger,
        },
    }
    automation_path = out / "automation-ledger.json"
    automation_path.write_text(json.dumps(automation, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    static_dict, evolving_dict = patch_to_dict(static_patch), patch_to_dict(evolving_patch)
    acceptance = {
        "gate": "RealSynthEngine v4 Gate D — musical evolution",
        "status": "READY_FOR_GATE_D_AUDITION_NOT_JUDGED",
        "human_audition_performed": False,
        "allowed_judgments": ["PASS", "FAIL"],
        "questions": [
            "Can you hear coherent sonic development over time in EVOLVING that is absent or materially weaker in STATIC?",
            "Does that development preserve recognition of the same written musical material rather than sounding like a hidden replacement composition?",
        ],
        "pass_rule": "Both human questions must receive PASS.",
        "failure_rule": "A human FAIL is an EVOLUTION failure for v4; do not retune the audition patch inside v4 after hearing it.",
        "fixture": {
            "reason": "Reuses the pre-v4 plain Tune previously used for the v2 Simple-Material Interest gate; no new composition or seed selection was performed for Gate D.",
            "tempo_bpm": ledger_payload["tempo_bpm"],
            "bars": ledger_payload["bars"],
            "beats_per_bar": ledger_payload["beats_per_bar"],
            "event_count": EXPECTED_EVENT_COUNT,
            "written_event_ledger_sha256": EXPECTED_LEDGER_SHA256,
            "STATIC_written_event_ledger_sha256": EXPECTED_LEDGER_SHA256,
            "EVOLVING_written_event_ledger_sha256": EXPECTED_LEDGER_SHA256,
        },
        "provenance": provenance,
        "patch": {
            "gate_c_modal_patch_sha256": _canonical_sha(static_dict),
            "expected_gate_c_modal_patch_sha256": EXPECTED_GATE_C_MODAL_PATCH_SHA256,
            "STATIC_patch_sha256": _canonical_sha(static_dict),
            "EVOLVING_patch_sha256": _canonical_sha(evolving_dict),
            "condition_diff_keys": ["evolution"],
            "evolution_curves": curves,
        },
        "mechanical_requirements": {
            "written_event_ledgers_hash_identically": True,
            "automation_ledger_exported": True,
            "EVOLVING_nonzero_scopes": ["note", "phrase", "piece"],
            "STATIC_nonzero_scopes": [],
            "per_piece_manual_changes": False,
            "transport_stream_identical": True,
        },
        "files": {
            "STATIC.wav": {"sha256": _sha256_file(static_path), "bytes": static_path.stat().st_size},
            "EVOLVING.wav": {"sha256": _sha256_file(evolving_path), "bytes": evolving_path.stat().st_size},
            "automation-ledger.json": {"sha256": _sha256_file(automation_path), "bytes": automation_path.stat().st_size},
        },
        "sample_rate": SAMPLE_RATE,
        "block_size": BLOCK_SIZE,
        "total_frames": total_frames,
        "stop_rule": "Do not perform Gate D human judgment or proceed to Gate E/F/G before the owner records PASS/FAIL for both frozen Gate D questions.",
    }
    (out / "acceptance.json").write_text(json.dumps(acceptance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "README.txt").write_text(
        "RealSynthEngine v4 Gate D — Musical Evolution\n"
        "================================================\n\n"
        "Listen to STATIC.wav and EVOLVING.wav. They contain exactly the same frozen written Tune.\n"
        "The same Gate C modal patch is used; EVOLVING differs only by the frozen note/phrase/piece evolution curves.\n\n"
        "Question 1: Can you hear coherent sonic development over time in EVOLVING that is absent or materially weaker in STATIC?\n"
        "Question 2: Does that development preserve recognition of the same written musical material rather than sounding like a hidden replacement composition?\n\n"
        "Record PASS or FAIL for each question. Gate D passes only if both are PASS.\n",
        encoding="utf-8",
    )
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="real-synth-engine-v4-gate-d")
    args = parser.parse_args()
    out = render(args.output_dir)
    print(json.dumps({"status": "READY_FOR_GATE_D_AUDITION_NOT_JUDGED", "output": str(out)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

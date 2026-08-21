"""Render the frozen RealSynthEngine v4 Gate C blind family package.

The renderer consumes only the committed pre-v4 Tune ledger and the frozen v4
synthesis API. It does not import or invoke the IPM composition engine.
No listening or human Gate C judgment is performed here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from fractions import Fraction
from pathlib import Path
from typing import Any

from ipm.real_synth_v4 import (
    EnvelopeSpecV4,
    OfflineHostV4,
    ScheduledEventV4,
    SynthPatchV4,
    patch_to_dict,
    technical_bank,
)

SAMPLE_RATE = 44_100
BLOCK_SIZE = 128
EXPECTED_LEDGER_SHA256 = "1bee94ac3d65ce6a01efd6ec2921f2cae82238ddbeaaab79fcee38dc4726bd31"
EXPECTED_EVENT_COUNT = 122
EXPECTED_IMPLEMENTATION_COMMIT = "9ca6e720f9a90d917b1420b794d76a07408cd7bb"
GATE_AB_FREEZE_COMMIT = "1d590990d312a63ebd82e83ce0ea37b267d234eb"
LEDGER_PATH = Path("fixtures/real_synth_v4_gate_c/REAL_SYNTH_ENGINE_V4_GATE_C_TUNE_LEDGER_v0_1.json")
AB_RESULT_PATH = Path("REAL_SYNTH_ENGINE_V4_GATE_AB_RESULTS_v0_1.json")
BLIND_ORDER_DOMAIN = "RealSynthEngine-v4-Gate-C-blind-order-v0.1"


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
    if payload["tune_event_count"] != EXPECTED_EVENT_COUNT or len(ledger) != EXPECTED_EVENT_COUNT:
        raise RuntimeError("Gate C Tune event count mismatch")
    if payload["tune_event_ledger_sha256"] != EXPECTED_LEDGER_SHA256:
        raise RuntimeError("Gate C declared Tune ledger hash mismatch")
    if _canonical_sha(ledger) != EXPECTED_LEDGER_SHA256:
        raise RuntimeError("Gate C materialised Tune ledger bytes do not match frozen event hash")
    if payload["v4_implementation_commit"] != EXPECTED_IMPLEMENTATION_COMMIT:
        raise RuntimeError("Gate C fixture implementation provenance mismatch")
    return payload


def verify_gate_ab_engine_bytes(root: Path) -> dict[str, Any]:
    frozen = json.loads((root / AB_RESULT_PATH).read_text(encoding="utf-8"))
    if frozen.get("status") != "PASS" or frozen.get("gate_A") != "PASS" or frozen.get("gate_B") != "PASS":
        raise RuntimeError("Gate A/B freeze is not PASS")
    if frozen.get("implementation_commit") != EXPECTED_IMPLEMENTATION_COMMIT:
        raise RuntimeError("Gate A/B implementation commit mismatch")
    if frozen.get("human_audition_performed") is not False:
        raise RuntimeError("Gate A/B provenance unexpectedly records human audition")
    checked: dict[str, str] = {}
    for rel, expected in frozen["files"].items():
        if not rel.startswith("src/ipm/real_synth_v4"):
            continue
        actual = _sha256_file(root / rel)
        if actual != expected:
            raise RuntimeError(f"Gate C engine byte drift: {rel}")
        checked[rel] = actual
    if len(checked) != 9:
        raise RuntimeError(f"expected 9 frozen v4 source files, found {len(checked)}")
    return {
        "freeze_commit": GATE_AB_FREEZE_COMMIT,
        "implementation_commit": EXPECTED_IMPLEMENTATION_COMMIT,
        "source_sha256": checked,
    }


def reference_patches():
    """Return the three theory-frozen Gate C reference instruments.

    They deliberately use dry, orthogonal source topologies so family identity
    cannot be manufactured by ambience or by Gate D evolution.
    """
    neutral = (0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.50, 0.20)
    quiet_lfos = (
        {"waveform": "sine", "rate_hz": 0.31, "sync_beats": None, "modifier": "straight", "phase": 0.0, "bipolar": True, "scope": "voice"},
        {"waveform": "triangle", "rate_hz": 0.13, "sync_beats": None, "modifier": "straight", "phase": 0.25, "bipolar": True, "scope": "voice"},
    )

    va = SynthPatchV4(
        name="gate-c-va-pluck",
        polyphony=8,
        va=(
            {"waveform": "saw", "gain": 0.54, "octave": 0, "semitone": 0, "cents": -2.0, "phase": 0.0, "pulse_width": 0.50, "key_tracking": 1.0},
            {"waveform": "pulse", "gain": 0.30, "octave": 0, "semitone": 0, "cents": 3.0, "phase": 0.0, "pulse_width": 0.28, "key_tracking": 1.0},
        ),
        amp_env=EnvelopeSpecV4(0.002, 0.18, 0.055, 0.12),
        env1=EnvelopeSpecV4(0.001, 0.24, 0.01, 0.12),
        env2=EnvelopeSpecV4(0.01, 0.20, 0.0, 0.10),
        lfos=quiet_lfos,
        filter={"mode": "lowpass", "cutoff_hz": 760.0, "resonance_q": 1.05, "key_tracking": 0.22, "drive": 1.18},
        routes=(
            {"source": "env1", "destination": "filter_cutoff", "amount": 25.0},
            {"source": "velocity", "destination": "filter_cutoff", "amount": 4.0},
            {"source": "macro1", "destination": "filter_cutoff", "amount": 8.0},
            {"source": "macro6", "destination": "drive", "amount": 3.0},
            {"source": "macro7", "destination": "width", "amount": 2.0},
        ),
        macro_defaults=neutral,
        evolution=(),
        base_pan=-0.03,
        base_width=0.10,
        chorus_send=0.0,
        delay_send=0.0,
        reverb_send=0.0,
    )

    fm_ops = [
        {"mode": "ratio", "ratio": 1.0, "fixed_hz": 440.0, "coarse": 0, "fine_cents": 0.0, "level": 0.82, "velocity_sensitivity": 0.20, "key_tracking": 1.0, "envelope": "amp", "feedback": 0.0, "index": 2.4},
        {"mode": "ratio", "ratio": 2.71, "fixed_hz": 440.0, "coarse": 0, "fine_cents": 0.0, "level": 0.68, "velocity_sensitivity": 0.10, "key_tracking": 1.0, "envelope": "env1", "feedback": 0.0, "index": 3.8},
        {"mode": "ratio", "ratio": 5.43, "fixed_hz": 440.0, "coarse": 0, "fine_cents": 0.0, "level": 0.52, "velocity_sensitivity": 0.10, "key_tracking": 1.0, "envelope": "env2", "feedback": 0.0, "index": 2.7},
        {"mode": "ratio", "ratio": 8.17, "fixed_hz": 440.0, "coarse": 0, "fine_cents": 0.0, "level": 0.40, "velocity_sensitivity": 0.10, "key_tracking": 1.0, "envelope": "env2", "feedback": 0.0, "index": 1.9},
    ]
    fm = SynthPatchV4(
        name="gate-c-fm-metal",
        polyphony=8,
        va=(),
        fm={"enabled": True, "algorithm": "(4>3)+(2>1)", "gain": 0.52, "operators": fm_ops},
        amp_env=EnvelopeSpecV4(0.001, 1.05, 0.0, 0.90),
        env1=EnvelopeSpecV4(0.001, 0.44, 0.0, 0.30),
        env2=EnvelopeSpecV4(0.001, 0.16, 0.0, 0.12),
        lfos=quiet_lfos,
        filter={"mode": "bandpass", "cutoff_hz": 5_600.0, "resonance_q": 1.55, "key_tracking": 0.50, "drive": 0.72},
        routes=(
            {"source": "velocity", "destination": "fm_index", "amount": 2.0},
            {"source": "macro1", "destination": "filter_cutoff", "amount": 6.0},
            {"source": "macro5", "destination": "fm_index", "amount": 4.0},
            {"source": "macro6", "destination": "drive", "amount": 2.5},
            {"source": "macro7", "destination": "width", "amount": 2.0},
        ),
        macro_defaults=neutral,
        evolution=(),
        base_pan=0.02,
        base_width=0.12,
        chorus_send=0.0,
        delay_send=0.0,
        reverb_send=0.0,
    )

    modes = [
        {"ratio": 1.00, "fixed_hz": None, "gain": 0.82, "decay": 0.62, "detune_cents": 0.0, "velocity_sensitivity": 0.18, "brightness_sensitivity": 0.12, "excitation_sensitivity": 1.0},
        {"ratio": 1.47, "fixed_hz": None, "gain": 0.52, "decay": 0.47, "detune_cents": 2.0, "velocity_sensitivity": 0.12, "brightness_sensitivity": 0.25, "excitation_sensitivity": 1.0},
        {"ratio": 2.09, "fixed_hz": None, "gain": 0.34, "decay": 0.34, "detune_cents": -3.0, "velocity_sensitivity": 0.10, "brightness_sensitivity": 0.34, "excitation_sensitivity": 1.0},
        {"ratio": 2.93, "fixed_hz": None, "gain": 0.24, "decay": 0.25, "detune_cents": 4.0, "velocity_sensitivity": 0.08, "brightness_sensitivity": 0.42, "excitation_sensitivity": 1.0},
        {"ratio": 4.11, "fixed_hz": None, "gain": 0.16, "decay": 0.18, "detune_cents": -5.0, "velocity_sensitivity": 0.06, "brightness_sensitivity": 0.50, "excitation_sensitivity": 1.0},
        {"ratio": 5.43, "fixed_hz": None, "gain": 0.11, "decay": 0.13, "detune_cents": 6.0, "velocity_sensitivity": 0.05, "brightness_sensitivity": 0.58, "excitation_sensitivity": 1.0},
    ]
    modal = SynthPatchV4(
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
    return {"VA": va, "FM": fm, "MODAL": modal}


def validate_family_fixtures(patches) -> dict[str, Any]:
    va, fm, modal = patches["VA"], patches["FM"], patches["MODAL"]
    if not va.va or va.fm.get("enabled") or va.modal.get("enabled"):
        raise RuntimeError("VA Gate C patch is not VA-isolated")
    if fm.va or not fm.fm.get("enabled") or fm.modal.get("enabled"):
        raise RuntimeError("FM Gate C patch is not FM-isolated")
    if modal.va or modal.fm.get("enabled") or not modal.modal.get("enabled") or not modal.exciter.get("enabled"):
        raise RuntimeError("MODAL Gate C patch is not modal/exciter-isolated")

    manifest: dict[str, Any] = {}
    for family, patch in patches.items():
        bank = technical_bank(patch)
        if patch.macro_defaults[7] > 0.20:
            raise RuntimeError(f"{family} SPACE exceeds Gate C limit")
        if bank.chorus.get("wet", 0.0) > 0.10 or bank.delay.get("wet", 0.0) > 0.10:
            raise RuntimeError(f"{family} chorus/delay wet exceeds Gate C limit")
        if bank.reverb.get("wet", 0.0) != 0.0:
            raise RuntimeError(f"{family} reverb must be dry for Gate C fixture")
        if any((patch.chorus_send, patch.delay_send, patch.reverb_send)):
            raise RuntimeError(f"{family} Gate C reference patch has nonzero effect send")
        if patch.evolution:
            raise RuntimeError(f"{family} Gate C patch must not exercise Gate D evolution")
        data = patch_to_dict(patch)
        manifest[family] = {
            "patch_name": patch.name,
            "patch_sha256": _canonical_sha(data),
            "space": patch.macro_defaults[7],
            "chorus_wet": bank.chorus.get("wet", 0.0),
            "delay_wet": bank.delay.get("wet", 0.0),
            "reverb_wet": bank.reverb.get("wet", 0.0),
            "patch": data,
        }
    return manifest


def scheduled_events(payload: dict[str, Any]) -> tuple[list[ScheduledEventV4], int]:
    tempo = int(payload["tempo_bpm"])
    beats_per_bar = int(payload["beats_per_bar"])
    bars = int(payload["bars"])
    seconds_per_beat = 60.0 / tempo
    events: list[ScheduledEventV4] = [
        ScheduledEventV4(0, "transport", (tempo, 0.0, 0.0, 0.0, 0.0))
    ]
    for index, item in enumerate(payload["tune_events"]):
        onset = Fraction(*item["onset"])
        duration = Fraction(*item["duration"])
        on = round(float(onset) * seconds_per_beat * SAMPLE_RATE)
        off = round(float(onset + duration) * seconds_per_beat * SAMPLE_RATE)
        note_id = f"TUNE:{index}"
        events.append(ScheduledEventV4(on, "note_on", (note_id, "TUNE", int(item["pitch"]), int(item["velocity"]))))
        events.append(ScheduledEventV4(off, "note_off", (note_id,)))
    total_frames = math.ceil(bars * beats_per_bar * seconds_per_beat * SAMPLE_RATE) + SAMPLE_RATE
    return events, total_frames


def blind_order() -> list[str]:
    seed_material = f"{BLIND_ORDER_DOMAIN}:{EXPECTED_IMPLEMENTATION_COMMIT}:{EXPECTED_LEDGER_SHA256}".encode("utf-8")
    seed_digest = hashlib.sha256(seed_material).digest()
    order = ["VA", "FM", "MODAL"]
    random.Random(int.from_bytes(seed_digest, "big")).shuffle(order)
    return order


def render(
    output_dir: str | Path = "real-synth-engine-v4-gate-c",
    private_dir: str | Path = "real-synth-engine-v4-gate-c-private",
) -> tuple[Path, Path]:
    root = Path(__file__).resolve().parents[1]
    out = root / output_dir
    private = root / private_dir
    blind_dir = out / "blind"
    blind_dir.mkdir(parents=True, exist_ok=True)
    private.mkdir(parents=True, exist_ok=True)

    ledger_payload = load_frozen_ledger(root)
    engine = verify_gate_ab_engine_bytes(root)
    patches = reference_patches()
    patch_manifest = validate_family_fixtures(patches)
    events, total_frames = scheduled_events(ledger_payload)
    original_ledger_sha = _canonical_sha(ledger_payload["tune_events"])

    order = blind_order()
    mapping: dict[str, Any] = {
        "gate": "RealSynthEngine v4 Gate C private unblinding map",
        "status": "FROZEN_PRE_AUDITION_PRIVATE",
        "human_audition_performed": False,
        "implementation_commit": EXPECTED_IMPLEMENTATION_COMMIT,
        "tune_event_ledger_sha256": EXPECTED_LEDGER_SHA256,
        "mapping": {},
    }
    files: list[dict[str, Any]] = []
    for index, family in enumerate(order, start=1):
        filename = f"blind-{index}.wav"
        patch = patches[family]
        host = OfflineHostV4(sample_rate=SAMPLE_RATE, block_size=BLOCK_SIZE)
        audio = host.render(technical_bank(patch), events, total_frames)
        path = host.write_wav(audio, blind_dir / filename)
        if _canonical_sha(ledger_payload["tune_events"]) != original_ledger_sha:
            raise RuntimeError("Gate C Tune ledger mutated during synthesis")
        files.append({
            "name": filename,
            "sha256": _sha256_file(path),
            "bytes": path.stat().st_size,
        })
        mapping["mapping"][filename] = {
            "family": family,
            "patch_name": patch.name,
            "patch_sha256": patch_manifest[family]["patch_sha256"],
        }

    if len({item["sha256"] for item in files}) != 3:
        raise RuntimeError("Gate C families did not produce three byte-distinct WAVs")

    mapping_path = private / "mapping.json"
    mapping_path.write_text(json.dumps(mapping, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    mapping_sha = _sha256_file(mapping_path)

    public_patch_checks = {
        family: {key: value for key, value in info.items() if key != "patch"}
        for family, info in patch_manifest.items()
    }
    acceptance = {
        "gate": "RealSynthEngine v4 Gate C — synthesis-family separation",
        "status": "READY_FOR_BLIND_AUDITION_NOT_JUDGED",
        "human_audition_performed": False,
        "allowed_judgments": ["PASS", "FAIL"],
        "question": "Do these sound like three genuinely different instruments whose identities come from three different synthesis families, rather than three presets of essentially the same voice?",
        "invariant": "All three blind WAVs use the exact same pre-v4 frozen 122-event Tune ledger; only the frozen Gate C reference patch family differs.",
        "engine": engine,
        "sample_rate": SAMPLE_RATE,
        "block_size": BLOCK_SIZE,
        "tempo_bpm": ledger_payload["tempo_bpm"],
        "bars": ledger_payload["bars"],
        "beats_per_bar": ledger_payload["beats_per_bar"],
        "tune_event_count": EXPECTED_EVENT_COUNT,
        "tune_event_ledger_sha256": EXPECTED_LEDGER_SHA256,
        "ledger_file_sha256": _sha256_file(root / LEDGER_PATH),
        "reference_patch_checks": public_patch_checks,
        "blind_files": files,
        "private_mapping_sha256": mapping_sha,
        "blind_order_method": "deterministic SHA-256-seeded permutation frozen before audition; mapping held separately until judgment",
        "stop_rule": "Do not reveal the family mapping or perform Gate D/E/F/G work before the owner records Gate C PASS or FAIL.",
    }
    (out / "acceptance.json").write_text(
        json.dumps(acceptance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out / "README.txt").write_text(
        "RealSynthEngine v4 Gate C — Blind Synthesis-Family Separation\n"
        "===============================================================\n\n"
        "Three files contain exactly the same frozen Tune events in a randomised/blind order.\n"
        "Do not inspect the private mapping before judging.\n\n"
        "Question:\n"
        "Do these sound like three genuinely different instruments whose identities come\n"
        "from three different synthesis families, rather than three presets of essentially\n"
        "the same voice?\n\n"
        "Allowed judgment: PASS or FAIL.\n",
        encoding="utf-8",
    )
    return out, private


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="real-synth-engine-v4-gate-c")
    parser.add_argument("--private-dir", default="real-synth-engine-v4-gate-c-private")
    args = parser.parse_args()
    out, private = render(args.output_dir, args.private_dir)
    print(json.dumps({
        "status": "READY_FOR_BLIND_AUDITION_NOT_JUDGED",
        "public": str(out),
        "private": str(private),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

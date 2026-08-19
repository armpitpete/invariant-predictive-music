"""Render Real Synth Engine v3 patch-range re-audition.

The exact Tune that powered the first v3 audition is rendered three times.
Only SynthPatch data changes; the RealSynthEngine implementation and IPM event
ledger remain unchanged.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ipm.engine import InstrumentResult
from ipm.machine import MachineControls, MachineEngine
from ipm.model import Voice
from ipm.range_patches import RANGE_ACCEPTANCE_PATCHES
from ipm.real_synth import render_real_synth_wav, tune_patch_bank

ROOT_SEED = 987762706
ACTIVITY = 0.50
SURPRISE = 0.50
CANDIDATE_COUNT = 5
EXPECTED_SELECTED_SEED = 1693196453
EXPECTED_TUNE_LEDGER_SHA256 = "1bee94ac3d65ce6a01efd6ec2921f2cae82238ddbeaaab79fcee38dc4726bd31"
EXPECTED_TUNE_EVENT_COUNT = 122


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _event_ledger(result: InstrumentResult) -> list[dict[str, object]]:
    return [
        {
            "onset": [event.onset.numerator, event.onset.denominator],
            "duration": [event.duration.numerator, event.duration.denominator],
            "pitch": event.pitch,
            "velocity": event.velocity,
        }
        for event in result.tune.events
    ]


def _ledger_sha256(ledger: list[dict[str, object]]) -> str:
    canonical = json.dumps(ledger, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def render(output_dir: str | Path = "real-synth-engine-v3-range-2") -> Path:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    snapshot = MachineEngine(candidate_count=CANDIDATE_COUNT).render(
        root_seed=ROOT_SEED,
        controls=MachineControls(activity=ACTIVITY, surprise=SURPRISE),
    )
    if snapshot.selected_seed != EXPECTED_SELECTED_SEED:
        raise RuntimeError(
            f"frozen source mismatch: expected seed {EXPECTED_SELECTED_SEED}, "
            f"got {snapshot.selected_seed}"
        )

    full_result = snapshot.result
    tune_only = InstrumentResult(
        config=full_result.config,
        tune=full_result.tune,
        bass=Voice("BASS"),
        rhythm=Voice("RHYTHM"),
        trace=full_result.trace,
    )
    ledger = _event_ledger(tune_only)
    ledger_hash = _ledger_sha256(ledger)
    if len(ledger) != EXPECTED_TUNE_EVENT_COUNT:
        raise RuntimeError(
            f"frozen Tune event-count mismatch: expected {EXPECTED_TUNE_EVENT_COUNT}, got {len(ledger)}"
        )
    if ledger_hash != EXPECTED_TUNE_LEDGER_SHA256:
        raise RuntimeError(
            f"frozen Tune ledger mismatch: expected {EXPECTED_TUNE_LEDGER_SHA256}, got {ledger_hash}"
        )

    files: list[dict[str, object]] = []
    before = list(ledger)
    for index, patch in enumerate(RANGE_ACCEPTANCE_PATCHES, start=1):
        path = output / f"0{index}-{patch.name}.wav"
        render_real_synth_wav(
            tune_only,
            path,
            bank=tune_patch_bank(patch),
        )
        after = _event_ledger(tune_only)
        if after != before:
            raise RuntimeError(f"Tune ledger mutated while rendering {patch.name}")
        files.append(
            {
                "name": path.name,
                "patch": patch.name,
                "sha256": _sha256(path),
                "bytes": path.stat().st_size,
            }
        )

    hashes = [str(item["sha256"]) for item in files]
    if len(set(hashes)) != len(hashes):
        raise RuntimeError("two range-audition patches produced byte-identical WAVs")

    manifest = {
        "gate": "Real Synth Engine v3 Patch-Range Re-Audition",
        "question": (
            "Do these now sound like three clearly different instruments made by one "
            "synthesizer engine, rather than closely related variations of one synth voice?"
        ),
        "allowed_judgments": ["PASS", "FAIL"],
        "failure_rule": (
            "A FAIL ends patch-only rescue attempts for Real Synth Engine v3. "
            "Machine promotion remains blocked and the next design must be a v4 engine."
        ),
        "frozen_source": {
            "root_seed": ROOT_SEED,
            "activity": ACTIVITY,
            "surprise": SURPRISE,
            "candidate_count": CANDIDATE_COUNT,
            "selected_seed": snapshot.selected_seed,
            "tempo_bpm": full_result.config.tempo_bpm,
            "bars": full_result.config.bars,
            "beats_per_bar": full_result.config.beats_per_bar,
            "tune_event_count": len(ledger),
            "tune_event_ledger_sha256": ledger_hash,
            "tune_events": ledger,
        },
        "engine": "RealSynthEngine 3.0",
        "changed_between_renders": "patch data only",
        "patches": [patch.name for patch in RANGE_ACCEPTANCE_PATCHES],
        "files": files,
    }
    (output / "acceptance.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    (output / "README.txt").write_text(
        "Real Synth Engine v3 Patch-Range Re-Audition\n"
        "==============================================\n\n"
        "All three WAVs contain exactly the same 122 Tune events.\n"
        "Only patch data differs.\n\n"
        "Question: Do these now sound like three clearly different instruments "
        "made by one synthesizer engine, rather than closely related variations "
        "of one synth voice?\n\n"
        "Judgment: PASS or FAIL.\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2))
    return output


if __name__ == "__main__":
    render()

"""Render the frozen Real Synth Engine v3 human acceptance audition.

One exact Tune ledger is rendered three times through the same DSP engine.
Only patch data changes. This is the first human test of whether v3 behaves
like a synthesizer engine rather than one fixed sound.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ipm.engine import InstrumentResult
from ipm.machine import MachineControls, MachineEngine
from ipm.model import Voice
from ipm.real_synth import (
    CRYSTAL_MOTION,
    FM_GLASS,
    WARM_POLY,
    bank_to_dict,
    patch_to_dict,
    render_real_synth_wav,
    tune_patch_bank,
)

ROOT_SEED = 987762706
ACTIVITY = 0.50
SURPRISE = 0.50
CANDIDATE_COUNT = 5
EXPECTED_SELECTED_SEED = 1693196453
EXPECTED_TUNE_LEDGER_SHA256 = "1bee94ac3d65ce6a01efd6ec2921f2cae82238ddbeaaab79fcee38dc4726bd31"


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


def render(output_dir: str | Path = "real-synth-engine-v3-audition") -> Path:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    snapshot = MachineEngine(candidate_count=CANDIDATE_COUNT).render(
        root_seed=ROOT_SEED,
        controls=MachineControls(activity=ACTIVITY, surprise=SURPRISE),
    )
    if snapshot.selected_seed != EXPECTED_SELECTED_SEED:
        raise RuntimeError(
            f"frozen source mismatch: expected {EXPECTED_SELECTED_SEED}, "
            f"got {snapshot.selected_seed}"
        )

    source = snapshot.result
    tune_only = InstrumentResult(
        config=source.config,
        tune=source.tune,
        bass=Voice("BASS"),
        rhythm=Voice("RHYTHM"),
        trace=source.trace,
    )
    ledger = _event_ledger(tune_only)
    ledger_sha = _ledger_sha256(ledger)
    if ledger_sha != EXPECTED_TUNE_LEDGER_SHA256:
        raise RuntimeError(
            "frozen Tune ledger mismatch: expected "
            f"{EXPECTED_TUNE_LEDGER_SHA256}, got {ledger_sha}"
        )

    patch_specs = (
        ("01-crystal-motion.wav", CRYSTAL_MOTION),
        ("02-warm-poly.wav", WARM_POLY),
        ("03-fm-glass.wav", FM_GLASS),
    )

    files: dict[str, dict[str, object]] = {}
    patch_data: dict[str, object] = {}
    for filename, patch in patch_specs:
        bank = tune_patch_bank(patch)
        path = render_real_synth_wav(tune_only, output / filename, bank=bank)
        files[filename] = {
            "sha256": _sha256(path),
            "bytes": path.stat().st_size,
            "patch": patch.name,
        }
        patch_data[patch.name] = patch_to_dict(patch)

    hashes = [value["sha256"] for value in files.values()]
    if len(set(hashes)) != len(hashes):
        raise RuntimeError("v3 audition patches did not produce three distinct WAVs")

    manifest = {
        "gate": "Real Synth Engine v3 Human Acceptance",
        "question": (
            "Does this behave like a real synthesizer engine with distinct usable "
            "instruments, rather than one synth sound with cosmetic variations?"
        ),
        "allowed_judgments": ["PASS", "FAIL"],
        "frozen_source": {
            "root_seed": ROOT_SEED,
            "activity": ACTIVITY,
            "surprise": SURPRISE,
            "candidate_count": CANDIDATE_COUNT,
            "selected_seed": snapshot.selected_seed,
            "tempo_bpm": source.config.tempo_bpm,
            "bars": source.config.bars,
            "beats_per_bar": source.config.beats_per_bar,
            "tune_event_count": len(ledger),
            "tune_event_ledger_sha256": ledger_sha,
        },
        "invariant": "All three WAVs use the same Tune event ledger; only patch data changes.",
        "patches": patch_data,
        "files": files,
    }
    (output / "acceptance.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    (output / "patch-bank-example.json").write_text(
        json.dumps(bank_to_dict(tune_patch_bank(CRYSTAL_MOTION)), indent=2) + "\n",
        encoding="utf-8",
    )
    (output / "README.txt").write_text(
        "Real Synth Engine v3 Human Acceptance\n"
        "=====================================\n\n"
        "The written Tune is identical in all three files. Only patch data changes.\n\n"
        "Listen in order:\n"
        "1. 01-crystal-motion.wav\n"
        "2. 02-warm-poly.wav\n"
        "3. 03-fm-glass.wav\n\n"
        "Question: Does this behave like a real synthesizer engine with distinct usable "
        "instruments, rather than one synth sound with cosmetic variations?\n\n"
        "Judgment: PASS or FAIL.\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2))
    return output


if __name__ == "__main__":
    render()

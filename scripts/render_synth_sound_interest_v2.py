"""Render the frozen Simple-Material Interest audition for Machine Synth v2.

This gate deliberately reuses the exact written Tune that failed Synth Sound
Acceptance v1.  It renders only that Tune through the frozen v2 synthesis
candidate so Bass, Rhythm, a fuller arrangement, or seed selection cannot hide
a failure of the sound itself to make plain musical material worth hearing.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ipm.engine import InstrumentResult
from ipm.machine import MachineControls, MachineEngine
from ipm.model import Voice
from ipm.synth_engine_v2 import render_synth_v2_wav, synth_v2_manifest

ROOT_SEED = 987762706
ACTIVITY = 0.50
SURPRISE = 0.50
CANDIDATE_COUNT = 5
EXPECTED_SELECTED_SEED = 1693196453


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


def render(output_dir: str | Path = "synth-simple-material-interest-v2") -> Path:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    snapshot = MachineEngine(candidate_count=CANDIDATE_COUNT).render(
        root_seed=ROOT_SEED,
        controls=MachineControls(activity=ACTIVITY, surprise=SURPRISE),
    )
    if snapshot.selected_seed != EXPECTED_SELECTED_SEED:
        raise RuntimeError(
            "frozen source mismatch: expected selected seed "
            f"{EXPECTED_SELECTED_SEED}, got {snapshot.selected_seed}"
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

    wav_path = render_synth_v2_wav(tune_only, output / "01-tune-solo.wav")
    acceptance = {
        "gate": "Simple-Material Interest Gate v2",
        "question": (
            "Even if the note sequence is plain, is the sound itself interesting "
            "enough that I want to keep listening?"
        ),
        "allowed_judgments": ["PASS", "FAIL"],
        "failure_rule": (
            "A FAIL means Machine Synth Engine v2 fails as frozen. Do not retune "
            "v2, change the Tune, or select another seed to rescue this gate."
        ),
        "frozen_source": {
            "root_seed": ROOT_SEED,
            "activity": ACTIVITY,
            "surprise": SURPRISE,
            "candidate_count": CANDIDATE_COUNT,
            "selected_seed": snapshot.selected_seed,
            "expected_selected_seed": EXPECTED_SELECTED_SEED,
            "tempo_bpm": full_result.config.tempo_bpm,
            "bars": full_result.config.bars,
            "beats_per_bar": full_result.config.beats_per_bar,
            "tune_event_count": len(ledger),
            "tune_event_ledger_sha256": _ledger_sha256(ledger),
            "tune_events": ledger,
        },
        "synth": synth_v2_manifest(),
        "file": {
            "name": wav_path.name,
            "sha256": _sha256(wav_path),
            "bytes": wav_path.stat().st_size,
        },
    }
    manifest_path = output / "acceptance.json"
    manifest_path.write_text(json.dumps(acceptance, indent=2) + "\n", encoding="utf-8")

    readme = output / "README.txt"
    readme.write_text(
        "Simple-Material Interest Gate v2\n"
        "================================\n\n"
        "Listen only to 01-tune-solo.wav.\n\n"
        "Question: Even if the note sequence is plain, is the sound itself "
        "interesting enough that I want to keep listening?\n\n"
        "Judgment: PASS or FAIL.\n"
        "A FAIL fails v2 as frozen; do not retune the synth or replace the Tune.\n",
        encoding="utf-8",
    )
    print(json.dumps(acceptance, indent=2))
    return output


if __name__ == "__main__":
    render()

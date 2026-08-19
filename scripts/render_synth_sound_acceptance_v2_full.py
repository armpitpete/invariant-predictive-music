"""Render the frozen full Synth Sound Acceptance v2 audition set.

The Tune already passed the Simple-Material Interest Gate. This harness reuses
that exact machine state and exact v2 engine, verifies the Tune has not drifted,
then renders Bass solo, Rhythm solo and the full mix without changing synthesis
or composition parameters.
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
EXPECTED_TUNE_LEDGER_SHA256 = "1bee94ac3d65ce6a01efd6ec2921f2cae82238ddbeaaab79fcee38dc4726bd31"
EXPECTED_TUNE_WAV_SHA256 = "c045a528ed6e2b0c0b63358257675aecdf773a55b51b72a2abb7e10be0f1e6ed"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _event_ledger(result: InstrumentResult, lane: str) -> list[dict[str, object]]:
    voice = {"TUNE": result.tune, "BASS": result.bass, "RHYTHM": result.rhythm}[lane]
    return [
        {
            "onset": [event.onset.numerator, event.onset.denominator],
            "duration": [event.duration.numerator, event.duration.denominator],
            "pitch": event.pitch,
            "velocity": event.velocity,
        }
        for event in voice.events
    ]


def _ledger_sha256(ledger: list[dict[str, object]]) -> str:
    canonical = json.dumps(ledger, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _lane_only(result: InstrumentResult, lane: str) -> InstrumentResult:
    return InstrumentResult(
        config=result.config,
        tune=result.tune if lane == "TUNE" else Voice("TUNE"),
        bass=result.bass if lane == "BASS" else Voice("BASS"),
        rhythm=result.rhythm if lane == "RHYTHM" else Voice("RHYTHM"),
        trace=result.trace,
    )


def render(output_dir: str | Path = "synth-sound-acceptance-v2") -> Path:
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

    result = snapshot.result
    tune_ledger = _event_ledger(result, "TUNE")
    tune_ledger_sha = _ledger_sha256(tune_ledger)
    if tune_ledger_sha != EXPECTED_TUNE_LEDGER_SHA256:
        raise RuntimeError(
            "frozen Tune ledger drift: expected "
            f"{EXPECTED_TUNE_LEDGER_SHA256}, got {tune_ledger_sha}"
        )

    renders = {
        "01-tune-solo.wav": _lane_only(result, "TUNE"),
        "02-bass-solo.wav": _lane_only(result, "BASS"),
        "03-rhythm-solo.wav": _lane_only(result, "RHYTHM"),
        "04-full-mix.wav": result,
    }

    paths: list[Path] = []
    for filename, source in renders.items():
        path = render_synth_v2_wav(source, output / filename)
        paths.append(path)

    tune_wav_sha = _sha256(output / "01-tune-solo.wav")
    if tune_wav_sha != EXPECTED_TUNE_WAV_SHA256:
        raise RuntimeError(
            "previously accepted Tune WAV drift: expected "
            f"{EXPECTED_TUNE_WAV_SHA256}, got {tune_wav_sha}"
        )

    acceptance = {
        "gate": "Synth Sound Acceptance v2",
        "question": (
            "Does Evolving Resonant Field v2 work as a complete musical instrument: "
            "credible Bass and Rhythm voices and an integrated full mix, while retaining "
            "the already-passed interesting Tune sound?"
        ),
        "allowed_judgments": ["PASS", "FAIL"],
        "prior_gate": {
            "name": "Simple-Material Interest Gate v2",
            "result": "PASS",
            "owner_judgment": "It does.",
            "accepted_tune_wav_sha256": EXPECTED_TUNE_WAV_SHA256,
        },
        "failure_rule": (
            "A FAIL means v2 is not accepted for Machine PLAY/FINISH. Do not change "
            "IPM composition, choose another seed, or silently retune between audition files."
        ),
        "frozen_source": {
            "root_seed": ROOT_SEED,
            "activity": ACTIVITY,
            "surprise": SURPRISE,
            "candidate_count": CANDIDATE_COUNT,
            "selected_seed": snapshot.selected_seed,
            "tempo_bpm": result.config.tempo_bpm,
            "bars": result.config.bars,
            "beats_per_bar": result.config.beats_per_bar,
            "tune_event_count": len(tune_ledger),
            "tune_event_ledger_sha256": tune_ledger_sha,
            "bass_event_count": len(result.bass.events),
            "rhythm_event_count": len(result.rhythm.events),
        },
        "synth": synth_v2_manifest(),
        "files": {
            path.name: {"sha256": _sha256(path), "bytes": path.stat().st_size}
            for path in paths
        },
    }

    (output / "acceptance.json").write_text(
        json.dumps(acceptance, indent=2) + "\n", encoding="utf-8"
    )
    (output / "README.txt").write_text(
        "Synth Sound Acceptance v2\n"
        "=========================\n\n"
        "01-tune-solo.wav is the already-passed Simple-Material Interest artifact, "
        "re-rendered and hash-checked for identity.\n\n"
        "Listen now to:\n"
        "2. 02-bass-solo.wav\n"
        "3. 03-rhythm-solo.wav\n"
        "4. 04-full-mix.wav\n\n"
        "Gate: PASS or FAIL.\n"
        "Judge whether Bass and Rhythm are credible and whether the full mix works as "
        "one interesting musical instrument.\n",
        encoding="utf-8",
    )
    print(json.dumps(acceptance, indent=2))
    return output


if __name__ == "__main__":
    render()

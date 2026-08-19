"""Render the frozen Synth Sound Acceptance audition set.

This is a human listening gate for Machine Synth Engine v1.  The musical
source and controls are fixed before listening so synth evaluation cannot
cherry-pick a flattering piece or alter timbre between solo and full renders.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ipm.engine import InstrumentResult
from ipm.machine import MachineControls, MachineEngine
from ipm.model import Voice
from ipm.synth_engine import render_synth_wav, synth_manifest

ROOT_SEED = 987762706
ACTIVITY = 0.50
SURPRISE = 0.50
CANDIDATE_COUNT = 5


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _lane_only(result: InstrumentResult, lane: str) -> InstrumentResult:
    return InstrumentResult(
        config=result.config,
        tune=result.tune if lane == "TUNE" else Voice("TUNE"),
        bass=result.bass if lane == "BASS" else Voice("BASS"),
        rhythm=result.rhythm if lane == "RHYTHM" else Voice("RHYTHM"),
        trace=result.trace,
    )


def render(output_dir: str | Path = "synth-sound-acceptance-v1") -> Path:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    snapshot = MachineEngine(candidate_count=CANDIDATE_COUNT).render(
        root_seed=ROOT_SEED,
        controls=MachineControls(activity=ACTIVITY, surprise=SURPRISE),
    )
    result = snapshot.result

    renders = {
        "01-tune-solo.wav": _lane_only(result, "TUNE"),
        "02-bass-solo.wav": _lane_only(result, "BASS"),
        "03-rhythm-solo.wav": _lane_only(result, "RHYTHM"),
        "04-full-mix.wav": result,
    }
    paths: list[Path] = []
    for filename, source in renders.items():
        path = render_synth_wav(source, output / filename)
        paths.append(path)

    acceptance = {
        "gate": "Synth Sound Acceptance v1",
        "question": (
            "Does Machine Synth Engine v1 sound like a real musical instrument "
            "rather than prototype/test audio?"
        ),
        "allowed_judgments": ["PASS", "FAIL"],
        "failure_note": (
            "On FAIL, identify the file and approximate timestamp plus the audible "
            "reason. Do not retune composition parameters from this gate."
        ),
        "frozen_source": {
            "root_seed": ROOT_SEED,
            "activity": ACTIVITY,
            "surprise": SURPRISE,
            "candidate_count": CANDIDATE_COUNT,
            "selected_seed": snapshot.selected_seed,
            "tempo_bpm": result.config.tempo_bpm,
            "bars": result.config.bars,
        },
        "synth": synth_manifest(),
        "files": {
            path.name: {
                "sha256": _sha256(path),
                "bytes": path.stat().st_size,
            }
            for path in paths
        },
    }
    manifest_path = output / "acceptance.json"
    manifest_path.write_text(json.dumps(acceptance, indent=2) + "\n", encoding="utf-8")

    readme = output / "README.txt"
    readme.write_text(
        "Synth Sound Acceptance v1\n"
        "=========================\n\n"
        "Question: Does Machine Synth Engine v1 sound like a real musical instrument "
        "rather than prototype/test audio?\n\n"
        "Listen in order:\n"
        "1. 01-tune-solo.wav\n"
        "2. 02-bass-solo.wav\n"
        "3. 03-rhythm-solo.wav\n"
        "4. 04-full-mix.wav\n\n"
        "Judgment: PASS or FAIL.\n"
        "If FAIL, give the file, approximate timestamp and audible reason.\n"
        "No synth or composition change is permitted between these files.\n",
        encoding="utf-8",
    )
    print(json.dumps(acceptance, indent=2))
    return output


if __name__ == "__main__":
    render()

"""Materialise the pre-v4 frozen Tune ledger for RealSynthEngine v4 Gate C.

This step performs composition recovery only. It creates no audio and makes no
human/audible judgment. The selected Tune seed and expected event-ledger hash
were frozen during the v3 acceptance work before the v4 architecture existed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from ipm.engine import ExperimentMode, InstrumentConfig, compose

HISTORIC_ROOT_SEED = 987762706
HISTORIC_ACTIVITY = 0.50
HISTORIC_SURPRISE = 0.50
HISTORIC_CANDIDATE_COUNT = 5
FROZEN_SELECTED_SEED = 1693196453
EXPECTED_TUNE_EVENT_COUNT = 122
EXPECTED_TUNE_LEDGER_SHA256 = "1bee94ac3d65ce6a01efd6ec2921f2cae82238ddbeaaab79fcee38dc4726bd31"
EXPECTED_TEMPO_BPM = 58
EXPECTED_BARS = 16
EXPECTED_BEATS_PER_BAR = 4
V4_IMPLEMENTATION_COMMIT = "9ca6e720f9a90d917b1420b794d76a07408cd7bb"
GATE_AB_FREEZE_COMMIT = "1d590990d312a63ebd82e83ce0ea37b267d234eb"


def event_ledger() -> tuple[InstrumentConfig, list[dict[str, object]]]:
    result = compose(
        InstrumentConfig(
            seed=FROZEN_SELECTED_SEED,
            mode=ExperimentMode.IPM,
        )
    )
    ledger = [
        {
            "onset": [event.onset.numerator, event.onset.denominator],
            "duration": [event.duration.numerator, event.duration.denominator],
            "pitch": event.pitch,
            "velocity": event.velocity,
        }
        for event in result.tune.events
    ]
    return result.config, ledger


def ledger_sha256(ledger: list[dict[str, object]]) -> str:
    canonical = json.dumps(
        ledger,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def materialise(output: str | Path) -> Path:
    config, ledger = event_ledger()
    digest = ledger_sha256(ledger)

    if len(ledger) != EXPECTED_TUNE_EVENT_COUNT:
        raise RuntimeError(
            f"frozen Tune event-count mismatch: expected {EXPECTED_TUNE_EVENT_COUNT}, got {len(ledger)}"
        )
    if digest != EXPECTED_TUNE_LEDGER_SHA256:
        raise RuntimeError(
            f"frozen Tune ledger mismatch: expected {EXPECTED_TUNE_LEDGER_SHA256}, got {digest}"
        )
    if (
        config.tempo_bpm != EXPECTED_TEMPO_BPM
        or config.bars != EXPECTED_BARS
        or config.beats_per_bar != EXPECTED_BEATS_PER_BAR
    ):
        raise RuntimeError("frozen Tune form/tempo mismatch")

    payload = {
        "gate": "RealSynthEngine v4 Gate C fixture materialisation",
        "status": "FROZEN_PRE_AUDITION_FIXTURE",
        "human_audition_performed": False,
        "audio_created": False,
        "v4_implementation_commit": V4_IMPLEMENTATION_COMMIT,
        "gate_ab_freeze_commit": GATE_AB_FREEZE_COMMIT,
        "historic_source": {
            "root_seed": HISTORIC_ROOT_SEED,
            "activity": HISTORIC_ACTIVITY,
            "surprise": HISTORIC_SURPRISE,
            "candidate_count": HISTORIC_CANDIDATE_COUNT,
            "selected_seed": FROZEN_SELECTED_SEED,
        },
        "tempo_bpm": config.tempo_bpm,
        "bars": config.bars,
        "beats_per_bar": config.beats_per_bar,
        "tune_event_count": len(ledger),
        "tune_event_ledger_sha256": digest,
        "tune_events": ledger,
        "boundary": (
            "This file materialises an already-frozen pre-v4 Tune ledger. "
            "Gate C synthesis must consume this ledger directly and must not invoke "
            "MachineEngine, candidate selection, A5, or any composition-scoring path."
        ),
    }
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="gate-c-materialization/REAL_SYNTH_ENGINE_V4_GATE_C_TUNE_LEDGER_v0_1.json",
    )
    args = parser.parse_args()
    path = materialise(args.output)
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

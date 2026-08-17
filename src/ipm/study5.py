"""Study #005: register-corrected subsidiary voices from Study #004.

This is a controlled listening correction. Main voice, rhythm-budget decisions,
tempo, mode, event timing, velocities and pitch classes are inherited unchanged
from Study #004. Only the octave placement of B_R and B_H is corrected.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from .midi import render_midi
from .model import IPMConfig, Voice
from .register import PitchRegister
from .study import StudyResult, _event_json
from .study4 import _occupancy_metrics, compose_study_004

_RESPONSE_REGISTER = PitchRegister(low=48, high=59, centre=55)  # C3-B3
_HARMONY_REGISTER = PitchRegister(low=36, high=47, centre=43)   # C2-B2


def compose_study_005(
    config: IPMConfig | None = None,
    *,
    tonic_midi: int = 60,
) -> StudyResult:
    """Correct Study #004's inherited counter-voice octave spikes."""

    parent = compose_study_004(config, tonic_midi=tonic_midi)

    response_events = _RESPONSE_REGISTER.project_events(parent.response.events)
    harmony_events = _HARMONY_REGISTER.project_events(parent.harmony.events)
    _RESPONSE_REGISTER.require_events(response_events)
    _HARMONY_REGISTER.require_events(harmony_events)

    response = Voice.from_events("B_R", response_events)
    harmony = Voice.from_events("B_H", harmony_events)

    trace = copy.deepcopy(parent.trace)
    trace["study"] = "005"
    trace["parent_study"] = "004"
    trace["controlled_change"] = "subsidiary octave placement only"
    trace["registers"] = {
        "M": {"low": 60, "high": 71},
        "B_R": {
            "low": _RESPONSE_REGISTER.low,
            "high": _RESPONSE_REGISTER.high,
            "centre": _RESPONSE_REGISTER.centre,
        },
        "B_H": {
            "low": _HARMONY_REGISTER.low,
            "high": _HARMONY_REGISTER.high,
            "centre": _HARMONY_REGISTER.centre,
        },
    }
    trace["voices"]["B_R"] = [_event_json(event) for event in response.events]
    trace["voices"]["B_H"] = [_event_json(event) for event in harmony.events]
    trace["metrics"] = _occupancy_metrics((parent.main, response, harmony))

    source_response_pc = [event.pitch % 12 for event in parent.response.events]
    source_harmony_pc = [event.pitch % 12 for event in parent.harmony.events]
    response_pc = [event.pitch % 12 for event in response.events]
    harmony_pc = [event.pitch % 12 for event in harmony.events]
    source_response_timing = [
        (event.onset, event.duration) for event in parent.response.events
    ]
    source_harmony_timing = [
        (event.onset, event.duration) for event in parent.harmony.events
    ]
    response_timing = [(event.onset, event.duration) for event in response.events]
    harmony_timing = [(event.onset, event.duration) for event in harmony.events]

    checks = {
        "parent_study_passed": parent.trace["validation"]["passed"],
        "response_in_C3_B3": _RESPONSE_REGISTER.contains_events(response.events),
        "harmony_in_C2_B2": _HARMONY_REGISTER.contains_events(harmony.events),
        "response_pitch_classes_preserved": response_pc == source_response_pc,
        "harmony_pitch_classes_preserved": harmony_pc == source_harmony_pc,
        "response_timing_preserved": response_timing == source_response_timing,
        "harmony_timing_preserved": harmony_timing == source_harmony_timing,
        "no_subsidiary_note_above_lead_register": all(
            event.pitch < 60 for event in (*response.events, *harmony.events)
        ),
        "final_tonic_preserved": parent.main.events[-1].pitch % 12 == tonic_midi % 12,
    }
    trace["validation"] = {"passed": all(checks.values()), "checks": checks}

    return StudyResult(
        config=parent.config,
        main=parent.main,
        response=response,
        harmony=harmony,
        trace=trace,
    )


def write_study_005_files(
    output_dir: str | Path,
    config: IPMConfig | None = None,
    *,
    tonic_midi: int = 60,
) -> tuple[Path, Path]:
    result = compose_study_005(config, tonic_midi=tonic_midi)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    midi_path = output / "ipm-study-005.mid"
    trace_path = output / "ipm-study-005.trace.json"
    midi_path.write_bytes(
        render_midi(
            result.voices,
            tempo_bpm=result.config.tempo_bpm,
            beats_per_bar=result.config.beats_per_bar,
        )
    )
    trace_path.write_text(json.dumps(result.trace, indent=2) + "\n", encoding="utf-8")
    return midi_path, trace_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate IPM Study #005")
    parser.add_argument("--output", default="examples", help="output directory")
    parser.add_argument("--seed", type=int, default=2026081704)
    args = parser.parse_args()
    for path in write_study_005_files(
        args.output,
        IPMConfig(seed=args.seed, tempo_bpm=58),
    ):
        print(path)


if __name__ == "__main__":
    main()

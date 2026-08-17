"""Study #003: controlled one-octave vocal-lead variant of Study #002.

This is deliberately a single-variable listening experiment. Rhythm, formal
branch decisions, Euclidean attack timing and subsidiary voices are inherited
from Study #002. Only the lead's octave placement changes, preserving every
lead pitch class and all event timing while enforcing a C4-C5 hard ambitus.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from .midi import render_midi
from .model import IPMConfig, Voice
from .register import FEMALE_LEAD_C4_C5, PitchRegister
from .study import StudyResult, _event_json, _texture_metrics
from .study2 import compose_study_002


def _register_for_tonic(tonic_midi: int) -> PitchRegister:
    if tonic_midi == 60:
        return FEMALE_LEAD_C4_C5
    if not 0 <= tonic_midi <= 115:
        raise ValueError("tonic_midi must allow a complete one-octave lead register")
    return PitchRegister(tonic_midi, tonic_midi + 12, tonic_midi + 6)


def compose_study_003(
    config: IPMConfig | None = None,
    *,
    tonic_midi: int = 60,
) -> StudyResult:
    """Compose the controlled one-octave lead variant of Study #002."""

    base = compose_study_002(config, tonic_midi=tonic_midi)
    register = _register_for_tonic(tonic_midi)
    projected_events = register.project_events(base.main.events)
    register.require_events(projected_events)
    main = Voice.from_events("M", projected_events)

    # Octave projection preserves pitch class, timing and every subsidiary event.
    # Recompute texture metrics against the actual rendered pitches anyway so the
    # trace describes the listening artifact rather than assuming equivalence.
    trace = copy.deepcopy(base.trace)
    trace["study"] = "003"
    trace["parent_study"] = "002"
    trace["controlled_change"] = "lead register only"
    trace["lead_register"] = {
        "low": register.low,
        "high": register.high,
        "centre": register.centre,
        "span_semitones": register.span,
    }
    trace["voices"]["M"] = [_event_json(event) for event in main.events]
    trace["metrics"] = _texture_metrics((main, base.response, base.harmony), base.config)

    source_pitch_classes = [event.pitch % 12 for event in base.main.events]
    projected_pitch_classes = [event.pitch % 12 for event in main.events]
    source_timing = [(event.onset, event.duration) for event in base.main.events]
    projected_timing = [(event.onset, event.duration) for event in main.events]
    checks = {
        "parent_study_passed": base.trace["validation"]["passed"],
        "lead_within_hard_register": register.contains_events(main.events),
        "lead_ambitus_at_most_one_octave": register.ambitus(main.events) <= 12,
        "lead_pitch_classes_preserved": projected_pitch_classes == source_pitch_classes,
        "lead_timing_preserved": projected_timing == source_timing,
        "response_voice_unchanged": base.response.events == compose_study_002(config, tonic_midi=tonic_midi).response.events,
        "harmony_voice_unchanged": base.harmony.events == compose_study_002(config, tonic_midi=tonic_midi).harmony.events,
        "exact_length": main.cursor == base.main.cursor,
        "final_tonic": main.events[-1].pitch % 12 == tonic_midi % 12,
    }
    trace["validation"] = {"passed": all(checks.values()), "checks": checks}

    return StudyResult(
        config=base.config,
        main=main,
        response=base.response,
        harmony=base.harmony,
        trace=trace,
    )


def write_study_003_files(
    output_dir: str | Path,
    config: IPMConfig | None = None,
    *,
    tonic_midi: int = 60,
) -> tuple[Path, Path]:
    result = compose_study_003(config, tonic_midi=tonic_midi)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    midi_path = output / "ipm-study-003.mid"
    trace_path = output / "ipm-study-003.trace.json"
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
    parser = argparse.ArgumentParser(description="Generate IPM Study #003")
    parser.add_argument("--output", default="examples", help="output directory")
    parser.add_argument("--seed", type=int, default=2026081702)
    args = parser.parse_args()
    paths = write_study_003_files(
        args.output,
        IPMConfig(seed=args.seed, tempo_bpm=108),
    )
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()

"""Study #004: slow Aeolian time-budget realisation of the one-octave lead.

Study #004 starts from Study #003's already-selected musical structure so the main
prediction / Euclidean counter-timing / one-octave work is preserved. It then applies
the listening corrections: a slower tempo, C Aeolian pitch projection, expressive
velocity shaping, and stochastic decomposition of each main-note duration into one
or more attacks whose allocated segments preserve the original time budget exactly.
"""

from __future__ import annotations

import argparse
import copy
import json
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
from typing import Any

from .midi import render_midi
from .model import IPMConfig, NoteEvent, Voice
from .randomness import SeededRandom
from .rhythm import RhythmBudgetPolicy, choose_rhythmic_partition, realise_partition
from .sonority import score_texture
from .study import StudyResult, _event_json
from .study3 import compose_study_003

_MAJOR = (0, 2, 4, 5, 7, 9, 11)
_AEOLIAN = (0, 2, 3, 5, 7, 8, 10)
_TOTAL_BEATS = Fraction(64)


def _phase_for_bar(bar: int) -> str:
    if bar <= 1:
        return "opening"
    if bar <= 4:
        return "establishment"
    if bar <= 9:
        return "development"
    if bar <= 11:
        return "climax"
    if bar <= 14:
        return "resolution"
    return "ending"


def _rhythm_intensity(bar: int) -> float:
    return {
        "opening": 0.05,
        "establishment": 0.18,
        "development": 0.38,
        "climax": 0.58,
        "resolution": 0.22,
        "ending": 0.04,
    }[_phase_for_bar(bar)]


def _velocity_for_bar(bar: int, original: int) -> int:
    target = {
        "opening": 66,
        "establishment": 70,
        "development": 75,
        "climax": 82,
        "resolution": 65,
        "ending": 55,
    }[_phase_for_bar(bar)]
    return max(35, min(92, round(0.25 * original + 0.75 * target)))


def _major_to_aeolian_pitch(pitch: int, *, tonic_midi: int = 60) -> int:
    relative = (pitch - tonic_midi) % 12
    try:
        degree = _MAJOR.index(relative)
    except ValueError as exc:
        raise ValueError("Study #004 parent pitch is outside the diatonic major world") from exc
    return pitch + (_AEOLIAN[degree] - _MAJOR[degree])


def _mode_project_voice(
    voice: Voice,
    *,
    name: str,
    tonic_midi: int,
    velocity_scale: float,
) -> Voice:
    events = [
        NoteEvent(
            event.onset,
            event.duration,
            _major_to_aeolian_pitch(event.pitch, tonic_midi=tonic_midi),
            max(25, min(127, round(event.velocity * velocity_scale))),
        )
        for event in voice.events
    ]
    return Voice.from_events(name, events)


def _occupancy_metrics(voices: tuple[Voice, ...]) -> dict[str, Any]:
    boundaries = {Fraction(0), _TOTAL_BEATS}
    order = {"M": 0, "B_R": 1, "B_H": 2}
    for voice in voices:
        for event in voice.events:
            boundaries.add(event.onset)
            boundaries.add(event.end)
    ordered = sorted(boundaries)
    durations: dict[str, Fraction] = {}
    for start, end in zip(ordered, ordered[1:], strict=False):
        active = [
            voice.name
            for voice in voices
            if any(event.onset <= start and event.end >= end for event in voice.events)
        ]
        key = "+".join(sorted(active, key=order.__getitem__)) if active else "silence"
        durations[key] = durations.get(key, Fraction(0)) + end - start

    texture = score_texture(voices)
    return {
        "texture_beats": {
            name: [duration.numerator, duration.denominator]
            for name, duration in sorted(durations.items())
        },
        "texture_ratio": {
            name: float(duration / _TOTAL_BEATS)
            for name, duration in sorted(durations.items())
        },
        "vertical_weighted_mean": texture.weighted_mean,
        "vertical_minimum": texture.minimum,
        "sonority_slices": texture.slices,
    }


def compose_study_004(
    config: IPMConfig | None = None,
    *,
    tonic_midi: int = 60,
) -> StudyResult:
    """Compose the first time-budget listening study."""

    if tonic_midi != 60:
        raise ValueError("Study #004 currently fixes tonic at C for the C4-B4 lead experiment")
    requested = config or IPMConfig(seed=2026081704, tempo_bpm=58)
    if requested.bars != 16 or requested.beats_per_bar != 4:
        raise ValueError("Study #004 is fixed at 16 bars of 4/4")

    parent = compose_study_003(
        IPMConfig(
            seed=requested.seed,
            tempo_bpm=108,
            bars=requested.bars,
            beats_per_bar=requested.beats_per_bar,
        ),
        tonic_midi=tonic_midi,
    )
    result_config = replace(requested, tempo_bpm=58)
    rhythm_rng = SeededRandom(requested.seed ^ 0x4004)
    policy = RhythmBudgetPolicy(grid=Fraction(1, 2), max_attacks=4)

    main = Voice("M")
    rhythm_trace: list[dict[str, Any]] = []
    for source in parent.main.events:
        bar = min(15, int(source.onset // 4))
        structural = NoteEvent(
            source.onset,
            source.duration,
            _major_to_aeolian_pitch(source.pitch, tonic_midi=tonic_midi),
            _velocity_for_bar(bar, source.velocity),
        )
        partition = choose_rhythmic_partition(
            structural.duration,
            rng=rhythm_rng,
            intensity=_rhythm_intensity(bar),
            policy=policy,
        )
        gate = Fraction(3, 4) if partition.attacks > 1 else Fraction(7, 8)
        realised = realise_partition(structural, partition, gate=gate)
        for attack_index, note in enumerate(realised):
            main.add(
                NoteEvent(
                    note.onset,
                    note.duration,
                    note.pitch,
                    max(30, note.velocity - 3 * attack_index),
                )
            )
        rhythm_trace.append(
            {
                "source_event": _event_json(source),
                "structural_event": _event_json(structural),
                "bar": bar,
                "phase": _phase_for_bar(bar),
                "intensity": _rhythm_intensity(bar),
                "attacks": partition.attacks,
                "segments": [
                    [segment.numerator, segment.denominator]
                    for segment in partition.segments
                ],
                "realised_events": [_event_json(event) for event in realised],
            }
        )

    response = _mode_project_voice(
        parent.response,
        name="B_R",
        tonic_midi=tonic_midi,
        velocity_scale=0.72,
    )
    harmony = _mode_project_voice(
        parent.harmony,
        name="B_H",
        tonic_midi=tonic_midi,
        velocity_scale=0.55,
    )

    trace = copy.deepcopy(parent.trace)
    trace["study"] = "004"
    trace["parent_study"] = "003"
    trace["tempo_bpm"] = result_config.tempo_bpm
    trace["mode"] = "C Aeolian"
    trace["controlled_changes"] = [
        "tempo 108 -> 58 BPM",
        "major scale degrees -> Aeolian scale degrees",
        "main structural durations -> stochastic time-budget attack partitions",
        "main articulation gains explicit breath gaps",
        "velocity shaped by formal phase",
        "subsidiary velocities reduced while preserving independent timing",
    ]
    trace["rhythm_budget_decisions"] = rhythm_trace
    trace["voices"] = {
        "M": [_event_json(event) for event in main.events],
        "B_R": [_event_json(event) for event in response.events],
        "B_H": [_event_json(event) for event in harmony.events],
    }
    metrics = _occupancy_metrics((main, response, harmony))
    trace["metrics"] = metrics

    parent_budgets = [event.duration for event in parent.main.events]
    allocated_budgets = [
        sum(
            (Fraction(num, den) for num, den in item["segments"]),
            Fraction(0),
        )
        for item in rhythm_trace
    ]
    main_pitches = [event.pitch for event in main.events]
    main_pitch_classes = {(pitch - tonic_midi) % 12 for pitch in main_pitches}
    gaps = [
        right.onset - left.end
        for left, right in zip(main.events, main.events[1:], strict=False)
    ]
    subdivided = sum(item["attacks"] > 1 for item in rhythm_trace)
    ratios = metrics["texture_ratio"]
    sounding_non_solo = [
        value
        for name, value in ratios.items()
        if name not in ("M", "silence")
    ]
    checks = {
        "parent_study_passed": parent.trace["validation"]["passed"],
        "tempo_is_slow": result_config.tempo_bpm == 58,
        "lead_stays_in_C4_B4": bool(main_pitches)
        and all(60 <= pitch <= 71 for pitch in main_pitches),
        "lead_is_aeolian": main_pitch_classes.issubset(set(_AEOLIAN)),
        "time_budgets_are_exactly_preserved": allocated_budgets == parent_budgets,
        "time_budget_subdivision_occurs": subdivided >= 4,
        "real_breath_gaps_occur": sum(gap > 0 for gap in gaps) >= len(gaps) // 2,
        "main_alone_remains_dominant": bool(sounding_non_solo)
        and ratios.get("M", 0.0) > max(sounding_non_solo),
        "three_voice_stack_is_not_a_quota": ratios.get("M+B_R+B_H", 0.0) <= 0.125,
        "vertical_compatibility_remains_bounded": metrics["vertical_minimum"] >= 0.45,
        "countervoices_remain_present": bool(response.events) and bool(harmony.events),
        "final_tonic": bool(main.events) and main.events[-1].pitch % 12 == tonic_midi % 12,
    }
    trace["validation"] = {"passed": all(checks.values()), "checks": checks}

    return StudyResult(
        config=result_config,
        main=main,
        response=response,
        harmony=harmony,
        trace=trace,
    )


def write_study_004_files(
    output_dir: str | Path,
    config: IPMConfig | None = None,
    *,
    tonic_midi: int = 60,
) -> tuple[Path, Path]:
    result = compose_study_004(config, tonic_midi=tonic_midi)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    midi_path = output / "ipm-study-004.mid"
    trace_path = output / "ipm-study-004.trace.json"
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
    parser = argparse.ArgumentParser(description="Generate IPM Study #004")
    parser.add_argument("--output", default="examples", help="output directory")
    parser.add_argument("--seed", type=int, default=2026081704)
    args = parser.parse_args()
    for path in write_study_004_files(
        args.output,
        IPMConfig(seed=args.seed, tempo_bpm=58),
    ):
        print(path)


if __name__ == "__main__":
    main()

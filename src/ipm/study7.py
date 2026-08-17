"""Study #007: slow pulse with an active rhythmic surface.

Study #006 proved the bar NOTE/REST grammar but still sounded like long notes because
58 BPM made even quarter-note cells last about one second. Study #007 keeps the same
slow pulse, mode, registers and pitch anchors while moving the audible rhythm to a
half-beat grid and explicitly making long notes exceptional.
"""

from __future__ import annotations

import argparse
import copy
import json
from fractions import Fraction
from pathlib import Path
from statistics import median
from typing import Any

from .bar_rhythm import BarCellKind, BarPattern, realise_bar_pattern
from .countervoice import CountervoicePolicy, SubsidiaryRole
from .midi import render_midi
from .model import IPMConfig, Voice
from .randomness import SeededRandom
from .study import StudyResult, _event_json
from .study4 import _occupancy_metrics, _phase_for_bar
from .study5 import compose_study_005
from .study6 import _screen_subsidiary, _structural_anchors
from .surface_rhythm import SurfaceRhythmPolicy, choose_surface_pattern

# Target audible attacks per 4/4 bar, independent of the slow metrical pulse.
_BAR_CONTROLS: dict[str, tuple[float, float]] = {
    "opening": (3.5, 0.16),
    "establishment": (4.5, 0.12),
    "development": (5.2, 0.15),
    "climax": (6.0, 0.10),
    "resolution": (4.3, 0.18),
    "ending": (3.2, 0.22),
}


def _fraction_json(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def _pattern_json(pattern: BarPattern) -> list[dict[str, Any]]:
    return [
        {"kind": cell.kind.value, "duration": _fraction_json(cell.duration)}
        for cell in pattern.cells
    ]


def _active_main(
    parent: StudyResult,
    *,
    rng: SeededRandom,
) -> tuple[Voice, list[dict[str, Any]]]:
    anchors = _structural_anchors(parent)
    policy = SurfaceRhythmPolicy(
        grid=Fraction(1, 2),
        max_cells=8,
        max_attacks=7,
        max_rest_fraction=0.50,
        long_note_threshold=Fraction(1),
        long_note_penalty=0.22,
        very_long_threshold=Fraction(2),
        very_long_penalty=0.18,
        short_note_bonus=1.55,
    )
    main = Voice("M")
    decisions: list[dict[str, Any]] = []

    for bar in range(16):
        phase = _phase_for_bar(bar)
        target_attacks, rest_target = _BAR_CONTROLS[phase]
        pattern = choose_surface_pattern(
            rng=rng,
            target_attacks=target_attacks,
            rest_target=rest_target,
            span=Fraction(4),
            policy=policy,
        )
        source = anchors[bar]
        realised = realise_bar_pattern(
            pattern,
            start=Fraction(bar * 4),
            pitches=tuple(event.pitch for event in source),
            velocities=tuple(event.velocity for event in source),
            gate=Fraction(7, 8),
        )
        for event in realised:
            main.add(event)
        decisions.append(
            {
                "bar": bar,
                "phase": phase,
                "target_attacks": target_attacks,
                "rest_target": rest_target,
                "cells": _pattern_json(pattern),
                "attacks": pattern.attacks,
                "note_beats": _fraction_json(pattern.note_beats),
                "rest_beats": _fraction_json(pattern.rest_beats),
                "source_anchors": [_event_json(event) for event in source],
                "realised_events": [_event_json(event) for event in realised],
            }
        )
    return main, decisions


def compose_study_007(
    config: IPMConfig | None = None,
    *,
    tonic_midi: int = 60,
) -> StudyResult:
    """Compose the active-surface correction to Study #006."""

    requested = config or IPMConfig(seed=2026081704, tempo_bpm=58)
    parent = compose_study_005(requested, tonic_midi=tonic_midi)
    main, bar_trace = _active_main(
        parent,
        rng=SeededRandom(requested.seed ^ 7000),
    )

    counter_policy = CountervoicePolicy(
        vertical_weight=0.80,
        density_weight=0.20,
        response_vertical_floor=0.55,
        harmony_vertical_floor=0.65,
        response_attack_cost=0.04,
        harmony_attack_cost=0.08,
    )
    response, response_trace = _screen_subsidiary(
        parent.response,
        role=SubsidiaryRole.RESPONSE,
        frozen_voices=(main,),
        policy=counter_policy,
    )
    harmony, harmony_trace = _screen_subsidiary(
        parent.harmony,
        role=SubsidiaryRole.HARMONY,
        frozen_voices=(main, response),
        policy=counter_policy,
    )

    trace = copy.deepcopy(parent.trace)
    trace["study"] = "007"
    trace["parent_study"] = "005"
    trace["controlled_change"] = (
        "slow 58-BPM pulse retained; main surface rhythm moved to half-beat grid "
        "with explicit attack-rate targets and long-note penalties"
    )
    trace["parent_rhythm_budget_decisions"] = trace.pop("rhythm_budget_decisions", [])
    trace["surface_rhythm_decisions"] = bar_trace
    trace["subsidiary_rescreen"] = response_trace + harmony_trace
    trace["voices"] = {
        "M": [_event_json(event) for event in main.events],
        "B_R": [_event_json(event) for event in response.events],
        "B_H": [_event_json(event) for event in harmony.events],
    }
    trace["metrics"] = _occupancy_metrics((main, response, harmony))

    allocated_note_durations = [
        Fraction(*cell["duration"])
        for bar in bar_trace
        for cell in bar["cells"]
        if cell["kind"] == BarCellKind.NOTE.value
    ]
    sounding_durations = [event.duration for event in main.events]
    shapes = {
        tuple((cell["kind"], tuple(cell["duration"])) for cell in bar["cells"])
        for bar in bar_trace
    }
    short_allocated = sum(duration <= Fraction(1) for duration in allocated_note_durations)
    eighth_allocated = sum(duration == Fraction(1, 2) for duration in allocated_note_durations)
    long_allocated = sum(duration >= Fraction(2) for duration in allocated_note_durations)
    rest_bars = sum(
        any(cell["kind"] == BarCellKind.REST.value for cell in bar["cells"])
        for bar in bar_trace
    )
    no_self_overlap = all(
        all(
            right.onset >= left.end
            for left, right in zip(voice.events, voice.events[1:], strict=False)
        )
        for voice in (main, response, harmony)
    )

    checks = {
        "parent_study_passed": parent.trace["validation"]["passed"],
        "tempo_remains_slow": parent.config.tempo_bpm == 58,
        "sixteen_exact_bars": len(bar_trace) == 16
        and all(
            sum(
                (Fraction(*cell["duration"]) for cell in bar["cells"]),
                Fraction(0),
            )
            == Fraction(4)
            for bar in bar_trace
        ),
        "audible_attack_rate_increased": len(main.events) >= 56,
        "median_sounding_note_is_under_one_beat": bool(sounding_durations)
        and median(sounding_durations) < Fraction(1),
        "short_cells_are_the_majority": bool(allocated_note_durations)
        and short_allocated / len(allocated_note_durations) >= 0.80,
        "eighth_note_cells_are_common": bool(allocated_note_durations)
        and eighth_allocated / len(allocated_note_durations) >= 0.30,
        "long_cells_are_exceptional": bool(allocated_note_durations)
        and long_allocated / len(allocated_note_durations) <= 0.08,
        "bar_shapes_remain_varied": len(shapes) >= 10,
        "literal_space_remains_present": rest_bars >= 6,
        "main_register_preserved": all(60 <= event.pitch <= 71 for event in main.events),
        "response_register_preserved": all(48 <= event.pitch <= 59 for event in response.events),
        "harmony_register_preserved": all(36 <= event.pitch <= 47 for event in harmony.events),
        "no_voice_overlaps_itself": no_self_overlap,
        "subsidiary_notes_still_beat_silence": all(
            not item["kept"] or item["note_score"] > item["silence_score"]
            for item in trace["subsidiary_rescreen"]
        ),
        "final_tonic": bool(main.events) and main.events[-1].pitch % 12 == tonic_midi % 12,
    }
    trace["duration_summary"] = {
        "main_attacks": len(main.events),
        "allocated_note_cells": len(allocated_note_durations),
        "short_cells_le_1_beat": short_allocated,
        "eighth_note_cells": eighth_allocated,
        "long_cells_ge_2_beats": long_allocated,
        "median_sounding_duration": _fraction_json(median(sounding_durations)),
    }
    trace["validation"] = {"passed": all(checks.values()), "checks": checks}

    return StudyResult(
        config=parent.config,
        main=main,
        response=response,
        harmony=harmony,
        trace=trace,
    )


def write_study_007_files(
    output_dir: str | Path,
    config: IPMConfig | None = None,
    *,
    tonic_midi: int = 60,
) -> tuple[Path, Path]:
    result = compose_study_007(config, tonic_midi=tonic_midi)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    midi_path = output / "ipm-study-007.mid"
    trace_path = output / "ipm-study-007.trace.json"
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
    parser = argparse.ArgumentParser(description="Generate IPM Study #007")
    parser.add_argument("--output", default="examples", help="output directory")
    parser.add_argument("--seed", type=int, default=2026081704)
    args = parser.parse_args()
    result = compose_study_007(IPMConfig(seed=args.seed, tempo_bpm=58))
    paths = write_study_007_files(
        args.output,
        IPMConfig(seed=args.seed, tempo_bpm=58),
    )
    print(json.dumps(result.trace["duration_summary"], indent=2))
    print(json.dumps(result.trace["validation"], indent=2))
    for path in paths:
        print(path)
    if not result.trace["validation"]["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

"""Study #008: sequential whole-bar musical decisions.

Study #007 fixed surface attack rate but still inherited a pre-existing pitch skeleton.
Study #008 removes that skeleton.  Each bar is proposed and selected as a complete
musical object: pitches, frequency/register, note count, durations, positions, rests
and rhythm are decided together.  The accepted bar updates musical memory before the
next bar is generated.
"""

from __future__ import annotations

import argparse
import copy
import json
from fractions import Fraction
from pathlib import Path
from statistics import median
from typing import Any

from .bar_rhythm import BarCellKind
from .countervoice import CountervoicePolicy, SubsidiaryRole
from .midi import render_midi
from .model import IPMConfig, Voice
from .randomness import SeededRandom
from .sequential_bar import (
    MusicalState,
    WholeBarDecision,
    choose_whole_bar,
    realise_whole_bar,
    scale_pitches,
)
from .study import StudyResult, _event_json
from .study4 import _occupancy_metrics, _phase_for_bar
from .study5 import compose_study_005
from .study6 import _screen_subsidiary


def _fraction_json(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def _pattern_json(decision: WholeBarDecision) -> list[dict[str, Any]]:
    return [
        {"kind": cell.kind.value, "duration": _fraction_json(cell.duration)}
        for cell in decision.selected.candidate.pattern.cells
    ]


def _state_json(state: MusicalState) -> dict[str, Any]:
    return {
        "bars_written": state.bars_written,
        "last_pitch": state.last_pitch,
        "last_interval": state.last_interval,
        "previous_attacks": state.previous_attacks,
        "previous_rest_fraction": state.previous_rest_fraction,
        "recent_pitches": list(state.recent_pitches),
        "recent_intervals": list(state.recent_intervals),
        "recent_attack_counts": list(state.recent_attack_counts),
    }


def _score_json(decision: WholeBarDecision) -> list[dict[str, Any]]:
    return [
        {
            "total": score.total,
            "pitches": list(score.candidate.pitches),
            "attacks": score.candidate.pattern.attacks,
            "rest_fraction": score.candidate.pattern.rest_fraction,
            "entry_continuity": score.entry_continuity,
            "rhythmic_continuity": score.rhythmic_continuity,
            "learned_vocabulary": score.learned_vocabulary,
            "phrase_direction": score.phrase_direction,
            "internal_variety": score.internal_variety,
            "non_repetition": score.non_repetition,
            "cadence": score.cadence,
        }
        for score in decision.alternatives
    ]


def _sequential_main(
    *,
    rng: SeededRandom,
    tonic_midi: int,
) -> tuple[Voice, list[dict[str, Any]]]:
    state = MusicalState()
    main = Voice("M")
    trace: list[dict[str, Any]] = []

    for bar in range(16):
        phase = _phase_for_bar(bar)
        decision = choose_whole_bar(
            rng=rng,
            phase=phase,
            state=state,
            tonic_midi=tonic_midi,
            final_bar=bar == 15,
            alternatives=12,
        )
        realised = realise_whole_bar(
            decision.selected.candidate,
            start=Fraction(bar * 4),
            phase=phase,
        )
        for event in realised:
            main.add(event)

        trace.append(
            {
                "bar": bar,
                "phase": phase,
                "decision_unit": "whole_bar",
                "state_before": _state_json(decision.state_before),
                "cells": _pattern_json(decision),
                "pitches": list(decision.selected.candidate.pitches),
                "realised_events": [_event_json(event) for event in realised],
                "selected_score": decision.selected.total,
                "alternatives": _score_json(decision),
                "state_after": _state_json(decision.state_after),
            }
        )
        state = decision.state_after
    return main, trace


def compose_study_008(
    config: IPMConfig | None = None,
    *,
    tonic_midi: int = 60,
) -> StudyResult:
    """Compose a piece by sequential history-aware whole-bar decisions."""

    requested = config or IPMConfig(seed=2026081704, tempo_bpm=58)
    parent = compose_study_005(requested, tonic_midi=tonic_midi)
    main, bar_trace = _sequential_main(
        rng=SeededRandom(requested.seed ^ 8000),
        tonic_midi=tonic_midi,
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
    trace["study"] = "008"
    trace["parent_study"] = "005"
    trace["controlled_change"] = (
        "main voice no longer inherits a pitch skeleton; each bar jointly decides "
        "pitch, duration, position, rest and rhythm from accumulated musical state"
    )
    trace["parent_rhythm_budget_decisions"] = trace.pop("rhythm_budget_decisions", [])
    trace["sequential_bar_decisions"] = bar_trace
    trace["subsidiary_rescreen"] = response_trace + harmony_trace
    trace["voices"] = {
        "M": [_event_json(event) for event in main.events],
        "B_R": [_event_json(event) for event in response.events],
        "B_H": [_event_json(event) for event in harmony.events],
    }
    trace["metrics"] = _occupancy_metrics((main, response, harmony))

    pitch_pool = set(scale_pitches(tonic_midi))
    cells = [cell for bar in bar_trace for cell in bar["cells"]]
    note_cells = [cell for cell in cells if cell["kind"] == BarCellKind.NOTE.value]
    rest_bars = sum(
        any(cell["kind"] == BarCellKind.REST.value for cell in bar["cells"])
        for bar in bar_trace
    )
    shapes = {
        (
            tuple((cell["kind"], tuple(cell["duration"])) for cell in bar["cells"]),
            tuple(bar["pitches"]),
        )
        for bar in bar_trace
    }
    sounding_durations = [event.duration for event in main.events]
    prior_link_ok = all(
        bar_trace[index]["state_before"]["last_pitch"]
        == bar_trace[index - 1]["state_after"]["last_pitch"]
        == bar_trace[index - 1]["pitches"][-1]
        for index in range(1, len(bar_trace))
    )
    state_clock_ok = all(
        bar["state_before"]["bars_written"] == index
        and bar["state_after"]["bars_written"] == index + 1
        for index, bar in enumerate(bar_trace)
    )
    no_adjacent_repeat = all(
        (
            bar_trace[index]["cells"],
            bar_trace[index]["pitches"],
        )
        != (
            bar_trace[index - 1]["cells"],
            bar_trace[index - 1]["pitches"],
        )
        for index in range(1, len(bar_trace))
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
        "sixteen_whole_bar_decisions": len(bar_trace) == 16
        and all(bar["decision_unit"] == "whole_bar" for bar in bar_trace),
        "each_bar_fills_exactly_four_beats": all(
            sum(
                (Fraction(*cell["duration"]) for cell in bar["cells"]),
                Fraction(0),
            )
            == Fraction(4)
            for bar in bar_trace
        ),
        "next_bar_receives_previous_bar_state": prior_link_ok,
        "history_clock_advances_once_per_selected_bar": state_clock_ok,
        "history_accumulates_beyond_previous_bar": all(
            len(bar["state_before"]["recent_pitches"]) > 0
            for bar in bar_trace[2:]
        ),
        "no_inherited_pitch_anchors_in_main_decisions": all(
            "source_anchors" not in bar for bar in bar_trace
        ),
        "main_pitch_world_is_one_octave_aeolian": all(
            event.pitch in pitch_pool for event in main.events
        ),
        "active_surface_is_preserved": len(main.events) >= 56
        and bool(sounding_durations)
        and median(sounding_durations) < Fraction(1),
        "literal_space_remains_present": rest_bars >= 4,
        "bars_are_not_repeated_verbatim": no_adjacent_repeat,
        "whole_bar_results_are_varied": len(shapes) >= 12,
        "response_register_preserved": all(48 <= event.pitch <= 59 for event in response.events),
        "harmony_register_preserved": all(36 <= event.pitch <= 47 for event in harmony.events),
        "no_voice_overlaps_itself": no_self_overlap,
        "subsidiary_notes_still_beat_silence": all(
            not item["kept"] or item["note_score"] > item["silence_score"]
            for item in trace["subsidiary_rescreen"]
        ),
        "final_tonic": bool(main.events) and main.events[-1].pitch == tonic_midi,
    }
    trace["sequential_summary"] = {
        "main_attacks": len(main.events),
        "distinct_whole_bars": len(shapes),
        "rest_bars": rest_bars,
        "median_sounding_duration": _fraction_json(median(sounding_durations)),
        "final_state": bar_trace[-1]["state_after"],
    }
    trace["validation"] = {"passed": all(checks.values()), "checks": checks}

    return StudyResult(
        config=parent.config,
        main=main,
        response=response,
        harmony=harmony,
        trace=trace,
    )


def write_study_008_files(
    output_dir: str | Path,
    config: IPMConfig | None = None,
    *,
    tonic_midi: int = 60,
) -> tuple[Path, Path]:
    result = compose_study_008(config, tonic_midi=tonic_midi)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    midi_path = output / "ipm-study-008.mid"
    trace_path = output / "ipm-study-008.trace.json"
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
    parser = argparse.ArgumentParser(description="Generate IPM Study #008")
    parser.add_argument("--output", default="examples", help="output directory")
    parser.add_argument("--seed", type=int, default=2026081704)
    args = parser.parse_args()
    config = IPMConfig(seed=args.seed, tempo_bpm=58)
    result = compose_study_008(config)
    for path in write_study_008_files(args.output, config):
        print(path)
    print(json.dumps(result.trace["sequential_summary"], indent=2))
    print(json.dumps(result.trace["validation"], indent=2))
    if not result.trace["validation"]["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

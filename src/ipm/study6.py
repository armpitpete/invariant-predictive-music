"""Study #006: bar-level NOTE/REST rhythm grammar.

Study #005 corrected register spikes. Study #006 changes the rhythmic abstraction:
each 4/4 bar is now selected as a NOTE/REST pattern that sums to four beats exactly.
Pitch anchors, mode, tempo, form and hard voice registers come from Study #005.
Subsidiary notes are re-screened against the new lead timeline and are retained only
when they still beat silence.
"""

from __future__ import annotations

import argparse
import copy
import json
from fractions import Fraction
from pathlib import Path
from typing import Any, Sequence

from .bar_rhythm import (
    BarCellKind,
    BarPattern,
    BarRhythmPolicy,
    choose_bar_pattern,
    realise_bar_pattern,
)
from .countervoice import (
    CandidateAction,
    CountervoicePolicy,
    StructuralPhase,
    SubsidiaryCandidate,
    SubsidiaryRole,
    evaluate_candidate,
)
from .midi import render_midi
from .model import IPMConfig, NoteEvent, Voice
from .randomness import SeededRandom
from .study import StudyResult, _event_json
from .study4 import _occupancy_metrics, _phase_for_bar
from .study5 import compose_study_005

_BAR_CONTROLS: dict[str, tuple[float, float]] = {
    "opening": (0.12, 0.12),
    "establishment": (0.30, 0.12),
    "development": (0.52, 0.16),
    "climax": (0.72, 0.10),
    "resolution": (0.34, 0.18),
    "ending": (0.10, 0.25),
}


def _fraction_json(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def _structural_anchors(parent: StudyResult) -> dict[int, list[NoteEvent]]:
    grouped: dict[int, list[NoteEvent]] = {bar: [] for bar in range(16)}
    for decision in parent.trace["rhythm_budget_decisions"]:
        raw = decision["structural_event"]
        event = NoteEvent(
            onset=Fraction(*raw["onset"]),
            duration=Fraction(*raw["duration"]),
            pitch=raw["pitch"],
            velocity=raw["velocity"],
        )
        grouped[decision["bar"]].append(event)
    for bar, events in grouped.items():
        if not events:
            raise ValueError(f"parent study has no structural pitch anchors for bar {bar}")
        events.sort(key=lambda event: event.onset)
    return grouped


def _pattern_json(pattern: BarPattern) -> list[dict[str, Any]]:
    return [
        {
            "kind": cell.kind.value,
            "duration": _fraction_json(cell.duration),
        }
        for cell in pattern.cells
    ]


def _main_from_bar_grammar(
    parent: StudyResult,
    *,
    rng: SeededRandom,
) -> tuple[Voice, list[dict[str, Any]]]:
    anchors = _structural_anchors(parent)
    policy = BarRhythmPolicy(
        grid=Fraction(1),
        max_cells=4,
        max_attacks=4,
        max_rest_fraction=0.50,
    )
    main = Voice("M")
    decisions: list[dict[str, Any]] = []

    for bar in range(16):
        phase = _phase_for_bar(bar)
        intensity, rest_target = _BAR_CONTROLS[phase]
        pattern = choose_bar_pattern(
            rng=rng,
            intensity=intensity,
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
            gate=Fraction(15, 16),
        )
        for event in realised:
            main.add(event)
        decisions.append(
            {
                "bar": bar,
                "phase": phase,
                "intensity": intensity,
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


def _screen_subsidiary(
    source: Voice,
    *,
    role: SubsidiaryRole,
    frozen_voices: Sequence[Voice],
    policy: CountervoicePolicy,
) -> tuple[Voice, list[dict[str, Any]]]:
    accepted = Voice(source.name)
    trace: list[dict[str, Any]] = []
    for event in source.events:
        bar = min(15, int(event.onset // 4))
        phase = StructuralPhase(_phase_for_bar(bar))
        note_candidate = SubsidiaryCandidate(CandidateAction.NOTE, event)
        silence_candidate = SubsidiaryCandidate(CandidateAction.SILENCE)
        note_score = evaluate_candidate(
            note_candidate,
            role=role,
            target_voice=accepted,
            frozen_voices=frozen_voices,
            start=event.onset,
            end=event.end,
            phase=phase,
            policy=policy,
        )
        silence_score = evaluate_candidate(
            silence_candidate,
            role=role,
            target_voice=accepted,
            frozen_voices=frozen_voices,
            start=event.onset,
            end=event.end,
            phase=phase,
            policy=policy,
        )
        keep = (
            note_score.valid
            and silence_score.valid
            and note_score.total > silence_score.total + policy.improvement_epsilon
        )
        if keep:
            accepted.add(event)
        trace.append(
            {
                "voice": source.name,
                "source_event": _event_json(event),
                "kept": keep,
                "note_score": note_score.total,
                "note_valid": note_score.valid,
                "note_reason": note_score.reason,
                "minimum_vertical": note_score.minimum_vertical,
                "silence_score": silence_score.total,
                "silence_valid": silence_score.valid,
            }
        )
    return accepted, trace


def compose_study_006(
    config: IPMConfig | None = None,
    *,
    tonic_midi: int = 60,
) -> StudyResult:
    """Compose Study #006 using the bar-level NOTE/REST grammar."""

    requested = config or IPMConfig(seed=2026081704, tempo_bpm=58)
    parent = compose_study_005(requested, tonic_midi=tonic_midi)

    # 6000 is only a deterministic stream separation constant, not a musical score.
    main, bar_trace = _main_from_bar_grammar(
        parent,
        rng=SeededRandom(requested.seed ^ 6000),
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
    trace["study"] = "006"
    trace["parent_study"] = "005"
    trace["controlled_change"] = "main rhythm replaced by exact bar-level NOTE/REST grammar"
    trace["parent_rhythm_budget_decisions"] = trace.pop("rhythm_budget_decisions", [])
    trace["bar_rhythm_decisions"] = bar_trace
    trace["subsidiary_rescreen"] = response_trace + harmony_trace
    trace["voices"] = {
        "M": [_event_json(event) for event in main.events],
        "B_R": [_event_json(event) for event in response.events],
        "B_H": [_event_json(event) for event in harmony.events],
    }
    trace["metrics"] = _occupancy_metrics((main, response, harmony))

    shapes = {
        tuple((cell["kind"], tuple(cell["duration"])) for cell in bar["cells"])
        for bar in bar_trace
    }
    rest_bars = [
        bar
        for bar in bar_trace
        if any(cell["kind"] == BarCellKind.REST.value for cell in bar["cells"])
    ]
    leading_rest_bars = [
        bar for bar in rest_bars if bar["cells"][0]["kind"] == BarCellKind.REST.value
    ]
    trailing_rest_bars = [
        bar for bar in rest_bars if bar["cells"][-1]["kind"] == BarCellKind.REST.value
    ]
    whole_note_bars = [
        bar
        for bar in bar_trace
        if len(bar["cells"]) == 1
        and bar["cells"][0]["kind"] == BarCellKind.NOTE.value
        and bar["cells"][0]["duration"] == [4, 1]
    ]
    two_half_note_bars = [
        bar
        for bar in bar_trace
        if [(cell["kind"], cell["duration"]) for cell in bar["cells"]]
        == [("note", [2, 1]), ("note", [2, 1])]
    ]

    all_voices = (main, response, harmony)
    no_self_overlap = all(
        all(
            right.onset >= left.end
            for left, right in zip(voice.events, voice.events[1:], strict=False)
        )
        for voice in all_voices
    )
    checks = {
        "parent_study_passed": parent.trace["validation"]["passed"],
        "sixteen_exact_bars": len(bar_trace) == 16
        and all(
            sum(
                (Fraction(*cell["duration"]) for cell in bar["cells"]),
                Fraction(0),
            )
            == Fraction(4)
            for bar in bar_trace
        ),
        "bar_shapes_are_varied": len(shapes) >= 8,
        "literal_rest_bars_exist": len(rest_bars) >= 4,
        "rest_position_varies": bool(leading_rest_bars) and bool(trailing_rest_bars),
        "whole_note_option_is_exercised": bool(whole_note_bars),
        "two_half_note_option_is_exercised": bool(two_half_note_bars),
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
    trace["validation"] = {"passed": all(checks.values()), "checks": checks}
    return StudyResult(
        config=parent.config,
        main=main,
        response=response,
        harmony=harmony,
        trace=trace,
    )


def write_study_006_files(
    output_dir: str | Path,
    config: IPMConfig | None = None,
    *,
    tonic_midi: int = 60,
) -> tuple[Path, Path]:
    result = compose_study_006(config, tonic_midi=tonic_midi)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    midi_path = output / "ipm-study-006.mid"
    trace_path = output / "ipm-study-006.trace.json"
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
    parser = argparse.ArgumentParser(description="Generate IPM Study #006")
    parser.add_argument("--output", default="examples", help="output directory")
    parser.add_argument("--seed", type=int, default=2026081704)
    args = parser.parse_args()
    result = compose_study_006(IPMConfig(seed=args.seed, tempo_bpm=58))
    paths = write_study_006_files(
        args.output,
        IPMConfig(seed=args.seed, tempo_bpm=58),
    )
    print(json.dumps(result.trace["validation"], indent=2))
    for path in paths:
        print(path)
    if not result.trace["validation"]["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

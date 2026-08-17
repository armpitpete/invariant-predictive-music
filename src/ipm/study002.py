"""Study #002: a slower, narrower, rhythmically transformed IPM study.

Study #001 is intentionally preserved as the failed first listening control. This
study corrects the implementation choices that made it hymn-like: fixed major-mode
phrase templates, full-window counter-voice alignment, constant dynamics, no breath,
and an unconstrained main register.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, Sequence

from .countervoice import (
    CandidateAction,
    CandidateDecision,
    CountervoicePolicy,
    StructuralPhase,
    SubsidiaryCandidate,
    SubsidiaryRole,
    choose_candidate,
)
from .main_voice import MainBranchKind, MainDecision, MainFuture, choose_main_future
from .midi import render_midi
from .model import Beat, IPMConfig, NoteEvent, Voice
from .randomness import SeededRandom
from .rhythm import RhythmPolicy, RhythmicPartition, choose_rhythmic_partition, realise_partition
from .sonority import score_texture

_AEOLIAN = (0, 2, 3, 5, 7, 8, 10)
_LEAD_LOW = 60
_LEAD_HIGH = 71  # C4 through B4: one MIDI octave, with Aeolian notes stopping at Bb4.
_SEED_DEGREES = (4, 3, 2, 0)  # G-F-Eb-C: falling, vocal, unresolved until the final anchor.
_SEED_BUDGETS = (Fraction(2), Fraction(1), Fraction(1), Fraction(4))
_PHASES = (
    StructuralPhase.OPENING,
    StructuralPhase.ESTABLISHMENT,
    StructuralPhase.DEVELOPMENT,
    StructuralPhase.DEVELOPMENT,
    StructuralPhase.CLIMAX,
    StructuralPhase.RESOLUTION,
    StructuralPhase.RESOLUTION,
    StructuralPhase.ENDING,
)
_EXPECTED_DEGREES = (
    (4, 3, 2, 0),
    (3, 4, 2, 1),
    (4, 5, 3, 2),
    (5, 4, 2, 3),
    (6, 5, 3, 4),
    (5, 4, 2, 1),
    (3, 2, 1, 0),
    (2, 1, 0, 0),
)
_EXPECTED_BUDGETS = (
    (Fraction(2), Fraction(1), Fraction(1), Fraction(4)),
    (Fraction(1), Fraction(2), Fraction(1), Fraction(4)),
    (Fraction(2), Fraction(1), Fraction(2), Fraction(3)),
    (Fraction(1), Fraction(1), Fraction(3), Fraction(3)),
    (Fraction(1), Fraction(2), Fraction(2), Fraction(3)),
    (Fraction(2), Fraction(2), Fraction(1), Fraction(3)),
    (Fraction(3), Fraction(1), Fraction(1), Fraction(3)),
    (Fraction(2), Fraction(1), Fraction(1), Fraction(4)),
)
_RHYTHM_INTENSITY = {
    StructuralPhase.OPENING: 0.05,
    StructuralPhase.ESTABLISHMENT: 0.18,
    StructuralPhase.DEVELOPMENT: 0.36,
    StructuralPhase.CLIMAX: 0.56,
    StructuralPhase.RESOLUTION: 0.22,
    StructuralPhase.ENDING: 0.04,
}
_RESPONSE_OPPORTUNITIES = {
    1: frozenset({2}),
    2: frozenset({1, 3}),
    3: frozenset({0, 2}),
    4: frozenset({1, 3}),
    5: frozenset({1}),
    6: frozenset({2}),
}
# Kept away from the response opportunities so three-way stacks are not a quota.
_HARMONY_OPPORTUNITIES = {
    2: frozenset({0}),
    3: frozenset({3}),
    4: frozenset({0}),
    5: frozenset({3}),
}


@dataclass(frozen=True, slots=True)
class Study002Result:
    config: IPMConfig
    structural_main: tuple[NoteEvent, ...]
    main: Voice
    response: Voice
    harmony: Voice
    trace: dict[str, Any]

    @property
    def voices(self) -> tuple[Voice, Voice, Voice]:
        return (self.main, self.response, self.harmony)


def _beat_json(value: Beat) -> list[int]:
    return [value.numerator, value.denominator]


def _event_json(event: NoteEvent) -> dict[str, Any]:
    return {
        "onset": _beat_json(event.onset),
        "duration": _beat_json(event.duration),
        "pitch": event.pitch,
        "velocity": event.velocity,
    }


def _degree_to_lead_pitch(degree: int, tonic_midi: int) -> int:
    if not 0 <= degree < len(_AEOLIAN):
        raise ValueError("Study #002 lead degrees must remain inside one Aeolian octave")
    pitch = tonic_midi + _AEOLIAN[degree]
    if not _LEAD_LOW <= pitch <= _LEAD_HIGH:
        raise ValueError("Study #002 lead pitch escaped the locked one-octave register")
    return pitch


def _pitch_to_degree(pitch: int, tonic_midi: int) -> int:
    semitones = pitch - tonic_midi
    try:
        return _AEOLIAN.index(semitones)
    except ValueError as exc:
        raise ValueError("pitch is outside the Study #002 Aeolian lead world") from exc


def _phase_velocity(phase: StructuralPhase, index: int) -> int:
    base = {
        StructuralPhase.OPENING: 68,
        StructuralPhase.ESTABLISHMENT: 72,
        StructuralPhase.DEVELOPMENT: 76,
        StructuralPhase.CLIMAX: 82,
        StructuralPhase.RESOLUTION: 68,
        StructuralPhase.ENDING: 58,
    }[phase]
    contour = (0, -4, -1, -7)
    return max(42, min(92, base + contour[index]))


def _events_from_plan(
    *,
    degrees: Sequence[int],
    budgets: Sequence[Beat],
    start: Beat,
    tonic_midi: int,
    phase: StructuralPhase,
) -> tuple[NoteEvent, ...]:
    if len(degrees) != 4 or len(budgets) != 4:
        raise ValueError("Study #002 futures use four structural anchors")
    if sum(budgets, Fraction(0)) != Fraction(8):
        raise ValueError("Study #002 structural budgets must sum to eight beats")
    cursor = start
    result: list[NoteEvent] = []
    for index, (degree, budget) in enumerate(zip(degrees, budgets, strict=True)):
        result.append(
            NoteEvent(
                onset=cursor,
                duration=budget,
                pitch=_degree_to_lead_pitch(degree, tonic_midi),
                velocity=_phase_velocity(phase, index),
            )
        )
        cursor += budget
    return tuple(result)


def seed_motif_002(tonic_midi: int = 60) -> tuple[NoteEvent, ...]:
    return _events_from_plan(
        degrees=_SEED_DEGREES,
        budgets=_SEED_BUDGETS,
        start=Fraction(0),
        tonic_midi=tonic_midi,
        phase=StructuralPhase.OPENING,
    )


def _phase_probabilities(
    phase: StructuralPhase,
) -> tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]]:
    if phase in (StructuralPhase.OPENING, StructuralPhase.ENDING):
        return (
            (0.82, 0.76, 0.80, 0.84),
            (0.30, 0.42, 0.50, 0.58),
            (0.14, 0.30, 0.36, 0.42),
        )
    if phase is StructuralPhase.ESTABLISHMENT:
        return (
            (0.76, 0.72, 0.76, 0.80),
            (0.30, 0.66, 0.72, 0.78),
            (0.18, 0.54, 0.60, 0.66),
        )
    if phase is StructuralPhase.DEVELOPMENT:
        return (
            (0.70, 0.66, 0.70, 0.74),
            (0.26, 0.80, 0.84, 0.88),
            (0.16, 0.72, 0.78, 0.82),
        )
    if phase is StructuralPhase.CLIMAX:
        return (
            (0.68, 0.64, 0.68, 0.72),
            (0.22, 0.84, 0.88, 0.92),
            (0.13, 0.80, 0.84, 0.88),
        )
    return (
        (0.78, 0.76, 0.80, 0.84),
        (0.28, 0.58, 0.64, 0.70),
        (0.16, 0.46, 0.52, 0.58),
    )


def _rotate_budgets(budgets: tuple[Beat, ...], amount: int) -> tuple[Beat, ...]:
    amount %= len(budgets)
    return budgets[amount:] + budgets[:amount]


def _main_futures_002(
    *,
    chunk_index: int,
    start: Beat,
    tonic_midi: int,
) -> tuple[MainFuture, MainFuture, MainFuture]:
    phase = _PHASES[chunk_index]
    expected_degrees = _EXPECTED_DEGREES[chunk_index]
    expected_budgets = _EXPECTED_BUDGETS[chunk_index]

    shift = -1 if max(expected_degrees) >= 6 else 1
    revealing_degrees = tuple(degree + shift for degree in expected_degrees)
    exploratory = list(expected_degrees)
    delta = 1 if chunk_index % 2 == 0 else -1
    exploratory[1] = max(0, min(6, exploratory[1] + delta))
    exploratory[2] = max(0, min(6, exploratory[2] - delta))
    exploratory_degrees = tuple(exploratory)

    revealing_budgets = _rotate_budgets(expected_budgets, 1)
    exploratory_budgets = _rotate_budgets(expected_budgets, 2)
    expected_p, revealing_p, exploratory_p = _phase_probabilities(phase)

    return (
        MainFuture(
            MainBranchKind.EXPECTED,
            _events_from_plan(
                degrees=expected_degrees,
                budgets=expected_budgets,
                start=start,
                tonic_midi=tonic_midi,
                phase=phase,
            ),
            expected_p,
        ),
        MainFuture(
            MainBranchKind.REVEALING,
            _events_from_plan(
                degrees=revealing_degrees,
                budgets=revealing_budgets,
                start=start,
                tonic_midi=tonic_midi,
                phase=phase,
            ),
            revealing_p,
        ),
        MainFuture(
            MainBranchKind.EXPLORATORY,
            _events_from_plan(
                degrees=exploratory_degrees,
                budgets=exploratory_budgets,
                start=start,
                tonic_midi=tonic_midi,
                phase=phase,
            ),
            exploratory_p,
        ),
    )


def _main_score_json(decision: MainDecision) -> dict[str, Any]:
    return {
        "selected": decision.selected.future.kind.value,
        "baseline": decision.baseline.future.kind.value,
        "selected_score": decision.selected.total,
        "baseline_score": decision.baseline.total,
        "eligible": [score.future.kind.value for score in decision.eligible],
        "candidates": [
            {
                "kind": score.future.kind.value,
                "total": score.total,
                "valid": score.valid,
                "reason": score.reason,
                "forward_probability": score.forward_probability,
                "surprise_bits": score.surprise_bits,
                "invariant_similarity": score.invariant_similarity,
                "lookahead_predictability": score.lookahead_predictability,
                "retrospective_coherence": score.retrospective_coherence,
                "retrospective_necessity": score.retrospective_necessity,
                "events": [_event_json(event) for event in score.future.events],
            }
            for score in decision.scored
        ],
    }


def _realise_main_anchor(
    event: NoteEvent,
    *,
    phase: StructuralPhase,
    rng: SeededRandom,
    policy: RhythmPolicy,
) -> tuple[tuple[NoteEvent, ...], RhythmicPartition]:
    partition = choose_rhythmic_partition(
        event.duration,
        rng=rng,
        intensity=_RHYTHM_INTENSITY[phase],
        policy=policy,
    )
    gate = Fraction(3, 4) if partition.attacks > 1 else Fraction(7, 8)
    raw = realise_partition(event, partition, gate=gate)
    realised = tuple(
        NoteEvent(
            note.onset,
            note.duration,
            note.pitch,
            max(35, note.velocity - 3 * index),
        )
        for index, note in enumerate(raw)
    )
    return realised, partition


def _response_candidates(
    *,
    anchor: NoteEvent,
    chunk_index: int,
    event_index: int,
    tonic_midi: int,
) -> tuple[SubsidiaryCandidate, ...]:
    candidates: list[SubsidiaryCandidate] = [SubsidiaryCandidate(CandidateAction.SILENCE)]
    if event_index not in _RESPONSE_OPPORTUNITIES.get(chunk_index, frozenset()):
        return tuple(candidates)

    if anchor.duration < Fraction(1):
        return tuple(candidates)
    delay = Fraction(1, 2) if anchor.duration <= Fraction(1) else Fraction(1)
    duration = min(Fraction(1), anchor.duration - delay)
    if duration < Fraction(1, 2):
        return tuple(candidates)
    onset = anchor.onset + delay
    degree = _pitch_to_degree(anchor.pitch, tonic_midi)
    offsets = (-2, -3) if degree >= 4 else (2, 3)
    for offset in offsets:
        response_degree = max(0, min(6, degree + offset))
        pitch = _degree_to_lead_pitch(response_degree, tonic_midi) - 12
        candidates.append(
            SubsidiaryCandidate(
                CandidateAction.NOTE,
                NoteEvent(onset, duration, pitch, 55),
            )
        )
    return tuple(candidates)


def _harmony_candidates(
    *,
    anchor: NoteEvent,
    chunk_index: int,
    event_index: int,
    tonic_midi: int,
) -> tuple[SubsidiaryCandidate, ...]:
    candidates: list[SubsidiaryCandidate] = [SubsidiaryCandidate(CandidateAction.SILENCE)]
    if event_index not in _HARMONY_OPPORTUNITIES.get(chunk_index, frozenset()):
        return tuple(candidates)
    if anchor.duration < Fraction(1):
        return tuple(candidates)

    duration = min(Fraction(1), anchor.duration / 2)
    onset = anchor.end - duration
    degree = _pitch_to_degree(anchor.pitch, tonic_midi)
    for offset in (-4, -2):
        support_degree = max(0, min(6, degree + offset))
        pitch = _degree_to_lead_pitch(support_degree, tonic_midi) - 12
        candidates.append(
            SubsidiaryCandidate(
                CandidateAction.NOTE,
                NoteEvent(onset, duration, pitch, 47),
            )
        )
    return tuple(candidates)


def _counter_json(
    *,
    voice: str,
    chunk_index: int,
    event_index: int,
    phase: StructuralPhase,
    anchor: NoteEvent,
    decision: CandidateDecision,
) -> dict[str, Any]:
    note = decision.selected.candidate.note
    return {
        "voice": voice,
        "chunk": chunk_index,
        "event_index": event_index,
        "phase": phase.value,
        "window": [_beat_json(anchor.onset), _beat_json(anchor.end)],
        "selected_action": decision.selected.candidate.action.value,
        "selected_note": _event_json(note) if note is not None else None,
        "selected_score": decision.selected.total,
        "silence_score": decision.silence.total if decision.silence is not None else None,
        "candidates": [
            {
                "action": score.candidate.action.value,
                "note": _event_json(score.candidate.note) if score.candidate.note is not None else None,
                "total": score.total,
                "vertical": score.vertical,
                "density_fit": score.density_fit,
                "minimum_vertical": score.minimum_vertical,
                "valid": score.valid,
                "reason": score.reason,
            }
            for score in decision.scored
        ],
    }


def _apply_counter(decision: CandidateDecision, voice: Voice) -> None:
    if decision.selected.candidate.action is CandidateAction.NOTE:
        assert decision.selected.candidate.note is not None
        voice.add(decision.selected.candidate.note)


def _texture_metrics(voices: Sequence[Voice], *, total_beats: Beat) -> dict[str, Any]:
    boundaries = {Fraction(0), total_beats}
    for voice in voices:
        for event in voice.events:
            boundaries.add(event.onset)
            boundaries.add(event.end)
    ordered = sorted(boundaries)
    texture_beats: dict[str, Beat] = defaultdict(lambda: Fraction(0))
    order = {"M": 0, "B_R": 1, "B_H": 2}
    for start, end in zip(ordered, ordered[1:], strict=False):
        active = [
            voice.name
            for voice in voices
            if any(event.onset <= start and event.end >= end for event in voice.events)
        ]
        name = "+".join(sorted(active, key=order.__getitem__)) if active else "silence"
        texture_beats[name] += end - start

    score = score_texture(voices)
    return {
        "total_beats": _beat_json(total_beats),
        "texture_beats": {
            name: _beat_json(duration) for name, duration in sorted(texture_beats.items())
        },
        "texture_ratio": {
            name: float(duration / total_beats)
            for name, duration in sorted(texture_beats.items())
        },
        "vertical_weighted_mean": score.weighted_mean,
        "vertical_minimum": score.minimum,
        "sonority_slices": score.slices,
    }


def _validation(
    *,
    config: IPMConfig,
    structural_main: Sequence[NoteEvent],
    main: Voice,
    response: Voice,
    harmony: Voice,
    rhythm_trace: Sequence[dict[str, Any]],
    counter_trace: Sequence[dict[str, Any]],
    metrics: dict[str, Any],
    tonic_midi: int,
) -> dict[str, Any]:
    total_beats = Fraction(config.bars * config.beats_per_bar)
    main_pitches = [event.pitch for event in main.events]
    ratios = metrics["texture_ratio"]
    two_voice = sum(
        ratio
        for name, ratio in ratios.items()
        if name in ("M+B_R", "M+B_H")
    )
    triple = ratios.get("M+B_R+B_H", 0.0)
    main_alone = ratios.get("M", 0.0)
    breath_gaps = sum(
        right.onset > left.end
        for left, right in zip(main.events, main.events[1:], strict=False)
    )
    selected_counter = [
        item for item in counter_trace if item["selected_action"] == CandidateAction.NOTE.value
    ]
    delayed_counter = [
        item
        for item in selected_counter
        if item["selected_note"] is not None
        and item["selected_note"]["onset"] != item["window"][0]
    ]
    partition_shapes = {
        tuple(tuple(segment) for segment in item["segments"])
        for item in rhythm_trace
    }

    checks = {
        "exact_structural_length": bool(structural_main) and structural_main[-1].end == total_beats,
        "lead_within_one_octave": bool(main_pitches)
        and all(_LEAD_LOW <= pitch <= _LEAD_HIGH for pitch in main_pitches)
        and max(main_pitches) - min(main_pitches) <= 11,
        "aeolian_lead": all((pitch - tonic_midi) in _AEOLIAN for pitch in main_pitches),
        "breath_is_audible": breath_gaps >= max(1, len(main.events) // 2),
        "rhythm_is_transformed": len(partition_shapes) >= 4
        and any(item["attacks"] > 1 for item in rhythm_trace),
        "responsive_voice_present": bool(response.events),
        "harmonic_colour_present": bool(harmony.events),
        "counter_timing_is_independent": bool(delayed_counter),
        "main_alone_is_dominant": main_alone >= 0.55,
        "two_note_texture_occurs": two_voice >= 0.05,
        "three_voice_texture_not_required": triple <= 0.06,
        "vertical_floor": metrics["vertical_minimum"] >= 0.55,
        "final_tonic": bool(main.events) and main.events[-1].pitch % 12 == tonic_midi % 12,
    }
    return {"passed": all(checks.values()), "checks": checks}


def compose_study_002(
    config: IPMConfig | None = None,
    *,
    tonic_midi: int = 60,
) -> Study002Result:
    """Compose the second listening study from the same IPM mechanisms."""

    config = config or IPMConfig(seed=20260817, tempo_bpm=58)
    if config.bars != 16 or config.beats_per_bar != 4:
        raise ValueError("Study #002 is fixed at 16 bars of 4/4")
    if tonic_midi != 60:
        raise ValueError("Study #002 currently locks the lead to the C4-B4 octave")

    rng = SeededRandom(config.seed)
    reference = seed_motif_002(tonic_midi)
    structural: list[NoteEvent] = []
    main = Voice("M")
    main_trace: list[dict[str, Any]] = []
    rhythm_trace: list[dict[str, Any]] = []
    rhythm_policy = RhythmPolicy(grid=Fraction(1, 2), max_attacks=4)

    for chunk_index, phase in enumerate(_PHASES):
        start = Fraction(chunk_index * 8)
        futures = _main_futures_002(
            chunk_index=chunk_index,
            start=start,
            tonic_midi=tonic_midi,
        )
        decision = choose_main_future(futures, reference_motif=reference, rng=rng)
        selected = decision.selected.future.events
        structural.extend(selected)

        main_entry = _main_score_json(decision)
        main_entry.update({"chunk": chunk_index, "phase": phase.value})
        main_trace.append(main_entry)

        for event_index, event in enumerate(selected):
            realised, partition = _realise_main_anchor(
                event,
                phase=phase,
                rng=rng,
                policy=rhythm_policy,
            )
            for note in realised:
                main.add(note)
            rhythm_trace.append(
                {
                    "chunk": chunk_index,
                    "event_index": event_index,
                    "phase": phase.value,
                    "anchor": _event_json(event),
                    "attacks": partition.attacks,
                    "segments": [_beat_json(segment) for segment in partition.segments],
                    "realised": [_event_json(note) for note in realised],
                }
            )

    response = Voice("B_R")
    harmony = Voice("B_H")
    counter_trace: list[dict[str, Any]] = []
    counter_policy = CountervoicePolicy(
        vertical_weight=0.75,
        density_weight=0.25,
        response_attack_cost=0.055,
        harmony_attack_cost=0.085,
        response_vertical_floor=0.50,
        harmony_vertical_floor=0.58,
    )

    for chunk_index, phase in enumerate(_PHASES):
        for event_index in range(4):
            anchor = structural[chunk_index * 4 + event_index]
            response_decision = choose_candidate(
                _response_candidates(
                    anchor=anchor,
                    chunk_index=chunk_index,
                    event_index=event_index,
                    tonic_midi=tonic_midi,
                ),
                role=SubsidiaryRole.RESPONSE,
                target_voice=response,
                frozen_voices=(main,),
                start=anchor.onset,
                end=anchor.end,
                phase=phase,
                rng=rng,
                beats_per_bar=config.beats_per_bar,
                policy=counter_policy,
            )
            _apply_counter(response_decision, response)
            counter_trace.append(
                _counter_json(
                    voice="B_R",
                    chunk_index=chunk_index,
                    event_index=event_index,
                    phase=phase,
                    anchor=anchor,
                    decision=response_decision,
                )
            )

            harmony_decision = choose_candidate(
                _harmony_candidates(
                    anchor=anchor,
                    chunk_index=chunk_index,
                    event_index=event_index,
                    tonic_midi=tonic_midi,
                ),
                role=SubsidiaryRole.HARMONY,
                target_voice=harmony,
                frozen_voices=(main, response),
                start=anchor.onset,
                end=anchor.end,
                phase=phase,
                rng=rng,
                beats_per_bar=config.beats_per_bar,
                policy=counter_policy,
            )
            _apply_counter(harmony_decision, harmony)
            counter_trace.append(
                _counter_json(
                    voice="B_H",
                    chunk_index=chunk_index,
                    event_index=event_index,
                    phase=phase,
                    anchor=anchor,
                    decision=harmony_decision,
                )
            )

    total_beats = Fraction(config.bars * config.beats_per_bar)
    metrics = _texture_metrics((main, response, harmony), total_beats=total_beats)
    validation = _validation(
        config=config,
        structural_main=structural,
        main=main,
        response=response,
        harmony=harmony,
        rhythm_trace=rhythm_trace,
        counter_trace=counter_trace,
        metrics=metrics,
        tonic_midi=tonic_midi,
    )
    trace = {
        "model": "IPM",
        "study": "002",
        "seed": config.seed,
        "tempo_bpm": config.tempo_bpm,
        "bars": config.bars,
        "beats_per_bar": config.beats_per_bar,
        "mode": "C Aeolian",
        "lead_register": [_LEAD_LOW, _LEAD_HIGH],
        "seed_motif": [_event_json(event) for event in reference],
        "main_decisions": main_trace,
        "rhythm_decisions": rhythm_trace,
        "counter_decisions": counter_trace,
        "voices": {
            main.name: [_event_json(event) for event in main.events],
            response.name: [_event_json(event) for event in response.events],
            harmony.name: [_event_json(event) for event in harmony.events],
        },
        "metrics": metrics,
        "validation": validation,
    }
    return Study002Result(config, tuple(structural), main, response, harmony, trace)


def write_study_002_files(
    result: Study002Result,
    *,
    midi_path: str | Path,
    trace_path: str | Path,
) -> tuple[Path, Path]:
    midi_target = Path(midi_path)
    trace_target = Path(trace_path)
    midi_target.parent.mkdir(parents=True, exist_ok=True)
    trace_target.parent.mkdir(parents=True, exist_ok=True)
    midi_target.write_bytes(
        render_midi(
            result.voices,
            tempo_bpm=result.config.tempo_bpm,
            beats_per_bar=result.config.beats_per_bar,
        )
    )
    trace_target.write_text(
        json.dumps(result.trace, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return midi_target, trace_target


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate IPM listening Study #002")
    parser.add_argument("--seed", type=int, default=20260817)
    parser.add_argument("--tempo", type=int, default=58)
    parser.add_argument("--midi", default="examples/study-002.mid")
    parser.add_argument("--trace", default="examples/study-002.trace.json")
    args = parser.parse_args(argv)

    result = compose_study_002(IPMConfig(seed=args.seed, tempo_bpm=args.tempo))
    midi_path, trace_path = write_study_002_files(
        result,
        midi_path=args.midi,
        trace_path=args.trace,
    )
    print(
        json.dumps(
            {
                "midi": str(midi_path),
                "trace": str(trace_path),
                "validation": result.trace["validation"],
                "metrics": result.trace["metrics"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if result.trace["validation"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

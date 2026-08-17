"""Study #002: faster transformed rhythm with Euclidean counter-voice timing."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, Sequence

from .countertime import TimedDecision, choose_timed_candidate, note_candidate
from .countervoice import CountervoicePolicy, StructuralPhase, SubsidiaryRole
from .euclidean import EuclideanPattern, euclidean_onsets, least_aligned_rotation
from .main_voice import MainBranchKind, MainDecision, MainFuture, choose_main_future
from .midi import render_midi
from .model import Beat, IPMConfig, NoteEvent, Voice
from .randomness import SeededRandom
from .study import (
    StudyResult,
    _beat_json,
    _degree_to_midi,
    _event_json,
    _midi_to_degree,
    _nearest_degree_octave,
    _phase_probabilities,
    _texture_metrics,
)

_MAJOR_SEED_SHAPE = (0, 2, 4, 3)
_EXPLORATORY_SHAPES = (
    (0, 3, 5, 4),
    (0, 2, 5, 3),
    (0, 3, 4, 2),
    (0, 1, 4, 3),
)
_RHYTHMS: tuple[tuple[Beat, ...], ...] = (
    (Fraction(1, 2), Fraction(1, 2), Fraction(1), Fraction(2)),
    (Fraction(1, 2), Fraction(1), Fraction(3, 2), Fraction(1)),
    (Fraction(1), Fraction(1, 2), Fraction(1), Fraction(3, 2)),
    (Fraction(1, 2), Fraction(3, 2), Fraction(1), Fraction(1)),
    (Fraction(1), Fraction(1), Fraction(1, 2), Fraction(3, 2)),
    (Fraction(3, 2), Fraction(1, 2), Fraction(1), Fraction(1)),
    (Fraction(1, 2), Fraction(1), Fraction(1), Fraction(3, 2)),
    (Fraction(1), Fraction(3, 2), Fraction(1, 2), Fraction(1)),
)
_ROOT_PLAN = (0, 0, 3, 4, 0, 5, 3, 4, 5, 4, 3, 1, 4, 3, 1, 0)
_PHASES = (
    StructuralPhase.OPENING,
    StructuralPhase.OPENING,
    StructuralPhase.ESTABLISHMENT,
    StructuralPhase.ESTABLISHMENT,
    StructuralPhase.ESTABLISHMENT,
    StructuralPhase.DEVELOPMENT,
    StructuralPhase.DEVELOPMENT,
    StructuralPhase.DEVELOPMENT,
    StructuralPhase.DEVELOPMENT,
    StructuralPhase.DEVELOPMENT,
    StructuralPhase.CLIMAX,
    StructuralPhase.CLIMAX,
    StructuralPhase.RESOLUTION,
    StructuralPhase.RESOLUTION,
    StructuralPhase.RESOLUTION,
    StructuralPhase.ENDING,
)
_BR_SPECS = ((3, 8), (5, 16), (5, 16), (3, 8))
_BH_SPECS = ((1, 16), (2, 16), (3, 16), (1, 16))


def _events_from_shape(
    *,
    root_degree: int,
    start: Beat,
    shape: Sequence[int],
    durations: Sequence[Beat],
    tonic_midi: int,
    velocity: int,
) -> tuple[NoteEvent, ...]:
    if len(shape) != 4 or len(durations) != 4:
        raise ValueError("study #002 futures require four notes")
    if sum(durations, Fraction(0)) != 4:
        raise ValueError("study #002 rhythmic variants must span one 4/4 bar")
    cursor = start
    events: list[NoteEvent] = []
    for offset, duration in zip(shape, durations, strict=True):
        events.append(
            NoteEvent(
                onset=cursor,
                duration=duration,
                pitch=_degree_to_midi(root_degree + offset, tonic_midi),
                velocity=velocity,
            )
        )
        cursor += duration
    return tuple(events)


def seed_motif_002(tonic_midi: int = 60) -> tuple[NoteEvent, ...]:
    return _events_from_shape(
        root_degree=0,
        start=Fraction(0),
        shape=_MAJOR_SEED_SHAPE,
        durations=_RHYTHMS[0],
        tonic_midi=tonic_midi,
        velocity=90,
    )


def _main_futures(
    *,
    bar: int,
    previous_pitch: int | None,
    tonic_midi: int,
) -> tuple[MainFuture, MainFuture, MainFuture]:
    start = Fraction(bar * 4)
    phase = _PHASES[bar]
    base_degree = _ROOT_PLAN[bar]
    expected_root = (
        base_degree
        if previous_pitch is None
        else _nearest_degree_octave(base_degree, previous_pitch, tonic_midi)
    )

    if bar == 15:
        expected_shape = (3, 2, 1, 0)
        revealing_shape = (0, 2, 3, 0)
        exploratory_shape = (0, 3, 4, 0)
        revealing_root = exploratory_root = expected_root
    else:
        expected_shape = _MAJOR_SEED_SHAPE
        revealing_shape = _MAJOR_SEED_SHAPE
        revealing_base = base_degree + (2 if phase not in (StructuralPhase.OPENING, StructuralPhase.ENDING) else -1)
        revealing_root = (
            revealing_base
            if previous_pitch is None
            else _nearest_degree_octave(revealing_base, previous_pitch, tonic_midi)
        )
        exploratory_base = base_degree + (1 if bar % 2 == 0 else -1)
        exploratory_root = (
            exploratory_base
            if previous_pitch is None
            else _nearest_degree_octave(exploratory_base, previous_pitch, tonic_midi)
        )
        exploratory_shape = _EXPLORATORY_SHAPES[bar % len(_EXPLORATORY_SHAPES)]

    expected_durations = _RHYTHMS[bar % len(_RHYTHMS)]
    revealing_durations = _RHYTHMS[(bar + 2) % len(_RHYTHMS)]
    exploratory_durations = _RHYTHMS[(bar + 5) % len(_RHYTHMS)]
    expected_p, revealing_p, exploratory_p = _phase_probabilities(phase)

    return (
        MainFuture(
            MainBranchKind.EXPECTED,
            _events_from_shape(
                root_degree=expected_root,
                start=start,
                shape=expected_shape,
                durations=expected_durations,
                tonic_midi=tonic_midi,
                velocity=90,
            ),
            expected_p,
        ),
        MainFuture(
            MainBranchKind.REVEALING,
            _events_from_shape(
                root_degree=revealing_root,
                start=start,
                shape=revealing_shape,
                durations=revealing_durations,
                tonic_midi=tonic_midi,
                velocity=90,
            ),
            revealing_p,
        ),
        MainFuture(
            MainBranchKind.EXPLORATORY,
            _events_from_shape(
                root_degree=exploratory_root,
                start=start,
                shape=exploratory_shape,
                durations=exploratory_durations,
                tonic_midi=tonic_midi,
                velocity=90,
            ),
            exploratory_p,
        ),
    )


def _main_trace(decision: MainDecision, bar: int) -> dict[str, Any]:
    return {
        "bar": bar,
        "phase": _PHASES[bar].value,
        "selected": decision.selected.future.kind.value,
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
                "invariant_similarity": score.invariant_similarity,
                "events": [_event_json(event) for event in score.future.events],
            }
            for score in decision.scored
        ],
    }


def _main_pitch_at(main: Voice, onset: Beat) -> int | None:
    for event in main.events:
        if event.onset <= onset < event.end:
            return event.pitch
    return None


def _occupied_indices(main: Voice, *, start: Beat, span: Beat, steps: int) -> tuple[int, ...]:
    step_duration = span / steps
    occupied: list[int] = []
    for event in main.events:
        if not start <= event.onset < start + span:
            continue
        index = (event.onset - start) / step_duration
        if index.denominator == 1:
            occupied.append(index.numerator)
    return tuple(occupied)


def _pattern_for_section(
    main: Voice,
    *,
    section: int,
    pulses: int,
    steps: int,
) -> EuclideanPattern:
    start = Fraction(section * 16)
    return least_aligned_rotation(
        pulses,
        steps,
        occupied_indices=_occupied_indices(main, start=start, span=Fraction(16), steps=steps),
    )


def _timed_trace(
    *,
    voice: str,
    onset: Beat,
    phase: StructuralPhase,
    decision: TimedDecision,
) -> dict[str, Any]:
    selected = decision.selected.candidate.note if decision.selected is not None else None
    return {
        "voice": voice,
        "onset": _beat_json(onset),
        "phase": phase.value,
        "selected": _event_json(selected) if selected is not None else None,
        "candidates": [
            {
                "event": _event_json(score.candidate.note),
                "valid": score.valid,
                "reason": score.reason,
                "improvement_over_silence": score.improvement,
                "vertical": score.note_score.vertical,
                "minimum_vertical": score.note_score.minimum_vertical,
            }
            for score in decision.scored
            if score.candidate.note is not None
        ],
    }


def _response_candidates(
    *,
    main: Voice,
    onset: Beat,
    duration: Beat,
    tonic_midi: int,
) -> tuple:
    pitch = _main_pitch_at(main, onset)
    if pitch is None:
        return ()
    degree = _midi_to_degree(pitch, tonic_midi)
    candidates = []
    for offset in (-4, 2, -2, 4):
        try:
            candidate_pitch = _degree_to_midi(degree + offset, tonic_midi)
        except ValueError:
            continue
        candidates.append(
            note_candidate(onset=onset, duration=duration, pitch=candidate_pitch, velocity=70)
        )
    return tuple(candidates)


def _harmony_candidates(
    *,
    main: Voice,
    onset: Beat,
    duration: Beat,
    tonic_midi: int,
) -> tuple:
    pitch = _main_pitch_at(main, onset)
    if pitch is None:
        return ()
    degree = _midi_to_degree(pitch, tonic_midi)
    candidates = []
    for offset in (-4, -7, -2, -9):
        try:
            candidate_pitch = _degree_to_midi(degree + offset, tonic_midi)
        except ValueError:
            continue
        if candidate_pitch >= pitch:
            continue
        candidates.append(
            note_candidate(onset=onset, duration=duration, pitch=candidate_pitch, velocity=56)
        )
    return tuple(candidates)


def _phase_at(onset: Beat) -> StructuralPhase:
    bar = min(15, int(onset // 4))
    return _PHASES[bar]


def _crosses_main_boundary(note: NoteEvent, main: Voice) -> bool:
    return any(note.onset < event.onset < note.end for event in main.events)


def _validation(
    *,
    result: StudyResult,
    proposed_attacks: int,
    accepted_attacks: int,
    tonic_midi: int,
) -> dict[str, Any]:
    main, response, harmony = result.voices
    metrics = result.trace["metrics"]
    ratios = metrics["texture_ratio"]
    main_alone = ratios.get("M", 0.0)
    other = [ratio for name, ratio in ratios.items() if name != "M"]
    durations = {tuple(event.duration for event in main.events[bar * 4 : bar * 4 + 4]) for bar in range(16)}
    main_onsets = {event.onset for event in main.events}
    counter_events = (*response.events, *harmony.events)
    checks = {
        "exact_length": main.cursor == Fraction(64),
        "tempo_is_108": result.config.tempo_bpm == 108,
        "rhythm_is_transformed": len(durations) >= 6,
        "no_four_beat_main_notes": max(event.duration for event in main.events) <= 2,
        "responsive_voice_present": bool(response.events),
        "harmonic_voice_present": bool(harmony.events),
        "independent_counter_onset_present": any(event.onset not in main_onsets for event in counter_events),
        "counter_note_crosses_main_boundary": any(_crosses_main_boundary(event, main) for event in counter_events),
        "euclidean_opportunities_are_not_quotas": accepted_attacks < proposed_attacks,
        "main_alone_is_most_common_texture": bool(other) and main_alone > max(other),
        "three_voice_texture_is_exceptional": ratios.get("M+B_R+B_H", 0.0) <= 0.125,
        "vertical_floor": metrics["vertical_minimum"] >= 0.65,
        "final_tonic": main.events[-1].pitch % 12 == tonic_midi % 12,
        "surprise_occurs": any(
            entry["selected"] != MainBranchKind.EXPECTED.value
            for entry in result.trace["main_decisions"]
        ),
    }
    return {"passed": all(checks.values()), "checks": checks}


def compose_study_002(
    config: IPMConfig | None = None,
    *,
    tonic_midi: int = 60,
) -> StudyResult:
    """Compose the second 16-bar listening study from the post-001 corrections."""

    config = config or IPMConfig(seed=2026081702, tempo_bpm=108)
    if config.bars != 16 or config.beats_per_bar != 4:
        raise ValueError("study #002 is fixed at 16 bars of 4/4")
    if not 0 <= tonic_midi <= 127:
        raise ValueError("tonic_midi must be in 0..127")

    rng = SeededRandom(config.seed)
    reference = seed_motif_002(tonic_midi)
    main = Voice("M")
    main_trace: list[dict[str, Any]] = []
    previous_pitch: int | None = None

    for bar in range(16):
        decision = choose_main_future(
            _main_futures(bar=bar, previous_pitch=previous_pitch, tonic_midi=tonic_midi),
            reference_motif=reference,
            rng=rng,
        )
        for event in decision.selected.future.events:
            main.add(event)
        previous_pitch = decision.selected.future.events[-1].pitch
        main_trace.append(_main_trace(decision, bar))

    response = Voice("B_R")
    harmony = Voice("B_H")
    counter_trace: list[dict[str, Any]] = []
    euclidean_trace: list[dict[str, Any]] = []
    proposed_attacks = 0
    accepted_attacks = 0
    policy = CountervoicePolicy(harmony_attack_cost=0.02)

    for section, (pulses, steps) in enumerate(_BR_SPECS):
        pattern = _pattern_for_section(main, section=section, pulses=pulses, steps=steps)
        start = Fraction(section * 16)
        onsets = euclidean_onsets(pulses, steps, start=start, span=Fraction(16), rotation=pattern.rotation)
        euclidean_trace.append(
            {
                "voice": "B_R",
                "section": section,
                "pulses": pulses,
                "steps": steps,
                "rotation": pattern.rotation,
                "attack_indices": list(pattern.attack_indices),
                "onsets": [_beat_json(onset) for onset in onsets],
            }
        )
        for onset in onsets:
            phase = _phase_at(onset)
            duration = Fraction(1, 2) if phase in (StructuralPhase.OPENING, StructuralPhase.ENDING) else Fraction(1)
            candidates = _response_candidates(main=main, onset=onset, duration=duration, tonic_midi=tonic_midi)
            if not candidates:
                continue
            proposed_attacks += 1
            decision = choose_timed_candidate(
                candidates,
                role=SubsidiaryRole.RESPONSE,
                target_voice=response,
                frozen_voices=(main,),
                phase=phase,
                rng=rng,
                beats_per_bar=config.beats_per_bar,
                policy=policy,
            )
            counter_trace.append(_timed_trace(voice="B_R", onset=onset, phase=phase, decision=decision))
            if decision.selected is not None:
                response.add(decision.selected.candidate.note)
                accepted_attacks += 1

    for section, (pulses, steps) in enumerate(_BH_SPECS):
        pattern = _pattern_for_section(main, section=section, pulses=pulses, steps=steps)
        start = Fraction(section * 16)
        onsets = euclidean_onsets(pulses, steps, start=start, span=Fraction(16), rotation=pattern.rotation)
        euclidean_trace.append(
            {
                "voice": "B_H",
                "section": section,
                "pulses": pulses,
                "steps": steps,
                "rotation": pattern.rotation,
                "attack_indices": list(pattern.attack_indices),
                "onsets": [_beat_json(onset) for onset in onsets],
            }
        )
        for onset in onsets:
            phase = _phase_at(onset)
            duration = Fraction(2) if phase is not StructuralPhase.CLIMAX else Fraction(3)
            if onset + duration > 64:
                duration = Fraction(64) - onset
            if duration <= 0:
                continue
            candidates = _harmony_candidates(main=main, onset=onset, duration=duration, tonic_midi=tonic_midi)
            if not candidates:
                continue
            proposed_attacks += 1
            decision = choose_timed_candidate(
                candidates,
                role=SubsidiaryRole.HARMONY,
                target_voice=harmony,
                frozen_voices=(main, response),
                phase=phase,
                rng=rng,
                beats_per_bar=config.beats_per_bar,
                policy=policy,
            )
            counter_trace.append(_timed_trace(voice="B_H", onset=onset, phase=phase, decision=decision))
            if decision.selected is not None:
                harmony.add(decision.selected.candidate.note)
                accepted_attacks += 1

    metrics = _texture_metrics((main, response, harmony))
    trace: dict[str, Any] = {
        "model": "IPM",
        "study": "002",
        "seed": config.seed,
        "tempo_bpm": config.tempo_bpm,
        "bars": config.bars,
        "beats_per_bar": config.beats_per_bar,
        "tonic_midi": tonic_midi,
        "seed_motif": [_event_json(event) for event in reference],
        "main_decisions": main_trace,
        "euclidean_timing": euclidean_trace,
        "counter_decisions": counter_trace,
        "voices": {
            main.name: [_event_json(event) for event in main.events],
            response.name: [_event_json(event) for event in response.events],
            harmony.name: [_event_json(event) for event in harmony.events],
        },
        "metrics": metrics,
        "euclidean_counts": {
            "proposed_attacks": proposed_attacks,
            "accepted_attacks": accepted_attacks,
        },
    }
    result = StudyResult(config, main, response, harmony, trace)
    trace["validation"] = _validation(
        result=result,
        proposed_attacks=proposed_attacks,
        accepted_attacks=accepted_attacks,
        tonic_midi=tonic_midi,
    )
    return result


def write_study_002_files(
    result: StudyResult,
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
    trace_target.write_text(json.dumps(result.trace, indent=2), encoding="utf-8")
    return midi_target, trace_target


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate IPM Study #002")
    parser.add_argument("--seed", type=int, default=2026081702)
    parser.add_argument("--midi", default="examples/study-002.mid")
    parser.add_argument("--trace", default="examples/study-002.trace.json")
    args = parser.parse_args(argv)
    result = compose_study_002(IPMConfig(seed=args.seed, tempo_bpm=108))
    write_study_002_files(result, midi_path=args.midi, trace_path=args.trace)
    if not result.trace["validation"]["passed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

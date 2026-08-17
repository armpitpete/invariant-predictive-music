"""End-to-end deterministic 16-bar IPM reference study."""

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
from .sonority import score_texture, set_coherence, slice_active_sonorities

_MAJOR_SCALE = (0, 2, 4, 5, 7, 9, 11)
_SEED_SHAPE = (0, 2, 3, 1)
_FINAL_SHAPE = (0, 2, 3, 0)
_DURATIONS = (Fraction(1), Fraction(1), Fraction(2), Fraction(4))
_ROOT_PLAN = (0, 1, 3, 4, 5, 4, 1, 0)
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
_BR_OPPORTUNITIES = {
    1: frozenset({0, 2}),
    2: frozenset({1, 2}),
    3: frozenset({0, 3}),
    4: frozenset({0, 2, 3}),
    5: frozenset({0, 2}),
    6: frozenset({1, 2}),
}
_BH_OPPORTUNITIES = {4: frozenset({2, 3})}


@dataclass(frozen=True, slots=True)
class StudyResult:
    """One complete deterministic IPM study and its inspectable decision trace."""

    config: IPMConfig
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


def _degree_to_midi(degree: int, tonic_midi: int) -> int:
    octave, scale_index = divmod(degree, len(_MAJOR_SCALE))
    pitch = tonic_midi + 12 * octave + _MAJOR_SCALE[scale_index]
    if not 0 <= pitch <= 127:
        raise ValueError("generated pitch is outside the MIDI range")
    return pitch


def _midi_to_degree(pitch: int, tonic_midi: int) -> int:
    octave, pitch_class = divmod(pitch - tonic_midi, 12)
    try:
        scale_index = _MAJOR_SCALE.index(pitch_class)
    except ValueError as exc:
        raise ValueError("study pitch is outside the major-scale reference world") from exc
    return octave * len(_MAJOR_SCALE) + scale_index


def _nearest_degree_octave(base_degree: int, target_pitch: int, tonic_midi: int) -> int:
    candidates: list[tuple[int, int]] = []
    for octave in range(-4, 5):
        degree = base_degree + 7 * octave
        try:
            pitch = _degree_to_midi(degree, tonic_midi)
        except ValueError:
            continue
        candidates.append((degree, pitch))
    if not candidates:
        raise ValueError("no in-range octave is available for the planned scale degree")
    return min(candidates, key=lambda item: abs(item[1] - target_pitch))[0]


def _events_from_shape(
    *,
    root_degree: int,
    start: Beat,
    shape: Sequence[int],
    tonic_midi: int,
    velocity: int,
) -> tuple[NoteEvent, ...]:
    if len(shape) != len(_DURATIONS):
        raise ValueError("study motif shape must contain four notes")
    events: list[NoteEvent] = []
    cursor = start
    for offset, duration in zip(shape, _DURATIONS, strict=True):
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


def seed_motif(tonic_midi: int = 60) -> tuple[NoteEvent, ...]:
    """Return scale degrees 1-3-4-2 with duration ratio 1:1:2:4."""

    return _events_from_shape(
        root_degree=0,
        start=Fraction(0),
        shape=_SEED_SHAPE,
        tonic_midi=tonic_midi,
        velocity=88,
    )


def _phase_probabilities(
    phase: StructuralPhase,
) -> tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]]:
    # Explicit study priors, not claims about universal listener probabilities.
    if phase in (StructuralPhase.OPENING, StructuralPhase.ENDING):
        return (
            (0.78, 0.76, 0.80, 0.82),
            (0.32, 0.12, 0.14, 0.16),
            (0.18, 0.08, 0.10, 0.12),
        )
    if phase is StructuralPhase.ESTABLISHMENT:
        return (
            (0.74, 0.72, 0.76, 0.78),
            (0.30, 0.62, 0.68, 0.72),
            (0.20, 0.55, 0.62, 0.66),
        )
    if phase is StructuralPhase.DEVELOPMENT:
        return (
            (0.70, 0.68, 0.72, 0.74),
            (0.28, 0.78, 0.82, 0.86),
            (0.18, 0.72, 0.76, 0.80),
        )
    if phase is StructuralPhase.CLIMAX:
        return (
            (0.68, 0.66, 0.70, 0.72),
            (0.22, 0.84, 0.88, 0.90),
            (0.14, 0.78, 0.82, 0.86),
        )
    return (
        (0.76, 0.76, 0.80, 0.84),
        (0.30, 0.50, 0.55, 0.62),
        (0.18, 0.42, 0.48, 0.55),
    )


def _main_futures(
    *,
    chunk_index: int,
    start: Beat,
    previous_pitch: int | None,
    tonic_midi: int,
) -> tuple[MainFuture, MainFuture, MainFuture]:
    phase = _PHASES[chunk_index]
    base_degree = _ROOT_PLAN[chunk_index]
    expected_root = (
        base_degree
        if previous_pitch is None
        else _nearest_degree_octave(base_degree, previous_pitch, tonic_midi)
    )

    revealing_shift = (
        2
        if phase
        in (
            StructuralPhase.ESTABLISHMENT,
            StructuralPhase.DEVELOPMENT,
            StructuralPhase.CLIMAX,
        )
        else -2
    )
    revealing_base = base_degree + revealing_shift
    revealing_root = (
        revealing_base
        if previous_pitch is None
        else _nearest_degree_octave(revealing_base, previous_pitch, tonic_midi)
    )
    exploratory_base = base_degree + 1
    exploratory_root = (
        exploratory_base
        if previous_pitch is None
        else _nearest_degree_octave(exploratory_base, previous_pitch, tonic_midi)
    )

    expected_shape = _FINAL_SHAPE if chunk_index == len(_ROOT_PLAN) - 1 else _SEED_SHAPE
    exploratory_shape = (0, 3, 4, 1) if chunk_index % 2 == 0 else (0, 2, 4, 1)
    expected_p, revealing_p, exploratory_p = _phase_probabilities(phase)

    return (
        MainFuture(
            MainBranchKind.EXPECTED,
            _events_from_shape(
                root_degree=expected_root,
                start=start,
                shape=expected_shape,
                tonic_midi=tonic_midi,
                velocity=88,
            ),
            expected_p,
        ),
        MainFuture(
            MainBranchKind.REVEALING,
            _events_from_shape(
                root_degree=revealing_root,
                start=start,
                shape=_SEED_SHAPE,
                tonic_midi=tonic_midi,
                velocity=88,
            ),
            revealing_p,
        ),
        MainFuture(
            MainBranchKind.EXPLORATORY,
            _events_from_shape(
                root_degree=exploratory_root,
                start=start,
                shape=exploratory_shape,
                tonic_midi=tonic_midi,
                velocity=88,
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


def _response_candidates(
    *,
    main_event: NoteEvent,
    chunk_index: int,
    event_index: int,
    tonic_midi: int,
) -> tuple[SubsidiaryCandidate, ...]:
    candidates: list[SubsidiaryCandidate] = [
        SubsidiaryCandidate(CandidateAction.SILENCE)
    ]
    if event_index not in _BR_OPPORTUNITIES.get(chunk_index, frozenset()):
        return tuple(candidates)

    main_degree = _midi_to_degree(main_event.pitch, tonic_midi)
    steps = (-2, -4) if main_event.pitch >= tonic_midi + 12 else (2, 4)
    for offset in steps:
        candidates.append(
            SubsidiaryCandidate(
                CandidateAction.NOTE,
                NoteEvent(
                    onset=main_event.onset,
                    duration=main_event.duration,
                    pitch=_degree_to_midi(main_degree + offset, tonic_midi),
                    velocity=68,
                ),
            )
        )
    return tuple(candidates)


def _active_pitch(voice: Voice, start: Beat, end: Beat) -> int | None:
    for event in reversed(voice.events):
        if event.onset <= start and event.end >= end:
            return event.pitch
    return None


def _harmony_candidates(
    *,
    main_event: NoteEvent,
    response: Voice,
    chunk_index: int,
    event_index: int,
    tonic_midi: int,
) -> tuple[SubsidiaryCandidate, ...]:
    candidates: list[SubsidiaryCandidate] = [
        SubsidiaryCandidate(CandidateAction.SILENCE)
    ]
    if event_index not in _BH_OPPORTUNITIES.get(chunk_index, frozenset()):
        return tuple(candidates)

    active_pitches = [main_event.pitch]
    response_pitch = _active_pitch(response, main_event.onset, main_event.end)
    if response_pitch is not None:
        active_pitches.append(response_pitch)

    support: list[tuple[float, int, int]] = []
    for degree in range(-7, 15):
        pitch = _degree_to_midi(degree, tonic_midi)
        if pitch >= main_event.pitch - 2:
            continue
        support.append(
            (
                set_coherence((*active_pitches, pitch)),
                -abs(pitch - (tonic_midi - 5)),
                pitch,
            )
        )

    for _, _, pitch in sorted(support, reverse=True)[:4]:
        candidates.append(
            SubsidiaryCandidate(
                CandidateAction.NOTE,
                NoteEvent(
                    onset=main_event.onset,
                    duration=main_event.duration,
                    pitch=pitch,
                    velocity=58,
                ),
            )
        )
    return tuple(candidates)


def _counter_decision_json(
    *,
    voice: str,
    chunk_index: int,
    event_index: int,
    phase: StructuralPhase,
    decision: CandidateDecision,
) -> dict[str, Any]:
    selected_note = decision.selected.candidate.note
    return {
        "voice": voice,
        "chunk": chunk_index,
        "event_index": event_index,
        "phase": phase.value,
        "selected_action": decision.selected.candidate.action.value,
        "selected_pitch": selected_note.pitch if selected_note is not None else None,
        "selected_score": decision.selected.total,
        "silence_score": decision.silence.total if decision.silence is not None else None,
        "candidates": [
            {
                "action": score.candidate.action.value,
                "pitch": score.candidate.note.pitch if score.candidate.note is not None else None,
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


def _apply_counter_decision(decision: CandidateDecision, voice: Voice) -> None:
    if decision.selected.candidate.action is CandidateAction.NOTE:
        assert decision.selected.candidate.note is not None
        voice.add(decision.selected.candidate.note)


def _texture_metrics(voices: Sequence[Voice]) -> dict[str, Any]:
    texture_beats: dict[str, Beat] = defaultdict(lambda: Fraction(0))
    order = {"M": 0, "B_R": 1, "B_H": 2}
    for sonority in slice_active_sonorities(voices):
        active_names = sorted({note.voice for note in sonority.notes}, key=order.__getitem__)
        texture_beats["+".join(active_names)] += sonority.duration

    score = score_texture(voices)
    total = sum(texture_beats.values(), Fraction(0))
    return {
        "total_beats": _beat_json(total),
        "texture_beats": {
            name: _beat_json(duration) for name, duration in sorted(texture_beats.items())
        },
        "texture_ratio": {
            name: float(duration / total) if total else 0.0
            for name, duration in sorted(texture_beats.items())
        },
        "vertical_weighted_mean": score.weighted_mean,
        "vertical_minimum": score.minimum,
        "sonority_slices": score.slices,
    }


def _validation(
    *,
    config: IPMConfig,
    main: Voice,
    response: Voice,
    harmony: Voice,
    metrics: dict[str, Any],
    tonic_midi: int,
) -> dict[str, Any]:
    total_beats = Fraction(config.bars * config.beats_per_bar)
    texture = metrics["texture_ratio"]
    main_alone = texture.get("M", 0.0)
    other_ratios = [ratio for name, ratio in texture.items() if name != "M"]
    triple = texture.get("M+B_R+B_H", 0.0)

    checks = {
        "exact_length": main.cursor == total_beats,
        "responsive_voice_present": bool(response.events),
        "harmonic_voice_present": bool(harmony.events),
        "main_alone_is_most_common_texture": bool(other_ratios)
        and main_alone > max(other_ratios),
        "three_voice_texture_is_exceptional": 0.0 < triple <= 0.125,
        "vertical_floor": metrics["vertical_minimum"] >= 0.65,
        "final_tonic": bool(main.events)
        and main.events[-1].pitch % 12 == tonic_midi % 12,
    }
    return {"passed": all(checks.values()), "checks": checks}


def compose_study(
    config: IPMConfig | None = None,
    *,
    tonic_midi: int = 60,
) -> StudyResult:
    """Compose study #001: 16 bars, three voices, one deterministic seed."""

    config = config or IPMConfig(seed=20260817)
    if config.bars != 16 or config.beats_per_bar != 4:
        raise ValueError("study #001 is fixed at 16 bars of 4/4")
    if not 0 <= tonic_midi <= 127:
        raise ValueError("tonic_midi must be in 0..127")

    rng = SeededRandom(config.seed)
    reference = seed_motif(tonic_midi)
    main = Voice("M")
    main_trace: list[dict[str, Any]] = []
    previous_pitch: int | None = None

    for chunk_index, phase in enumerate(_PHASES):
        start = Fraction(chunk_index * 8)
        futures = _main_futures(
            chunk_index=chunk_index,
            start=start,
            previous_pitch=previous_pitch,
            tonic_midi=tonic_midi,
        )
        decision = choose_main_future(futures, reference_motif=reference, rng=rng)
        for event in decision.selected.future.events:
            main.add(event)
        previous_pitch = decision.selected.future.events[-1].pitch
        entry = _main_score_json(decision)
        entry.update(
            {
                "chunk": chunk_index,
                "phase": phase.value,
                "window": [_beat_json(start), _beat_json(start + 8)],
            }
        )
        main_trace.append(entry)

    response = Voice("B_R")
    harmony = Voice("B_H")
    counter_trace: list[dict[str, Any]] = []
    # Study #001 permits sparse harmonic entries without a separate attack tax.
    # They still must beat silence and satisfy the harmony vertical floor.
    counter_policy = CountervoicePolicy(harmony_attack_cost=0.0)

    for chunk_index, phase in enumerate(_PHASES):
        for event_index in range(4):
            main_event = main.events[chunk_index * 4 + event_index]

            response_decision = choose_candidate(
                _response_candidates(
                    main_event=main_event,
                    chunk_index=chunk_index,
                    event_index=event_index,
                    tonic_midi=tonic_midi,
                ),
                role=SubsidiaryRole.RESPONSE,
                target_voice=response,
                frozen_voices=(main,),
                start=main_event.onset,
                end=main_event.end,
                phase=phase,
                rng=rng,
                beats_per_bar=config.beats_per_bar,
                policy=counter_policy,
            )
            _apply_counter_decision(response_decision, response)
            counter_trace.append(
                _counter_decision_json(
                    voice="B_R",
                    chunk_index=chunk_index,
                    event_index=event_index,
                    phase=phase,
                    decision=response_decision,
                )
            )

            harmony_decision = choose_candidate(
                _harmony_candidates(
                    main_event=main_event,
                    response=response,
                    chunk_index=chunk_index,
                    event_index=event_index,
                    tonic_midi=tonic_midi,
                ),
                role=SubsidiaryRole.HARMONY,
                target_voice=harmony,
                frozen_voices=(main, response),
                start=main_event.onset,
                end=main_event.end,
                phase=phase,
                rng=rng,
                beats_per_bar=config.beats_per_bar,
                policy=counter_policy,
            )
            _apply_counter_decision(harmony_decision, harmony)
            counter_trace.append(
                _counter_decision_json(
                    voice="B_H",
                    chunk_index=chunk_index,
                    event_index=event_index,
                    phase=phase,
                    decision=harmony_decision,
                )
            )

    metrics = _texture_metrics((main, response, harmony))
    validation = _validation(
        config=config,
        main=main,
        response=response,
        harmony=harmony,
        metrics=metrics,
        tonic_midi=tonic_midi,
    )
    trace = {
        "model": "IPM",
        "study": "001",
        "seed": config.seed,
        "tempo_bpm": config.tempo_bpm,
        "bars": config.bars,
        "beats_per_bar": config.beats_per_bar,
        "tonic_midi": tonic_midi,
        "seed_motif": [_event_json(event) for event in reference],
        "main_decisions": main_trace,
        "counter_decisions": counter_trace,
        "voices": {
            main.name: [_event_json(event) for event in main.events],
            response.name: [_event_json(event) for event in response.events],
            harmony.name: [_event_json(event) for event in harmony.events],
        },
        "metrics": metrics,
        "validation": validation,
    }
    return StudyResult(config, main, response, harmony, trace)


def write_study_files(
    result: StudyResult,
    *,
    midi_path: str | Path,
    trace_path: str | Path,
) -> tuple[Path, Path]:
    """Write the audible MIDI study and complete machine-readable decision trace."""

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
    parser = argparse.ArgumentParser(description="Generate deterministic IPM study #001")
    parser.add_argument("--seed", type=int, default=20260817)
    parser.add_argument("--tempo", type=int, default=88)
    parser.add_argument("--midi", default="examples/study-001.mid")
    parser.add_argument("--trace", default="examples/study-001.trace.json")
    args = parser.parse_args(argv)

    result = compose_study(IPMConfig(seed=args.seed, tempo_bpm=args.tempo))
    midi_path, trace_path = write_study_files(
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

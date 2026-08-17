"""IPM v0.2 consolidated Tune/Bass/Rhythm instrument.

The numbered studies remain historical evidence.  This module is the current
instrument: it composes directly from reusable primitives, exposes musical
controls, and restores the falsifiable prediction/surprise/invariant gate at
the Tune decision layer.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from fractions import Fraction
from math import e, exp, log2
from pathlib import Path
from typing import Any, Iterable, Sequence

from .bar_rhythm import BarCellKind
from .lanes import BASS_LANE, RHYTHM_LANE, TUNE_LANE, LaneSpec, ScaleWorld
from .midi import render_midi
from .micro_rhythm import realise_micro_bar
from .model import Beat, NoteEvent, Voice
from .patterns import PatternBank, capture_pattern, realise_pattern
from .randomness import SeededRandom
from .sequential_bar import (
    MusicalState,
    WholeBarCandidate,
    WholeBarScore,
    advance_state,
    propose_whole_bar,
    score_whole_bar,
)
from .sonority import interval_prior, score_texture, set_coherence


class ExperimentMode(str, Enum):
    PREDICTABLE = "predictable"
    IPM = "ipm"
    UNSTRUCTURED_SURPRISE = "unstructured-surprise"


@dataclass(frozen=True, slots=True)
class BassControls:
    """User-facing bass behaviour. All continuous controls are in 0..1."""

    activity: float = 0.72
    sustain: float = 0.62
    movement: float = 0.30
    pattern_complexity: float = 0.42
    gate: float = 0.88

    def __post_init__(self) -> None:
        _validate_unit_controls(self)


@dataclass(frozen=True, slots=True)
class RhythmControls:
    """User-facing pitched-rhythm behaviour."""

    activity: float = 0.68
    complexity: float = 0.56
    syncopation: float = 0.42
    gate: float = 0.75

    def __post_init__(self) -> None:
        _validate_unit_controls(self)


@dataclass(frozen=True, slots=True)
class PatternLockSpec:
    """Repeat one learned subsidiary pattern over an inclusive bar window."""

    lane: str
    source_bar: int
    start_bar: int
    end_bar: int

    def __post_init__(self) -> None:
        if self.lane not in {BASS_LANE.name, RHYTHM_LANE.name}:
            raise ValueError("v0.2 pattern locks are supported for BASS and RHYTHM")
        if min(self.source_bar, self.start_bar, self.end_bar) < 0:
            raise ValueError("pattern-lock bars must be non-negative")
        if self.end_bar < self.start_bar:
            raise ValueError("pattern-lock end_bar must be >= start_bar")


@dataclass(frozen=True, slots=True)
class InstrumentConfig:
    """Current IPM instrument configuration."""

    seed: int = 2026081704
    tempo_bpm: int = 58
    bars: int = 16
    beats_per_bar: int = 4
    tonic_midi: int = 60
    mode: ExperimentMode = ExperimentMode.IPM
    tune_alternatives: int = 18
    bass: BassControls = field(default_factory=BassControls)
    rhythm: RhythmControls = field(default_factory=RhythmControls)
    pattern_locks: tuple[PatternLockSpec, ...] = ()

    def __post_init__(self) -> None:
        if self.tempo_bpm <= 0:
            raise ValueError("tempo_bpm must be positive")
        if self.bars <= 0:
            raise ValueError("bars must be positive")
        if self.beats_per_bar != 4:
            raise ValueError("v0.2 currently fixes the structural bar at 4/4")
        if self.tune_alternatives < 9:
            raise ValueError("tune_alternatives must be >= 9 for meaningful branch competition")
        ScaleWorld(self.tonic_midi)
        for lock in self.pattern_locks:
            if max(lock.source_bar, lock.start_bar, lock.end_bar) >= self.bars:
                raise ValueError("pattern-lock bar escapes configured form")


@dataclass(frozen=True, slots=True)
class InstrumentResult:
    config: InstrumentConfig
    tune: Voice
    bass: Voice
    rhythm: Voice
    trace: dict[str, Any]

    @property
    def voices(self) -> tuple[Voice, Voice, Voice]:
        return self.tune, self.bass, self.rhythm


@dataclass(frozen=True, slots=True)
class PredictiveBarScore:
    candidate: WholeBarCandidate
    base: WholeBarScore
    probability: float
    surprise_bits: float
    calibrated_surprise: float
    invariant_similarity: float
    retrospective_coherence: float
    retrospective_necessity: float
    ipm_score: float


def _validate_unit_controls(value: Any) -> None:
    for name, control in asdict(value).items():
        if not 0.0 <= control <= 1.0:
            raise ValueError(f"{name} must be in 0..1")


def _fraction_json(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def _event_json(event: NoteEvent) -> dict[str, Any]:
    return {
        "pitch": event.pitch,
        "onset": _fraction_json(event.onset),
        "duration": _fraction_json(event.duration),
        "velocity": event.velocity,
    }


def _phase_for_bar(bar: int, bars: int) -> str:
    position = (bar + 0.5) / bars
    if bar == 0:
        return "opening"
    if bar == bars - 1:
        return "ending"
    if position < 0.31:
        return "establishment"
    if position < 0.66:
        return "development"
    if position < 0.78:
        return "climax"
    return "resolution"


def _softmax_probabilities(scores: Sequence[float], temperature: float = 0.08) -> tuple[float, ...]:
    peak = max(scores)
    weights = [exp((score - peak) / temperature) for score in scores]
    total = sum(weights)
    return tuple(weight / total for weight in weights)


def _calibrated_surprise(probability: float, decay: float = 0.5) -> float:
    surprise = -log2(max(probability, 1e-12))
    if surprise == 0:
        return 0.0
    return decay * e * surprise * exp(-decay * surprise)


def _direction(value: int) -> int:
    return 1 if value > 0 else -1 if value < 0 else 0


def _bar_invariant_similarity(state: MusicalState, candidate: WholeBarCandidate) -> float:
    """Compare candidate with recently learned pitch/rhythm invariants.

    This deliberately ignores absolute pitch so transposition and harmonic
    re-anchoring can preserve identity.
    """

    intervals = candidate.intervals
    if state.recent_intervals and intervals:
        recent = state.recent_intervals[-len(intervals):]
        n = min(len(recent), len(intervals))
        contour = sum(
            _direction(left) == _direction(right)
            for left, right in zip(recent[-n:], intervals[-n:], strict=True)
        ) / n
        recent_sizes = {abs(value) for value in state.recent_intervals[-12:]}
        vocabulary = sum(abs(value) in recent_sizes for value in intervals) / len(intervals)
    else:
        contour = 0.65
        vocabulary = 0.65

    if state.previous_attacks is None:
        attack_shape = 0.75
    else:
        attack_shape = exp(-abs(candidate.pattern.attacks - state.previous_attacks) / 1.5)

    if state.previous_rest_fraction is None:
        rest_shape = 0.75
    else:
        rest_shape = exp(
            -abs(candidate.pattern.rest_fraction - state.previous_rest_fraction) / 0.22
        )

    return 0.34 * contour + 0.28 * vocabulary + 0.22 * attack_shape + 0.16 * rest_shape


def _score_predictive_pool(
    candidates: Sequence[WholeBarCandidate],
    *,
    state: MusicalState,
    phase: str,
    tonic_midi: int,
    final_bar: bool,
) -> tuple[PredictiveBarScore, ...]:
    bases = tuple(
        score_whole_bar(
            candidate,
            state=state,
            phase=phase,
            tonic_midi=tonic_midi,
            final_bar=final_bar,
        )
        for candidate in candidates
    )
    probabilities = _softmax_probabilities([base.total for base in bases])
    result: list[PredictiveBarScore] = []
    for candidate, base, probability in zip(candidates, bases, probabilities, strict=True):
        invariant = _bar_invariant_similarity(state, candidate)
        surprise = -log2(max(probability, 1e-12))
        calibrated = _calibrated_surprise(probability)
        retrospective = (
            0.50 * invariant
            + 0.32 * base.phrase_direction
            + 0.18 * base.cadence
        )
        necessity = (1.0 - probability) * retrospective
        ipm_score = (
            0.32 * base.total
            + 0.28 * invariant
            + 0.22 * necessity
            + 0.18 * calibrated
        )
        result.append(
            PredictiveBarScore(
                candidate=candidate,
                base=base,
                probability=probability,
                surprise_bits=surprise,
                calibrated_surprise=calibrated,
                invariant_similarity=invariant,
                retrospective_coherence=retrospective,
                retrospective_necessity=necessity,
                ipm_score=ipm_score,
            )
        )
    return tuple(result)


def _choose_predictive_bar(
    scored: Sequence[PredictiveBarScore],
    *,
    mode: ExperimentMode,
) -> tuple[PredictiveBarScore, str, dict[str, Any]]:
    expected = max(scored, key=lambda item: (item.probability, item.base.total))
    surprising = [item for item in scored if item is not expected]

    revealing_pool = [
        item for item in surprising
        if item.invariant_similarity >= 0.58
        and item.probability < expected.probability
    ]
    revealing = max(
        revealing_pool,
        key=lambda item: (item.ipm_score, item.invariant_similarity),
        default=None,
    )

    exploratory_pool = [
        item for item in surprising
        if 0.20 <= item.invariant_similarity < 0.58
        and item.probability < expected.probability
    ]
    exploratory = max(
        exploratory_pool,
        key=lambda item: (item.calibrated_surprise, item.base.total),
        default=None,
    )

    ipm_candidates = [
        item for item in (revealing, exploratory)
        if item is not None and item.ipm_score > expected.ipm_score
    ]
    ipm_selected = max(ipm_candidates, key=lambda item: item.ipm_score, default=expected)

    if mode is ExperimentMode.PREDICTABLE:
        selected, branch = expected, "expected"
    elif mode is ExperimentMode.IPM:
        selected = ipm_selected
        branch = (
            "expected" if selected is expected
            else "revealing" if selected is revealing
            else "exploratory"
        )
    else:
        target_surprise = ipm_selected.surprise_bits
        controls = [
            item for item in surprising
            if item.base.total >= expected.base.total - 0.18
        ] or surprising
        selected = min(
            controls,
            key=lambda item: (
                abs(item.surprise_bits - target_surprise),
                item.invariant_similarity,
                -item.base.total,
            ),
        )
        branch = "unstructured-surprise"

    gate = {
        "expected_probability": expected.probability,
        "expected_ipm_score": expected.ipm_score,
        "revealing_available": revealing is not None,
        "exploratory_available": exploratory is not None,
        "ipm_would_select": (
            "expected" if ipm_selected is expected
            else "revealing" if ipm_selected is revealing
            else "exploratory"
        ),
        "selected_branch": branch,
    }
    return selected, branch, gate


def _compose_tune(
    config: InstrumentConfig,
    *,
    world: ScaleWorld,
) -> tuple[Voice, list[dict[str, Any]]]:
    rng = SeededRandom(config.seed ^ 0xA20)
    micro_rng = SeededRandom(config.seed ^ 0xA21)
    state = MusicalState()
    tune = Voice("TUNE")
    trace: list[dict[str, Any]] = []

    for bar in range(config.bars):
        phase = _phase_for_bar(bar, config.bars)
        candidates = tuple(
            propose_whole_bar(
                rng=rng,
                phase=phase,
                state=state,
                tonic_midi=world.tonic_midi,
                final_bar=bar == config.bars - 1,
            )
            for _ in range(config.tune_alternatives)
        )
        scored = _score_predictive_pool(
            candidates,
            state=state,
            phase=phase,
            tonic_midi=world.tonic_midi,
            final_bar=bar == config.bars - 1,
        )
        selected, branch, gate = _choose_predictive_bar(scored, mode=config.mode)

        cells = tuple((cell.kind, cell.duration) for cell in selected.candidate.pattern.cells)
        events, micro = realise_micro_bar(
            cells,
            selected.candidate.pitches,
            start=Fraction(bar * config.beats_per_bar),
            phase=phase,
            rng=micro_rng,
            tonic_midi=world.tonic_midi,
        )
        for event in events:
            tune.add(event)

        alternatives = sorted(scored, key=lambda item: item.probability, reverse=True)
        trace.append(
            {
                "bar": bar,
                "phase": phase,
                "mode": config.mode.value,
                "selected_branch": branch,
                "selected": {
                    "probability": selected.probability,
                    "surprise_bits": selected.surprise_bits,
                    "invariant_similarity": selected.invariant_similarity,
                    "retrospective_coherence": selected.retrospective_coherence,
                    "retrospective_necessity": selected.retrospective_necessity,
                    "base_score": selected.base.total,
                    "ipm_score": selected.ipm_score,
                    "events": [_event_json(event) for event in events],
                },
                "gate": gate,
                "alternatives": [
                    {
                        "probability": item.probability,
                        "surprise_bits": item.surprise_bits,
                        "invariant_similarity": item.invariant_similarity,
                        "retrospective_necessity": item.retrospective_necessity,
                        "base_score": item.base.total,
                        "ipm_score": item.ipm_score,
                        "attacks": item.candidate.pattern.attacks,
                    }
                    for item in alternatives
                ],
                "micro_rhythm": [
                    {
                        "onset": _fraction_json(item.onset),
                        "structural_duration": _fraction_json(item.structural_duration),
                        "segments": [_fraction_json(value) for value in item.segments],
                    }
                    for item in micro
                ],
            }
        )
        state = advance_state(state, selected.candidate)

    return tune, trace


def _overlapping(events: Iterable[NoteEvent], start: Beat, end: Beat) -> tuple[NoteEvent, ...]:
    return tuple(event for event in events if event.onset < end and event.end > start)


def _overlap_weight(event: NoteEvent, start: Beat, end: Beat) -> float:
    return max(0.0, float(min(event.end, end) - max(event.onset, start)))


def _degree_distance(left: int, right: int, size: int = 7) -> int:
    raw = abs((left % size) - (right % size))
    return min(raw, size - raw)


def _bass_pattern(
    controls: BassControls,
    *,
    phase: str,
    rng: SeededRandom,
) -> tuple[Beat, ...]:
    """Turn sustain/complexity into a bar time-budget vocabulary."""

    phase_motion = 0.16 if phase in {"development", "climax"} else 0.0
    density = (1.0 - controls.sustain) * 0.72 + controls.pattern_complexity * 0.28 + phase_motion
    roll = rng.random()
    if density < 0.24:
        return (Fraction(4),)
    if density < 0.50:
        return (Fraction(2), Fraction(2))
    if density < 0.76:
        return (
            (Fraction(1), Fraction(1), Fraction(2))
            if roll < 0.5
            else (Fraction(2), Fraction(1), Fraction(1))
        )
    return (Fraction(1), Fraction(1), Fraction(1), Fraction(1))


def _bass_score(
    degree: int,
    pitch: int,
    tune_events: Sequence[NoteEvent],
    *,
    start: Beat,
    end: Beat,
    previous_degree: int | None,
    controls: BassControls,
    final: bool,
) -> float:
    if tune_events:
        weights = [_overlap_weight(event, start, end) for event in tune_events]
        denominator = sum(weights)
        vertical = (
            sum(
                weight * interval_prior(pitch, event.pitch)
                for event, weight in zip(tune_events, weights, strict=True)
            ) / denominator
            if denominator
            else 1.0
        )
    else:
        vertical = 1.0

    continuity = (
        1.0 if previous_degree is None
        else exp(-_degree_distance(degree, previous_degree) / (0.8 + 2.8 * controls.movement))
    )
    motion_reward = (
        0.72 if previous_degree is None
        else min(1.0, _degree_distance(degree, previous_degree) / 2.0)
    )
    tonic = 1.0 if degree % 7 == 0 else 0.70
    if final:
        tonic = 1.0 if degree % 7 == 0 else 0.0
    return (
        0.58 * vertical
        + 0.18 * ((1.0 - controls.movement) * continuity + controls.movement * motion_reward)
        + 0.14 * tonic
        + 0.10 * controls.sustain
    )


def _compose_bass(
    config: InstrumentConfig,
    tune: Voice,
    *,
    world: ScaleWorld,
) -> tuple[Voice, list[dict[str, Any]]]:
    rng = SeededRandom(config.seed ^ 0xB20)
    bass = Voice("BASS")
    trace: list[dict[str, Any]] = []
    previous_degree: int | None = None

    for bar in range(config.bars):
        phase = _phase_for_bar(bar, config.bars)
        pattern = _bass_pattern(config.bass, phase=phase, rng=rng)
        cursor = Fraction(bar * config.beats_per_bar)
        decisions: list[dict[str, Any]] = []

        for segment_index, span in enumerate(pattern):
            start, end = cursor, cursor + span
            tune_events = _overlapping(tune.events, start, end)
            if tune_events:
                anchor_event = max(tune_events, key=lambda event: (event.end, event.onset))
                anchor = world.degree_class(world.degree_from_pitch(anchor_event.pitch))
            else:
                anchor = previous_degree if previous_degree is not None else 0

            degrees = sorted({anchor, anchor - 2, anchor - 4, 0, 4})
            final = bar == config.bars - 1 and segment_index == len(pattern) - 1
            candidates: list[tuple[float, int, int]] = []
            for degree in degrees:
                degree = world.degree_class(degree)
                pitch = world.project_degree(degree, BASS_LANE)
                candidates.append(
                    (
                        _bass_score(
                            degree,
                            pitch,
                            tune_events,
                            start=start,
                            end=end,
                            previous_degree=previous_degree,
                            controls=config.bass,
                            final=final,
                        ),
                        degree,
                        pitch,
                    )
                )

            best = max(candidates, key=lambda item: item[0])
            silence_score = 0.86 - 0.32 * config.bass.activity
            accepted = best[0] > silence_score
            if accepted:
                _, degree, pitch = best
                event = NoteEvent(
                    onset=start,
                    duration=span * Fraction(max(1, round(config.bass.gate * 64)), 64),
                    pitch=pitch,
                    velocity=64 if phase == "climax" else 58,
                )
                bass.add(event)
                previous_degree = degree
            decisions.append(
                {
                    "segment": segment_index,
                    "span": _fraction_json(span),
                    "silence_score": silence_score,
                    "best_note_score": best[0],
                    "accepted": accepted,
                    "selected_degree": best[1] if accepted else None,
                    "selected_pitch": best[2] if accepted else None,
                }
            )
            cursor = end
        trace.append(
            {
                "bar": bar,
                "phase": phase,
                "pattern": [_fraction_json(span) for span in pattern],
                "decisions": decisions,
            }
        )

    return bass, trace


_RHYTHM_PATTERNS: tuple[tuple[Fraction, ...], ...] = (
    (Fraction(0), Fraction(1, 4), Fraction(1, 2), Fraction(3, 4)),
    (Fraction(0), Fraction(1, 2), Fraction(3, 4), Fraction(5, 4)),
    (Fraction(0), Fraction(1, 4), Fraction(3, 4), Fraction(1)),
    (Fraction(0), Fraction(1, 2), Fraction(1), Fraction(3, 2)),
    (Fraction(1, 4), Fraction(3, 4), Fraction(5, 4), Fraction(7, 4)),
)
_RHYTHM_CONTOURS: tuple[tuple[int, ...], ...] = (
    (0, 2, 4, 2),
    (0, 4, 2, 4),
    (4, 2, 0, 2),
    (0, 2, 0, 4),
    (0, 1, 3, 1),
)


def _active_pitch(voice: Voice, onset: Beat) -> int | None:
    for event in reversed(voice.events):
        if event.onset <= onset < event.end:
            return event.pitch
        if event.end <= onset:
            break
    return None


def _rhythm_candidate(
    *,
    world: ScaleWorld,
    tune: Voice,
    bass: Voice,
    bar: int,
    pattern: Sequence[Fraction],
    contour: Sequence[int],
    start_offset: Beat,
    controls: RhythmControls,
) -> tuple[float, tuple[NoteEvent, ...], int]:
    bar_start = Fraction(bar * 4)
    start = bar_start + start_offset
    bass_pitch = _active_pitch(bass, start)
    if bass_pitch is not None:
        anchor = world.lane_degree(bass_pitch, BASS_LANE)
    else:
        tune_pitch = _active_pitch(tune, start)
        anchor = world.degree_class(world.degree_from_pitch(tune_pitch)) if tune_pitch is not None else 0

    events: list[NoteEvent] = []
    verticals: list[float] = []
    gate = Fraction(max(1, round(controls.gate * 16)), 16)
    for relative_onset, degree_offset in zip(pattern, contour, strict=True):
        onset = start + relative_onset
        pitch = world.project_degree(anchor + degree_offset, RHYTHM_LANE)
        active = [
            value
            for value in (_active_pitch(tune, onset), _active_pitch(bass, onset))
            if value is not None
        ]
        verticals.append(set_coherence((*active, pitch)) if active else 1.0)
        events.append(
            NoteEvent(
                onset=onset,
                duration=Fraction(1, 4) * gate,
                pitch=pitch,
                velocity=57 if len(events) % 2 == 0 else 53,
            )
        )
    variety = len({event.pitch for event in events}) / len(events)
    sync = sum((event.onset * 2).denominator == 2 for event in events) / len(events)
    score = (
        0.70 * (sum(verticals) / len(verticals))
        + 0.18 * variety
        + 0.12 * ((1.0 - controls.syncopation) * (1.0 - sync) + controls.syncopation * sync)
    )
    return score, tuple(events), anchor


def _compose_rhythm(
    config: InstrumentConfig,
    tune: Voice,
    bass: Voice,
    *,
    world: ScaleWorld,
) -> tuple[Voice, list[dict[str, Any]]]:
    rng = SeededRandom(config.seed ^ 0xC20)
    rhythm = Voice("RHYTHM")
    trace: list[dict[str, Any]] = []

    for bar in range(config.bars):
        phase = _phase_for_bar(bar, config.bars)
        candidates: list[tuple[float, tuple[NoteEvent, ...], int, int, int, Beat]] = []
        pattern_count = max(2, min(len(_RHYTHM_PATTERNS), 2 + round(3 * config.rhythm.complexity)))
        for pattern_index, pattern in enumerate(_RHYTHM_PATTERNS[:pattern_count]):
            pattern_end = max(pattern) + Fraction(1, 4)
            offsets = (Fraction(0), Fraction(1), Fraction(2))
            for offset in offsets:
                if offset + pattern_end > 4:
                    continue
                for contour_index, contour in enumerate(_RHYTHM_CONTOURS[:pattern_count]):
                    score, events, anchor = _rhythm_candidate(
                        world=world,
                        tune=tune,
                        bass=bass,
                        bar=bar,
                        pattern=pattern,
                        contour=contour,
                        start_offset=offset,
                        controls=config.rhythm,
                    )
                    score += rng.random() * 0.004
                    candidates.append(
                        (score, events, anchor, pattern_index, contour_index, offset)
                    )

        best = max(candidates, key=lambda item: item[0])
        phase_bias = 0.06 if phase in {"development", "climax"} else 0.0
        silence_score = 0.88 - 0.34 * config.rhythm.activity - phase_bias
        accepted = best[0] > silence_score
        if accepted:
            for event in best[1]:
                rhythm.add(event)
        trace.append(
            {
                "bar": bar,
                "phase": phase,
                "silence_score": silence_score,
                "best_note_score": best[0],
                "accepted": accepted,
                "selected": (
                    {
                        "anchor_degree": best[2],
                        "pattern_index": best[3],
                        "contour_index": best[4],
                        "start_offset": _fraction_json(best[5]),
                        "events": [_event_json(event) for event in best[1]],
                    }
                    if accepted
                    else None
                ),
            }
        )
    return rhythm, trace


def _pattern_anchor_score(
    events: Sequence[NoteEvent],
    *,
    other_voices: Sequence[Voice],
) -> float:
    values: list[float] = []
    for event in events:
        active = [
            pitch
            for pitch in (_active_pitch(voice, event.onset) for voice in other_voices)
            if pitch is not None
        ]
        values.append(set_coherence((*active, event.pitch)) if active else 1.0)
    return sum(values) / len(values)


def _apply_locks(
    config: InstrumentConfig,
    tune: Voice,
    bass: Voice,
    rhythm: Voice,
    *,
    world: ScaleWorld,
) -> tuple[Voice, Voice, list[dict[str, Any]]]:
    if not config.pattern_locks:
        return bass, rhythm, []

    bank = PatternBank()
    current = {BASS_LANE.name: bass, RHYTHM_LANE.name: rhythm}
    lanes: dict[str, LaneSpec] = {BASS_LANE.name: BASS_LANE, RHYTHM_LANE.name: RHYTHM_LANE}
    trace: list[dict[str, Any]] = []

    for index, spec in enumerate(config.pattern_locks):
        lane = lanes[spec.lane]
        voice = current[spec.lane]
        start = Fraction(spec.source_bar * 4)
        pattern = capture_pattern(
            tuple(voice.events),
            world=world,
            lane=lane,
            start=start,
            span=Fraction(4),
        )
        name = f"{spec.lane.lower()}-{index}"
        bank.remember(name, pattern)
        bank.lock(lane, name)

        targets = set(range(spec.start_bar, spec.end_bar + 1))
        kept = [
            event for event in voice.events
            if int(event.onset // 4) not in targets
        ]
        applications: list[dict[str, Any]] = []
        other = [tune, rhythm if spec.lane == BASS_LANE.name else bass]
        for bar in range(spec.start_bar, spec.end_bar + 1):
            bar_start = Fraction(bar * 4)
            choices: list[tuple[float, int, tuple[NoteEvent, ...]]] = []
            for anchor in range(world.degrees_per_octave):
                realised = realise_pattern(
                    pattern,
                    world=world,
                    lane=lane,
                    start=bar_start,
                    anchor_degree=anchor,
                    velocity=57,
                )
                choices.append(
                    (_pattern_anchor_score(realised, other_voices=other), anchor, realised)
                )
            score, anchor, realised = max(choices, key=lambda item: (item[0], -item[1]))
            kept.extend(realised)
            applications.append(
                {
                    "bar": bar,
                    "anchor_degree": anchor,
                    "vertical_score": score,
                    "events": [_event_json(event) for event in realised],
                }
            )
        bank.unlock(lane)
        current[spec.lane] = Voice.from_events(spec.lane, kept)
        if spec.lane == BASS_LANE.name:
            bass = current[spec.lane]
        else:
            rhythm = current[spec.lane]
        trace.append(
            {
                "name": name,
                "lane": spec.lane,
                "source_bar": spec.source_bar,
                "target_bars": [spec.start_bar, spec.end_bar],
                "signature": [
                    {
                        "onset": _fraction_json(attack.onset),
                        "duration": _fraction_json(attack.duration),
                        "degree_offset": attack.degree_offset,
                    }
                    for attack in pattern.attacks
                ],
                "applications": applications,
                "unlocked": bank.locked_name(lane) is None,
            }
        )

    return bass, rhythm, trace


def compose(config: InstrumentConfig | None = None) -> InstrumentResult:
    config = config or InstrumentConfig()
    world = ScaleWorld(config.tonic_midi)

    tune, tune_trace = _compose_tune(config, world=world)
    bass, bass_trace = _compose_bass(config, tune, world=world)
    rhythm, rhythm_trace = _compose_rhythm(config, tune, bass, world=world)
    bass, rhythm, lock_trace = _apply_locks(
        config, tune, bass, rhythm, world=world
    )

    texture = score_texture((tune, bass, rhythm))
    checks = {
        "three_explicit_lanes": [voice.name for voice in (tune, bass, rhythm)]
        == ["TUNE", "BASS", "RHYTHM"],
        "tune_in_lane": all(TUNE_LANE.contains(event.pitch, tonic_midi=config.tonic_midi) for event in tune.events),
        "bass_in_lane": all(BASS_LANE.contains(event.pitch, tonic_midi=config.tonic_midi) for event in bass.events),
        "rhythm_in_lane": all(RHYTHM_LANE.contains(event.pitch, tonic_midi=config.tonic_midi) for event in rhythm.events),
        "shared_scale": all(world.pitch_is_in_scale(event.pitch) for voice in (tune, bass, rhythm) for event in voice.events),
        "no_self_overlap": all(
            all(right.onset >= left.end for left, right in zip(voice.events, voice.events[1:], strict=False))
            for voice in (tune, bass, rhythm)
        ),
        "predictive_gate_traced": len(tune_trace) == config.bars and all("gate" in item for item in tune_trace),
        "subsidiary_silence_competes": all(
            "silence_score" in decision
            for bar in bass_trace
            for decision in bar["decisions"]
        ) and all("silence_score" in bar for bar in rhythm_trace),
        "vertical_floor": texture.minimum >= 0.30,
    }

    trace = {
        "version": "0.2",
        "architecture": {
            "parts": ["TUNE", "BASS", "RHYTHM"],
            "pitch_model": "abstract scale degree -> tonic-relative lane",
            "tonic_midi": config.tonic_midi,
            "scale": "Aeolian",
            "experiment_mode": config.mode.value,
        },
        "config": {
            "seed": config.seed,
            "tempo_bpm": config.tempo_bpm,
            "bars": config.bars,
            "bass": asdict(config.bass),
            "rhythm": asdict(config.rhythm),
            "pattern_locks": [asdict(lock) for lock in config.pattern_locks],
        },
        "tune_decisions": tune_trace,
        "bass_decisions": bass_trace,
        "rhythm_decisions": rhythm_trace,
        "pattern_locks": lock_trace,
        "voices": {
            "TUNE": [_event_json(event) for event in tune.events],
            "BASS": [_event_json(event) for event in bass.events],
            "RHYTHM": [_event_json(event) for event in rhythm.events],
        },
        "metrics": {
            "tune_events": len(tune.events),
            "bass_events": len(bass.events),
            "rhythm_events": len(rhythm.events),
            "vertical_weighted_mean": texture.weighted_mean,
            "vertical_minimum": texture.minimum,
            "revealing_bars": sum(item["selected_branch"] == "revealing" for item in tune_trace),
            "exploratory_bars": sum(item["selected_branch"] == "exploratory" for item in tune_trace),
            "expected_bars": sum(item["selected_branch"] == "expected" for item in tune_trace),
        },
        "validation": {"passed": all(checks.values()), "checks": checks},
    }
    return InstrumentResult(config, tune, bass, rhythm, trace)


def compose_experiment_bundle(
    config: InstrumentConfig | None = None,
) -> dict[ExperimentMode, InstrumentResult]:
    """Generate the three falsification conditions from one high-level config."""

    base = config or InstrumentConfig()
    return {
        mode: compose(
            InstrumentConfig(
                seed=base.seed,
                tempo_bpm=base.tempo_bpm,
                bars=base.bars,
                beats_per_bar=base.beats_per_bar,
                tonic_midi=base.tonic_midi,
                mode=mode,
                tune_alternatives=base.tune_alternatives,
                bass=base.bass,
                rhythm=base.rhythm,
                pattern_locks=base.pattern_locks,
            )
        )
        for mode in ExperimentMode
    }


def write_files(
    output_dir: str | Path,
    config: InstrumentConfig | None = None,
) -> tuple[Path, Path]:
    result = compose(config)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    midi_path = output / "ipm-v0.2.mid"
    trace_path = output / "ipm-v0.2.trace.json"
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
    parser = argparse.ArgumentParser(description="Generate the consolidated IPM v0.2 instrument")
    parser.add_argument("--output", default="examples")
    parser.add_argument("--seed", type=int, default=2026081704)
    parser.add_argument("--tonic-midi", type=int, default=60)
    parser.add_argument("--mode", choices=[mode.value for mode in ExperimentMode], default="ipm")
    parser.add_argument("--bass-activity", type=float, default=0.72)
    parser.add_argument("--bass-sustain", type=float, default=0.62)
    parser.add_argument("--bass-movement", type=float, default=0.30)
    parser.add_argument("--rhythm-activity", type=float, default=0.68)
    args = parser.parse_args()
    config = InstrumentConfig(
        seed=args.seed,
        tonic_midi=args.tonic_midi,
        mode=ExperimentMode(args.mode),
        bass=BassControls(
            activity=args.bass_activity,
            sustain=args.bass_sustain,
            movement=args.bass_movement,
        ),
        rhythm=RhythmControls(activity=args.rhythm_activity),
    )
    result = compose(config)
    for path in write_files(args.output, config):
        print(path)
    print(json.dumps(result.trace["metrics"], indent=2))
    print(json.dumps(result.trace["validation"], indent=2))
    if not result.trace["validation"]["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

"""History-aware whole-bar composition for IPM.

The bar is the decision unit.  Rhythm, rests, attack positions, durations and pitches
are proposed together as one candidate.  A selected bar updates musical state; the
next bar is then judged against the history actually created so far rather than an
independent template or a pre-existing pitch skeleton.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from math import exp
from typing import Sequence

from .bar_rhythm import BarCellKind, BarPattern, BarRhythmPolicy, bar_patterns, realise_bar_pattern
from .model import Beat, NoteEvent
from .randomness import SeededRandom

_AEOLIAN = (0, 2, 3, 5, 7, 8, 10)
_PHASE_TARGETS: dict[str, tuple[float, float, int]] = {
    "opening": (3.5, 0.16, 3),
    "establishment": (4.5, 0.12, 5),
    "development": (5.2, 0.15, 7),
    "climax": (6.0, 0.10, 8),
    "resolution": (4.3, 0.18, 3),
    "ending": (3.2, 0.22, 0),
}


@dataclass(frozen=True, slots=True)
class MusicalState:
    """Compact memory carried from one accepted bar into the next."""

    bars_written: int = 0
    last_pitch: int | None = None
    last_interval: int = 0
    previous_attacks: int | None = None
    previous_rest_fraction: float | None = None
    previous_signature: tuple | None = None
    recent_pitches: tuple[int, ...] = ()
    recent_intervals: tuple[int, ...] = ()
    recent_attack_counts: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class WholeBarCandidate:
    pattern: BarPattern
    pitches: tuple[int, ...]

    def __post_init__(self) -> None:
        if len(self.pitches) != self.pattern.attacks:
            raise ValueError("one pitch is required for every bar attack")

    @property
    def intervals(self) -> tuple[int, ...]:
        return tuple(
            right - left for left, right in zip(self.pitches, self.pitches[1:], strict=False)
        )

    @property
    def signature(self) -> tuple:
        return (
            tuple((cell.kind.value, cell.duration) for cell in self.pattern.cells),
            self.pitches,
        )


@dataclass(frozen=True, slots=True)
class WholeBarScore:
    candidate: WholeBarCandidate
    total: float
    entry_continuity: float
    rhythmic_continuity: float
    learned_vocabulary: float
    phrase_direction: float
    internal_variety: float
    non_repetition: float
    cadence: float


@dataclass(frozen=True, slots=True)
class WholeBarDecision:
    selected: WholeBarScore
    alternatives: tuple[WholeBarScore, ...]
    state_before: MusicalState
    state_after: MusicalState


def scale_pitches(tonic_midi: int) -> tuple[int, ...]:
    """One named octave of Aeolian pitches rooted at ``tonic_midi``."""

    return tuple(tonic_midi + offset for offset in _AEOLIAN)


@lru_cache(maxsize=8)
def _active_patterns() -> tuple[BarPattern, ...]:
    policy = BarRhythmPolicy(
        grid=Fraction(1, 2),
        max_cells=8,
        max_attacks=7,
        max_rest_fraction=0.50,
    )
    result: list[BarPattern] = []
    for pattern in bar_patterns(Fraction(4), policy=policy):
        note_durations = [
            cell.duration for cell in pattern.cells if cell.kind is BarCellKind.NOTE
        ]
        if not 3 <= pattern.attacks <= 7:
            continue
        if any(duration > Fraction(3, 2) for duration in note_durations):
            continue
        if not any(duration == Fraction(1, 2) for duration in note_durations):
            continue
        result.append(pattern)
    return tuple(result)


def _choose_pattern(
    *,
    rng: SeededRandom,
    phase: str,
    state: MusicalState,
) -> BarPattern:
    target_attacks, rest_target, _ = _PHASE_TARGETS[phase]
    candidates = _active_patterns()
    weights: list[float] = []
    for pattern in candidates:
        attack_fit = exp(-abs(pattern.attacks - target_attacks) / 0.65)
        rest_fit = exp(-abs(pattern.rest_fraction - rest_target) / 0.16)
        short = sum(
            cell.kind is BarCellKind.NOTE and cell.duration == Fraction(1, 2)
            for cell in pattern.cells
        )
        short_bonus = 1.18 ** short
        continuity = 1.0
        if state.previous_attacks is not None:
            continuity *= exp(-abs(pattern.attacks - state.previous_attacks) / 2.0)
        if state.previous_rest_fraction is not None:
            continuity *= exp(-abs(pattern.rest_fraction - state.previous_rest_fraction) / 0.30)
        weights.append(attack_fit * rest_fit * short_bonus * (0.55 + 0.45 * continuity))
    return rng.weighted_choice(candidates, weights)


def _phase_pitch_target(tonic_midi: int, phase: str) -> int:
    _, _, offset = _PHASE_TARGETS[phase]
    return tonic_midi + offset


def _choose_pitch(
    *,
    rng: SeededRandom,
    pool: Sequence[int],
    previous: int,
    phase_target: int,
    state: MusicalState,
    first_in_bar: bool,
) -> int:
    recent = set(state.recent_pitches[-12:])
    weights: list[float] = []
    for pitch in pool:
        interval = pitch - previous
        distance_weight = exp(-abs(interval) / (2.5 if first_in_bar else 2.0))
        target_weight = exp(-abs(pitch - phase_target) / 5.0)
        learned_weight = 1.18 if pitch in recent else 1.0
        repetition_weight = 0.58 if pitch == previous else 1.0
        leap_weight = 0.22 if abs(interval) > 5 else 1.0
        weights.append(
            distance_weight * target_weight * learned_weight * repetition_weight * leap_weight
        )
    return rng.weighted_choice(pool, weights)


def propose_whole_bar(
    *,
    rng: SeededRandom,
    phase: str,
    state: MusicalState,
    tonic_midi: int = 60,
    final_bar: bool = False,
) -> WholeBarCandidate:
    """Propose rhythm and pitch together from the current musical state."""

    if phase not in _PHASE_TARGETS:
        raise ValueError("unknown structural phase")
    pattern = _choose_pattern(rng=rng, phase=phase, state=state)
    pool = scale_pitches(tonic_midi)
    phase_target = _phase_pitch_target(tonic_midi, phase)
    previous = state.last_pitch if state.last_pitch is not None else tonic_midi
    pitches: list[int] = []
    for attack in range(pattern.attacks):
        pitch = _choose_pitch(
            rng=rng,
            pool=pool,
            previous=previous,
            phase_target=phase_target,
            state=state,
            first_in_bar=attack == 0,
        )
        pitches.append(pitch)
        previous = pitch
    if final_bar:
        pitches[-1] = tonic_midi
    return WholeBarCandidate(pattern=pattern, pitches=tuple(pitches))


def _phrase_direction_score(candidate: WholeBarCandidate, *, phase: str, tonic_midi: int) -> float:
    if not candidate.pitches:
        return 0.0
    start = candidate.pitches[0]
    end = candidate.pitches[-1]
    displacement = end - start
    if phase in {"development", "climax"}:
        return max(0.0, min(1.0, 0.55 + displacement / 10.0))
    if phase in {"resolution", "ending"}:
        before = abs(start - tonic_midi)
        after = abs(end - tonic_midi)
        return max(0.0, min(1.0, 0.55 + (before - after) / 8.0))
    return max(0.0, 1.0 - abs(displacement) / 10.0)


def score_whole_bar(
    candidate: WholeBarCandidate,
    *,
    state: MusicalState,
    phase: str,
    tonic_midi: int = 60,
    final_bar: bool = False,
) -> WholeBarScore:
    """Score one complete bar against both local history and global form."""

    if state.last_pitch is None:
        entry_continuity = 1.0
    else:
        entry_continuity = exp(-abs(candidate.pitches[0] - state.last_pitch) / 3.0)

    if state.previous_attacks is None or state.previous_rest_fraction is None:
        rhythmic_continuity = 1.0
    else:
        attack_fit = exp(-abs(candidate.pattern.attacks - state.previous_attacks) / 2.0)
        rest_fit = exp(-abs(candidate.pattern.rest_fraction - state.previous_rest_fraction) / 0.30)
        rhythmic_continuity = 0.65 * attack_fit + 0.35 * rest_fit

    recent_intervals = {abs(value) for value in state.recent_intervals[-12:]}
    candidate_intervals = [abs(value) for value in candidate.intervals]
    if not candidate_intervals or not recent_intervals:
        learned_vocabulary = 0.75
    else:
        learned_vocabulary = sum(
            interval in recent_intervals for interval in candidate_intervals
        ) / len(candidate_intervals)

    phrase_direction = _phrase_direction_score(
        candidate, phase=phase, tonic_midi=tonic_midi
    )
    unique_ratio = len(set(candidate.pitches)) / len(candidate.pitches)
    internal_variety = min(1.0, 0.35 + 0.85 * unique_ratio)
    non_repetition = 0.15 if candidate.signature == state.previous_signature else 1.0

    if final_bar:
        cadence = 1.0 if candidate.pitches[-1] == tonic_midi else 0.0
    elif phase in {"resolution", "ending"}:
        cadence = exp(-abs(candidate.pitches[-1] - tonic_midi) / 3.0)
    else:
        cadence = 0.75

    total = (
        0.22 * entry_continuity
        + 0.16 * rhythmic_continuity
        + 0.16 * learned_vocabulary
        + 0.18 * phrase_direction
        + 0.12 * internal_variety
        + 0.10 * non_repetition
        + 0.06 * cadence
    )
    return WholeBarScore(
        candidate=candidate,
        total=total,
        entry_continuity=entry_continuity,
        rhythmic_continuity=rhythmic_continuity,
        learned_vocabulary=learned_vocabulary,
        phrase_direction=phrase_direction,
        internal_variety=internal_variety,
        non_repetition=non_repetition,
        cadence=cadence,
    )


def advance_state(state: MusicalState, selected: WholeBarCandidate) -> MusicalState:
    intervals = selected.intervals
    return MusicalState(
        bars_written=state.bars_written + 1,
        last_pitch=selected.pitches[-1],
        last_interval=intervals[-1] if intervals else state.last_interval,
        previous_attacks=selected.pattern.attacks,
        previous_rest_fraction=selected.pattern.rest_fraction,
        previous_signature=selected.signature,
        recent_pitches=(state.recent_pitches + selected.pitches)[-16:],
        recent_intervals=(state.recent_intervals + intervals)[-16:],
        recent_attack_counts=(state.recent_attack_counts + (selected.pattern.attacks,))[-8:],
    )


def choose_whole_bar(
    *,
    rng: SeededRandom,
    phase: str,
    state: MusicalState,
    tonic_midi: int = 60,
    final_bar: bool = False,
    alternatives: int = 12,
) -> WholeBarDecision:
    """Generate competing complete bars and accept the strongest musical continuation."""

    if alternatives < 2:
        raise ValueError("at least two whole-bar alternatives are required")
    scored = tuple(
        score_whole_bar(
            propose_whole_bar(
                rng=rng,
                phase=phase,
                state=state,
                tonic_midi=tonic_midi,
                final_bar=final_bar,
            ),
            state=state,
            phase=phase,
            tonic_midi=tonic_midi,
            final_bar=final_bar,
        )
        for _ in range(alternatives)
    )
    selected = max(scored, key=lambda item: item.total)
    return WholeBarDecision(
        selected=selected,
        alternatives=scored,
        state_before=state,
        state_after=advance_state(state, selected.candidate),
    )


def realise_whole_bar(
    candidate: WholeBarCandidate,
    *,
    start: Beat,
    phase: str,
    gate: Fraction = Fraction(7, 8),
) -> tuple[NoteEvent, ...]:
    base_velocity = {
        "opening": 70,
        "establishment": 74,
        "development": 79,
        "climax": 86,
        "resolution": 73,
        "ending": 66,
    }[phase]
    velocities = tuple(
        max(48, min(102, base_velocity + (3 if index % 2 == 0 else -2)))
        for index in range(candidate.pattern.attacks)
    )
    return realise_bar_pattern(
        candidate.pattern,
        start=start,
        pitches=candidate.pitches,
        velocities=velocities,
        gate=gate,
    )

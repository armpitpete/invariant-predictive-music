"""Main-voice branch competition: expected, revealing, and exploratory futures."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import e, exp, log, log2
from typing import Sequence

from .model import NoteEvent, Voice
from .randomness import SeededRandom
from .rhythm import rhythmic_invariant_similarity


class MainBranchKind(str, Enum):
    EXPECTED = "expected"
    REVEALING = "revealing"
    EXPLORATORY = "exploratory"


@dataclass(frozen=True, slots=True)
class MainVoicePolicy:
    """Scoring defaults for the three-way main-voice branch gate."""

    invariant_weight: float = 0.35
    lookahead_weight: float = 0.25
    necessity_weight: float = 0.25
    surprise_weight: float = 0.15
    revealing_invariant_floor: float = 0.65
    exploratory_invariant_floor: float = 0.30
    max_exploratory_surprise_bits: float = 5.0
    surprise_decay: float = 0.50
    min_lookahead_events: int = 2
    max_lookahead_events: int = 4
    selection_temperature: float = 0.10
    improvement_epsilon: float = 1e-9

    def __post_init__(self) -> None:
        weights = (
            self.invariant_weight,
            self.lookahead_weight,
            self.necessity_weight,
            self.surprise_weight,
        )
        if any(weight < 0 for weight in weights):
            raise ValueError("score weights must be non-negative")
        if sum(weights) <= 0:
            raise ValueError("score weights must sum to a positive value")
        if not 0 <= self.revealing_invariant_floor <= 1:
            raise ValueError("revealing_invariant_floor must be in 0..1")
        if not 0 <= self.exploratory_invariant_floor <= 1:
            raise ValueError("exploratory_invariant_floor must be in 0..1")
        if self.exploratory_invariant_floor > self.revealing_invariant_floor:
            raise ValueError("exploratory invariant floor cannot exceed revealing floor")
        if self.max_exploratory_surprise_bits <= 0:
            raise ValueError("max_exploratory_surprise_bits must be positive")
        if self.surprise_decay <= 0:
            raise ValueError("surprise_decay must be positive")
        if self.min_lookahead_events < 2:
            raise ValueError("lookahead must contain at least two events")
        if self.max_lookahead_events < self.min_lookahead_events:
            raise ValueError("max_lookahead_events must be >= min_lookahead_events")
        if self.selection_temperature <= 0:
            raise ValueError("selection_temperature must be positive")


@dataclass(frozen=True, slots=True)
class MainFuture:
    """One short alternative future from the same main-voice decision point.

    ``event_probabilities`` are the listener-model probabilities assigned to each
    event as the branch unfolds. The first value represents the local prediction
    being tested; the remaining values provide short-lookahead evidence.
    """

    kind: MainBranchKind
    events: tuple[NoteEvent, ...]
    event_probabilities: tuple[float, ...]

    def __post_init__(self) -> None:
        if not self.events:
            raise ValueError("main future requires at least one event")
        if len(self.events) != len(self.event_probabilities):
            raise ValueError("events and event_probabilities must have equal length")
        if any(probability <= 0 or probability > 1 for probability in self.event_probabilities):
            raise ValueError("event probabilities must be in (0, 1]")
        if tuple(sorted(self.events, key=lambda event: event.onset)) != self.events:
            raise ValueError("main future events must be ordered by onset")
        Voice.from_events("M_future", self.events)

    @property
    def start(self):
        return self.events[0].onset

    @property
    def end(self):
        return self.events[-1].end

    @property
    def forward_probability(self) -> float:
        return self.event_probabilities[0]


@dataclass(frozen=True, slots=True)
class MainFutureScore:
    future: MainFuture
    total: float
    forward_probability: float
    surprise_bits: float
    calibrated_surprise: float
    invariant_similarity: float
    lookahead_predictability: float
    retrospective_coherence: float
    retrospective_necessity: float
    valid: bool
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class MainDecision:
    selected: MainFutureScore
    baseline: MainFutureScore
    eligible: tuple[MainFutureScore, ...]
    scored: tuple[MainFutureScore, ...]


def _direction(interval: int) -> int:
    return 1 if interval > 0 else -1 if interval < 0 else 0


def _normalise(values: Sequence[float]) -> tuple[float, ...]:
    total = sum(values)
    if total == 0:
        return tuple(0.0 for _ in values)
    return tuple(value / total for value in values)


def _shape_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        return 0.0
    if not left:
        return 1.0
    left_norm = _normalise(left)
    right_norm = _normalise(right)
    distance = 0.5 * sum(abs(a - b) for a, b in zip(left_norm, right_norm, strict=True))
    return max(0.0, 1.0 - distance)


def invariant_similarity(
    reference: Sequence[NoteEvent],
    candidate: Sequence[NoteEvent],
) -> float:
    """Compare melodic identity while allowing rhythmic transformation.

    Pitch identity remains transposition-invariant through contour and interval
    shape. Rhythmic identity is evaluated as a transformable invariant rather than
    an exact duration template.
    """

    if len(reference) != len(candidate) or len(reference) < 2:
        return 0.0

    reference_intervals = [b.pitch - a.pitch for a, b in zip(reference, reference[1:], strict=False)]
    candidate_intervals = [b.pitch - a.pitch for a, b in zip(candidate, candidate[1:], strict=False)]

    reference_directions = [_direction(interval) for interval in reference_intervals]
    candidate_directions = [_direction(interval) for interval in candidate_intervals]
    contour = sum(
        left == right
        for left, right in zip(reference_directions, candidate_directions, strict=True)
    ) / len(reference_directions)

    interval_shape = _shape_similarity(
        [abs(interval) for interval in reference_intervals],
        [abs(interval) for interval in candidate_intervals],
    )
    rhythm = rhythmic_invariant_similarity(reference, candidate)

    return 0.45 * contour + 0.30 * interval_shape + 0.25 * rhythm


def surprise_bits(probability: float) -> float:
    if probability <= 0 or probability > 1:
        raise ValueError("probability must be in (0, 1]")
    return -log2(probability)


def calibrated_surprise(probability: float, *, decay: float = 0.50) -> float:
    """Inverted-U surprise utility, normalised to peak at 1."""

    if decay <= 0:
        raise ValueError("decay must be positive")
    surprise = surprise_bits(probability)
    if surprise == 0:
        return 0.0
    return decay * e * surprise * exp(-decay * surprise)


def _lookahead_predictability(probabilities: Sequence[float]) -> float:
    if len(probabilities) < 2:
        return 0.0
    tail = probabilities[1:]
    return exp(sum(log(probability) for probability in tail) / len(tail))


def _validate_competing_futures(
    futures: Sequence[MainFuture],
    reference_motif: Sequence[NoteEvent],
    policy: MainVoicePolicy,
) -> dict[MainBranchKind, MainFuture]:
    if len(futures) != 3:
        raise ValueError("exactly three main futures are required")
    by_kind = {future.kind: future for future in futures}
    if len(by_kind) != 3 or set(by_kind) != set(MainBranchKind):
        raise ValueError("one EXPECTED, one REVEALING, and one EXPLORATORY future are required")

    lengths = {len(future.events) for future in futures}
    if len(lengths) != 1:
        raise ValueError("competing futures must use the same lookahead event count")
    length = next(iter(lengths))
    if not policy.min_lookahead_events <= length <= policy.max_lookahead_events:
        raise ValueError("lookahead event count is outside policy bounds")
    if len(reference_motif) != length:
        raise ValueError("reference motif length must match the branch lookahead length")

    starts = {future.start for future in futures}
    ends = {future.end for future in futures}
    if len(starts) != 1 or len(ends) != 1:
        raise ValueError("competing futures must cover the same time horizon")

    expected = by_kind[MainBranchKind.EXPECTED]
    if any(
        future.forward_probability > expected.forward_probability + policy.improvement_epsilon
        for future in futures
        if future.kind is not MainBranchKind.EXPECTED
    ):
        raise ValueError("EXPECTED must be the highest-probability local continuation")
    return by_kind


def _score_future(
    future: MainFuture,
    *,
    reference_motif: Sequence[NoteEvent],
    expected_probability: float,
    policy: MainVoicePolicy,
) -> MainFutureScore:
    invariant = invariant_similarity(reference_motif, future.events)
    lookahead = _lookahead_predictability(future.event_probabilities)
    surprise = surprise_bits(future.forward_probability)
    surprise_utility = calibrated_surprise(
        future.forward_probability,
        decay=policy.surprise_decay,
    )
    retrospective = 0.65 * invariant + 0.35 * lookahead
    necessity = (1.0 - future.forward_probability) * retrospective

    valid = True
    reason = None
    if future.kind is MainBranchKind.REVEALING:
        if future.forward_probability >= expected_probability - policy.improvement_epsilon:
            valid = False
            reason = "revealing branch must violate the local prediction"
        elif invariant < policy.revealing_invariant_floor:
            valid = False
            reason = "revealing invariant floor"
    elif future.kind is MainBranchKind.EXPLORATORY:
        if future.forward_probability >= expected_probability - policy.improvement_epsilon:
            valid = False
            reason = "exploratory branch must differ from the local prediction"
        elif invariant < policy.exploratory_invariant_floor:
            valid = False
            reason = "exploratory invariant floor"
        elif surprise > policy.max_exploratory_surprise_bits:
            valid = False
            reason = "exploratory surprise ceiling"

    total_weight = (
        policy.invariant_weight
        + policy.lookahead_weight
        + policy.necessity_weight
        + policy.surprise_weight
    )
    total = (
        policy.invariant_weight * invariant
        + policy.lookahead_weight * lookahead
        + policy.necessity_weight * necessity
        + policy.surprise_weight * surprise_utility
    ) / total_weight

    return MainFutureScore(
        future=future,
        total=total,
        forward_probability=future.forward_probability,
        surprise_bits=surprise,
        calibrated_surprise=surprise_utility,
        invariant_similarity=invariant,
        lookahead_predictability=lookahead,
        retrospective_coherence=retrospective,
        retrospective_necessity=necessity,
        valid=valid,
        reason=reason,
    )


def evaluate_main_futures(
    futures: Sequence[MainFuture],
    *,
    reference_motif: Sequence[NoteEvent],
    policy: MainVoicePolicy = MainVoicePolicy(),
) -> tuple[MainFutureScore, ...]:
    """Score all three short futures against the same predictable baseline."""

    by_kind = _validate_competing_futures(futures, reference_motif, policy)
    expected_probability = by_kind[MainBranchKind.EXPECTED].forward_probability
    return tuple(
        _score_future(
            future,
            reference_motif=reference_motif,
            expected_probability=expected_probability,
            policy=policy,
        )
        for future in futures
    )


def choose_main_future(
    futures: Sequence[MainFuture],
    *,
    reference_motif: Sequence[NoteEvent],
    rng: SeededRandom,
    policy: MainVoicePolicy = MainVoicePolicy(),
) -> MainDecision:
    """Choose a short future while keeping prediction as the mandatory baseline.

    A surprising branch is not eligible for selection unless it is structurally
    valid *and* its full lookahead score beats the expected branch.
    """

    scored = evaluate_main_futures(
        futures,
        reference_motif=reference_motif,
        policy=policy,
    )
    baseline = next(
        score for score in scored if score.future.kind is MainBranchKind.EXPECTED
    )
    if not baseline.valid:
        raise ValueError("EXPECTED baseline must be valid")

    eligible = (baseline,) + tuple(
        score
        for score in scored
        if score.future.kind is not MainBranchKind.EXPECTED
        and score.valid
        and score.total > baseline.total + policy.improvement_epsilon
    )

    if len(eligible) == 1:
        return MainDecision(baseline, baseline, eligible, scored)

    best = max(score.total for score in eligible)
    weights = [exp((score.total - best) / policy.selection_temperature) for score in eligible]
    selected = rng.weighted_choice(eligible, weights)
    return MainDecision(selected, baseline, eligible, scored)

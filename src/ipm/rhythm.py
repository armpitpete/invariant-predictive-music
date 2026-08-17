"""Rhythmic invariants and time-budget transformations for IPM.

The invariant layer describes how rhythmic identity can survive transformation. The
budget layer goes one step further: a structural event owns a span of musical time,
not necessarily one sounding attack. The same two-beat span can therefore surface as
``2``, ``1+1``, ``1/2+1/2+1/2+1/2``, asymmetric ordered partitions, or other exact
subdivisions while preserving the structural time budget.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from math import exp
from typing import Sequence

from .model import Beat, NoteEvent
from .randomness import SeededRandom


def _normalise(values: Sequence[float]) -> tuple[float, ...]:
    total = sum(values)
    if total <= 0:
        return tuple(0.0 for _ in values)
    return tuple(value / total for value in values)


def _shape_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        return 0.0
    if not left:
        return 1.0
    left_norm = _normalise(left)
    right_norm = _normalise(right)
    distance = 0.5 * sum(
        abs(a - b) for a, b in zip(left_norm, right_norm, strict=True)
    )
    return max(0.0, 1.0 - distance)


def _direction(left: float, right: float) -> int:
    return 1 if right > left else -1 if right < left else 0


def rhythmic_invariant_similarity(
    reference: Sequence[NoteEvent],
    candidate: Sequence[NoteEvent],
) -> float:
    """Measure rhythmic identity while permitting meaningful transformation.

    Three features contribute:

    - ordered duration shape: where duration weight falls in the gesture;
    - duration profile: the relative collection of short/medium/long values,
      independent of their exact positions;
    - duration contour: whether successive notes lengthen, shorten, or stay equal.

    Uniform augmentation/diminution therefore preserves the invariant exactly,
    while redistribution or rotation can remain recognisably related without being
    forced to copy the source duration sequence.
    """

    if len(reference) != len(candidate) or len(reference) < 2:
        return 0.0

    reference_durations = [float(event.duration) for event in reference]
    candidate_durations = [float(event.duration) for event in candidate]

    ordered_shape = _shape_similarity(reference_durations, candidate_durations)
    duration_profile = _shape_similarity(
        sorted(reference_durations),
        sorted(candidate_durations),
    )

    reference_contour = [
        _direction(left, right)
        for left, right in zip(reference_durations, reference_durations[1:], strict=False)
    ]
    candidate_contour = [
        _direction(left, right)
        for left, right in zip(candidate_durations, candidate_durations[1:], strict=False)
    ]
    contour = sum(
        left == right
        for left, right in zip(reference_contour, candidate_contour, strict=True)
    ) / len(reference_contour)

    return 0.35 * ordered_shape + 0.40 * duration_profile + 0.25 * contour


@dataclass(frozen=True, slots=True)
class RhythmBudgetPolicy:
    """Defaults for stochastic decomposition of one structural time budget."""

    grid: Beat = Fraction(1, 2)
    max_attacks: int = 4
    attack_temperature: float = 0.85
    balance_bias: float = 1.25
    equal_partition_penalty: float = 0.90

    def __post_init__(self) -> None:
        if self.grid <= 0:
            raise ValueError("grid must be positive")
        if self.max_attacks <= 0:
            raise ValueError("max_attacks must be positive")
        if self.attack_temperature <= 0:
            raise ValueError("attack_temperature must be positive")
        if self.balance_bias < 0:
            raise ValueError("balance_bias must be non-negative")
        if not 0 < self.equal_partition_penalty <= 1:
            raise ValueError("equal_partition_penalty must be in (0, 1]")


@dataclass(frozen=True, slots=True)
class RhythmicPartition:
    """One ordered decomposition of a fixed structural span."""

    span: Beat
    segments: tuple[Beat, ...]

    def __post_init__(self) -> None:
        if self.span <= 0:
            raise ValueError("span must be positive")
        if not self.segments or any(segment <= 0 for segment in self.segments):
            raise ValueError("segments must contain positive durations")
        if sum(self.segments, Fraction(0)) != self.span:
            raise ValueError("segments must sum exactly to span")

    @property
    def attacks(self) -> int:
        return len(self.segments)


def _pulse_count(span: Beat, grid: Beat) -> int:
    pulses = span / grid
    if pulses.denominator != 1:
        raise ValueError("span must be exactly divisible by grid")
    return pulses.numerator


def _compositions(total: int, parts: int) -> tuple[tuple[int, ...], ...]:
    """Return ordered positive integer compositions of ``total`` into ``parts``."""

    if total <= 0 or parts <= 0 or parts > total:
        return ()
    if parts == 1:
        return ((total,),)
    result: list[tuple[int, ...]] = []
    for first in range(1, total - parts + 2):
        for tail in _compositions(total - first, parts - 1):
            result.append((first, *tail))
    return tuple(result)


def rhythmic_partitions(
    span: Beat,
    *,
    grid: Beat = Fraction(1, 2),
    attacks: int | None = None,
    max_attacks: int | None = None,
) -> tuple[RhythmicPartition, ...]:
    """Enumerate exact ordered decompositions of a structural time budget.

    Example for a two-beat span on a half-beat grid: ``2``, ``1+1``,
    ``1/2+1/2+1/2+1/2``, ``3/2+1/2``, ``1/2+1+1/2``, and the other ordered
    compositions. Equal subdivisions are live options, not mandatory templates.
    """

    if span <= 0 or grid <= 0:
        raise ValueError("span and grid must be positive")
    pulses = _pulse_count(span, grid)
    upper = pulses if max_attacks is None else min(pulses, max_attacks)
    if upper <= 0:
        raise ValueError("max_attacks must permit at least one attack")
    counts = (attacks,) if attacks is not None else tuple(range(1, upper + 1))
    result: list[RhythmicPartition] = []
    for count in counts:
        if count is None or count <= 0 or count > upper:
            raise ValueError("attacks must be in the permitted range")
        for composition in _compositions(pulses, count):
            result.append(
                RhythmicPartition(
                    span=span,
                    segments=tuple(Fraction(pulse) * grid for pulse in composition),
                )
            )
    return tuple(result)


def euclidean_partition(
    span: Beat,
    attacks: int,
    *,
    grid: Beat = Fraction(1, 2),
    rotation: int = 0,
) -> RhythmicPartition:
    """Return an even-as-possible linear partition with optional cyclic rotation.

    This complements :mod:`ipm.euclidean`: that module proposes attack positions in
    a larger grid, while this function divides one already-owned time budget into
    inter-attack durations.
    """

    pulses = _pulse_count(span, grid)
    if attacks <= 0 or attacks > pulses:
        raise ValueError("attacks must be between 1 and the pulse count")
    onsets = tuple((index * pulses) // attacks for index in range(attacks))
    widths = tuple(
        (onsets[index + 1] if index + 1 < attacks else pulses) - onset
        for index, onset in enumerate(onsets)
    )
    if rotation:
        offset = rotation % attacks
        widths = widths[offset:] + widths[:offset]
    return RhythmicPartition(
        span=span,
        segments=tuple(Fraction(width) * grid for width in widths),
    )


def choose_rhythmic_partition(
    span: Beat,
    *,
    rng: SeededRandom,
    intensity: float,
    policy: RhythmBudgetPolicy = RhythmBudgetPolicy(),
    attacks: int | None = None,
) -> RhythmicPartition:
    """Choose a decomposition with attack density governed by structural intensity.

    ``intensity=0`` biases toward a sustain; ``intensity=1`` moves the target toward
    the permitted maximum. Once attack count is chosen, balanced/Euclidean-like
    partitions are mildly favoured but asymmetric ordered compositions remain live.
    """

    if not 0 <= intensity <= 1:
        raise ValueError("intensity must be in 0..1")
    pulses = _pulse_count(span, policy.grid)
    maximum = min(pulses, policy.max_attacks)
    if attacks is None:
        counts = tuple(range(1, maximum + 1))
        target = 1.0 + intensity * (maximum - 1)
        count_weights = [
            exp(-abs(count - target) / policy.attack_temperature) / (count ** 0.20)
            for count in counts
        ]
        attacks = rng.weighted_choice(counts, count_weights)
    elif attacks <= 0 or attacks > maximum:
        raise ValueError("attacks is outside the permitted range")

    candidates = rhythmic_partitions(
        span,
        grid=policy.grid,
        attacks=attacks,
        max_attacks=policy.max_attacks,
    )
    mean = float(span / attacks)
    weights: list[float] = []
    for candidate in candidates:
        imbalance = sum(
            abs(float(segment) - mean) for segment in candidate.segments
        ) / float(span)
        weight = exp(-policy.balance_bias * imbalance)
        if attacks > 1 and len(set(candidate.segments)) == 1:
            weight *= policy.equal_partition_penalty
        weights.append(weight)
    return rng.weighted_choice(candidates, weights)


def realise_partition(
    event: NoteEvent,
    partition: RhythmicPartition,
    *,
    gate: Fraction = Fraction(7, 8),
) -> tuple[NoteEvent, ...]:
    """Retrigger one structural pitch according to a rhythmic partition.

    The allocated segments still sum to the original structural duration. ``gate``
    shortens the sounding attack inside each segment, introducing explicit breath
    without moving the next structural boundary.
    """

    if partition.span != event.duration:
        raise ValueError("partition span must match event duration")
    if gate <= 0 or gate > 1:
        raise ValueError("gate must be in (0, 1]")
    cursor = event.onset
    realised: list[NoteEvent] = []
    for segment in partition.segments:
        realised.append(
            NoteEvent(
                onset=cursor,
                duration=segment * gate,
                pitch=event.pitch,
                velocity=event.velocity,
            )
        )
        cursor += segment
    return tuple(realised)

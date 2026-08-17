"""Euclidean rhythm utilities for proposing attack times without imposing quotas.

A Euclidean pattern distributes ``pulses`` candidate attacks as evenly as possible
across ``steps`` positions. IPM treats those positions as opportunities: later
silence, vertical, density, and structural gates still decide whether a note sounds.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable

from .model import Beat


@dataclass(frozen=True, slots=True)
class EuclideanPattern:
    pulses: int
    steps: int
    rotation: int
    hits: tuple[bool, ...]

    def __post_init__(self) -> None:
        if self.steps <= 0:
            raise ValueError("steps must be positive")
        if not 0 <= self.pulses <= self.steps:
            raise ValueError("pulses must be in 0..steps")
        if len(self.hits) != self.steps:
            raise ValueError("hit count must equal steps")
        if sum(self.hits) != self.pulses:
            raise ValueError("hit pattern must contain exactly pulses attacks")

    @property
    def attack_indices(self) -> tuple[int, ...]:
        return tuple(index for index, hit in enumerate(self.hits) if hit)

    @property
    def spacing(self) -> tuple[int, ...]:
        """Circular step distances between successive attacks."""

        indices = self.attack_indices
        if not indices:
            return ()
        if len(indices) == 1:
            return (self.steps,)
        return tuple(
            (right - left) % self.steps
            for left, right in zip(indices, (*indices[1:], indices[0]), strict=True)
        )


def euclidean_pattern(pulses: int, steps: int, *, rotation: int = 0) -> EuclideanPattern:
    """Return one maximally-even Euclidean attack pattern.

    The modular construction is a canonical rotation of the usual Bjorklund
    family. ``rotation`` moves the surface accent while preserving pulse count
    and circular spacing.
    """

    if steps <= 0:
        raise ValueError("steps must be positive")
    if not 0 <= pulses <= steps:
        raise ValueError("pulses must be in 0..steps")

    if pulses == 0:
        base = (False,) * steps
    elif pulses == steps:
        base = (True,) * steps
    else:
        base = tuple(((index * pulses) % steps) < pulses for index in range(steps))

    normalised_rotation = rotation % steps
    hits = tuple(base[(index - normalised_rotation) % steps] for index in range(steps))
    return EuclideanPattern(pulses, steps, normalised_rotation, hits)


def euclidean_onsets(
    pulses: int,
    steps: int,
    *,
    start: Beat = Fraction(0),
    span: Beat,
    rotation: int = 0,
) -> tuple[Beat, ...]:
    """Map Euclidean attack opportunities onto a real musical time span."""

    if start < 0:
        raise ValueError("start must be non-negative")
    if span <= 0:
        raise ValueError("span must be positive")
    pattern = euclidean_pattern(pulses, steps, rotation=rotation)
    step_duration = span / steps
    return tuple(start + index * step_duration for index in pattern.attack_indices)


def rotation_overlap_count(
    pattern: EuclideanPattern,
    occupied_indices: Iterable[int],
) -> int:
    """Count Euclidean attacks that coincide with supplied pulse indices."""

    occupied = {index % pattern.steps for index in occupied_indices}
    return sum(index in occupied for index in pattern.attack_indices)


def least_aligned_rotation(
    pulses: int,
    steps: int,
    *,
    occupied_indices: Iterable[int],
) -> EuclideanPattern:
    """Choose the rotation with the fewest attacks on already-occupied pulses.

    Ties prefer the smallest rotation so the result remains deterministic.
    """

    occupied = tuple(occupied_indices)
    candidates = [euclidean_pattern(pulses, steps, rotation=rotation) for rotation in range(steps)]
    return min(
        candidates,
        key=lambda pattern: (rotation_overlap_count(pattern, occupied), pattern.rotation),
    )

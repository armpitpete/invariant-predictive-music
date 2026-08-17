"""Rhythmic invariants that preserve identity without freezing a duration template."""

from __future__ import annotations

from typing import Sequence

from .model import NoteEvent


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

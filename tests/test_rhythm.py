from fractions import Fraction

import pytest

from ipm.main_voice import invariant_similarity
from ipm.model import NoteEvent
from ipm.rhythm import rhythmic_invariant_similarity


def motif(durations=(1, 1, 2, 4)):
    cursor = Fraction(0)
    events = []
    for pitch, duration in zip((60, 64, 65, 62), durations, strict=True):
        value = Fraction(duration)
        events.append(NoteEvent(cursor, value, pitch))
        cursor += value
    return tuple(events)


def test_uniform_augmentation_preserves_rhythmic_invariant_exactly() -> None:
    assert rhythmic_invariant_similarity(
        motif((1, 1, 2, 4)),
        motif((2, 2, 4, 8)),
    ) == pytest.approx(1.0)


def test_duration_redistribution_can_preserve_identity_without_copying_template() -> None:
    reference = motif((1, 1, 2, 4))
    transformed = motif((1, 2, 1, 4))

    score = rhythmic_invariant_similarity(reference, transformed)

    assert 0.70 < score < 1.0
    assert invariant_similarity(reference, transformed) > 0.90


def test_flattening_all_durations_loses_more_identity_than_structured_transform() -> None:
    reference = motif((1, 1, 2, 4))
    transformed = motif((1, 2, 1, 4))
    flattened = motif((2, 2, 2, 2))

    assert rhythmic_invariant_similarity(reference, transformed) > rhythmic_invariant_similarity(
        reference,
        flattened,
    )


def test_rhythmic_invariant_is_not_an_exact_duration_equality_test() -> None:
    reference = motif((1, 1, 2, 4))
    expressive = motif((Fraction(1, 2), Fraction(3, 2), 2, 4))

    assert [event.duration for event in reference] != [event.duration for event in expressive]
    assert rhythmic_invariant_similarity(reference, expressive) > 0.80

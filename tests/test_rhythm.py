from fractions import Fraction

import pytest

from ipm.main_voice import invariant_similarity
from ipm.model import NoteEvent
from ipm.randomness import SeededRandom
from ipm.rhythm import (
    RhythmBudgetPolicy,
    choose_rhythmic_partition,
    euclidean_partition,
    realise_partition,
    rhythmic_invariant_similarity,
    rhythmic_partitions,
)


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


def test_two_beat_budget_contains_requested_surface_forms() -> None:
    partitions = rhythmic_partitions(Fraction(2), grid=Fraction(1, 2))
    shapes = {partition.segments for partition in partitions}

    assert (Fraction(2),) in shapes
    assert (Fraction(1), Fraction(1)) in shapes
    assert (Fraction(1, 2),) * 4 in shapes
    assert (Fraction(3, 2), Fraction(1, 2)) in shapes
    assert (Fraction(1, 2), Fraction(1), Fraction(1, 2)) in shapes


def test_every_budget_partition_preserves_exact_total_time() -> None:
    partitions = rhythmic_partitions(
        Fraction(4),
        grid=Fraction(1, 2),
        max_attacks=4,
    )
    assert partitions
    assert all(sum(partition.segments, Fraction(0)) == Fraction(4) for partition in partitions)


def test_euclidean_budget_partition_can_mean_two_or_four_attacks() -> None:
    assert euclidean_partition(Fraction(2), 2).segments == (
        Fraction(1),
        Fraction(1),
    )
    assert euclidean_partition(Fraction(2), 4).segments == (Fraction(1, 2),) * 4


def test_euclidean_budget_rotation_moves_unequal_spacing() -> None:
    base = euclidean_partition(Fraction(2), 3)
    rotated = euclidean_partition(Fraction(2), 3, rotation=1)

    assert base.segments != rotated.segments
    assert sum(base.segments, Fraction(0)) == Fraction(2)
    assert sum(rotated.segments, Fraction(0)) == Fraction(2)


def test_budget_choice_is_seed_reproducible() -> None:
    policy = RhythmBudgetPolicy(grid=Fraction(1, 2), max_attacks=4)
    first = choose_rhythmic_partition(
        Fraction(2),
        rng=SeededRandom(91),
        intensity=0.65,
        policy=policy,
    )
    second = choose_rhythmic_partition(
        Fraction(2),
        rng=SeededRandom(91),
        intensity=0.65,
        policy=policy,
    )

    assert first == second


def test_realisation_can_retrigger_with_real_breath_gaps() -> None:
    event = NoteEvent(Fraction(4), Fraction(2), 64, 81)
    partition = euclidean_partition(Fraction(2), 2)
    realised = realise_partition(event, partition, gate=Fraction(3, 4))

    assert [note.onset for note in realised] == [Fraction(4), Fraction(5)]
    assert [note.duration for note in realised] == [Fraction(3, 4), Fraction(3, 4)]
    assert [note.pitch for note in realised] == [64, 64]
    assert realised[0].end < realised[1].onset
    assert realised[-1].end < event.end

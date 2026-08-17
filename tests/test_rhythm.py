from fractions import Fraction

from ipm.model import NoteEvent
from ipm.randomness import SeededRandom
from ipm.rhythm import (
    RhythmPolicy,
    choose_rhythmic_partition,
    euclidean_partition,
    realise_partition,
    rhythmic_partitions,
)


def test_two_beat_budget_contains_requested_surface_forms() -> None:
    partitions = rhythmic_partitions(Fraction(2), grid=Fraction(1, 2))
    shapes = {partition.segments for partition in partitions}

    assert (Fraction(2),) in shapes
    assert (Fraction(1), Fraction(1)) in shapes
    assert (Fraction(1, 2),) * 4 in shapes
    assert (Fraction(3, 2), Fraction(1, 2)) in shapes
    assert (Fraction(1, 2), Fraction(1), Fraction(1, 2)) in shapes


def test_all_partitions_preserve_exact_time_budget() -> None:
    for partition in rhythmic_partitions(Fraction(4), grid=Fraction(1, 2), max_attacks=4):
        assert sum(partition.segments, Fraction(0)) == Fraction(4)


def test_euclidean_partition_evenly_splits_two_beats() -> None:
    assert euclidean_partition(Fraction(2), 2).segments == (Fraction(1), Fraction(1))
    assert euclidean_partition(Fraction(2), 4).segments == (Fraction(1, 2),) * 4


def test_euclidean_rotation_moves_unequal_segment() -> None:
    base = euclidean_partition(Fraction(2), 3)
    rotated = euclidean_partition(Fraction(2), 3, rotation=1)

    assert sum(base.segments, Fraction(0)) == Fraction(2)
    assert sum(rotated.segments, Fraction(0)) == Fraction(2)
    assert base.segments != rotated.segments


def test_same_seed_replays_same_rhythmic_partition() -> None:
    policy = RhythmPolicy(grid=Fraction(1, 2), max_attacks=4)
    first = choose_rhythmic_partition(
        Fraction(2), rng=SeededRandom(91), intensity=0.65, policy=policy
    )
    second = choose_rhythmic_partition(
        Fraction(2), rng=SeededRandom(91), intensity=0.65, policy=policy
    )

    assert first == second


def test_intensity_zero_can_be_forced_to_single_sustain() -> None:
    partition = choose_rhythmic_partition(
        Fraction(2), rng=SeededRandom(1), intensity=0.0, attacks=1
    )
    assert partition.segments == (Fraction(2),)


def test_realisation_retriggers_pitch_with_breath_gaps() -> None:
    event = NoteEvent(Fraction(4), Fraction(2), 64, 81)
    partition = euclidean_partition(Fraction(2), 2)
    realised = realise_partition(event, partition, gate=Fraction(3, 4))

    assert [note.onset for note in realised] == [Fraction(4), Fraction(5)]
    assert [note.duration for note in realised] == [Fraction(3, 4), Fraction(3, 4)]
    assert [note.pitch for note in realised] == [64, 64]
    assert realised[0].end < realised[1].onset
    assert realised[-1].end < event.end

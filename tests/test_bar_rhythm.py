from fractions import Fraction

from ipm.bar_rhythm import (
    BarCell,
    BarCellKind,
    BarPattern,
    BarRhythmPolicy,
    bar_patterns,
    choose_bar_pattern,
    realise_bar_pattern,
)
from ipm.randomness import SeededRandom


def shape(pattern: BarPattern):
    return tuple((cell.kind.value, cell.duration) for cell in pattern.cells)


def test_default_4_4_grammar_contains_requested_bar_forms() -> None:
    patterns = {shape(pattern) for pattern in bar_patterns()}

    assert (("note", Fraction(4)),) in patterns
    assert (("note", Fraction(2)), ("note", Fraction(2))) in patterns
    assert (("note", Fraction(2)), ("rest", Fraction(2))) in patterns
    assert (("rest", Fraction(2)), ("note", Fraction(2))) in patterns
    assert (
        ("note", Fraction(2)),
        ("note", Fraction(1)),
        ("note", Fraction(1)),
    ) in patterns
    assert (
        ("note", Fraction(2)),
        ("rest", Fraction(1)),
        ("note", Fraction(1)),
    ) in patterns
    assert (
        ("note", Fraction(1)),
        ("rest", Fraction(1)),
        ("note", Fraction(2)),
    ) in patterns


def test_every_pattern_fills_exactly_one_bar() -> None:
    for pattern in bar_patterns():
        assert sum((cell.duration for cell in pattern.cells), Fraction(0)) == Fraction(4)
        assert pattern.note_beats + pattern.rest_beats == Fraction(4)
        assert pattern.attacks >= 1


def test_no_pattern_contains_redundant_adjacent_rests() -> None:
    for pattern in bar_patterns():
        assert not any(
            left.kind is BarCellKind.REST and right.kind is BarCellKind.REST
            for left, right in zip(pattern.cells, pattern.cells[1:], strict=False)
        )


def test_same_seed_replays_same_bar_choice() -> None:
    first = choose_bar_pattern(
        rng=SeededRandom(91), intensity=0.45, rest_target=0.20
    )
    second = choose_bar_pattern(
        rng=SeededRandom(91), intensity=0.45, rest_target=0.20
    )
    assert first == second


def test_lower_intensity_biases_toward_fewer_attacks_over_many_seeds() -> None:
    low = []
    high = []
    for seed in range(100):
        low.append(
            choose_bar_pattern(
                rng=SeededRandom(seed), intensity=0.05, rest_target=0.10
            ).attacks
        )
        high.append(
            choose_bar_pattern(
                rng=SeededRandom(seed), intensity=0.90, rest_target=0.10
            ).attacks
        )
    assert sum(low) / len(low) < sum(high) / len(high)


def test_rest_target_changes_average_space_without_becoming_all_rest() -> None:
    dry = []
    spacious = []
    for seed in range(100):
        dry.append(
            choose_bar_pattern(
                rng=SeededRandom(seed), intensity=0.35, rest_target=0.0
            ).rest_fraction
        )
        spacious.append(
            choose_bar_pattern(
                rng=SeededRandom(seed), intensity=0.35, rest_target=0.45
            ).rest_fraction
        )
    assert sum(dry) / len(dry) < sum(spacious) / len(spacious)
    assert all(value < 1.0 for value in spacious)


def test_realisation_preserves_literal_rest_position() -> None:
    pattern = BarPattern(
        Fraction(4),
        (
            BarCell(BarCellKind.REST, Fraction(2)),
            BarCell(BarCellKind.NOTE, Fraction(2)),
        ),
    )
    events = realise_bar_pattern(
        pattern,
        start=Fraction(8),
        pitches=(60, 62, 64, 65),
        velocities=(60, 65, 70, 75),
        gate=Fraction(1),
    )

    assert len(events) == 1
    assert events[0].onset == Fraction(10)
    assert events[0].duration == Fraction(2)
    assert events[0].pitch == 65


def test_two_attacks_sample_first_and_final_melodic_anchors() -> None:
    pattern = BarPattern(
        Fraction(4),
        (
            BarCell(BarCellKind.NOTE, Fraction(2)),
            BarCell(BarCellKind.NOTE, Fraction(2)),
        ),
    )
    events = realise_bar_pattern(
        pattern,
        start=Fraction(0),
        pitches=(60, 62, 64, 67),
        gate=Fraction(1),
    )
    assert [event.pitch for event in events] == [60, 67]


def test_half_beat_grid_is_available_without_changing_abstraction() -> None:
    policy = BarRhythmPolicy(grid=Fraction(1, 2), max_cells=6, max_attacks=6)
    patterns = {shape(pattern) for pattern in bar_patterns(policy=policy)}
    assert (
        ("note", Fraction(1, 2)),
        ("note", Fraction(1, 2)),
        ("note", Fraction(1)),
        ("note", Fraction(2)),
    ) in patterns

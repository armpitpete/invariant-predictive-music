from fractions import Fraction

from ipm.bar_rhythm import BarCellKind
from ipm.randomness import SeededRandom
from ipm.surface_rhythm import SurfaceRhythmPolicy, choose_surface_pattern


def note_durations(pattern):
    return [
        cell.duration
        for cell in pattern.cells
        if cell.kind is BarCellKind.NOTE
    ]


def test_surface_choice_is_deterministic() -> None:
    first = choose_surface_pattern(
        rng=SeededRandom(91), target_attacks=5.0, rest_target=0.15
    )
    second = choose_surface_pattern(
        rng=SeededRandom(91), target_attacks=5.0, rest_target=0.15
    )
    assert first == second


def test_surface_patterns_still_fill_exact_bar() -> None:
    for seed in range(40):
        pattern = choose_surface_pattern(
            rng=SeededRandom(seed), target_attacks=4.5, rest_target=0.15
        )
        assert sum((cell.duration for cell in pattern.cells), Fraction(0)) == Fraction(4)


def test_active_policy_produces_more_attacks_than_old_slow_surface() -> None:
    attacks = [
        choose_surface_pattern(
            rng=SeededRandom(seed), target_attacks=5.0, rest_target=0.15
        ).attacks
        for seed in range(100)
    ]
    assert sum(attacks) / len(attacks) >= 4.3


def test_long_notes_are_exceptional_across_many_choices() -> None:
    durations = []
    for seed in range(120):
        pattern = choose_surface_pattern(
            rng=SeededRandom(seed), target_attacks=5.0, rest_target=0.15
        )
        durations.extend(note_durations(pattern))

    assert durations
    short = sum(duration <= Fraction(1) for duration in durations)
    long = sum(duration >= Fraction(2) for duration in durations)
    assert short / len(durations) >= 0.80
    assert long / len(durations) <= 0.05


def test_eighth_note_cells_are_genuinely_used() -> None:
    durations = []
    for seed in range(60):
        pattern = choose_surface_pattern(
            rng=SeededRandom(seed), target_attacks=5.5, rest_target=0.10
        )
        durations.extend(note_durations(pattern))

    assert sum(duration == Fraction(1, 2) for duration in durations) / len(durations) >= 0.25


def test_policy_rejects_invalid_penalties() -> None:
    try:
        SurfaceRhythmPolicy(long_note_penalty=0)
    except ValueError as error:
        assert "long_note_penalty" in str(error)
    else:
        raise AssertionError("expected validation failure")

from fractions import Fraction

from ipm.bar_rhythm import BarCellKind
from ipm.randomness import SeededRandom
from ipm.sequential_bar import (
    MusicalState,
    advance_state,
    choose_whole_bar,
    propose_whole_bar,
    scale_pitches,
)


def test_whole_bar_jointly_contains_rhythm_positions_lengths_and_pitches() -> None:
    candidate = propose_whole_bar(
        rng=SeededRandom(17),
        phase="development",
        state=MusicalState(),
    )
    assert sum((cell.duration for cell in candidate.pattern.cells), Fraction(0)) == Fraction(4)
    assert len(candidate.pitches) == candidate.pattern.attacks
    assert all(pitch in scale_pitches(60) for pitch in candidate.pitches)
    assert any(cell.kind is BarCellKind.NOTE for cell in candidate.pattern.cells)


def test_selected_bar_updates_the_state_seen_by_the_next_bar() -> None:
    rng = SeededRandom(33)
    first = choose_whole_bar(
        rng=rng,
        phase="opening",
        state=MusicalState(),
    )
    second = choose_whole_bar(
        rng=rng,
        phase="establishment",
        state=first.state_after,
    )
    assert first.state_after.last_pitch == first.selected.candidate.pitches[-1]
    assert second.state_before == first.state_after
    assert second.state_before.bars_written == 1
    assert second.state_before.recent_pitches
    assert second.state_before.previous_attacks == first.selected.candidate.pattern.attacks


def test_state_accumulates_more_than_only_the_last_pitch() -> None:
    candidate = propose_whole_bar(
        rng=SeededRandom(71),
        phase="development",
        state=MusicalState(),
    )
    state = advance_state(MusicalState(), candidate)
    assert state.recent_pitches == candidate.pitches
    assert state.recent_intervals == candidate.intervals
    assert state.recent_attack_counts == (candidate.pattern.attacks,)


def test_same_seed_replays_same_whole_bar_decision() -> None:
    first = choose_whole_bar(
        rng=SeededRandom(101),
        phase="development",
        state=MusicalState(last_pitch=63, recent_pitches=(60, 63, 65)),
    )
    second = choose_whole_bar(
        rng=SeededRandom(101),
        phase="development",
        state=MusicalState(last_pitch=63, recent_pitches=(60, 63, 65)),
    )
    assert first.selected.candidate == second.selected.candidate
    assert first.selected.total == second.selected.total


def test_final_bar_candidate_resolves_to_tonic() -> None:
    decision = choose_whole_bar(
        rng=SeededRandom(404),
        phase="ending",
        state=MusicalState(last_pitch=65, recent_pitches=(60, 63, 65, 67)),
        final_bar=True,
    )
    assert decision.selected.candidate.pitches[-1] == 60

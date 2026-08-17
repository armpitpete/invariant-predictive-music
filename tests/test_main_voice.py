from fractions import Fraction

import pytest

from ipm.main_voice import (
    MainBranchKind,
    MainFuture,
    MainVoicePolicy,
    choose_main_future,
    evaluate_main_futures,
    invariant_similarity,
)
from ipm.model import NoteEvent, VoiceOverlapError
from ipm.randomness import SeededRandom


def motif(*, transpose: int = 0, durations=(1, 1, 2)):
    return (
        NoteEvent(Fraction(0), Fraction(durations[0]), 60 + transpose),
        NoteEvent(Fraction(1), Fraction(durations[1]), 64 + transpose),
        NoteEvent(Fraction(2), Fraction(durations[2]), 65 + transpose),
    )


def futures(
    *,
    expected_probs=(0.72, 0.72, 0.72),
    revealing_probs=(0.20, 0.82, 0.82),
    exploratory_probs=(0.08, 0.45, 0.45),
):
    expected = MainFuture(
        MainBranchKind.EXPECTED,
        motif(),
        expected_probs,
    )
    revealing = MainFuture(
        MainBranchKind.REVEALING,
        motif(transpose=7),
        revealing_probs,
    )
    exploratory = MainFuture(
        MainBranchKind.EXPLORATORY,
        (
            NoteEvent(Fraction(0), Fraction(1), 63),
            NoteEvent(Fraction(1), Fraction(1), 67),
            NoteEvent(Fraction(2), Fraction(2), 64),
        ),
        exploratory_probs,
    )
    return expected, revealing, exploratory


def test_transposition_preserves_melodic_invariant() -> None:
    assert invariant_similarity(motif(), motif(transpose=7)) == pytest.approx(1.0)


def test_duration_shape_is_part_of_the_invariant() -> None:
    altered = (
        NoteEvent(Fraction(0), Fraction(2), 60),
        NoteEvent(Fraction(2), Fraction(1), 64),
        NoteEvent(Fraction(3), Fraction(1), 65),
    )
    assert invariant_similarity(motif(), altered) < 1.0


def test_future_rejects_self_overlap() -> None:
    with pytest.raises(VoiceOverlapError):
        MainFuture(
            MainBranchKind.EXPECTED,
            (
                NoteEvent(Fraction(0), Fraction(2), 60),
                NoteEvent(Fraction(1), Fraction(1), 62),
            ),
            (0.8, 0.8),
        )


def test_exactly_three_distinct_branch_kinds_are_required() -> None:
    expected, revealing, _ = futures()
    with pytest.raises(ValueError, match="one EXPECTED"):
        evaluate_main_futures(
            (expected, revealing, revealing),
            reference_motif=motif(),
        )


def test_expected_must_be_highest_probability_local_continuation() -> None:
    branches = futures(revealing_probs=(0.80, 0.82, 0.82))
    with pytest.raises(ValueError, match="EXPECTED must be"):
        evaluate_main_futures(branches, reference_motif=motif())


def test_competing_futures_must_cover_same_time_horizon() -> None:
    expected, revealing, exploratory = futures()
    shortened = MainFuture(
        MainBranchKind.EXPLORATORY,
        (
            NoteEvent(Fraction(0), Fraction(1), 63),
            NoteEvent(Fraction(1), Fraction(1), 67),
            NoteEvent(Fraction(2), Fraction(1), 64),
        ),
        exploratory.event_probabilities,
    )
    with pytest.raises(ValueError, match="same time horizon"):
        evaluate_main_futures(
            (expected, revealing, shortened),
            reference_motif=motif(),
        )


def test_revealing_branch_requires_deep_invariant_continuity() -> None:
    expected, _, exploratory = futures()
    weak_revealing = MainFuture(
        MainBranchKind.REVEALING,
        (
            NoteEvent(Fraction(0), Fraction(1), 65),
            NoteEvent(Fraction(1), Fraction(1), 61),
            NoteEvent(Fraction(2), Fraction(2), 68),
        ),
        (0.20, 0.82, 0.82),
    )
    scores = evaluate_main_futures(
        (expected, weak_revealing, exploratory),
        reference_motif=motif(),
    )
    revealing_score = next(
        score for score in scores if score.future.kind is MainBranchKind.REVEALING
    )
    assert not revealing_score.valid
    assert revealing_score.reason == "revealing invariant floor"


def test_exploratory_branch_has_a_surprise_ceiling() -> None:
    expected, revealing, exploratory = futures(exploratory_probs=(0.01, 0.45, 0.45))
    policy = MainVoicePolicy(max_exploratory_surprise_bits=5.0)
    scores = evaluate_main_futures(
        (expected, revealing, exploratory),
        reference_motif=motif(),
        policy=policy,
    )
    exploratory_score = next(
        score for score in scores if score.future.kind is MainBranchKind.EXPLORATORY
    )
    assert not exploratory_score.valid
    assert exploratory_score.reason == "exploratory surprise ceiling"


def test_surprise_that_does_not_beat_prediction_is_not_eligible() -> None:
    branches = futures(
        revealing_probs=(0.20, 0.10, 0.10),
        exploratory_probs=(0.08, 0.10, 0.10),
    )
    decision = choose_main_future(
        branches,
        reference_motif=motif(),
        rng=SeededRandom(1),
    )
    assert decision.selected.future.kind is MainBranchKind.EXPECTED
    assert decision.eligible == (decision.baseline,)


def test_integrated_revealing_future_can_beat_the_expected_baseline() -> None:
    decision = choose_main_future(
        futures(),
        reference_motif=motif(),
        rng=SeededRandom(9),
    )
    kinds = {score.future.kind for score in decision.eligible}
    assert MainBranchKind.REVEALING in kinds
    revealing = next(
        score for score in decision.eligible if score.future.kind is MainBranchKind.REVEALING
    )
    assert revealing.total > decision.baseline.total
    assert revealing.invariant_similarity == pytest.approx(1.0)
    assert revealing.forward_probability < decision.baseline.forward_probability


def test_same_seed_replays_same_main_branch_decision() -> None:
    branches = futures()
    first = choose_main_future(
        branches,
        reference_motif=motif(),
        rng=SeededRandom(20260817),
    )
    second = choose_main_future(
        branches,
        reference_motif=motif(),
        rng=SeededRandom(20260817),
    )
    assert first.selected.future.kind is second.selected.future.kind
    assert first.selected.total == second.selected.total


def test_lookahead_event_count_is_bounded() -> None:
    short_reference = motif()[:1]
    short = tuple(
        MainFuture(kind, short_reference, (probability,))
        for kind, probability in (
            (MainBranchKind.EXPECTED, 0.8),
            (MainBranchKind.REVEALING, 0.2),
            (MainBranchKind.EXPLORATORY, 0.1),
        )
    )
    with pytest.raises(ValueError, match="lookahead event count"):
        evaluate_main_futures(short, reference_motif=short_reference)

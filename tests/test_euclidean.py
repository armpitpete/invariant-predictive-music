from fractions import Fraction

import pytest

from ipm.countertime import choose_timed_candidate, note_candidate
from ipm.countervoice import StructuralPhase, SubsidiaryRole
from ipm.euclidean import (
    euclidean_onsets,
    euclidean_pattern,
    least_aligned_rotation,
    rotation_overlap_count,
)
from ipm.model import NoteEvent, Voice
from ipm.randomness import SeededRandom


def test_three_of_eight_is_maximally_even() -> None:
    pattern = euclidean_pattern(3, 8)
    assert pattern.attack_indices == (0, 3, 6)
    assert sorted(pattern.spacing) == [2, 3, 3]
    assert max(pattern.spacing) - min(pattern.spacing) <= 1


def test_five_of_sixteen_is_maximally_even() -> None:
    pattern = euclidean_pattern(5, 16)
    assert len(pattern.attack_indices) == 5
    assert sorted(pattern.spacing) == [3, 3, 3, 3, 4]


def test_rotation_preserves_density_and_spacing() -> None:
    original = euclidean_pattern(3, 8)
    rotated = euclidean_pattern(3, 8, rotation=5)
    assert rotated.attack_indices != original.attack_indices
    assert sorted(rotated.spacing) == sorted(original.spacing)
    assert sum(rotated.hits) == sum(original.hits) == 3


def test_onsets_map_exactly_onto_requested_span() -> None:
    onsets = euclidean_onsets(3, 8, start=Fraction(4), span=Fraction(4))
    assert onsets == (Fraction(4), Fraction(11, 2), Fraction(7))
    assert all(Fraction(4) <= onset < Fraction(8) for onset in onsets)


def test_least_aligned_rotation_avoids_existing_attacks_when_possible() -> None:
    occupied = (0, 3, 6)
    base = euclidean_pattern(3, 8)
    rotated = least_aligned_rotation(3, 8, occupied_indices=occupied)
    assert rotation_overlap_count(base, occupied) == 3
    assert rotation_overlap_count(rotated, occupied) == 0


def test_euclidean_pulses_are_opportunities_not_note_quotas() -> None:
    main = Voice.from_events("M", [NoteEvent(Fraction(0), Fraction(4), 60)])
    response = Voice("B_R")
    onsets = euclidean_onsets(3, 8, span=Fraction(4), rotation=1)
    candidates = tuple(
        note_candidate(onset=onset, duration=Fraction(1, 2), pitch=67)
        for onset in onsets
    )

    decision = choose_timed_candidate(
        candidates,
        role=SubsidiaryRole.RESPONSE,
        target_voice=response,
        frozen_voices=(main,),
        phase=StructuralPhase.OPENING,
        rng=SeededRandom(11),
    )

    assert len(candidates) == 3
    assert decision.selected is None
    assert all(not score.valid for score in decision.scored)
    assert response.events == []


def test_invalid_euclidean_requests_are_rejected() -> None:
    with pytest.raises(ValueError, match="pulses"):
        euclidean_pattern(9, 8)
    with pytest.raises(ValueError, match="steps"):
        euclidean_pattern(0, 0)
    with pytest.raises(ValueError, match="span"):
        euclidean_onsets(1, 4, span=Fraction(0))

from fractions import Fraction

import pytest

from ipm import IPMConfig, NoteEvent, SeededRandom, Voice, VoiceOverlapError


def test_same_seed_replays_identical_stochastic_sequence() -> None:
    first = SeededRandom(20260817)
    second = SeededRandom(20260817)

    first_sequence = [first.random() for _ in range(32)]
    second_sequence = [second.random() for _ in range(32)]

    assert first_sequence == second_sequence


def test_weighted_choice_is_reproducible_for_same_seed() -> None:
    values = ["expected", "revealing", "exploratory"]
    weights = [0.7, 0.25, 0.05]

    first = SeededRandom(41)
    second = SeededRandom(41)

    assert [first.weighted_choice(values, weights) for _ in range(20)] == [
        second.weighted_choice(values, weights) for _ in range(20)
    ]


def test_voice_allows_adjacent_notes_without_overlap() -> None:
    voice = Voice("M")
    voice.add(NoteEvent(Fraction(0), Fraction(1), 60))
    voice.add(NoteEvent(Fraction(1), Fraction(1, 2), 62))

    assert voice.cursor == Fraction(3, 2)


def test_voice_allows_rest_between_notes() -> None:
    voice = Voice("B_R")
    voice.add(NoteEvent(Fraction(0), Fraction(1, 2), 67))
    voice.add(NoteEvent(Fraction(1), Fraction(1, 2), 69))

    assert voice.cursor == Fraction(3, 2)


def test_voice_rejects_self_overlap() -> None:
    voice = Voice("B_H")
    voice.add(NoteEvent(Fraction(0), Fraction(2), 48))

    with pytest.raises(VoiceOverlapError):
        voice.add(NoteEvent(Fraction(3, 2), Fraction(1), 52))


def test_from_events_sorts_then_validates() -> None:
    events = [
        NoteEvent(Fraction(2), Fraction(1), 64),
        NoteEvent(Fraction(0), Fraction(1), 60),
        NoteEvent(Fraction(1), Fraction(1), 62),
    ]

    voice = Voice.from_events("M", events)

    assert [event.pitch for event in voice.events] == [60, 62, 64]


def test_config_rejects_invalid_time_dimensions() -> None:
    with pytest.raises(ValueError):
        IPMConfig(seed=1, tempo_bpm=0)
    with pytest.raises(ValueError):
        IPMConfig(seed=1, bars=0)
    with pytest.raises(ValueError):
        IPMConfig(seed=1, beats_per_bar=0)

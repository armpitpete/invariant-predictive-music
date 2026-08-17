from fractions import Fraction

import pytest

from ipm import (
    NoteEvent,
    Voice,
    contextual_pair_score,
    interval_class,
    score_sonority,
    score_texture,
    set_coherence,
    slice_active_sonorities,
)


def voice(name: str, *events: tuple[int, int, int]) -> Voice:
    return Voice.from_events(
        name,
        [NoteEvent(Fraction(onset), Fraction(duration), pitch) for onset, duration, pitch in events],
    )


def test_slicing_changes_only_at_note_boundaries_and_ignores_total_silence() -> None:
    main = voice("M", (0, 4, 60))
    response = voice("B_R", (1, 1, 67), (3, 1, 69))

    slices = slice_active_sonorities([main, response])

    assert [(s.start, s.end, tuple(n.voice for n in s.notes)) for s in slices] == [
        (Fraction(0), Fraction(1), ("M",)),
        (Fraction(1), Fraction(2), ("M", "B_R")),
        (Fraction(2), Fraction(3), ("M",)),
        (Fraction(3), Fraction(4), ("M", "B_R")),
    ]


def test_sibling_voices_may_overlap_each_other() -> None:
    main = voice("M", (0, 2, 60))
    response = voice("B_R", (0, 2, 64))
    harmonic = voice("B_H", (0, 2, 67))

    slices = slice_active_sonorities([main, response, harmonic])

    assert len(slices) == 1
    assert slices[0].pitches == (60, 64, 67)


def test_interval_class_uses_pitch_class_distance() -> None:
    assert interval_class(60, 67) == 7
    assert interval_class(67, 60) == 7
    assert interval_class(60, 72) == 0


def test_whole_set_rewards_major_triad_over_semitone_cluster() -> None:
    assert set_coherence([60, 64, 67]) > 0.95
    assert set_coherence([60, 61, 62]) < 0.50


def test_short_weak_beat_dissonance_is_more_tolerable_than_long_downbeat_dissonance() -> None:
    brief = contextual_pair_score(
        60,
        61,
        duration=Fraction(1, 8),
        onset=Fraction(1, 2),
        beats_per_bar=4,
    )
    sustained = contextual_pair_score(
        60,
        61,
        duration=Fraction(2),
        onset=Fraction(0),
        beats_per_bar=4,
    )

    assert brief > sustained


def test_one_bad_pair_cannot_hide_inside_good_triad_average() -> None:
    main = voice("M", (0, 2, 60))
    response = voice("B_R", (0, 2, 67))
    clash = voice("B_H", (0, 2, 61))
    sonority = slice_active_sonorities([main, response, clash])[0]

    score = score_sonority(sonority)

    assert score.pairwise_min < 0.30
    assert score.vertical < 0.60


def test_texture_score_is_duration_weighted_and_tracks_minimum() -> None:
    main = voice("M", (0, 4, 60))
    response = voice("B_R", (0, 3, 67), (3, 1, 61))

    texture = score_texture([main, response])
    slices = slice_active_sonorities([main, response])
    scores = [score_sonority(s).vertical for s in slices]

    assert texture.slices == 2
    assert texture.duration == Fraction(4)
    assert texture.minimum == pytest.approx(min(scores))
    assert texture.weighted_mean > texture.minimum

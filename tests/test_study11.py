from fractions import Fraction

import pytest

from ipm.lanes import BASS_LANE, RHYTHM_LANE, TUNE_LANE, ScaleWorld
from ipm.midi import render_midi
from ipm.model import IPMConfig, NoteEvent
from ipm.patterns import PatternBank, capture_pattern, realise_pattern
from ipm.study10 import compose_study_010
from ipm.study11 import compose_study_011


@pytest.fixture(scope="module")
def study011():
    return compose_study_011(IPMConfig(seed=2026081704, tempo_bpm=58))


def test_pattern_bank_locks_and_releases_per_lane() -> None:
    world = ScaleWorld(60)
    events = (
        NoteEvent(Fraction(0), Fraction(3, 16), 48, 57),
        NoteEvent(Fraction(1, 2), Fraction(3, 16), 51, 57),
        NoteEvent(Fraction(1), Fraction(3, 16), 55, 57),
    )
    pattern = capture_pattern(
        events,
        world=world,
        lane=RHYTHM_LANE,
        start=Fraction(0),
        span=Fraction(2),
    )
    bank = PatternBank()
    bank.remember("a", pattern)
    bank.lock(RHYTHM_LANE, "a")
    assert bank.locked_pattern(RHYTHM_LANE) == pattern
    assert bank.locked_pattern(BASS_LANE) is None
    bank.unlock(RHYTHM_LANE)
    assert bank.locked_pattern(RHYTHM_LANE) is None


def test_locked_pattern_is_scale_and_lane_relative() -> None:
    c_world = ScaleWorld(60)
    pattern = capture_pattern(
        (
            NoteEvent(Fraction(0), Fraction(1, 4), 48, 57),
            NoteEvent(Fraction(1, 2), Fraction(1, 4), 51, 57),
            NoteEvent(Fraction(1), Fraction(1, 4), 55, 57),
        ),
        world=c_world,
        lane=RHYTHM_LANE,
        start=Fraction(0),
        span=Fraction(2),
    )
    c_rhythm = realise_pattern(
        pattern,
        world=c_world,
        lane=RHYTHM_LANE,
        start=Fraction(0),
        anchor_degree=0,
        velocity=57,
    )
    d_world = ScaleWorld(62)
    d_bass = realise_pattern(
        pattern,
        world=d_world,
        lane=BASS_LANE,
        start=Fraction(4),
        anchor_degree=2,
        velocity=57,
    )
    assert [event.onset for event in d_bass] == [Fraction(4), Fraction(9, 2), Fraction(5)]
    assert all(RHYTHM_LANE.contains(event.pitch, tonic_midi=60) for event in c_rhythm)
    assert all(BASS_LANE.contains(event.pitch, tonic_midi=62) for event in d_bass)
    assert [attack.degree_offset for attack in pattern.attacks] == [0, 2, 4]


def test_default_study_011_passes(study011) -> None:
    assert study011.trace["validation"]["passed"]
    assert [voice.name for voice in study011.voices] == ["TUNE", "BASS", "RHYTHM"]


def test_bass_is_shorter_but_stays_bass(study011) -> None:
    parent = compose_study_010(IPMConfig(seed=2026081704, tempo_bpm=58))
    old_median = sorted(event.duration for event in parent.bass.events)[len(parent.bass.events) // 2]
    new_median = sorted(event.duration for event in study011.bass.events)[len(study011.bass.events) // 2]
    assert new_median < old_median
    assert sum(event.duration <= Fraction(7, 8) for event in study011.bass.events) >= 8
    assert all(BASS_LANE.contains(event.pitch, tonic_midi=60) for event in study011.bass.events)


def test_rhythm_pattern_is_locked_then_unlocked(study011) -> None:
    lock = study011.trace["pattern_lock"]
    assert lock["remembered"] == "rhythm-a"
    assert lock["target_bars"] == [7, 8, 9]
    signatures = [application["signature"] for application in lock["applications"]]
    assert len(signatures) == 3
    assert signatures[0] == signatures[1] == signatures[2]
    assert lock["lock_state_after"] is None


def test_study_011_transposes_all_lanes() -> None:
    result = compose_study_011(
        IPMConfig(seed=2026081704, tempo_bpm=58),
        tonic_midi=62,
    )
    assert result.trace["validation"]["passed"]
    assert all(TUNE_LANE.contains(event.pitch, tonic_midi=62) for event in result.tune.events)
    assert all(BASS_LANE.contains(event.pitch, tonic_midi=62) for event in result.bass.events)
    assert all(RHYTHM_LANE.contains(event.pitch, tonic_midi=62) for event in result.rhythm.events)


def test_study_011_renders_valid_midi(study011) -> None:
    midi = render_midi(
        study011.voices,
        tempo_bpm=study011.config.tempo_bpm,
        beats_per_bar=study011.config.beats_per_bar,
    )
    assert midi[:4] == b"MThd"

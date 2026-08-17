from fractions import Fraction

import pytest

from ipm.model import NoteEvent
from ipm.register import FEMALE_LEAD_C4_B4, PitchRegister, midi_octave_number


def note(pitch: int, onset: int = 0) -> NoteEvent:
    return NoteEvent(onset=Fraction(onset), duration=Fraction(1), pitch=pitch)


def test_lead_register_cannot_exceed_one_octave() -> None:
    with pytest.raises(ValueError, match="one octave"):
        PitchRegister(60, 73)


def test_current_female_lead_target_is_exactly_c4_to_b4() -> None:
    assert FEMALE_LEAD_C4_B4.low == 60
    assert FEMALE_LEAD_C4_B4.high == 71
    assert FEMALE_LEAD_C4_B4.span == 11
    assert FEMALE_LEAD_C4_B4.is_single_named_octave
    assert midi_octave_number(FEMALE_LEAD_C4_B4.low) == 4
    assert midi_octave_number(FEMALE_LEAD_C4_B4.high) == 4


def test_c4_to_c5_is_not_a_single_named_octave() -> None:
    assert not PitchRegister(60, 72, centre=66).is_single_named_octave


def test_projection_removes_octave_drift_without_changing_pitch_class() -> None:
    source = (note(60, 0), note(76, 1), note(91, 2), note(108, 3), note(120, 4))
    projected = FEMALE_LEAD_C4_B4.project_events(source)

    assert FEMALE_LEAD_C4_B4.contains_events(projected)
    assert FEMALE_LEAD_C4_B4.ambitus(projected) <= 11
    assert FEMALE_LEAD_C4_B4.events_share_named_octave(projected)
    assert {midi_octave_number(event.pitch) for event in projected} == {4}
    assert [event.pitch % 12 for event in projected] == [event.pitch % 12 for event in source]
    assert [event.onset for event in projected] == [event.onset for event in source]
    assert [event.duration for event in projected] == [event.duration for event in source]


def test_boundary_c_cannot_escape_into_c5() -> None:
    # A C pitch class must remain C4 even when the previous lead note is B4.
    assert FEMALE_LEAD_C4_B4.project_pitch(84, previous=71) == 60


def test_hard_register_rejects_c5() -> None:
    with pytest.raises(ValueError, match="hard register"):
        FEMALE_LEAD_C4_B4.require_events((note(60), note(72, 1)))

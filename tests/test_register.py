from fractions import Fraction

import pytest

from ipm.model import NoteEvent
from ipm.register import FEMALE_LEAD_C4_C5, PitchRegister


def note(pitch: int, onset: int = 0) -> NoteEvent:
    return NoteEvent(onset=Fraction(onset), duration=Fraction(1), pitch=pitch)


def test_lead_register_cannot_exceed_one_octave() -> None:
    with pytest.raises(ValueError, match="one octave"):
        PitchRegister(60, 73)


def test_current_female_lead_target_is_exactly_c4_to_c5() -> None:
    assert FEMALE_LEAD_C4_C5.low == 60
    assert FEMALE_LEAD_C4_C5.high == 72
    assert FEMALE_LEAD_C4_C5.span == 12


def test_projection_removes_octave_drift_without_changing_pitch_class() -> None:
    source = (note(60, 0), note(76, 1), note(91, 2), note(108, 3), note(120, 4))
    projected = FEMALE_LEAD_C4_C5.project_events(source)

    assert FEMALE_LEAD_C4_C5.contains_events(projected)
    assert FEMALE_LEAD_C4_C5.ambitus(projected) <= 12
    assert [event.pitch % 12 for event in projected] == [event.pitch % 12 for event in source]
    assert [event.onset for event in projected] == [event.onset for event in source]
    assert [event.duration for event in projected] == [event.duration for event in source]


def test_projection_uses_previous_note_to_choose_boundary_c() -> None:
    register = PitchRegister(60, 72, centre=66)
    # C can be C4 or C5. From B4 the vocal-continuity choice is C5.
    assert register.project_pitch(84, previous=71) == 72
    # From D4 the continuity choice is C4.
    assert register.project_pitch(84, previous=62) == 60


def test_hard_register_rejects_out_of_range_event_sequence() -> None:
    with pytest.raises(ValueError, match="hard register"):
        FEMALE_LEAD_C4_C5.require_events((note(60), note(74, 1)))

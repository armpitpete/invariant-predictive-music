from ipm.register import midi_octave_number
from ipm.study2 import compose_study_002
from ipm.study3 import compose_study_003


def test_study_003_passes_register_acceptance_gate() -> None:
    result = compose_study_003()
    assert result.trace["validation"]["passed"], result.trace["validation"]["checks"]


def test_study_003_lead_is_hard_limited_to_c4_b4() -> None:
    result = compose_study_003()
    pitches = [event.pitch for event in result.main.events]
    assert min(pitches) >= 60
    assert max(pitches) <= 71
    assert max(pitches) - min(pitches) <= 11
    assert {midi_octave_number(pitch) for pitch in pitches} == {4}


def test_study_003_changes_only_lead_octave_placement() -> None:
    base = compose_study_002()
    result = compose_study_003()

    assert [event.pitch % 12 for event in result.main.events] == [
        event.pitch % 12 for event in base.main.events
    ]
    assert [(event.onset, event.duration) for event in result.main.events] == [
        (event.onset, event.duration) for event in base.main.events
    ]
    assert result.response.events == base.response.events
    assert result.harmony.events == base.harmony.events


def test_study_003_register_is_recorded_in_trace() -> None:
    result = compose_study_003()
    assert result.trace["lead_register"] == {
        "low": 60,
        "high": 71,
        "centre": 66,
        "span_semitones": 11,
    }
    checks = result.trace["validation"]["checks"]
    assert checks["lead_register_is_single_named_octave"]
    assert checks["lead_events_share_named_octave"]

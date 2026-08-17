from ipm.model import IPMConfig
from ipm.study4 import compose_study_004
from ipm.study5 import compose_study_005


def test_study_005_passes_register_correction_gate() -> None:
    result = compose_study_005()
    assert result.trace["validation"]["passed"] is True
    assert all(result.trace["validation"]["checks"].values())


def test_only_subsidiary_octaves_change_from_study_004() -> None:
    config = IPMConfig(seed=2026081704, tempo_bpm=58)
    parent = compose_study_004(config)
    fixed = compose_study_005(config)

    assert fixed.main.events == parent.main.events
    assert [(e.onset, e.duration, e.velocity) for e in fixed.response.events] == [
        (e.onset, e.duration, e.velocity) for e in parent.response.events
    ]
    assert [(e.onset, e.duration, e.velocity) for e in fixed.harmony.events] == [
        (e.onset, e.duration, e.velocity) for e in parent.harmony.events
    ]
    assert [e.pitch % 12 for e in fixed.response.events] == [
        e.pitch % 12 for e in parent.response.events
    ]
    assert [e.pitch % 12 for e in fixed.harmony.events] == [
        e.pitch % 12 for e in parent.harmony.events
    ]


def test_response_is_locked_to_c3_b3() -> None:
    result = compose_study_005()
    pitches = [event.pitch for event in result.response.events]
    assert pitches
    assert min(pitches) >= 48
    assert max(pitches) <= 59


def test_harmony_is_locked_to_c2_b2() -> None:
    result = compose_study_005()
    pitches = [event.pitch for event in result.harmony.events]
    assert pitches
    assert min(pitches) >= 36
    assert max(pitches) <= 47


def test_no_subsidiary_pitch_can_spike_above_lead_register() -> None:
    result = compose_study_005()
    assert max(event.pitch for event in (*result.response.events, *result.harmony.events)) < 60


def test_study_005_is_deterministic() -> None:
    config = IPMConfig(seed=2026081704, tempo_bpm=58)
    first = compose_study_005(config)
    second = compose_study_005(config)
    assert first.voices == second.voices
    assert first.trace == second.trace

from fractions import Fraction

from ipm.midi import render_midi
from ipm.model import IPMConfig
from ipm.study9 import compose_study_009


def _result():
    return compose_study_009(IPMConfig(seed=2026081704, tempo_bpm=58))


def test_default_study_009_passes_listening_correction_gate() -> None:
    assert _result().trace["validation"]["passed"]


def test_lead_contains_genuinely_short_attacks_without_losing_long_values() -> None:
    result = _result()
    durations = [event.duration for event in result.main.events]
    assert sum(duration <= Fraction(3, 16) for duration in durations) >= 8
    assert any(duration >= Fraction(7, 8) for duration in durations)


def test_micro_bursts_return_to_the_structural_anchor() -> None:
    result = _result()
    burst_decisions = [
        decision
        for bar in result.trace["micro_rhythm"]
        for decision in bar["decisions"]
        if decision["has_short_attack"]
    ]
    assert len(burst_decisions) >= 6
    assert all(decision["pitches"][-1] in {60, 62, 63, 65, 67, 68, 70} for decision in burst_decisions)


def test_both_subsidiary_roles_are_available_and_sound_as_figures() -> None:
    result = _result()
    branches = result.trace["branch_motifs"]
    assert branches["available"]["B_R"] >= 2
    assert branches["available"]["B_H"] >= 1
    assert len(branches["B_R"]) >= 2
    assert len(branches["B_H"]) >= 1
    for motif in branches["B_R"] + branches["B_H"]:
        assert len(motif["events"]) >= 2
        assert len({event["pitch"] for event in motif["events"]}) >= 2
        assert all(Fraction(*event["duration"]) <= Fraction(3, 16) for event in motif["events"])
        assert all(margin > 0 for margin in motif["margins"])


def test_branch_registers_remain_below_the_lead() -> None:
    result = _result()
    assert all(48 <= event.pitch <= 59 for event in result.response.events)
    assert all(36 <= event.pitch <= 47 for event in result.harmony.events)
    assert all(event.pitch < 60 for event in (*result.response.events, *result.harmony.events))


def test_study_009_is_deterministic() -> None:
    first = _result()
    second = _result()
    assert first.main.events == second.main.events
    assert first.response.events == second.response.events
    assert first.harmony.events == second.harmony.events
    assert first.trace["branch_motifs"] == second.trace["branch_motifs"]


def test_study_009_renders_valid_midi_header() -> None:
    result = _result()
    midi = render_midi(
        result.voices,
        tempo_bpm=result.config.tempo_bpm,
        beats_per_bar=result.config.beats_per_bar,
    )
    assert midi[:4] == b"MThd"

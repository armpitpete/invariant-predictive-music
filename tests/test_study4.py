from fractions import Fraction

from ipm.midi import render_midi
from ipm.model import IPMConfig
from ipm.study4 import compose_study_004


def test_default_study_004_passes_corrective_gate() -> None:
    result = compose_study_004()
    assert result.trace["validation"]["passed"] is True
    assert all(result.trace["validation"]["checks"].values())


def test_study_004_is_slow_and_aeolian() -> None:
    result = compose_study_004()
    assert result.config.tempo_bpm == 58
    assert result.trace["mode"] == "C Aeolian"
    allowed = {0, 2, 3, 5, 7, 8, 10}
    assert {(event.pitch - 60) % 12 for event in result.main.events}.issubset(allowed)


def test_study_004_lead_remains_inside_single_c4_b4_octave() -> None:
    result = compose_study_004()
    pitches = [event.pitch for event in result.main.events]
    assert pitches
    assert all(60 <= pitch <= 71 for pitch in pitches)
    assert max(pitches) - min(pitches) <= 11


def test_every_rhythm_partition_preserves_parent_time_budget() -> None:
    result = compose_study_004()
    decisions = result.trace["rhythm_budget_decisions"]
    assert decisions
    assert any(item["attacks"] > 1 for item in decisions)

    for item in decisions:
        source = item["source_event"]["duration"]
        source_duration = Fraction(source[0], source[1])
        allocated = sum(
            (Fraction(num, den) for num, den in item["segments"]),
            Fraction(0),
        )
        assert allocated == source_duration


def test_time_budget_realisation_creates_actual_breath() -> None:
    result = compose_study_004()
    gaps = [
        right.onset - left.end
        for left, right in zip(result.main.events, result.main.events[1:], strict=False)
    ]
    assert sum(gap > 0 for gap in gaps) >= len(gaps) // 2


def test_study_004_is_deterministic_for_same_seed() -> None:
    config = IPMConfig(seed=2026081704, tempo_bpm=58)
    first = compose_study_004(config)
    second = compose_study_004(config)

    assert first.main.events == second.main.events
    assert first.response.events == second.response.events
    assert first.harmony.events == second.harmony.events
    assert first.trace == second.trace


def test_study_004_preserves_countervoices_without_requiring_three_voice_stack() -> None:
    result = compose_study_004()
    ratios = result.trace["metrics"]["texture_ratio"]
    assert result.response.events
    assert result.harmony.events
    assert ratios.get("M+B_R+B_H", 0.0) <= 0.125


def test_study_004_midi_is_valid_format_one() -> None:
    result = compose_study_004()
    data = render_midi(
        result.voices,
        tempo_bpm=result.config.tempo_bpm,
        beats_per_bar=result.config.beats_per_bar,
    )
    assert data[:4] == b"MThd"
    assert int.from_bytes(data[8:10], "big") == 1
    assert data.count(b"MTrk") == 4

from fractions import Fraction
from statistics import median

from ipm.midi import render_midi
from ipm.model import IPMConfig
from ipm.study8 import compose_study_008


def test_default_study_008_passes_sequential_validation() -> None:
    result = compose_study_008(IPMConfig(seed=2026081704, tempo_bpm=58))
    assert result.trace["validation"]["passed"]


def test_every_bar_receives_the_state_created_by_the_previous_bar() -> None:
    result = compose_study_008(IPMConfig(seed=2026081704, tempo_bpm=58))
    bars = result.trace["sequential_bar_decisions"]
    for index in range(1, len(bars)):
        assert bars[index]["state_before"] == bars[index - 1]["state_after"]
        assert bars[index]["state_before"]["last_pitch"] == bars[index - 1]["pitches"][-1]


def test_main_is_not_filled_from_parent_pitch_anchors() -> None:
    result = compose_study_008(IPMConfig(seed=2026081704, tempo_bpm=58))
    bars = result.trace["sequential_bar_decisions"]
    assert all("source_anchors" not in bar for bar in bars)
    assert all(bar["decision_unit"] == "whole_bar" for bar in bars)


def test_each_bar_jointly_decides_an_exact_four_beat_object() -> None:
    result = compose_study_008(IPMConfig(seed=2026081704, tempo_bpm=58))
    for bar in result.trace["sequential_bar_decisions"]:
        assert sum(
            (Fraction(*cell["duration"]) for cell in bar["cells"]),
            Fraction(0),
        ) == Fraction(4)
        assert len(bar["pitches"]) == sum(cell["kind"] == "note" for cell in bar["cells"])
        assert len(bar["alternatives"]) == 12


def test_active_surface_and_register_survive_the_architecture_change() -> None:
    result = compose_study_008(IPMConfig(seed=2026081704, tempo_bpm=58))
    assert len(result.main.events) >= 56
    assert median(event.duration for event in result.main.events) < Fraction(1)
    assert all(60 <= event.pitch <= 71 for event in result.main.events)
    assert result.main.events[-1].pitch == 60


def test_study_008_is_deterministic() -> None:
    first = compose_study_008(IPMConfig(seed=2026081704, tempo_bpm=58))
    second = compose_study_008(IPMConfig(seed=2026081704, tempo_bpm=58))
    assert first.main.events == second.main.events
    assert first.trace["sequential_bar_decisions"] == second.trace["sequential_bar_decisions"]


def test_study_008_renders_valid_midi_header() -> None:
    result = compose_study_008(IPMConfig(seed=2026081704, tempo_bpm=58))
    midi = render_midi(
        result.voices,
        tempo_bpm=result.config.tempo_bpm,
        beats_per_bar=result.config.beats_per_bar,
    )
    assert midi[:4] == b"MThd"

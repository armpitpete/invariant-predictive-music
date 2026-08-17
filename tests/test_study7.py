from fractions import Fraction

from ipm.model import IPMConfig
from ipm.study7 import compose_study_007


def test_default_study_007_passes_active_surface_gate() -> None:
    result = compose_study_007()
    assert result.trace["validation"]["passed"] is True
    assert all(result.trace["validation"]["checks"].values())


def test_attack_rate_is_materially_higher_than_study_006() -> None:
    result = compose_study_007()
    assert len(result.main.events) >= 56


def test_most_surface_cells_are_one_beat_or_shorter() -> None:
    result = compose_study_007()
    cells = [
        Fraction(*cell["duration"])
        for bar in result.trace["surface_rhythm_decisions"]
        for cell in bar["cells"]
        if cell["kind"] == "note"
    ]
    assert sum(duration <= 1 for duration in cells) / len(cells) >= 0.80
    assert sum(duration == Fraction(1, 2) for duration in cells) / len(cells) >= 0.30
    assert sum(duration >= 2 for duration in cells) / len(cells) <= 0.08


def test_slow_tempo_is_preserved_while_notes_get_shorter() -> None:
    result = compose_study_007()
    assert result.config.tempo_bpm == 58
    durations = sorted(event.duration for event in result.main.events)
    assert durations[len(durations) // 2] < 1


def test_literal_rests_and_bar_variety_survive() -> None:
    result = compose_study_007()
    bars = result.trace["surface_rhythm_decisions"]
    rest_bars = [bar for bar in bars if any(cell["kind"] == "rest" for cell in bar["cells"])]
    shapes = {
        tuple((cell["kind"], tuple(cell["duration"])) for cell in bar["cells"])
        for bar in bars
    }
    assert len(rest_bars) >= 6
    assert len(shapes) >= 10


def test_register_spike_fix_is_preserved() -> None:
    result = compose_study_007()
    assert all(60 <= event.pitch <= 71 for event in result.main.events)
    assert all(48 <= event.pitch <= 59 for event in result.response.events)
    assert all(36 <= event.pitch <= 47 for event in result.harmony.events)


def test_same_seed_replays_same_surface() -> None:
    config = IPMConfig(seed=2026081704, tempo_bpm=58)
    first = compose_study_007(config)
    second = compose_study_007(config)
    assert first.voices == second.voices
    assert first.trace == second.trace

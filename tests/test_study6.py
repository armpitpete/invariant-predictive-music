from fractions import Fraction

from ipm.model import IPMConfig
from ipm.study6 import compose_study_006


def test_default_study_006_passes_bar_rhythm_gate() -> None:
    result = compose_study_006()
    assert result.trace["validation"]["passed"] is True
    assert all(result.trace["validation"]["checks"].values())


def test_each_bar_is_exactly_four_beats_of_notes_and_rests() -> None:
    result = compose_study_006()
    bars = result.trace["bar_rhythm_decisions"]
    assert len(bars) == 16
    for bar in bars:
        assert sum(
            (Fraction(*cell["duration"]) for cell in bar["cells"]),
            Fraction(0),
        ) == Fraction(4)
        assert any(cell["kind"] == "note" for cell in bar["cells"])


def test_default_seed_exercises_simple_and_spacious_bar_forms() -> None:
    result = compose_study_006()
    shapes = [
        [(cell["kind"], Fraction(*cell["duration"])) for cell in bar["cells"]]
        for bar in result.trace["bar_rhythm_decisions"]
    ]

    assert [("note", Fraction(4))] in shapes
    assert [("note", Fraction(2)), ("note", Fraction(2))] in shapes
    assert any(shape[0][0] == "rest" for shape in shapes)
    assert any(shape[-1][0] == "rest" for shape in shapes)
    assert any(
        shape == [
            ("note", Fraction(2)),
            ("rest", Fraction(1)),
            ("note", Fraction(1)),
        ]
        or shape == [
            ("note", Fraction(1)),
            ("rest", Fraction(1)),
            ("note", Fraction(2)),
        ]
        for shape in shapes
    )


def test_bar_grammar_is_not_the_old_note_partition_trace() -> None:
    result = compose_study_006()
    assert "bar_rhythm_decisions" in result.trace
    assert "rhythm_budget_decisions" not in result.trace
    assert "parent_rhythm_budget_decisions" in result.trace


def test_new_main_has_real_spaces_and_no_self_overlap() -> None:
    result = compose_study_006()
    events = result.main.events
    assert events
    assert any(
        right.onset > left.end
        for left, right in zip(events, events[1:], strict=False)
    )
    assert all(
        right.onset >= left.end
        for left, right in zip(events, events[1:], strict=False)
    )


def test_hard_registers_survive_rhythm_change() -> None:
    result = compose_study_006()
    assert all(60 <= event.pitch <= 71 for event in result.main.events)
    assert all(48 <= event.pitch <= 59 for event in result.response.events)
    assert all(36 <= event.pitch <= 47 for event in result.harmony.events)


def test_kept_subsidiary_notes_still_beat_silence() -> None:
    result = compose_study_006()
    kept = [item for item in result.trace["subsidiary_rescreen"] if item["kept"]]
    assert kept
    assert all(item["note_score"] > item["silence_score"] for item in kept)


def test_final_main_attack_still_resolves_to_tonic() -> None:
    result = compose_study_006()
    assert result.main.events[-1].pitch % 12 == 0


def test_study_006_is_deterministic() -> None:
    config = IPMConfig(seed=2026081704, tempo_bpm=58)
    first = compose_study_006(config)
    second = compose_study_006(config)
    assert first.voices == second.voices
    assert first.trace == second.trace

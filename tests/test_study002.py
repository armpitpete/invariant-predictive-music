from ipm.midi import render_midi
from ipm.model import IPMConfig
from ipm.study002 import compose_study_002


def test_default_study_002_passes_corrected_acceptance_gate() -> None:
    result = compose_study_002()
    assert result.trace["validation"]["passed"] is True
    assert all(result.trace["validation"]["checks"].values())


def test_study_002_is_deterministic() -> None:
    first = compose_study_002(IPMConfig(seed=20260817, tempo_bpm=58))
    second = compose_study_002(IPMConfig(seed=20260817, tempo_bpm=58))

    assert first.structural_main == second.structural_main
    assert first.main.events == second.main.events
    assert first.response.events == second.response.events
    assert first.harmony.events == second.harmony.events
    assert first.trace == second.trace
    assert render_midi(first.voices, tempo_bpm=58) == render_midi(second.voices, tempo_bpm=58)


def test_lead_is_strictly_inside_one_midi_octave() -> None:
    result = compose_study_002()
    pitches = [event.pitch for event in result.main.events]

    assert pitches
    assert all(60 <= pitch <= 71 for pitch in pitches)
    assert max(pitches) - min(pitches) <= 11


def test_structural_phrase_is_sixteen_bars_even_with_breath_gaps() -> None:
    result = compose_study_002()

    assert result.structural_main[-1].end == 64
    assert result.main.events[-1].end <= 64
    assert result.main.events[-1].pitch % 12 == 0


def test_rhythm_budget_is_surface_transform_not_fixed_template() -> None:
    result = compose_study_002()
    decisions = result.trace["rhythm_decisions"]
    shapes = {tuple(tuple(segment) for segment in item["segments"]) for item in decisions}

    assert len(shapes) >= 4
    assert any(item["attacks"] == 1 for item in decisions)
    assert any(item["attacks"] > 1 for item in decisions)
    for item in decisions:
        anchor_duration = item["anchor"]["duration"]
        anchor_fraction = anchor_duration[0] / anchor_duration[1]
        realised_budget = sum(segment[0] / segment[1] for segment in item["segments"])
        assert realised_budget == anchor_fraction


def test_main_voice_contains_real_breath_between_attacks() -> None:
    result = compose_study_002()
    events = result.main.events
    gaps = [right.onset - left.end for left, right in zip(events, events[1:], strict=False)]

    assert sum(gap > 0 for gap in gaps) >= len(events) // 2


def test_countervoices_are_not_forced_to_main_note_boundaries() -> None:
    result = compose_study_002()
    selected = [
        item
        for item in result.trace["counter_decisions"]
        if item["selected_action"] == "note"
    ]

    assert selected
    assert any(item["selected_note"]["onset"] != item["window"][0] for item in selected)
    for item in selected:
        assert item["selected_score"] > item["silence_score"]


def test_texture_prefers_solo_and_two_note_moments_over_chorale_stack() -> None:
    result = compose_study_002()
    ratios = result.trace["metrics"]["texture_ratio"]

    assert ratios.get("M", 0.0) >= 0.55
    assert ratios.get("M+B_R", 0.0) + ratios.get("M+B_H", 0.0) >= 0.05
    assert ratios.get("M+B_R+B_H", 0.0) <= 0.06


def test_main_surprise_still_has_to_beat_expected() -> None:
    result = compose_study_002()
    for decision in result.trace["main_decisions"]:
        if decision["selected"] != "expected":
            assert decision["selected_score"] > decision["baseline_score"]


def test_study_002_midi_remains_standard_format_one() -> None:
    result = compose_study_002()
    data = render_midi(
        result.voices,
        tempo_bpm=result.config.tempo_bpm,
        beats_per_bar=result.config.beats_per_bar,
    )

    assert data[:4] == b"MThd"
    assert int.from_bytes(data[8:10], "big") == 1
    assert int.from_bytes(data[10:12], "big") == 4
    assert data.count(b"MTrk") == 4

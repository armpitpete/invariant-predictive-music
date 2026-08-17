import json

from ipm.midi import render_midi
from ipm.model import IPMConfig
from ipm.study import compose_study, write_study_files


def test_default_study_passes_acceptance_checks() -> None:
    result = compose_study()
    assert result.trace["validation"]["passed"] is True
    assert all(result.trace["validation"]["checks"].values())


def test_default_study_is_deterministic() -> None:
    first = compose_study(IPMConfig(seed=20260817))
    second = compose_study(IPMConfig(seed=20260817))
    assert first.main.events == second.main.events
    assert first.response.events == second.response.events
    assert first.harmony.events == second.harmony.events
    assert first.trace == second.trace
    assert render_midi(first.voices) == render_midi(second.voices)


def test_study_is_exactly_sixteen_bars_and_resolves_to_tonic() -> None:
    result = compose_study()
    assert result.main.cursor == 64
    assert len(result.main.events) == 32
    assert result.main.events[-1].pitch % 12 == result.trace["tonic_midi"] % 12


def test_main_surprise_must_beat_expected_baseline() -> None:
    result = compose_study()
    assert len(result.trace["main_decisions"]) == 8
    for decision in result.trace["main_decisions"]:
        if decision["selected"] != "expected":
            assert decision["selected_score"] > decision["baseline_score"]


def test_every_selected_counter_note_beats_silence() -> None:
    result = compose_study()
    assert len(result.trace["counter_decisions"]) == 64
    selected_notes = [
        decision
        for decision in result.trace["counter_decisions"]
        if decision["selected_action"] == "note"
    ]
    assert selected_notes
    for decision in selected_notes:
        assert decision["silence_score"] is not None
        assert decision["selected_score"] > decision["silence_score"]


def test_texture_remains_sparse_and_three_voice_moment_is_exceptional() -> None:
    result = compose_study()
    ratios = result.trace["metrics"]["texture_ratio"]
    assert ratios["M"] > max(value for name, value in ratios.items() if name != "M")
    assert 0 < ratios["M+B_R+B_H"] <= 0.125
    assert result.response.events
    assert result.harmony.events


def test_complete_texture_respects_vertical_floor() -> None:
    result = compose_study()
    assert result.trace["metrics"]["vertical_minimum"] >= 0.65


def test_midi_is_format_one_with_tempo_plus_three_voice_tracks() -> None:
    result = compose_study()
    data = render_midi(
        result.voices,
        tempo_bpm=result.config.tempo_bpm,
        beats_per_bar=result.config.beats_per_bar,
    )
    assert data[:4] == b"MThd"
    assert int.from_bytes(data[4:8], "big") == 6
    assert int.from_bytes(data[8:10], "big") == 1
    assert int.from_bytes(data[10:12], "big") == 4
    assert int.from_bytes(data[12:14], "big") == 480
    assert data.count(b"MTrk") == 4


def test_write_study_files_emits_midi_and_json_trace(tmp_path) -> None:
    result = compose_study()
    midi_path, trace_path = write_study_files(
        result,
        midi_path=tmp_path / "study.mid",
        trace_path=tmp_path / "study.trace.json",
    )
    assert midi_path.read_bytes()[:4] == b"MThd"
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert trace["validation"]["passed"] is True
    assert trace["seed"] == 20260817

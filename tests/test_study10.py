from fractions import Fraction

from ipm.lanes import BASS_LANE, RHYTHM_LANE, TUNE_LANE, ScaleWorld
from ipm.midi import render_midi
from ipm.model import IPMConfig
from ipm.study10 import compose_study_010


def test_scale_degrees_project_into_separate_lanes() -> None:
    world = ScaleWorld(60)
    for degree in range(7):
        tune = world.project_degree(degree, TUNE_LANE)
        rhythm = world.project_degree(degree, RHYTHM_LANE)
        bass = world.project_degree(degree, BASS_LANE)
        assert tune - rhythm == 12
        assert tune - bass == 24
        assert world.lane_degree(tune, TUNE_LANE) == degree
        assert world.lane_degree(rhythm, RHYTHM_LANE) == degree
        assert world.lane_degree(bass, BASS_LANE) == degree


def test_transposing_tonic_moves_every_lane_equally() -> None:
    c_world = ScaleWorld(60)
    d_world = c_world.transpose_tonic(2)
    for lane in (TUNE_LANE, BASS_LANE, RHYTHM_LANE):
        for degree in range(7):
            assert d_world.project_degree(degree, lane) == c_world.project_degree(degree, lane) + 2


def test_default_study_010_passes_three_lane_validation() -> None:
    result = compose_study_010(IPMConfig(seed=2026081704, tempo_bpm=58))
    assert result.trace["validation"]["passed"]
    assert [voice.name for voice in result.voices] == ["TUNE", "BASS", "RHYTHM"]


def test_every_note_fits_its_lane_and_shared_scale() -> None:
    result = compose_study_010(IPMConfig(seed=2026081704, tempo_bpm=58))
    world = ScaleWorld(60)
    for voice, lane in (
        (result.tune, TUNE_LANE),
        (result.bass, BASS_LANE),
        (result.rhythm, RHYTHM_LANE),
    ):
        assert all(lane.contains(event.pitch, tonic_midi=60) for event in voice.events)
        assert all(world.pitch_is_in_scale(event.pitch) for event in voice.events)


def test_bass_is_slower_than_rhythm() -> None:
    result = compose_study_010(IPMConfig(seed=2026081704, tempo_bpm=58))
    assert min(event.duration for event in result.bass.events) >= Fraction(15, 8)
    assert max(event.duration for event in result.rhythm.events) <= Fraction(3, 16)


def test_rhythm_is_a_distributed_arpeggiated_part() -> None:
    result = compose_study_010(IPMConfig(seed=2026081704, tempo_bpm=58))
    active_bars = {int(event.onset // 4) for event in result.rhythm.events}
    assert len(active_bars) >= 10
    assert max(active_bars) >= 12
    for item in result.trace["rhythm_decisions"]:
        if item["selected"] is not None:
            assert len(item["selected"]["events"]) == 4
            assert len({event["pitch"] for event in item["selected"]["events"]}) >= 3


def test_study_010_transposes_without_lane_leakage() -> None:
    result = compose_study_010(
        IPMConfig(seed=2026081704, tempo_bpm=58),
        tonic_midi=62,
    )
    world = ScaleWorld(62)
    assert all(TUNE_LANE.contains(event.pitch, tonic_midi=62) for event in result.tune.events)
    assert all(BASS_LANE.contains(event.pitch, tonic_midi=62) for event in result.bass.events)
    assert all(RHYTHM_LANE.contains(event.pitch, tonic_midi=62) for event in result.rhythm.events)
    assert all(world.pitch_is_in_scale(event.pitch) for voice in result.voices for event in voice.events)


def test_study_010_is_deterministic() -> None:
    config = IPMConfig(seed=2026081704, tempo_bpm=58)
    first = compose_study_010(config)
    second = compose_study_010(config)
    assert first.tune.events == second.tune.events
    assert first.bass.events == second.bass.events
    assert first.rhythm.events == second.rhythm.events
    assert first.trace["rhythm_decisions"] == second.trace["rhythm_decisions"]


def test_study_010_renders_valid_midi_header() -> None:
    result = compose_study_010(IPMConfig(seed=2026081704, tempo_bpm=58))
    midi = render_midi(
        result.voices,
        tempo_bpm=result.config.tempo_bpm,
        beats_per_bar=result.config.beats_per_bar,
    )
    assert midi[:4] == b"MThd"

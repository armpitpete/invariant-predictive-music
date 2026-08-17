import pytest

from ipm.engine import (
    BassControls,
    ExperimentMode,
    InstrumentConfig,
    PatternLockSpec,
    RhythmControls,
    compose,
    compose_experiment_bundle,
)
from ipm.lanes import BASS_LANE, RHYTHM_LANE, TUNE_LANE, ScaleWorld


def _accepted_bass(result):
    return sum(
        decision["accepted"]
        for bar in result.trace["bass_decisions"]
        for decision in bar["decisions"]
    )


def test_default_v02_is_a_valid_three_lane_instrument():
    result = compose()
    assert result.trace["validation"]["passed"]
    assert [voice.name for voice in result.voices] == ["TUNE", "BASS", "RHYTHM"]
    assert result.trace["architecture"]["experiment_mode"] == "ipm"
    assert len(result.trace["tune_decisions"]) == 16
    assert all("silence_score" in bar for bar in result.trace["rhythm_decisions"])
    assert all(
        not bar["accepted"] or bar["minimum_attack_score"] > bar["silence_score"]
        for bar in result.trace["rhythm_decisions"]
    )


def test_bass_controls_are_real_parameters_not_study_constants():
    low = compose(
        InstrumentConfig(
            bars=8,
            bass=BassControls(activity=0.05, sustain=0.90, movement=0.05),
        )
    )
    high = compose(
        InstrumentConfig(
            bars=8,
            bass=BassControls(activity=0.95, sustain=0.20, movement=0.85),
        )
    )
    assert _accepted_bass(high) >= _accepted_bass(low)

    low_segments = sum(len(bar["pattern"]) for bar in low.trace["bass_decisions"])
    high_segments = sum(len(bar["pattern"]) for bar in high.trace["bass_decisions"])
    assert high_segments > low_segments


def test_predictable_mode_never_replaces_expected_baseline():
    result = compose(InstrumentConfig(bars=8, mode=ExperimentMode.PREDICTABLE))
    assert all(
        decision["selected_branch"] == "expected"
        for decision in result.trace["tune_decisions"]
    )


def test_all_three_falsification_conditions_share_high_level_config():
    bundle = compose_experiment_bundle(InstrumentConfig(bars=8))
    assert set(bundle) == set(ExperimentMode)
    for mode, result in bundle.items():
        assert result.config.mode is mode
        assert result.config.seed == 2026081704
        assert result.config.tonic_midi == 60
        assert len(result.trace["tune_decisions"]) == 8


def test_pattern_lock_preserves_geometry_and_still_respects_silence():
    result = compose(
        InstrumentConfig(
            bars=8,
            pattern_locks=(
                PatternLockSpec(
                    lane="BASS",
                    source_bar=0,
                    start_bar=3,
                    end_bar=5,
                ),
            ),
        )
    )
    lock = result.trace["pattern_locks"][0]
    assert lock["unlocked"]
    assert lock["lane"] == "BASS"
    assert len(lock["applications"]) == 3
    assert lock["signature"]
    assert all(
        not application["accepted"]
        or application["minimum_attack_score"] > application["silence_score"]
        for application in lock["applications"]
    )


def test_transposition_moves_every_lane_without_leakage():
    result = compose(InstrumentConfig(bars=8, tonic_midi=62))
    world = ScaleWorld(62)
    assert all(TUNE_LANE.contains(event.pitch, tonic_midi=62) for event in result.tune.events)
    assert all(BASS_LANE.contains(event.pitch, tonic_midi=62) for event in result.bass.events)
    assert all(RHYTHM_LANE.contains(event.pitch, tonic_midi=62) for event in result.rhythm.events)
    assert all(
        world.pitch_is_in_scale(event.pitch)
        for voice in result.voices
        for event in voice.events
    )


def test_controls_reject_values_outside_unit_interval():
    with pytest.raises(ValueError):
        BassControls(activity=1.01)
    with pytest.raises(ValueError):
        RhythmControls(gate=-0.01)


def test_generation_is_deterministic():
    config = InstrumentConfig(bars=8)
    left = compose(config)
    right = compose(config)
    assert left.voices[0].events == right.voices[0].events
    assert left.voices[1].events == right.voices[1].events
    assert left.voices[2].events == right.voices[2].events
    assert left.trace["metrics"] == right.trace["metrics"]

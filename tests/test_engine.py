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


def _accepted_rhythm(result):
    return sum(bar["accepted"] for bar in result.trace["rhythm_decisions"])


def test_default_v02_is_a_valid_sparse_three_lane_instrument():
    result = compose()
    assert result.trace["validation"]["passed"]
    assert [voice.name for voice in result.voices] == ["TUNE", "BASS", "RHYTHM"]
    assert result.trace["architecture"]["experiment_mode"] == "ipm"
    assert len(result.trace["tune_decisions"]) == 16

    bass_decisions = [
        decision
        for bar in result.trace["bass_decisions"]
        for decision in bar["decisions"]
    ]
    rhythm_decisions = result.trace["rhythm_decisions"]
    assert any(not decision["opportunity"] for decision in bass_decisions)
    assert any(not bar["opportunity"] for bar in rhythm_decisions)
    assert any(not decision["accepted"] for decision in bass_decisions)
    assert any(not bar["accepted"] for bar in rhythm_decisions)
    assert all(
        not bar["accepted"]
        or bar["minimum_attack_score"] > bar["silence_score"]
        for bar in rhythm_decisions
    )

    occupancy = result.trace["metrics"]["texture_occupancy"]
    assert occupancy["TUNE"] == max(occupancy.values())
    assert occupancy["TUNE+BASS+RHYTHM"] < occupancy["TUNE"]


def test_activity_is_a_real_density_governor():
    low_bass = compose(
        InstrumentConfig(
            bars=8,
            bass=BassControls(activity=0.05, sustain=0.90, movement=0.05),
        )
    )
    high_bass = compose(
        InstrumentConfig(
            bars=8,
            bass=BassControls(activity=0.95, sustain=0.20, movement=0.85),
        )
    )
    assert _accepted_bass(high_bass) > _accepted_bass(low_bass)

    low_segments = sum(len(bar["pattern"]) for bar in low_bass.trace["bass_decisions"])
    high_segments = sum(len(bar["pattern"]) for bar in high_bass.trace["bass_decisions"])
    assert high_segments > low_segments

    low_rhythm = compose(
        InstrumentConfig(bars=8, rhythm=RhythmControls(activity=0.05))
    )
    high_rhythm = compose(
        InstrumentConfig(bars=8, rhythm=RhythmControls(activity=0.95))
    )
    assert _accepted_rhythm(high_rhythm) > _accepted_rhythm(low_rhythm)


def test_activity_endpoints_have_exact_opportunity_semantics():
    silent = compose(
        InstrumentConfig(
            bars=8,
            bass=BassControls(activity=0.0),
            rhythm=RhythmControls(activity=0.0),
        )
    )
    assert not any(
        decision["opportunity"]
        for bar in silent.trace["bass_decisions"]
        for decision in bar["decisions"]
    )
    assert not any(bar["opportunity"] for bar in silent.trace["rhythm_decisions"])

    full = compose(
        InstrumentConfig(
            bars=8,
            bass=BassControls(activity=1.0),
            rhythm=RhythmControls(activity=1.0),
        )
    )
    assert all(
        decision["opportunity"]
        for bar in full.trace["bass_decisions"]
        for decision in bar["decisions"]
    )
    assert all(bar["opportunity"] for bar in full.trace["rhythm_decisions"])


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
            bass=BassControls(activity=1.0),
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
        or application["minimum_silence_margin"] > 0.0
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

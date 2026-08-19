from math import isclose

from ipm import experiment as v1
from ipm.engine import ExperimentMode, _choose_predictive_bar, _phase_for_bar
from ipm.experiment_v2 import (
    _fixed_rhythm_pitch_scores,
    _reference_score,
)
from ipm.randomness import SeededRandom
from ipm.sequential_bar import MusicalState, advance_state


def _target_context(seed: int = 2026081800):
    config = v1.pilot_config(seed=seed, bars=8)
    rng = SeededRandom(config.seed ^ 0xA20)
    state = MusicalState()
    for bar in range(4):
        scored = v1._pool(rng=rng, state=state, config=config, bar=bar)
        selected = v1._expected(scored)
        state = advance_state(state, selected.candidate)
    scored = v1._pool(rng=rng, state=state, config=config, bar=4)
    ipm, _, _ = _choose_predictive_bar(scored, mode=ExperimentMode.IPM)
    return config, state, ipm


def test_reference_score_preserves_frozen_ipm_probability_for_same_candidate():
    config, state, ipm = _target_context()
    rescored = _reference_score(
        ipm.candidate,
        ipm=ipm,
        state=state,
        phase=_phase_for_bar(4, 8),
        tonic_midi=config.tonic_midi,
        final_bar=False,
    )
    assert isclose(rescored.base.total, ipm.base.total, abs_tol=1e-12)
    assert isclose(rescored.probability, ipm.probability, rel_tol=1e-12)
    assert isclose(rescored.surprise_bits, ipm.surprise_bits, rel_tol=1e-12)


def test_v2_control_generation_holds_target_rhythm_fixed_and_is_deterministic():
    config, state, ipm = _target_context()
    kwargs = dict(
        seed=config.seed,
        target_bar=4,
        ipm=ipm,
        state=state,
        phase=_phase_for_bar(4, 8),
        tonic_midi=config.tonic_midi,
        count=12,
    )
    first = _fixed_rhythm_pitch_scores(**kwargs)
    second = _fixed_rhythm_pitch_scores(**kwargs)
    assert first
    assert [item.candidate.pitches for item in first] == [
        item.candidate.pitches for item in second
    ]
    assert all(item.candidate.pattern == ipm.candidate.pattern for item in first)
    assert all(item.candidate.pitches != ipm.candidate.pitches for item in first)

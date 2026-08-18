from ipm import experiment as v1
from ipm.engine import ExperimentMode, _choose_predictive_bar, _phase_for_bar
from ipm.experiment_v2 import _fixed_rhythm_pitch_scores
from ipm.experiment_v2_articulation import (
    _ipm_target_events_and_articulation,
    _realise_with_fixed_articulation,
    _rhythm_signature,
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


def test_control_replays_ipm_audible_target_rhythm():
    config, state, ipm = _target_context()
    controls = _fixed_rhythm_pitch_scores(
        seed=config.seed,
        target_bar=4,
        ipm=ipm,
        state=state,
        phase=_phase_for_bar(4, 8),
        tonic_midi=config.tonic_midi,
        count=4,
    )
    ipm_events, articulation = _ipm_target_events_and_articulation(
        ipm.candidate,
        seed=config.seed,
        bar=4,
        phase=_phase_for_bar(4, 8),
        tonic_midi=config.tonic_midi,
        beats_per_bar=config.beats_per_bar,
    )
    control_events = _realise_with_fixed_articulation(
        controls[0].candidate,
        articulation,
        seed=config.seed,
        bar=4,
        tonic_midi=config.tonic_midi,
        beats_per_bar=config.beats_per_bar,
    )
    assert _rhythm_signature(ipm_events) == _rhythm_signature(control_events)
    assert [event.pitch for event in ipm_events] != [event.pitch for event in control_events]

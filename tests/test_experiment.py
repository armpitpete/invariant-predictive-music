from fractions import Fraction
from types import SimpleNamespace

import pytest

from ipm.engine import ExperimentMode
from ipm.experiment import (
    MatchCriteria,
    _blind_id,
    _participant_schedules,
    pilot_config,
    qualify_episodes,
)


@pytest.fixture(scope="module")
def one_counterfactual_episode():
    # Structural tests use permissive numeric thresholds, but retain the hard
    # causal requirements: one shared target pool, an actual IPM deviation,
    # and an IPM/control pair with identical target rhythm.
    criteria = MatchCriteria(
        min_ipm_surprise_bits=0.0,
        max_target_surprise_error_bits=100.0,
        min_local_invariant_gap=0.0,
        min_future_integration_gap=0.0,
        min_ipm_future_integration=0.0,
        max_target_base_score_delta=100.0,
    )
    return qualify_episodes(
        start_seed=2026081800,
        count=1,
        search_limit=192,
        bars=8,
        target_bar=4,
        criteria=criteria,
    )


def test_pilot_is_an_eight_bar_episode_with_a_real_prefix_and_suffix():
    config = pilot_config(seed=1)
    assert config.bars == 8
    with pytest.raises(ValueError):
        pilot_config(seed=1, bars=5)


def test_counterfactual_episode_changes_only_the_target_bar(one_counterfactual_episode):
    episode = one_counterfactual_episode.qualified[0]
    start = Fraction(episode.target_bar * 4)
    end = start + 4

    def outside_target(variant):
        return tuple(
            event
            for event in variant.tune.events
            if event.onset < start or event.onset >= end
        )

    outside = {
        outside_target(variant)
        for variant in episode.variants.values()
    }
    assert len(outside) == 1
    assert episode.audit.checks["shared_target_candidate_pool"]
    assert episode.audit.checks["non_target_music_identical"]
    assert episode.audit.checks["ipm_control_target_rhythm_identical"]


def test_target_ipm_and_control_are_distinct_candidates(one_counterfactual_episode):
    episode = one_counterfactual_episode.qualified[0]
    ipm = episode.variants[ExperimentMode.IPM].target.candidate
    control = episode.variants[ExperimentMode.UNSTRUCTURED_SURPRISE].target.candidate
    assert ipm.pitches != control.pitches
    assert ipm.pattern.cells == control.pattern.cells


def test_qualification_retains_the_complete_selection_funnel(one_counterfactual_episode):
    run = one_counterfactual_episode
    assert run.audits
    assert run.final_seed_examined == run.audits[-1].seed
    assert any(audit.passed for audit in run.audits)
    assert run.qualified[0].seed in {audit.seed for audit in run.audits}


def test_blind_ids_do_not_reveal_condition_names():
    ids = {_blind_id(9, 100, mode) for mode in ExperimentMode}
    assert len(ids) == 3
    assert all("predictable" not in value for value in ids)
    assert all("ipm" not in value for value in ids)
    assert all("surprise" not in value for value in ids)


def test_participants_keep_condition_balance_but_receive_individual_orders():
    qualified = [SimpleNamespace(seed=seed) for seed in range(10, 22)]
    schedules = _participant_schedules(
        qualified,
        blind_seed=77,
        participant_count=9,
    )
    assert [item["group"] for item in schedules] == [1, 2, 3, 1, 2, 3, 1, 2, 3]
    assert all(len(item["rows"]) == 12 for item in schedules)

    # Within a group the condition assignment is fixed, but trial orders should
    # not collapse to one shared order.
    group_one_orders = [
        tuple(row["stimulus_id"] for row in item["rows"])
        for item in schedules
        if item["group"] == 1
    ]
    assert len(set(group_one_orders)) == len(group_one_orders)

    for seed in range(10, 22):
        heard_modes = {
            row["mode"]
            for item in schedules[:3]
            for row in item["rows"]
            if row["seed"] == seed
        }
        assert heard_modes == set(ExperimentMode)

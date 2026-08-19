from types import SimpleNamespace

import pytest

import ipm.experiment as experiment
from ipm.engine import ExperimentMode
from ipm.experiment import (
    EpisodeAudit,
    MatchCriteria,
    QualifiedEpisode,
    _blind_id,
    _participant_schedules,
    future_integration,
    pilot_config,
    qualify_episodes,
)
from ipm.sequential_bar import WholeBarCandidate, _active_patterns


def test_pilot_is_an_eight_bar_episode_with_a_real_prefix_and_suffix():
    config = pilot_config(seed=1)
    assert config.bars == 8
    with pytest.raises(ValueError):
        pilot_config(seed=1, bars=5)


def test_future_integration_depends_on_the_actual_suffix():
    pattern = _active_patterns()[0]
    attacks = pattern.attacks
    target_pitches = tuple(60 + 2 * index for index in range(attacks))
    target = WholeBarCandidate(pattern=pattern, pitches=target_pitches)

    echo_pitches = tuple(
        target_pitches[-1] + 2 * (index + 1)
        for index in range(attacks)
    )
    contrary_pitches = tuple(
        target_pitches[-1] - 5 * (index + 1)
        for index in range(attacks)
    )
    echo = WholeBarCandidate(pattern=pattern, pitches=echo_pitches)
    contrary = WholeBarCandidate(pattern=pattern, pitches=contrary_pitches)

    assert future_integration(target, (echo,)) > future_integration(target, (contrary,))


def test_qualification_retains_rejections_before_the_accepted_episode(monkeypatch):
    rejected = EpisodeAudit(
        seed=10,
        target_bar=4,
        passed=False,
        checks={"matched_control_exists": False},
        metrics={},
    )
    accepted_audit = EpisodeAudit(
        seed=11,
        target_bar=4,
        passed=True,
        checks={"matched_control_exists": True},
        metrics={},
    )
    accepted = QualifiedEpisode(
        seed=11,
        target_bar=4,
        variants={},
        audit=accepted_audit,
    )

    def fake_episode_for_seed(*, seed, bars, target_bar, criteria):
        del bars, criteria
        if seed == 10:
            return None, rejected
        return accepted, accepted_audit

    monkeypatch.setattr(experiment, "_episode_for_seed", fake_episode_for_seed)
    run = qualify_episodes(
        start_seed=10,
        count=1,
        search_limit=2,
        bars=8,
        target_bar=4,
    )
    assert [audit.seed for audit in run.audits] == [10, 11]
    assert [item.seed for item in run.qualified] == [11]
    assert run.final_seed_examined == 11


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


def test_match_criteria_reject_negative_thresholds():
    with pytest.raises(ValueError):
        MatchCriteria(min_future_integration_gap=-0.01)

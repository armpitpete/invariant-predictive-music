from ipm.engine import ExperimentMode, compose_experiment_bundle
from ipm.experiment import (
    MatchCriteria,
    _blind_id,
    _counterbalance_rows,
    audit_bundle,
    pilot_config,
    QualifiedBundle,
)


def test_pilot_configuration_is_tune_only_and_predictable_remains_baseline():
    bundle = compose_experiment_bundle(pilot_config(seed=2026081704, bars=6))
    assert all(not result.bass.events for result in bundle.values())
    assert all(not result.rhythm.events for result in bundle.values())
    assert all(
        decision["selected_branch"] == "expected"
        for decision in bundle[ExperimentMode.PREDICTABLE].trace["tune_decisions"]
    )


def test_audit_runs_against_real_bundle_without_human_response_data():
    bundle = compose_experiment_bundle(pilot_config(seed=2026081704, bars=6))
    criteria = MatchCriteria(
        min_ipm_surprise_bars=0,
        max_mean_bar_surprise_error_bits=100.0,
        max_global_surprise_error_bits=100.0,
        min_mean_invariant_gap=-1.0,
        min_weaker_invariant_fraction=0.0,
        max_tune_event_count_fraction_delta=1.0,
    )
    audit = audit_bundle(bundle, criteria)
    assert audit.checks["same_high_level_configuration"]
    assert audit.checks["all_engine_validation_passed"]
    assert audit.checks["predictable_is_expected_baseline"]
    assert audit.checks["tune_only_mechanism_isolation"]
    assert audit.passed


def test_blind_ids_do_not_reveal_condition_names():
    ids = {
        _blind_id(9, 100, mode)
        for mode in ExperimentMode
    }
    assert len(ids) == 3
    assert all("predictable" not in value for value in ids)
    assert all("ipm" not in value for value in ids)
    assert all("surprise" not in value for value in ids)


def test_three_group_counterbalance_rotates_every_seed_through_every_condition():
    criteria = MatchCriteria()
    qualified = []
    for seed in (10, 11, 12, 13, 14, 15):
        bundle = compose_experiment_bundle(pilot_config(seed=seed, bars=4))
        qualified.append(
            QualifiedBundle(
                seed=seed,
                results=bundle,
                audit=audit_bundle(
                    bundle,
                    MatchCriteria(
                        min_ipm_surprise_bars=0,
                        max_mean_bar_surprise_error_bits=100.0,
                        max_global_surprise_error_bits=100.0,
                        min_mean_invariant_gap=-1.0,
                        min_weaker_invariant_fraction=0.0,
                        max_tune_event_count_fraction_delta=1.0,
                    ),
                ),
            )
        )

    groups = _counterbalance_rows(qualified, blind_seed=77)
    assert set(groups) == {1, 2, 3}
    for group_rows in groups.values():
        assert len(group_rows) == len(qualified)
        assert len({row["seed"] for row in group_rows}) == len(qualified)

    for seed in (10, 11, 12, 13, 14, 15):
        heard_modes = {
            row["mode"]
            for group_rows in groups.values()
            for row in group_rows
            if row["seed"] == seed
        }
        assert heard_modes == set(ExperimentMode)

    del criteria

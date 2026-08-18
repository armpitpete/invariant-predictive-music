"""Diagnostic-only attrition audit for Listening Experiment 1.

This script does not change stimulus selection, composer behaviour, or matching
thresholds. It explains which pre-listening control constraint removes candidate
pairs across the frozen seed window.
"""

from __future__ import annotations

import json
from collections import Counter
from concurrent.futures import ProcessPoolExecutor

from ipm.engine import ExperimentMode, _choose_predictive_bar
from ipm.experiment import (
    MatchCriteria,
    _candidate_pattern_signature,
    _choose_control,
    _expected,
    _pool,
    pilot_config,
)
from ipm.randomness import SeededRandom
from ipm.sequential_bar import MusicalState, advance_state

START_SEED = 2026081800
SEARCH_LIMIT = 512
BARS = 8
TARGET_BAR = 4


def _target_context(seed: int):
    config = pilot_config(seed=seed, bars=BARS)
    rng = SeededRandom(config.seed ^ 0xA20)
    state = MusicalState()
    for bar in range(TARGET_BAR):
        scored = _pool(rng=rng, state=state, config=config, bar=bar)
        selected = _expected(scored)
        state = advance_state(state, selected.candidate)
    target_scored = _pool(rng=rng, state=state, config=config, bar=TARGET_BAR)
    expected = _expected(target_scored)
    ipm, ipm_branch, _ = _choose_predictive_bar(target_scored, mode=ExperimentMode.IPM)
    return config, rng, state, target_scored, expected, ipm, ipm_branch


def _suffix(config, rng, state, expected):
    suffix_state = advance_state(state, expected.candidate)
    suffix = []
    for bar in range(TARGET_BAR + 1, BARS):
        scored = _pool(rng=rng, state=suffix_state, config=config, bar=bar)
        selected = _expected(scored)
        suffix.append(selected.candidate)
        suffix_state = advance_state(suffix_state, selected.candidate)
    return tuple(suffix)


def _analyse_seed(seed: int) -> dict:
    criteria = MatchCriteria()
    config, rng, state, scored, expected, ipm, ipm_branch = _target_context(seed)
    seed_counts = Counter(examined=1)
    candidate_totals = Counter()

    ipm_nonexpected = ipm is not expected and ipm_branch != "expected"
    ipm_surprising = ipm.surprise_bits >= criteria.min_ipm_surprise_bits
    if ipm_nonexpected:
        seed_counts["ipm_replaces_expected"] += 1
    if ipm_nonexpected and ipm_surprising:
        seed_counts["eligible_ipm_target"] += 1
    if not (ipm_nonexpected and ipm_surprising):
        return {
            "seed_counts": dict(seed_counts),
            "candidate_totals": {},
            "future_gap": None,
            "ipm_future_integration": None,
        }

    candidates = [item for item in scored if item is not expected and item is not ipm]
    candidate_totals["eligible_nonbaseline"] += len(candidates)
    ipm_pattern = _candidate_pattern_signature(ipm.candidate)

    same_rhythm = [
        item for item in candidates
        if _candidate_pattern_signature(item.candidate) == ipm_pattern
    ]
    surprise = [
        item for item in candidates
        if abs(item.surprise_bits - ipm.surprise_bits)
        <= criteria.max_target_surprise_error_bits
    ]
    weaker = [
        item for item in candidates
        if ipm.invariant_similarity - item.invariant_similarity
        >= criteria.min_local_invariant_gap
    ]
    base = [
        item for item in candidates
        if abs(ipm.base.total - item.base.total)
        <= criteria.max_target_base_score_delta
    ]

    stage_surprise = [item for item in same_rhythm if item in surprise]
    stage_weaker = [item for item in stage_surprise if item in weaker]
    stage_base = [item for item in stage_weaker if item in base]

    for name, values in (
        ("same_rhythm", same_rhythm),
        ("surprise_independent", surprise),
        ("weaker_invariant_independent", weaker),
        ("base_quality_independent", base),
        ("rhythm_then_surprise", stage_surprise),
        ("then_weaker_invariant", stage_weaker),
        ("fully_locally_matched", stage_base),
    ):
        candidate_totals[name] += len(values)
        if values:
            seed_counts[name] += 1

    if not stage_base:
        return {
            "seed_counts": dict(seed_counts),
            "candidate_totals": dict(candidate_totals),
            "future_gap": None,
            "ipm_future_integration": None,
        }

    suffix = _suffix(config, rng, state, expected)
    _, metrics = _choose_control(ipm=ipm, controls=stage_base, suffix=suffix)
    if metrics["ipm_future_integration"] >= criteria.min_ipm_future_integration:
        seed_counts["ipm_future_integration_pass"] += 1
    if metrics["future_integration_gap"] >= criteria.min_future_integration_gap:
        seed_counts["future_gap_pass"] += 1
    return {
        "seed_counts": dict(seed_counts),
        "candidate_totals": dict(candidate_totals),
        "future_gap": metrics["future_integration_gap"],
        "ipm_future_integration": metrics["ipm_future_integration"],
    }


def main() -> None:
    criteria = MatchCriteria()
    seed_counts = Counter()
    candidate_totals = Counter()
    future_gaps = []
    future_ipm = []

    seeds = range(START_SEED, START_SEED + SEARCH_LIMIT)
    with ProcessPoolExecutor(max_workers=4) as executor:
        for item in executor.map(_analyse_seed, seeds, chunksize=8):
            seed_counts.update(item["seed_counts"])
            candidate_totals.update(item["candidate_totals"])
            if item["future_gap"] is not None:
                future_gaps.append(item["future_gap"])
            if item["ipm_future_integration"] is not None:
                future_ipm.append(item["ipm_future_integration"])

    result = {
        "seed_window": {
            "start_seed": START_SEED,
            "search_limit": SEARCH_LIMIT,
            "bars": BARS,
            "target_bar": TARGET_BAR,
        },
        "criteria": {
            "min_ipm_surprise_bits": criteria.min_ipm_surprise_bits,
            "max_target_surprise_error_bits": criteria.max_target_surprise_error_bits,
            "min_local_invariant_gap": criteria.min_local_invariant_gap,
            "min_future_integration_gap": criteria.min_future_integration_gap,
            "min_ipm_future_integration": criteria.min_ipm_future_integration,
            "max_target_base_score_delta": criteria.max_target_base_score_delta,
        },
        "seed_counts": dict(seed_counts),
        "candidate_totals": dict(candidate_totals),
        "future_gap_values": future_gaps,
        "ipm_future_integration_values": future_ipm,
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

"""Corpus-wide diagnostic for Counterfactual Episode v2.

This is experiment-layer tooling only. It applies the frozen v1 qualification
thresholds to every seed in the frozen 512-seed window using the v2 episode
constructor. It does not change composer behaviour, thresholds, or selection.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from pathlib import Path

from ipm.experiment import MatchCriteria
from ipm.experiment_v2 import _episode_for_seed_v2

START_SEED = 2026081800
SEARCH_LIMIT = 512
BARS = 8
TARGET_BAR = 4
REQUIRED_QUALIFIED = 12

FAILURE_ORDER = (
    "target_pool_frozen_before_control_search",
    "shared_pre_target_state",
    "ipm_replaces_expected",
    "ipm_is_sufficiently_surprising",
    "control_pitch_realisations_generated",
    "ipm_control_target_rhythm_identical",
    "target_surprise_match_available",
    "weaker_local_invariant_available",
    "target_base_quality_match_available",
    "matched_control_exists",
    "suffix_generated_from_ipm_target_state",
    "ipm_integrates_with_actual_suffix",
    "actual_suffix_favours_ipm",
    "non_target_music_identical",
)


def _analyse_seed(seed: int) -> dict:
    criteria = MatchCriteria()
    _, audit = _episode_for_seed_v2(
        seed=seed,
        bars=BARS,
        target_bar=TARGET_BAR,
        criteria=criteria,
    )
    failed = tuple(name for name, passed in audit.checks.items() if not passed)
    first_failure = next(
        (name for name in FAILURE_ORDER if audit.checks.get(name) is False),
        None,
    )
    return {
        "seed": seed,
        "passed": audit.passed,
        "first_failure": first_failure,
        "failed_checks": failed,
        "checks": dict(audit.checks),
        "metrics": dict(audit.metrics),
    }


def build_report(*, workers: int = 4) -> dict:
    criteria = MatchCriteria()
    seeds = range(START_SEED, START_SEED + SEARCH_LIMIT)
    with ProcessPoolExecutor(max_workers=workers) as executor:
        audits = list(executor.map(_analyse_seed, seeds, chunksize=8))

    qualified = [item["seed"] for item in audits if item["passed"]]
    first_failures = Counter(
        item["first_failure"]
        for item in audits
        if not item["passed"] and item["first_failure"] is not None
    )
    failed_checks = Counter(
        check
        for item in audits
        for check in item["failed_checks"]
    )

    generated = [
        item["metrics"].get("generated_control_count", 0)
        for item in audits
        if "generated_control_count" in item["metrics"]
    ]
    locally_matched = [
        item["metrics"].get("locally_matched_control_count", 0)
        for item in audits
        if "locally_matched_control_count" in item["metrics"]
    ]

    return {
        "experiment": "Counterfactual Episode v2 corpus gate",
        "seed_window": {
            "start_seed": START_SEED,
            "search_limit": SEARCH_LIMIT,
            "final_seed": START_SEED + SEARCH_LIMIT - 1,
            "bars": BARS,
            "target_bar": TARGET_BAR,
        },
        "criteria": asdict(criteria),
        "control_construction": {
            "rhythm": "IPM target rhythm held fixed",
            "pitch_search_state": "identical pre-target state",
            "future_state": "IPM target state",
            "future_attachment": "same suffix attached to Predictable, IPM, Control",
        },
        "gate": {
            "required_qualified": REQUIRED_QUALIFIED,
            "qualified_count": len(qualified),
            "passed": len(qualified) >= REQUIRED_QUALIFIED,
        },
        "qualified_seeds": qualified,
        "first_failure_counts": dict(sorted(first_failures.items())),
        "failed_check_counts": dict(sorted(failed_checks.items())),
        "control_search": {
            "seeds_reaching_generated_controls": len(generated),
            "generated_control_count_min": min(generated) if generated else 0,
            "generated_control_count_max": max(generated) if generated else 0,
            "seeds_with_locally_matched_control": sum(value > 0 for value in locally_matched),
        },
        "audits": audits,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the frozen 512-seed Counterfactual Episode v2 corpus gate"
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    if args.workers <= 0:
        raise SystemExit("--workers must be positive")

    report = build_report(workers=args.workers)
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")

    if not report["gate"]["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

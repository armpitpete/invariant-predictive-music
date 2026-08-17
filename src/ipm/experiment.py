"""Matched listening-experiment tooling for IPM v0.2.

This module does not add compositional behaviour. It packages and audits the
existing Predictable / IPM / Unstructured-Surprise conditions for human
listening tests.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import fmean
from typing import Any, Mapping, Sequence

from .engine import (
    BassControls,
    ExperimentMode,
    InstrumentConfig,
    InstrumentResult,
    RhythmControls,
    compose_experiment_bundle,
)
from .midi import render_midi


@dataclass(frozen=True, slots=True)
class MatchCriteria:
    """Pre-listening qualification criteria for one three-condition seed set."""

    min_ipm_surprise_bars: int = 3
    max_mean_bar_surprise_error_bits: float = 0.90
    max_global_surprise_error_bits: float = 0.40
    min_mean_invariant_gap: float = 0.08
    min_weaker_invariant_fraction: float = 0.70
    max_tune_event_count_fraction_delta: float = 0.18

    def __post_init__(self) -> None:
        if self.min_ipm_surprise_bars < 0:
            raise ValueError("min_ipm_surprise_bars must be non-negative")
        for name in (
            "max_mean_bar_surprise_error_bits",
            "max_global_surprise_error_bits",
            "max_tune_event_count_fraction_delta",
        ):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be non-negative")
        if not 0.0 <= self.min_weaker_invariant_fraction <= 1.0:
            raise ValueError("min_weaker_invariant_fraction must be in 0..1")


@dataclass(frozen=True, slots=True)
class BundleAudit:
    seed: int
    passed: bool
    checks: Mapping[str, bool]
    metrics: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class QualifiedBundle:
    seed: int
    results: Mapping[ExperimentMode, InstrumentResult]
    audit: BundleAudit


def pilot_config(*, seed: int, bars: int = 16) -> InstrumentConfig:
    """Return the mechanism-isolation configuration for Listening Experiment 1.

    Bass and Rhythm are disabled through their existing activity governors.
    This deliberately tests the Tune prediction/surprise mechanism before a
    later full-texture replication.
    """

    return InstrumentConfig(
        seed=seed,
        bars=bars,
        bass=BassControls(activity=0.0),
        rhythm=RhythmControls(activity=0.0),
    )


def _selected_profile(result: InstrumentResult, field: str) -> list[float]:
    return [
        float(decision["selected"][field])
        for decision in result.trace["tune_decisions"]
    ]


def _surprise_bars(result: InstrumentResult) -> list[int]:
    return [
        int(decision["bar"])
        for decision in result.trace["tune_decisions"]
        if decision["selected_branch"] != "expected"
    ]


def _high_level_signature(result: InstrumentResult) -> tuple[Any, ...]:
    config = result.config
    return (
        config.seed,
        config.tempo_bpm,
        config.bars,
        config.beats_per_bar,
        config.tonic_midi,
        config.tune_alternatives,
        config.bass,
        config.rhythm,
        config.pattern_locks,
    )


def audit_bundle(
    bundle: Mapping[ExperimentMode, InstrumentResult],
    criteria: MatchCriteria | None = None,
) -> BundleAudit:
    """Decide whether a generated seed is sufficiently matched for listening.

    Qualification is based on control matching and the intended invariant
    manipulation, never on human-response variables.
    """

    criteria = criteria or MatchCriteria()
    predictable = bundle[ExperimentMode.PREDICTABLE]
    ipm = bundle[ExperimentMode.IPM]
    control = bundle[ExperimentMode.UNSTRUCTURED_SURPRISE]

    ipm_surprise_bars = _surprise_bars(ipm)
    ipm_surprise = _selected_profile(ipm, "surprise_bits")
    control_surprise = _selected_profile(control, "surprise_bits")
    bar_surprise_errors = [
        abs(left - right)
        for left, right in zip(ipm_surprise, control_surprise, strict=True)
    ]
    mean_bar_surprise_error = fmean(bar_surprise_errors)
    global_surprise_error = abs(fmean(ipm_surprise) - fmean(control_surprise))

    ipm_invariant = _selected_profile(ipm, "invariant_similarity")
    control_invariant = _selected_profile(control, "invariant_similarity")
    invariant_gaps = [
        ipm_invariant[bar] - control_invariant[bar]
        for bar in ipm_surprise_bars
    ]
    mean_invariant_gap = fmean(invariant_gaps) if invariant_gaps else 0.0
    weaker_fraction = (
        sum(gap > 0.0 for gap in invariant_gaps) / len(invariant_gaps)
        if invariant_gaps
        else 0.0
    )

    ipm_events = len(ipm.tune.events)
    control_events = len(control.tune.events)
    event_fraction_delta = abs(ipm_events - control_events) / max(
        1,
        ipm_events,
        control_events,
    )

    signatures = {_high_level_signature(result) for result in bundle.values()}
    predictable_expected = all(
        decision["selected_branch"] == "expected"
        for decision in predictable.trace["tune_decisions"]
    )
    subsidiary_silent = all(
        not result.bass.events and not result.rhythm.events
        for result in bundle.values()
    )
    validation_passed = all(
        result.trace["validation"]["passed"]
        for result in bundle.values()
    )

    checks = {
        "same_high_level_configuration": len(signatures) == 1,
        "all_engine_validation_passed": validation_passed,
        "predictable_is_expected_baseline": predictable_expected,
        "tune_only_mechanism_isolation": subsidiary_silent,
        "enough_ipm_surprise_events": (
            len(ipm_surprise_bars) >= criteria.min_ipm_surprise_bars
        ),
        "model_surprise_burden_matched": (
            mean_bar_surprise_error <= criteria.max_mean_bar_surprise_error_bits
            and global_surprise_error <= criteria.max_global_surprise_error_bits
        ),
        "control_has_weaker_invariants": (
            mean_invariant_gap >= criteria.min_mean_invariant_gap
            and weaker_fraction >= criteria.min_weaker_invariant_fraction
        ),
        "surface_event_density_matched": (
            event_fraction_delta <= criteria.max_tune_event_count_fraction_delta
        ),
    }

    metrics = {
        "ipm_surprise_bars": ipm_surprise_bars,
        "ipm_surprise_bar_count": len(ipm_surprise_bars),
        "mean_bar_surprise_error_bits": mean_bar_surprise_error,
        "global_surprise_error_bits": global_surprise_error,
        "mean_invariant_gap_on_ipm_surprise_bars": mean_invariant_gap,
        "weaker_invariant_fraction": weaker_fraction,
        "ipm_tune_events": ipm_events,
        "control_tune_events": control_events,
        "tune_event_count_fraction_delta": event_fraction_delta,
    }
    return BundleAudit(
        seed=ipm.config.seed,
        passed=all(checks.values()),
        checks=checks,
        metrics=metrics,
    )


def qualify_bundles(
    *,
    start_seed: int,
    count: int,
    search_limit: int,
    bars: int = 16,
    criteria: MatchCriteria | None = None,
) -> tuple[QualifiedBundle, ...]:
    """Search a deterministic seed range and retain only prequalified sets."""

    if count <= 0:
        raise ValueError("count must be positive")
    if search_limit < count:
        raise ValueError("search_limit must be >= count")
    criteria = criteria or MatchCriteria()

    accepted: list[QualifiedBundle] = []
    rejected: list[BundleAudit] = []
    for seed in range(start_seed, start_seed + search_limit):
        results = compose_experiment_bundle(pilot_config(seed=seed, bars=bars))
        audit = audit_bundle(results, criteria)
        if audit.passed:
            accepted.append(QualifiedBundle(seed, results, audit))
            if len(accepted) == count:
                return tuple(accepted)
        else:
            rejected.append(audit)

    failure_counts: dict[str, int] = {}
    for audit in rejected:
        for name, passed in audit.checks.items():
            if not passed:
                failure_counts[name] = failure_counts.get(name, 0) + 1
    raise RuntimeError(
        "Only "
        f"{len(accepted)} of {count} required matched bundles qualified within "
        f"{search_limit} seeds. Failure counts: {failure_counts}"
    )


def _blind_id(blind_seed: int, seed: int, mode: ExperimentMode) -> str:
    payload = f"{blind_seed}:{seed}:{mode.value}".encode("utf-8")
    return "stim-" + hashlib.sha256(payload).hexdigest()[:12]


def _counterbalance_rows(
    qualified: Sequence[QualifiedBundle],
    *,
    blind_seed: int,
) -> dict[int, list[dict[str, Any]]]:
    """Create three groups: one condition per seed, balanced across groups."""

    modes = (
        ExperimentMode.PREDICTABLE,
        ExperimentMode.IPM,
        ExperimentMode.UNSTRUCTURED_SURPRISE,
    )
    groups: dict[int, list[dict[str, Any]]] = {}
    for group in range(3):
        rows: list[dict[str, Any]] = []
        for index, item in enumerate(qualified):
            mode = modes[(index + group) % len(modes)]
            rows.append(
                {
                    "seed": item.seed,
                    "mode": mode,
                    "stimulus_id": _blind_id(blind_seed, item.seed, mode),
                }
            )
        random.Random(blind_seed ^ (group + 1)).shuffle(rows)
        groups[group + 1] = [
            {
                "trial": trial,
                "stimulus_id": row["stimulus_id"],
                "seed": row["seed"],
                "mode": row["mode"],
            }
            for trial, row in enumerate(rows, start=1)
        ]
    return groups


def _write_csv(path: Path, fieldnames: Sequence[str], rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_listening_pilot(
    output_dir: str | Path,
    *,
    start_seed: int = 2026081800,
    set_count: int = 12,
    search_limit: int = 96,
    bars: int = 16,
    blind_seed: int = 2026081801,
    criteria: MatchCriteria | None = None,
) -> Path:
    """Build the blinded MIDI set, audit trail and counterbalancing schedules."""

    criteria = criteria or MatchCriteria()
    qualified = qualify_bundles(
        start_seed=start_seed,
        count=set_count,
        search_limit=search_limit,
        bars=bars,
        criteria=criteria,
    )

    output = Path(output_dir)
    stimuli = output / "stimuli"
    researcher = output / "researcher"
    traces = researcher / "traces"
    groups_dir = output / "participant-groups"
    stimuli.mkdir(parents=True, exist_ok=True)
    traces.mkdir(parents=True, exist_ok=True)
    groups_dir.mkdir(parents=True, exist_ok=True)

    key_rows: list[dict[str, Any]] = []
    for item in qualified:
        for mode, result in item.results.items():
            stimulus_id = _blind_id(blind_seed, item.seed, mode)
            midi_path = stimuli / f"{stimulus_id}.mid"
            midi_path.write_bytes(
                render_midi(
                    result.voices,
                    tempo_bpm=result.config.tempo_bpm,
                    beats_per_bar=result.config.beats_per_bar,
                )
            )
            (traces / f"{stimulus_id}.trace.json").write_text(
                json.dumps(result.trace, indent=2) + "\n",
                encoding="utf-8",
            )
            key_rows.append(
                {
                    "stimulus_id": stimulus_id,
                    "seed": item.seed,
                    "condition": mode.value,
                }
            )

    _write_csv(
        researcher / "condition-key.csv",
        ("stimulus_id", "seed", "condition"),
        key_rows,
    )

    groups = _counterbalance_rows(qualified, blind_seed=blind_seed)
    for group, rows in groups.items():
        participant_rows = [
            {"trial": row["trial"], "stimulus_id": row["stimulus_id"]}
            for row in rows
        ]
        _write_csv(
            groups_dir / f"group-{group}.csv",
            ("trial", "stimulus_id"),
            participant_rows,
        )

    _write_csv(
        output / "response-schema.csv",
        (
            "participant_id",
            "counterbalance_group",
            "trial",
            "stimulus_id",
            "liking_0_100",
            "coherence_0_100",
            "surprise_0_100",
            "retrospective_sense_0_100",
            "hear_again_0_100",
        ),
        (),
    )

    manifest = {
        "experiment": "IPM Listening Experiment 1 — mechanism isolation pilot",
        "bars": bars,
        "set_count": set_count,
        "conditions": [mode.value for mode in ExperimentMode],
        "mechanism_isolation": {
            "bass_activity": 0.0,
            "rhythm_activity": 0.0,
        },
        "criteria": asdict(criteria),
        "qualified_seeds": [item.seed for item in qualified],
        "audits": [
            {
                "seed": item.seed,
                "passed": item.audit.passed,
                "checks": dict(item.audit.checks),
                "metrics": dict(item.audit.metrics),
            }
            for item in qualified
        ],
        "blinding": {
            "condition_key": "researcher/condition-key.csv",
            "participant_files_expose_condition": False,
            "counterbalance_groups": 3,
        },
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return output


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the matched IPM Listening Experiment 1 pilot set"
    )
    parser.add_argument("--output", default="listening-pilot")
    parser.add_argument("--sets", type=int, default=12)
    parser.add_argument("--start-seed", type=int, default=2026081800)
    parser.add_argument("--search-limit", type=int, default=96)
    parser.add_argument("--bars", type=int, default=16)
    parser.add_argument("--blind-seed", type=int, default=2026081801)
    args = parser.parse_args()

    output = write_listening_pilot(
        args.output,
        start_seed=args.start_seed,
        set_count=args.sets,
        search_limit=args.search_limit,
        bars=args.bars,
        blind_seed=args.blind_seed,
    )
    print(output)


if __name__ == "__main__":
    main()

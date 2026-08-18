"""Matched counterfactual listening-experiment tooling for IPM v0.2.

This module does not add compositional behaviour. It constructs controlled
listener episodes from the existing Tune candidate machinery so the causal
contrast is local:

    identical prefix -> one target-bar intervention -> identical suffix

Predictable and IPM use the engine's existing selection logic at the shared
target candidate pool. The Unstructured-Surprise control is selected from that
same pool to match IPM's surprise while weakening local invariant continuity.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from dataclasses import asdict, dataclass
from fractions import Fraction
from math import exp
from pathlib import Path
from typing import Any, Mapping, Sequence

from .engine import (
    ExperimentMode,
    InstrumentConfig,
    PredictiveBarScore,
    _choose_predictive_bar,
    _phase_for_bar,
    _score_predictive_pool,
)
from .micro_rhythm import realise_micro_bar
from .midi import render_midi
from .model import NoteEvent, Voice
from .randomness import SeededRandom
from .sequential_bar import (
    MusicalState,
    WholeBarCandidate,
    advance_state,
    propose_whole_bar,
)


@dataclass(frozen=True, slots=True)
class MatchCriteria:
    """Pre-listening qualification criteria for one counterfactual episode."""

    min_ipm_surprise_bits: float = 1.50
    max_target_surprise_error_bits: float = 0.65
    min_local_invariant_gap: float = 0.10
    min_future_integration_gap: float = 0.10
    min_ipm_future_integration: float = 0.40
    max_target_base_score_delta: float = 0.10

    def __post_init__(self) -> None:
        for name in (
            "min_ipm_surprise_bits",
            "max_target_surprise_error_bits",
            "min_local_invariant_gap",
            "min_future_integration_gap",
            "min_ipm_future_integration",
            "max_target_base_score_delta",
        ):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be non-negative")
        if self.min_ipm_future_integration > 1.0:
            raise ValueError("min_ipm_future_integration must be <= 1")


@dataclass(frozen=True, slots=True)
class EpisodeAudit:
    seed: int
    target_bar: int
    passed: bool
    checks: Mapping[str, bool]
    metrics: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class EpisodeVariant:
    mode: ExperimentMode
    tune: Voice
    target: PredictiveBarScore
    future_integration: float


@dataclass(frozen=True, slots=True)
class QualifiedEpisode:
    seed: int
    target_bar: int
    variants: Mapping[ExperimentMode, EpisodeVariant]
    audit: EpisodeAudit


@dataclass(frozen=True, slots=True)
class QualificationRun:
    qualified: tuple[QualifiedEpisode, ...]
    audits: tuple[EpisodeAudit, ...]
    final_seed_examined: int


def pilot_config(*, seed: int, bars: int = 8) -> InstrumentConfig:
    """Return the Tune-only structural configuration for Listening Experiment 1."""

    if bars < 6:
        raise ValueError("counterfactual episodes need at least 6 bars")
    return InstrumentConfig(seed=seed, bars=bars)


def _candidate_pattern_signature(candidate: WholeBarCandidate) -> tuple[tuple[str, Fraction], ...]:
    return tuple((cell.kind.value, cell.duration) for cell in candidate.pattern.cells)


def _realise_candidate(
    candidate: WholeBarCandidate,
    *,
    seed: int,
    bar: int,
    phase: str,
    tonic_midi: int,
    beats_per_bar: int,
) -> tuple[NoteEvent, ...]:
    cells = tuple((cell.kind, cell.duration) for cell in candidate.pattern.cells)
    # Each bar starts from its own deterministic micro-rhythm seed. This keeps
    # the copied prefix/suffix independent of which target candidate is rendered.
    micro_rng = SeededRandom(seed ^ 0xA21000 ^ (bar * 0x9E3779B1))
    events, _ = realise_micro_bar(
        cells,
        candidate.pitches,
        start=Fraction(bar * beats_per_bar),
        phase=phase,
        rng=micro_rng,
        tonic_midi=tonic_midi,
    )
    return events


def _expected(scored: Sequence[PredictiveBarScore]) -> PredictiveBarScore:
    selected, _, _ = _choose_predictive_bar(scored, mode=ExperimentMode.PREDICTABLE)
    return selected


def _pool(
    *,
    rng: SeededRandom,
    state: MusicalState,
    config: InstrumentConfig,
    bar: int,
) -> tuple[PredictiveBarScore, ...]:
    phase = _phase_for_bar(bar, config.bars)
    candidates = tuple(
        propose_whole_bar(
            rng=rng,
            phase=phase,
            state=state,
            tonic_midi=config.tonic_midi,
            final_bar=bar == config.bars - 1,
        )
        for _ in range(config.tune_alternatives)
    )
    return _score_predictive_pool(
        candidates,
        state=state,
        phase=phase,
        tonic_midi=config.tonic_midi,
        final_bar=bar == config.bars - 1,
    )


def _interval_window_similarity(
    target: Sequence[int],
    future: Sequence[int],
) -> float:
    if not target or not future:
        return 0.0
    n = min(len(target), len(future))
    target = tuple(target[-n:])
    if len(future) < n:
        windows = (tuple(future),)
    else:
        windows = tuple(
            tuple(future[start : start + n])
            for start in range(len(future) - n + 1)
        )

    def score(window: Sequence[int]) -> float:
        local_target = target[-len(window):]
        contour = sum(
            (left > 0) == (right > 0)
            and (left < 0) == (right < 0)
            for left, right in zip(local_target, window, strict=True)
        ) / len(window)
        size = sum(
            exp(-abs(abs(left) - abs(right)) / 2.0)
            for left, right in zip(local_target, window, strict=True)
        ) / len(window)
        exact = sum(
            left == right
            for left, right in zip(local_target, window, strict=True)
        ) / len(window)
        return 0.45 * contour + 0.35 * size + 0.20 * exact

    return max(score(window) for window in windows)


def future_integration(
    target: WholeBarCandidate,
    suffix: Sequence[WholeBarCandidate],
) -> float:
    """Measure target structure against the music that actually follows it.

    Unlike the engine's prospective selection score, this quantity cannot be
    computed until an actual suffix exists.
    """

    if not suffix:
        return 0.0
    future_pitches = tuple(pitch for candidate in suffix for pitch in candidate.pitches)
    future_intervals = tuple(
        right - left
        for left, right in zip(future_pitches, future_pitches[1:], strict=False)
    )
    interval_echo = _interval_window_similarity(target.intervals, future_intervals)
    bridge = exp(-abs(suffix[0].pitches[0] - target.pitches[-1]) / 3.0)
    return 0.80 * interval_echo + 0.20 * bridge


def _candidate_digest(scored: Sequence[PredictiveBarScore]) -> str:
    payload = [
        {
            "pattern": [
                (cell.kind.value, [cell.duration.numerator, cell.duration.denominator])
                for cell in item.candidate.pattern.cells
            ],
            "pitches": list(item.candidate.pitches),
            "probability": item.probability,
            "invariant_similarity": item.invariant_similarity,
            "base_score": item.base.total,
        }
        for item in scored
    ]
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _choose_control(
    *,
    ipm: PredictiveBarScore,
    expected: PredictiveBarScore,
    scored: Sequence[PredictiveBarScore],
    suffix: Sequence[WholeBarCandidate],
    criteria: MatchCriteria,
) -> tuple[PredictiveBarScore | None, dict[str, Any]]:
    ipm_future = future_integration(ipm.candidate, suffix)
    candidates: list[tuple[tuple[float, ...], PredictiveBarScore, dict[str, float]]] = []
    ipm_pattern = _candidate_pattern_signature(ipm.candidate)

    for control in scored:
        if control is expected or control is ipm:
            continue
        if _candidate_pattern_signature(control.candidate) != ipm_pattern:
            continue
        surprise_error = abs(control.surprise_bits - ipm.surprise_bits)
        invariant_gap = ipm.invariant_similarity - control.invariant_similarity
        base_delta = abs(ipm.base.total - control.base.total)
        control_future = future_integration(control.candidate, suffix)
        future_gap = ipm_future - control_future
        metrics = {
            "target_surprise_error_bits": surprise_error,
            "local_invariant_gap": invariant_gap,
            "target_base_score_delta": base_delta,
            "ipm_future_integration": ipm_future,
            "control_future_integration": control_future,
            "future_integration_gap": future_gap,
        }
        if (
            surprise_error <= criteria.max_target_surprise_error_bits
            and invariant_gap >= criteria.min_local_invariant_gap
            and base_delta <= criteria.max_target_base_score_delta
            and ipm_future >= criteria.min_ipm_future_integration
            and future_gap >= criteria.min_future_integration_gap
        ):
            rank = (
                future_gap,
                invariant_gap,
                -surprise_error,
                -base_delta,
                control.base.total,
            )
            candidates.append((rank, control, metrics))

    if not candidates:
        return None, {
            "target_surprise_error_bits": None,
            "local_invariant_gap": None,
            "target_base_score_delta": None,
            "ipm_future_integration": ipm_future,
            "control_future_integration": None,
            "future_integration_gap": None,
        }
    _, control, metrics = max(candidates, key=lambda item: item[0])
    return control, metrics


def _episode_for_seed(
    *,
    seed: int,
    bars: int,
    target_bar: int,
    criteria: MatchCriteria,
) -> tuple[QualifiedEpisode | None, EpisodeAudit]:
    config = pilot_config(seed=seed, bars=bars)
    if not 1 <= target_bar < bars - 1:
        raise ValueError("target_bar must leave both a prefix and a suffix")

    rng = SeededRandom(config.seed ^ 0xA20)
    state = MusicalState()
    prefix: list[WholeBarCandidate] = []
    prefix_events: list[NoteEvent] = []

    for bar in range(target_bar):
        scored = _pool(rng=rng, state=state, config=config, bar=bar)
        selected = _expected(scored)
        prefix.append(selected.candidate)
        prefix_events.extend(
            _realise_candidate(
                selected.candidate,
                seed=seed,
                bar=bar,
                phase=_phase_for_bar(bar, bars),
                tonic_midi=config.tonic_midi,
                beats_per_bar=config.beats_per_bar,
            )
        )
        state = advance_state(state, selected.candidate)

    target_scored = _pool(rng=rng, state=state, config=config, bar=target_bar)
    expected = _expected(target_scored)
    ipm, ipm_branch, _ = _choose_predictive_bar(
        target_scored,
        mode=ExperimentMode.IPM,
    )

    # The suffix is generated once from the Predictable reference trajectory.
    # It is then copied verbatim into all three listener variants.
    suffix_state = advance_state(state, expected.candidate)
    suffix: list[WholeBarCandidate] = []
    suffix_events: list[NoteEvent] = []
    for bar in range(target_bar + 1, bars):
        scored = _pool(rng=rng, state=suffix_state, config=config, bar=bar)
        selected = _expected(scored)
        suffix.append(selected.candidate)
        suffix_events.extend(
            _realise_candidate(
                selected.candidate,
                seed=seed,
                bar=bar,
                phase=_phase_for_bar(bar, bars),
                tonic_midi=config.tonic_midi,
                beats_per_bar=config.beats_per_bar,
            )
        )
        suffix_state = advance_state(suffix_state, selected.candidate)

    control, pair_metrics = _choose_control(
        ipm=ipm,
        expected=expected,
        scored=target_scored,
        suffix=suffix,
        criteria=criteria,
    )

    ipm_nonexpected = ipm is not expected and ipm_branch != "expected"
    ipm_surprising = ipm.surprise_bits >= criteria.min_ipm_surprise_bits
    control_found = control is not None
    same_target_pattern = (
        control is not None
        and _candidate_pattern_signature(ipm.candidate)
        == _candidate_pattern_signature(control.candidate)
    )

    checks = {
        "shared_target_candidate_pool": True,
        "ipm_replaces_expected": ipm_nonexpected,
        "ipm_is_sufficiently_surprising": ipm_surprising,
        "matched_control_exists": control_found,
        "ipm_control_target_rhythm_identical": same_target_pattern,
        "target_surprise_matched": (
            control_found
            and pair_metrics["target_surprise_error_bits"]
            <= criteria.max_target_surprise_error_bits
        ),
        "control_has_weaker_local_invariants": (
            control_found
            and pair_metrics["local_invariant_gap"] >= criteria.min_local_invariant_gap
        ),
        "target_base_quality_matched": (
            control_found
            and pair_metrics["target_base_score_delta"]
            <= criteria.max_target_base_score_delta
        ),
        "ipm_integrates_with_actual_suffix": (
            control_found
            and pair_metrics["ipm_future_integration"]
            >= criteria.min_ipm_future_integration
        ),
        "actual_suffix_favours_ipm": (
            control_found
            and pair_metrics["future_integration_gap"]
            >= criteria.min_future_integration_gap
        ),
    }

    metrics: dict[str, Any] = {
        "candidate_pool_sha256": _candidate_digest(target_scored),
        "target_bar": target_bar,
        "ipm_branch": ipm_branch,
        "expected_surprise_bits": expected.surprise_bits,
        "ipm_surprise_bits": ipm.surprise_bits,
        "expected_invariant_similarity": expected.invariant_similarity,
        "ipm_invariant_similarity": ipm.invariant_similarity,
        **pair_metrics,
    }
    if control is not None:
        metrics.update(
            {
                "control_surprise_bits": control.surprise_bits,
                "control_invariant_similarity": control.invariant_similarity,
            }
        )

    passed = all(checks.values())
    audit = EpisodeAudit(seed, target_bar, passed, checks, metrics)
    if not passed or control is None:
        return None, audit

    target_phase = _phase_for_bar(target_bar, bars)
    common_non_target = tuple(prefix_events + suffix_events)
    variants: dict[ExperimentMode, EpisodeVariant] = {}
    for mode, target_score in (
        (ExperimentMode.PREDICTABLE, expected),
        (ExperimentMode.IPM, ipm),
        (ExperimentMode.UNSTRUCTURED_SURPRISE, control),
    ):
        target_events = _realise_candidate(
            target_score.candidate,
            seed=seed,
            bar=target_bar,
            phase=target_phase,
            tonic_midi=config.tonic_midi,
            beats_per_bar=config.beats_per_bar,
        )
        tune = Voice.from_events("TUNE", (*common_non_target, *target_events))
        variants[mode] = EpisodeVariant(
            mode=mode,
            tune=tune,
            target=target_score,
            future_integration=future_integration(target_score.candidate, suffix),
        )

    # Verify the causal object itself, rather than trusting construction intent.
    start = Fraction(target_bar * config.beats_per_bar)
    end = start + config.beats_per_bar

    def outside_target(voice: Voice) -> tuple[NoteEvent, ...]:
        return tuple(event for event in voice.events if event.onset < start or event.onset >= end)

    outside = {outside_target(variant.tune) for variant in variants.values()}
    if len(outside) != 1:
        failed_checks = dict(checks)
        failed_checks["non_target_music_identical"] = False
        failed = EpisodeAudit(seed, target_bar, False, failed_checks, metrics)
        return None, failed

    final_checks = dict(checks)
    final_checks["non_target_music_identical"] = True
    final_audit = EpisodeAudit(seed, target_bar, True, final_checks, metrics)
    return QualifiedEpisode(seed, target_bar, variants, final_audit), final_audit


def qualify_episodes(
    *,
    start_seed: int,
    count: int,
    search_limit: int,
    bars: int = 8,
    target_bar: int = 4,
    criteria: MatchCriteria | None = None,
) -> QualificationRun:
    """Search a deterministic seed range and retain the entire selection funnel."""

    if count <= 0:
        raise ValueError("count must be positive")
    if search_limit < count:
        raise ValueError("search_limit must be >= count")
    criteria = criteria or MatchCriteria()

    accepted: list[QualifiedEpisode] = []
    audits: list[EpisodeAudit] = []
    final_seed = start_seed - 1
    for seed in range(start_seed, start_seed + search_limit):
        final_seed = seed
        episode, audit = _episode_for_seed(
            seed=seed,
            bars=bars,
            target_bar=target_bar,
            criteria=criteria,
        )
        audits.append(audit)
        if episode is not None:
            accepted.append(episode)
            if len(accepted) == count:
                return QualificationRun(tuple(accepted), tuple(audits), final_seed)

    failure_counts: dict[str, int] = {}
    for audit in audits:
        for name, passed in audit.checks.items():
            if not passed:
                failure_counts[name] = failure_counts.get(name, 0) + 1
    raise RuntimeError(
        "Only "
        f"{len(accepted)} of {count} required matched episodes qualified within "
        f"{search_limit} seeds. Failure counts: {failure_counts}"
    )


def _blind_id(blind_seed: int, seed: int, mode: ExperimentMode) -> str:
    payload = f"{blind_seed}:{seed}:{mode.value}".encode("utf-8")
    return "stim-" + hashlib.sha256(payload).hexdigest()[:12]


def _condition_assignments(
    qualified: Sequence[QualifiedEpisode],
    *,
    blind_seed: int,
) -> dict[int, list[dict[str, Any]]]:
    """Create three condition-assignment groups, one condition per seed."""

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
        groups[group + 1] = rows
    return groups


def _participant_schedules(
    qualified: Sequence[QualifiedEpisode],
    *,
    blind_seed: int,
    participant_count: int,
) -> tuple[dict[str, Any], ...]:
    """Balance conditions by group but give every participant a unique order."""

    if participant_count <= 0:
        raise ValueError("participant_count must be positive")
    groups = _condition_assignments(qualified, blind_seed=blind_seed)
    schedules: list[dict[str, Any]] = []
    for index in range(participant_count):
        participant_id = f"P{index + 1:03d}"
        group = (index % 3) + 1
        rows = [dict(row) for row in groups[group]]
        random.Random(blind_seed ^ 0x51A7 ^ (index + 1)).shuffle(rows)
        schedules.append(
            {
                "participant_id": participant_id,
                "group": group,
                "rows": [
                    {
                        "trial": trial,
                        "stimulus_id": row["stimulus_id"],
                        "seed": row["seed"],
                        "mode": row["mode"],
                    }
                    for trial, row in enumerate(rows, start=1)
                ],
            }
        )
    return tuple(schedules)


def _write_csv(
    path: Path,
    fieldnames: Sequence[str],
    rows: Sequence[Mapping[str, Any]],
) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _audit_json(audit: EpisodeAudit) -> dict[str, Any]:
    return {
        "seed": audit.seed,
        "target_bar": audit.target_bar,
        "passed": audit.passed,
        "checks": dict(audit.checks),
        "metrics": dict(audit.metrics),
    }


def write_listening_pilot(
    output_dir: str | Path,
    *,
    start_seed: int = 2026081800,
    set_count: int = 12,
    search_limit: int = 512,
    bars: int = 8,
    target_bar: int = 4,
    blind_seed: int = 2026081801,
    participant_count: int = 36,
    source_revision: str = "unknown",
    criteria: MatchCriteria | None = None,
) -> Path:
    """Build the blinded counterfactual MIDI set and complete research audit trail."""

    criteria = criteria or MatchCriteria()
    run = qualify_episodes(
        start_seed=start_seed,
        count=set_count,
        search_limit=search_limit,
        bars=bars,
        target_bar=target_bar,
        criteria=criteria,
    )

    output = Path(output_dir)
    stimuli = output / "stimuli"
    researcher = output / "researcher"
    schedules_dir = output / "participant-schedules"
    stimuli.mkdir(parents=True, exist_ok=True)
    researcher.mkdir(parents=True, exist_ok=True)
    schedules_dir.mkdir(parents=True, exist_ok=True)

    key_rows: list[dict[str, Any]] = []
    for item in run.qualified:
        for mode, variant in item.variants.items():
            stimulus_id = _blind_id(blind_seed, item.seed, mode)
            midi_path = stimuli / f"{stimulus_id}.mid"
            midi_path.write_bytes(
                render_midi(
                    (variant.tune,),
                    tempo_bpm=pilot_config(seed=item.seed, bars=bars).tempo_bpm,
                    beats_per_bar=4,
                )
            )
            key_rows.append(
                {
                    "stimulus_id": stimulus_id,
                    "seed": item.seed,
                    "condition": mode.value,
                    "target_bar": item.target_bar,
                    "target_surprise_bits": variant.target.surprise_bits,
                    "target_invariant_similarity": variant.target.invariant_similarity,
                    "future_integration": variant.future_integration,
                }
            )

    _write_csv(
        researcher / "condition-key.csv",
        (
            "stimulus_id",
            "seed",
            "condition",
            "target_bar",
            "target_surprise_bits",
            "target_invariant_similarity",
            "future_integration",
        ),
        key_rows,
    )

    with (researcher / "qualification-audits.jsonl").open("w", encoding="utf-8") as handle:
        for audit in run.audits:
            handle.write(json.dumps(_audit_json(audit), sort_keys=True) + "\n")

    schedules = _participant_schedules(
        run.qualified,
        blind_seed=blind_seed,
        participant_count=participant_count,
    )
    assignment_rows: list[dict[str, Any]] = []
    for schedule in schedules:
        participant_id = schedule["participant_id"]
        group = schedule["group"]
        participant_rows = [
            {"trial": row["trial"], "stimulus_id": row["stimulus_id"]}
            for row in schedule["rows"]
        ]
        _write_csv(
            schedules_dir / f"{participant_id}.csv",
            ("trial", "stimulus_id"),
            participant_rows,
        )
        assignment_rows.append(
            {"participant_id": participant_id, "counterbalance_group": group}
        )

    _write_csv(
        researcher / "participant-assignments.csv",
        ("participant_id", "counterbalance_group"),
        assignment_rows,
    )

    _write_csv(
        output / "participant-schema.csv",
        (
            "participant_id",
            "counterbalance_group",
            "music_making_years",
            "formal_music_training_years",
            "completed_main_block",
            "playback_failure",
            "duplicate_participation",
            "record_usable",
            "exclusion_reason",
        ),
        (),
    )
    _write_csv(
        output / "response-schema.csv",
        (
            "participant_id",
            "trial",
            "stimulus_id",
            "retrospective_sense_0_100",
            "surprise_0_100",
            "coherence_0_100",
            "liking_0_100",
            "hear_again_0_100",
        ),
        (),
    )

    manifest = {
        "experiment": "IPM Listening Experiment 1 — matched counterfactual episode pilot",
        "source_revision": source_revision,
        "bars": bars,
        "target_bar_zero_indexed": target_bar,
        "set_count": set_count,
        "participant_count": participant_count,
        "conditions": [mode.value for mode in ExperimentMode],
        "causal_contract": {
            "prefix_identical": True,
            "shared_target_candidate_pool": True,
            "single_target_bar_intervention": True,
            "suffix_identical": True,
            "primary_mechanism_outcome": "retrospective_sense_0_100",
        },
        "criteria": asdict(criteria),
        "selection": {
            "start_seed": start_seed,
            "search_limit": search_limit,
            "final_seed_examined": run.final_seed_examined,
            "attempted_seed_count": len(run.audits),
            "qualified_seeds": [item.seed for item in run.qualified],
            "audit_trail": "researcher/qualification-audits.jsonl",
        },
        "blinding": {
            "blind_seed": blind_seed,
            "condition_key": "researcher/condition-key.csv",
            "participant_files_expose_condition": False,
            "counterbalance_groups": 3,
            "participant_specific_trial_order": True,
        },
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return output


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the matched IPM counterfactual listening pilot"
    )
    parser.add_argument("--output", default="listening-pilot")
    parser.add_argument("--sets", type=int, default=12)
    parser.add_argument("--start-seed", type=int, default=2026081800)
    parser.add_argument("--search-limit", type=int, default=512)
    parser.add_argument("--bars", type=int, default=8)
    parser.add_argument("--target-bar", type=int, default=4)
    parser.add_argument("--blind-seed", type=int, default=2026081801)
    parser.add_argument("--participants", type=int, default=36)
    parser.add_argument("--source-revision", default="unknown")
    args = parser.parse_args()

    output = write_listening_pilot(
        args.output,
        start_seed=args.start_seed,
        set_count=args.sets,
        search_limit=args.search_limit,
        bars=args.bars,
        target_bar=args.target_bar,
        blind_seed=args.blind_seed,
        participant_count=args.participants,
        source_revision=args.source_revision,
    )
    print(output)


if __name__ == "__main__":
    main()

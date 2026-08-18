"""Counterfactual Episode v2 for the IPM listening gate.

This module is experiment-layer only.  It freezes the production target pool and
IPM selection, then constructs a surprise-matched control by holding the IPM
target rhythm fixed while generating alternative pitch realisations from the
identical pre-target musical state.  The common suffix is generated from the
IPM target state and then attached unchanged to all three variants.
"""

from __future__ import annotations

import argparse
import json
from math import exp, log2
from fractions import Fraction
from pathlib import Path
from typing import Sequence

from . import experiment as v1
from .engine import (
    ExperimentMode,
    PredictiveBarScore,
    _bar_invariant_similarity,
    _calibrated_surprise,
    _choose_predictive_bar,
    _phase_for_bar,
)
from .model import Voice
from .randomness import SeededRandom
from .sequential_bar import (
    MusicalState,
    WholeBarCandidate,
    _choose_pitch,
    _phase_pitch_target,
    advance_state,
    scale_pitches,
    score_whole_bar,
)

CONTROL_PITCH_ALTERNATIVES = 64
_CONTROL_RNG_XOR = 0xC02F7A11
_SOFTMAX_TEMPERATURE = 0.08  # engine._softmax_probabilities default in v0.2


def _reference_score(
    candidate: WholeBarCandidate,
    *,
    ipm: PredictiveBarScore,
    state: MusicalState,
    phase: str,
    tonic_midi: int,
    final_bar: bool,
) -> PredictiveBarScore:
    """Score a generated control without renormalising the frozen target pool.

    Softmax odds are exponential in base-score difference.  Referencing the
    frozen IPM probability therefore puts generated controls on the exact same
    surprise scale while leaving the original target probabilities untouched.
    """

    base = score_whole_bar(
        candidate,
        state=state,
        phase=phase,
        tonic_midi=tonic_midi,
        final_bar=final_bar,
    )
    probability = ipm.probability * exp(
        (base.total - ipm.base.total) / _SOFTMAX_TEMPERATURE
    )
    probability = min(1.0, max(probability, 1e-12))
    invariant = _bar_invariant_similarity(state, candidate)
    surprise = -log2(probability)
    calibrated = _calibrated_surprise(probability)
    retrospective = (
        0.50 * invariant
        + 0.32 * base.phrase_direction
        + 0.18 * base.cadence
    )
    necessity = (1.0 - probability) * retrospective
    ipm_score = (
        0.32 * base.total
        + 0.28 * invariant
        + 0.22 * necessity
        + 0.18 * calibrated
    )
    return PredictiveBarScore(
        candidate=candidate,
        base=base,
        probability=probability,
        surprise_bits=surprise,
        calibrated_surprise=calibrated,
        invariant_similarity=invariant,
        retrospective_coherence=retrospective,
        retrospective_necessity=necessity,
        ipm_score=ipm_score,
    )


def _fixed_rhythm_pitch_scores(
    *,
    seed: int,
    target_bar: int,
    ipm: PredictiveBarScore,
    state: MusicalState,
    phase: str,
    tonic_midi: int,
    count: int = CONTROL_PITCH_ALTERNATIVES,
) -> tuple[PredictiveBarScore, ...]:
    """Generate deterministic pitch-only alternatives on the IPM target rhythm."""

    if count <= 0:
        raise ValueError("control pitch alternative count must be positive")

    rng = SeededRandom(seed ^ _CONTROL_RNG_XOR ^ (target_bar * 0x9E3779B1))
    pitch_pool = scale_pitches(tonic_midi)
    phase_target = _phase_pitch_target(tonic_midi, phase)
    pattern = ipm.candidate.pattern
    seen = {ipm.candidate.pitches}
    result: list[PredictiveBarScore] = []
    attempts = 0
    max_attempts = count * 16

    while len(result) < count and attempts < max_attempts:
        attempts += 1
        previous = state.last_pitch if state.last_pitch is not None else tonic_midi
        pitches: list[int] = []
        for attack in range(pattern.attacks):
            pitch = _choose_pitch(
                rng=rng,
                pool=pitch_pool,
                previous=previous,
                phase_target=phase_target,
                state=state,
                first_in_bar=attack == 0,
            )
            pitches.append(pitch)
            previous = pitch
        pitch_tuple = tuple(pitches)
        if pitch_tuple in seen:
            continue
        seen.add(pitch_tuple)
        candidate = WholeBarCandidate(pattern=pattern, pitches=pitch_tuple)
        result.append(
            _reference_score(
                candidate,
                ipm=ipm,
                state=state,
                phase=phase,
                tonic_midi=tonic_midi,
                final_bar=False,
            )
        )

    return tuple(result)


def _locally_matched_controls_v2(
    *,
    ipm: PredictiveBarScore,
    controls: Sequence[PredictiveBarScore],
    criteria: v1.MatchCriteria,
) -> tuple[PredictiveBarScore, ...]:
    return tuple(
        control
        for control in controls
        if abs(control.surprise_bits - ipm.surprise_bits)
        <= criteria.max_target_surprise_error_bits
        and ipm.invariant_similarity - control.invariant_similarity
        >= criteria.min_local_invariant_gap
        and abs(ipm.base.total - control.base.total)
        <= criteria.max_target_base_score_delta
    )


def _episode_for_seed_v2(
    *,
    seed: int,
    bars: int,
    target_bar: int,
    criteria: v1.MatchCriteria,
) -> tuple[v1.QualifiedEpisode | None, v1.EpisodeAudit]:
    config = v1.pilot_config(seed=seed, bars=bars)
    if not 1 <= target_bar < bars - 1:
        raise ValueError("target_bar must leave both a prefix and a suffix")

    rng = SeededRandom(config.seed ^ 0xA20)
    state = MusicalState()
    prefix_events = []

    for bar in range(target_bar):
        scored = v1._pool(rng=rng, state=state, config=config, bar=bar)
        selected = v1._expected(scored)
        prefix_events.extend(
            v1._realise_candidate(
                selected.candidate,
                seed=seed,
                bar=bar,
                phase=_phase_for_bar(bar, bars),
                tonic_midi=config.tonic_midi,
                beats_per_bar=config.beats_per_bar,
            )
        )
        state = advance_state(state, selected.candidate)

    target_scored = v1._pool(rng=rng, state=state, config=config, bar=target_bar)
    expected = v1._expected(target_scored)
    ipm, ipm_branch, _ = _choose_predictive_bar(
        target_scored,
        mode=ExperimentMode.IPM,
    )
    ipm_nonexpected = ipm is not expected and ipm_branch != "expected"
    ipm_surprising = ipm.surprise_bits >= criteria.min_ipm_surprise_bits
    phase = _phase_for_bar(target_bar, bars)

    base_metrics = {
        "candidate_pool_sha256": v1._candidate_digest(target_scored),
        "target_bar": target_bar,
        "ipm_branch": ipm_branch,
        "expected_surprise_bits": expected.surprise_bits,
        "ipm_surprise_bits": ipm.surprise_bits,
        "expected_invariant_similarity": expected.invariant_similarity,
        "ipm_invariant_similarity": ipm.invariant_similarity,
        "control_pitch_alternative_budget": CONTROL_PITCH_ALTERNATIVES,
    }
    if not ipm_nonexpected or not ipm_surprising:
        checks = {
            "target_pool_frozen_before_control_search": True,
            "shared_pre_target_state": True,
            "ipm_replaces_expected": ipm_nonexpected,
            "ipm_is_sufficiently_surprising": ipm_surprising,
        }
        return None, v1.EpisodeAudit(seed, target_bar, False, checks, base_metrics)

    generated_controls = _fixed_rhythm_pitch_scores(
        seed=seed,
        target_bar=target_bar,
        ipm=ipm,
        state=state,
        phase=phase,
        tonic_midi=config.tonic_midi,
    )
    surprise_matched = tuple(
        item
        for item in generated_controls
        if abs(item.surprise_bits - ipm.surprise_bits)
        <= criteria.max_target_surprise_error_bits
    )
    weaker_invariant = tuple(
        item
        for item in generated_controls
        if ipm.invariant_similarity - item.invariant_similarity
        >= criteria.min_local_invariant_gap
    )
    base_matched = tuple(
        item
        for item in generated_controls
        if abs(ipm.base.total - item.base.total)
        <= criteria.max_target_base_score_delta
    )
    local_controls = _locally_matched_controls_v2(
        ipm=ipm,
        controls=generated_controls,
        criteria=criteria,
    )

    local_checks = {
        "target_pool_frozen_before_control_search": True,
        "shared_pre_target_state": True,
        "ipm_replaces_expected": ipm_nonexpected,
        "ipm_is_sufficiently_surprising": ipm_surprising,
        "control_pitch_realisations_generated": bool(generated_controls),
        "ipm_control_target_rhythm_identical": bool(generated_controls),
        "target_surprise_match_available": bool(surprise_matched),
        "weaker_local_invariant_available": bool(weaker_invariant),
        "target_base_quality_match_available": bool(base_matched),
        "matched_control_exists": bool(local_controls),
    }
    local_metrics = {
        **base_metrics,
        "generated_control_count": len(generated_controls),
        "surprise_matched_control_count": len(surprise_matched),
        "weaker_invariant_control_count": len(weaker_invariant),
        "base_matched_control_count": len(base_matched),
        "locally_matched_control_count": len(local_controls),
    }
    if not all(local_checks.values()):
        return None, v1.EpisodeAudit(seed, target_bar, False, local_checks, local_metrics)

    # The common future is conditioned on the IPM intervention itself, then frozen.
    suffix_state = advance_state(state, ipm.candidate)
    suffix = []
    suffix_events = []
    for bar in range(target_bar + 1, bars):
        scored = v1._pool(rng=rng, state=suffix_state, config=config, bar=bar)
        selected = v1._expected(scored)
        suffix.append(selected.candidate)
        suffix_events.extend(
            v1._realise_candidate(
                selected.candidate,
                seed=seed,
                bar=bar,
                phase=_phase_for_bar(bar, bars),
                tonic_midi=config.tonic_midi,
                beats_per_bar=config.beats_per_bar,
            )
        )
        suffix_state = advance_state(suffix_state, selected.candidate)

    control, pair_metrics = v1._choose_control(
        ipm=ipm,
        controls=local_controls,
        suffix=suffix,
    )
    checks = {
        **local_checks,
        "suffix_generated_from_ipm_target_state": True,
        "ipm_integrates_with_actual_suffix": (
            pair_metrics["ipm_future_integration"]
            >= criteria.min_ipm_future_integration
        ),
        "actual_suffix_favours_ipm": (
            pair_metrics["future_integration_gap"]
            >= criteria.min_future_integration_gap
        ),
    }
    metrics = {
        **local_metrics,
        **pair_metrics,
        "control_surprise_bits": control.surprise_bits,
        "control_invariant_similarity": control.invariant_similarity,
    }
    if not all(checks.values()):
        return None, v1.EpisodeAudit(seed, target_bar, False, checks, metrics)

    target_phase = _phase_for_bar(target_bar, bars)
    common_non_target = tuple(prefix_events + suffix_events)
    variants = {}
    for mode, target_score in (
        (ExperimentMode.PREDICTABLE, expected),
        (ExperimentMode.IPM, ipm),
        (ExperimentMode.UNSTRUCTURED_SURPRISE, control),
    ):
        target_events = v1._realise_candidate(
            target_score.candidate,
            seed=seed,
            bar=target_bar,
            phase=target_phase,
            tonic_midi=config.tonic_midi,
            beats_per_bar=config.beats_per_bar,
        )
        tune = Voice.from_events("TUNE", (*common_non_target, *target_events))
        variants[mode] = v1.EpisodeVariant(
            mode=mode,
            tune=tune,
            target=target_score,
            future_integration=v1.future_integration(target_score.candidate, suffix),
        )

    start = Fraction(target_bar * config.beats_per_bar)
    end = start + config.beats_per_bar

    def outside_target(voice):
        return tuple(
            event
            for event in voice.events
            if event.onset < start or event.onset >= end
        )

    outside = {outside_target(variant.tune) for variant in variants.values()}
    if len(outside) != 1:
        failed_checks = dict(checks)
        failed_checks["non_target_music_identical"] = False
        return None, v1.EpisodeAudit(seed, target_bar, False, failed_checks, metrics)

    final_checks = dict(checks)
    final_checks["non_target_music_identical"] = True
    final_audit = v1.EpisodeAudit(seed, target_bar, True, final_checks, metrics)
    return v1.QualifiedEpisode(seed, target_bar, variants, final_audit), final_audit


def write_listening_pilot_v2(
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
    criteria: v1.MatchCriteria | None = None,
) -> Path:
    """Build the v2 corpus while reusing v1's artifact/blinding machinery."""

    original_episode_builder = v1._episode_for_seed
    v1._episode_for_seed = _episode_for_seed_v2
    try:
        output = v1.write_listening_pilot(
            output_dir,
            start_seed=start_seed,
            set_count=set_count,
            search_limit=search_limit,
            bars=bars,
            target_bar=target_bar,
            blind_seed=blind_seed,
            participant_count=participant_count,
            source_revision=source_revision,
            criteria=criteria,
        )
    finally:
        v1._episode_for_seed = original_episode_builder

    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["experiment"] = (
        "IPM Listening Experiment 1 — Counterfactual Episode v2 pilot"
    )
    manifest["causal_contract"] = {
        "prefix_identical": True,
        "target_pool_frozen_before_control_search": True,
        "control_pitch_search_same_pre_target_state": True,
        "control_target_rhythm_identical_to_ipm": True,
        "single_target_bar_intervention": True,
        "suffix_generated_from_ipm_target_state": True,
        "suffix_identical_across_conditions": True,
        "primary_mechanism_outcome": "retrospective_sense_0_100",
    }
    manifest["control_construction"] = {
        "pitch_alternative_budget": CONTROL_PITCH_ALTERNATIVES,
        "independent_rng_stream": True,
        "surprise_reference": "frozen original target-pool softmax",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build Counterfactual Episode v2 for the IPM listening gate"
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

    output = write_listening_pilot_v2(
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

"""Audible-articulation lock for Counterfactual Episode v2.

The v2 control already fixes the IPM structural bar pattern, but the production
micro-rhythm realiser consumes pitch-dependent random draws and can therefore
produce different audible subdivisions for different pitch anchors.  This
experiment-only layer freezes the IPM target's realised subdivision, duration,
and velocity template and replays it for the control.  Pitch remains the only
IPM-vs-control target difference.
"""

from __future__ import annotations

import argparse
import json
from fractions import Fraction
from pathlib import Path
from typing import Sequence

from . import experiment as v1
from . import experiment_v2 as v2
from .bar_rhythm import BarCellKind
from .engine import ExperimentMode, _phase_for_bar
from .micro_rhythm import _micro_pitches, aeolian_pool, realise_micro_bar
from .model import NoteEvent, Voice
from .randomness import SeededRandom
from .sequential_bar import WholeBarCandidate

_BASE_EPISODE_BUILDER = v2._episode_for_seed_v2
_PITCH_RNG_XOR = 0xC017A710

Articulation = tuple[tuple[tuple[Fraction, ...], tuple[int, ...]], ...]


def _ipm_target_events_and_articulation(
    candidate: WholeBarCandidate,
    *,
    seed: int,
    bar: int,
    phase: str,
    tonic_midi: int,
    beats_per_bar: int,
) -> tuple[tuple[NoteEvent, ...], Articulation]:
    cells = tuple((cell.kind, cell.duration) for cell in candidate.pattern.cells)
    micro_rng = SeededRandom(seed ^ 0xA21000 ^ (bar * 0x9E3779B1))
    events, decisions = realise_micro_bar(
        cells,
        candidate.pitches,
        start=Fraction(bar * beats_per_bar),
        phase=phase,
        rng=micro_rng,
        tonic_midi=tonic_midi,
    )
    articulation = []
    cursor = 0
    for decision in decisions:
        count = len(decision.segments)
        velocities = tuple(event.velocity for event in events[cursor : cursor + count])
        articulation.append((decision.segments, velocities))
        cursor += count
    if cursor != len(events):
        raise AssertionError("micro-rhythm articulation did not account for all events")
    return events, tuple(articulation)


def _realise_with_fixed_articulation(
    candidate: WholeBarCandidate,
    articulation: Sequence[tuple[tuple[Fraction, ...], tuple[int, ...]]],
    *,
    seed: int,
    bar: int,
    tonic_midi: int,
    beats_per_bar: int,
) -> tuple[NoteEvent, ...]:
    if len(articulation) != candidate.pattern.attacks:
        raise ValueError("articulation must cover every structural note cell")

    pitch_rng = SeededRandom(seed ^ _PITCH_RNG_XOR ^ (bar * 0x9E3779B1))
    pool = aeolian_pool(tonic_midi)
    cursor = Fraction(bar * beats_per_bar)
    note_index = 0
    events: list[NoteEvent] = []

    for cell in candidate.pattern.cells:
        if cell.kind is BarCellKind.REST:
            cursor += cell.duration
            continue

        segments, velocities = articulation[note_index]
        if sum(segments, Fraction(0)) != cell.duration:
            raise ValueError("frozen articulation does not fill its structural cell")
        if len(segments) != len(velocities):
            raise ValueError("frozen articulation velocity count mismatch")

        anchor = candidate.pitches[note_index]
        micro_pitches = _micro_pitches(anchor, len(segments), pool=pool, rng=pitch_rng)
        local = cursor
        for segment, pitch, velocity in zip(segments, micro_pitches, velocities, strict=True):
            gate = Fraction(3, 4) if segment == Fraction(1, 4) else Fraction(7, 8)
            events.append(
                NoteEvent(
                    onset=local,
                    duration=segment * gate,
                    pitch=pitch,
                    velocity=velocity,
                )
            )
            local += segment
        cursor += cell.duration
        note_index += 1

    return tuple(events)


def _rhythm_signature(events: Sequence[NoteEvent]) -> tuple[tuple[Fraction, Fraction, int], ...]:
    return tuple((event.onset, event.duration, event.velocity) for event in events)


def _episode_for_seed_v2_articulated(
    *,
    seed: int,
    bars: int,
    target_bar: int,
    criteria: v1.MatchCriteria,
) -> tuple[v1.QualifiedEpisode | None, v1.EpisodeAudit]:
    episode, audit = _BASE_EPISODE_BUILDER(
        seed=seed,
        bars=bars,
        target_bar=target_bar,
        criteria=criteria,
    )
    if episode is None:
        return None, audit

    config = v1.pilot_config(seed=seed, bars=bars)
    target_phase = _phase_for_bar(target_bar, bars)
    ipm_variant = episode.variants[ExperimentMode.IPM]
    control_variant = episode.variants[ExperimentMode.UNSTRUCTURED_SURPRISE]

    ipm_events, articulation = _ipm_target_events_and_articulation(
        ipm_variant.target.candidate,
        seed=seed,
        bar=target_bar,
        phase=target_phase,
        tonic_midi=config.tonic_midi,
        beats_per_bar=config.beats_per_bar,
    )
    control_events = _realise_with_fixed_articulation(
        control_variant.target.candidate,
        articulation,
        seed=seed,
        bar=target_bar,
        tonic_midi=config.tonic_midi,
        beats_per_bar=config.beats_per_bar,
    )

    checks = dict(audit.checks)
    audible_match = _rhythm_signature(ipm_events) == _rhythm_signature(control_events)
    checks["ipm_control_audible_rhythm_identical"] = audible_match
    if not audible_match:
        return None, v1.EpisodeAudit(seed, target_bar, False, checks, audit.metrics)

    target_start = Fraction(target_bar * config.beats_per_bar)
    target_end = target_start + config.beats_per_bar
    common_non_target = tuple(
        event
        for event in ipm_variant.tune.events
        if event.onset < target_start or event.onset >= target_end
    )

    variants = dict(episode.variants)
    variants[ExperimentMode.IPM] = v1.EpisodeVariant(
        mode=ExperimentMode.IPM,
        tune=Voice.from_events("TUNE", (*common_non_target, *ipm_events)),
        target=ipm_variant.target,
        future_integration=ipm_variant.future_integration,
    )
    variants[ExperimentMode.UNSTRUCTURED_SURPRISE] = v1.EpisodeVariant(
        mode=ExperimentMode.UNSTRUCTURED_SURPRISE,
        tune=Voice.from_events("TUNE", (*common_non_target, *control_events)),
        target=control_variant.target,
        future_integration=control_variant.future_integration,
    )

    final_audit = v1.EpisodeAudit(seed, target_bar, True, checks, audit.metrics)
    return v1.QualifiedEpisode(seed, target_bar, variants, final_audit), final_audit


def write_listening_pilot_v2_articulated(
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
    original = v2._episode_for_seed_v2
    v2._episode_for_seed_v2 = _episode_for_seed_v2_articulated
    try:
        output = v2.write_listening_pilot_v2(
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
        v2._episode_for_seed_v2 = original

    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["causal_contract"]["control_audible_articulation_identical_to_ipm"] = True
    manifest["realisation"] = {
        "target_articulation_source": "IPM target",
        "control_replays_ipm_subdivisions_durations_velocities": True,
        "control_pitch_stream_independent": True,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build articulated Counterfactual Episode v2 listening pilot"
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

    output = write_listening_pilot_v2_articulated(
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

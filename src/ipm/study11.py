"""Study #011: shorter bass phrasing plus explicit learn/lock/unlock patterns.

Study #010 established TUNE/BASS/RHYTHM as three scalable lanes. Listening found the
bass slightly too sustained and suggested that good patterns should be lockable.
Study #011 shortens the bass vocabulary while demonstrating a scalable rhythm pattern
captured from one generated bar, locked for a short window, then released again.
"""

from __future__ import annotations

import argparse
import copy
import json
from fractions import Fraction
from pathlib import Path
from statistics import median
from typing import Any

from .lanes import BASS_LANE, RHYTHM_LANE, ScaleWorld
from .midi import render_midi
from .model import Beat, IPMConfig, NoteEvent, Voice
from .patterns import PatternBank, capture_pattern, realise_pattern
from .sonority import score_texture, set_coherence
from .study import _event_json
from .study10 import (
    ThreeLaneStudyResult,
    _bass_candidate_score,
    _circular_degree_distance,
    _overlapping,
    compose_study_010,
)


_BASS_PATTERNS: dict[str, tuple[tuple[Beat, ...], ...]] = {
    "opening": ((Fraction(2), Fraction(2)),),
    "establishment": (
        (Fraction(2), Fraction(2)),
        (Fraction(1), Fraction(1), Fraction(2)),
    ),
    "development": (
        (Fraction(1), Fraction(1), Fraction(2)),
        (Fraction(2), Fraction(1), Fraction(1)),
    ),
    "climax": ((Fraction(1), Fraction(1), Fraction(1), Fraction(1)),),
    "resolution": (
        (Fraction(2), Fraction(2)),
        (Fraction(1), Fraction(1), Fraction(2)),
    ),
    "ending": ((Fraction(2), Fraction(2)),),
}

_LOCK_SOURCE_BAR = 5
_LOCK_TARGET_BARS = (7, 8, 9)


def _fraction_json(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def _active_pitch(voice: Voice, onset: Beat) -> int | None:
    for event in reversed(voice.events):
        if event.onset <= onset < event.end:
            return event.pitch
        if event.end <= onset:
            break
    return None


def _bass_pattern(phase: str, bar_index: int) -> tuple[Beat, ...]:
    choices = _BASS_PATTERNS[phase]
    return choices[bar_index % len(choices)]


def _compose_shorter_bass(
    tune: Voice,
    bar_trace: list[dict[str, Any]],
    *,
    world: ScaleWorld,
) -> tuple[Voice, list[dict[str, Any]]]:
    bass = Voice("BASS")
    trace: list[dict[str, Any]] = []
    previous_degree: int | None = None

    for bar in bar_trace:
        bar_index = int(bar["bar"])
        phase = str(bar["phase"])
        spans = _bass_pattern(phase, bar_index)
        cursor = Fraction(bar_index * 4)
        decisions: list[dict[str, Any]] = []

        for segment_index, span in enumerate(spans):
            start = cursor
            end = start + span
            tune_events = _overlapping(tune.events, start, end)
            if tune_events:
                anchor_event = max(tune_events, key=lambda event: (event.end, event.onset))
                anchor_degree = world.degree_class(world.degree_from_pitch(anchor_event.pitch))
            else:
                anchor_degree = previous_degree if previous_degree is not None else 0

            candidates = sorted(
                {
                    anchor_degree % 7,
                    (anchor_degree - 2) % 7,
                    (anchor_degree - 4) % 7,
                    0,
                    4,
                }
            )
            final_segment = bar_index == 15 and segment_index == len(spans) - 1
            scored: list[tuple[float, int, int]] = []
            for degree in candidates:
                pitch = world.project_degree(degree, BASS_LANE)
                score = _bass_candidate_score(
                    degree=degree,
                    pitch=pitch,
                    tune_events=tune_events,
                    start=start,
                    end=end,
                    previous_degree=previous_degree,
                    phase=phase,
                    final_segment=final_segment,
                )
                scored.append((score, degree, pitch))

            if final_segment:
                selected = next(item for item in scored if item[1] == 0)
            else:
                selected = max(
                    scored,
                    key=lambda item: (
                        item[0],
                        -_circular_degree_distance(item[1], anchor_degree),
                        -item[1],
                    ),
                )
            score, degree, pitch = selected
            event = NoteEvent(
                onset=start,
                duration=span * Fraction(7, 8),
                pitch=pitch,
                velocity=58 if phase != "climax" else 64,
            )
            bass.add(event)
            decisions.append(
                {
                    "segment": segment_index,
                    "span": _fraction_json(span),
                    "onset": _fraction_json(start),
                    "anchor_degree": anchor_degree,
                    "selected_degree": degree,
                    "selected_pitch": pitch,
                    "selected_score": score,
                }
            )
            previous_degree = degree
            cursor += span

        if cursor != Fraction((bar_index + 1) * 4):
            raise ValueError("bass pattern must fill exactly one four-beat bar")
        trace.append(
            {
                "bar": bar_index,
                "phase": phase,
                "pattern": [_fraction_json(span) for span in spans],
                "decisions": decisions,
            }
        )
    return bass, trace


def _locked_anchor_score(
    events: tuple[NoteEvent, ...],
    *,
    tune: Voice,
    bass: Voice,
) -> float:
    scores: list[float] = []
    for event in events:
        active = [
            pitch
            for pitch in (_active_pitch(tune, event.onset), _active_pitch(bass, event.onset))
            if pitch is not None
        ]
        scores.append(set_coherence((*active, event.pitch)) if active else 1.0)
    return sum(scores) / len(scores)


def _apply_rhythm_lock(
    parent_rhythm: Voice,
    tune: Voice,
    bass: Voice,
    *,
    world: ScaleWorld,
) -> tuple[Voice, dict[str, Any]]:
    bank = PatternBank()
    source_start = Fraction(_LOCK_SOURCE_BAR * 4)
    pattern = capture_pattern(
        tuple(parent_rhythm.events),
        world=world,
        lane=RHYTHM_LANE,
        start=source_start,
        span=Fraction(4),
    )
    bank.remember("rhythm-a", pattern)
    bank.lock(RHYTHM_LANE, "rhythm-a")

    target_set = set(_LOCK_TARGET_BARS)
    kept = [
        event
        for event in parent_rhythm.events
        if int(event.onset // 4) not in target_set
    ]
    locked_trace: list[dict[str, Any]] = []
    for bar_index in _LOCK_TARGET_BARS:
        start = Fraction(bar_index * 4)
        candidates: list[tuple[float, int, tuple[NoteEvent, ...]]] = []
        for anchor_degree in range(world.degrees_per_octave):
            events = realise_pattern(
                pattern,
                world=world,
                lane=RHYTHM_LANE,
                start=start,
                anchor_degree=anchor_degree,
                velocity=57,
            )
            candidates.append(
                (
                    _locked_anchor_score(events, tune=tune, bass=bass),
                    anchor_degree,
                    events,
                )
            )
        score, anchor_degree, events = max(candidates, key=lambda item: (item[0], -item[1]))
        kept.extend(events)
        locked_trace.append(
            {
                "bar": bar_index,
                "pattern": bank.locked_name(RHYTHM_LANE),
                "anchor_degree": anchor_degree,
                "vertical_score": score,
                "signature": [
                    {
                        "onset": _fraction_json(attack.onset),
                        "duration": _fraction_json(attack.duration),
                        "degree_offset": attack.degree_offset,
                    }
                    for attack in pattern.attacks
                ],
                "events": [_event_json(event) for event in events],
            }
        )

    bank.unlock(RHYTHM_LANE)
    return Voice.from_events("RHYTHM", sorted(kept, key=lambda event: event.onset)), {
        "remembered": "rhythm-a",
        "source_bar": _LOCK_SOURCE_BAR,
        "locked_lane": RHYTHM_LANE.name,
        "target_bars": list(_LOCK_TARGET_BARS),
        "applications": locked_trace,
        "unlocked_after_bar": _LOCK_TARGET_BARS[-1],
        "lock_state_after": bank.locked_name(RHYTHM_LANE),
    }


def compose_study_011(
    config: IPMConfig | None = None,
    *,
    tonic_midi: int = 60,
) -> ThreeLaneStudyResult:
    """Shorten bass notes and demonstrate scalable explicit pattern locking."""

    requested = config or IPMConfig(seed=2026081704, tempo_bpm=58)
    parent = compose_study_010(requested, tonic_midi=tonic_midi)
    world = ScaleWorld(tonic_midi)
    bar_trace = parent.trace["sequential_bar_decisions"]

    tune = Voice.from_events("TUNE", parent.tune.events)
    bass, bass_trace = _compose_shorter_bass(tune, bar_trace, world=world)
    rhythm, lock_trace = _apply_rhythm_lock(
        parent.rhythm,
        tune,
        bass,
        world=world,
    )

    trace = copy.deepcopy(parent.trace)
    trace["study"] = "011"
    trace["parent_study"] = "010"
    trace["controlled_change"] = (
        "bass uses shorter one/two-beat structural cells; rhythm demonstrates a named "
        "scale-degree pattern captured, locked for three bars, harmonically re-anchored, "
        "then explicitly unlocked"
    )
    trace["bass_decisions"] = bass_trace
    trace["pattern_lock"] = lock_trace
    trace["voices"] = {
        "TUNE": [_event_json(event) for event in tune.events],
        "BASS": [_event_json(event) for event in bass.events],
        "RHYTHM": [_event_json(event) for event in rhythm.events],
    }

    texture = score_texture((tune, bass, rhythm))
    parent_bass_median = median(event.duration for event in parent.bass.events)
    bass_median = median(event.duration for event in bass.events)
    bass_short = sum(event.duration <= Fraction(7, 8) for event in bass.events)
    locked = lock_trace["applications"]
    signatures = [application["signature"] for application in locked]
    rhythm_bars = {int(event.onset // 4) for event in rhythm.events}

    checks = {
        "parent_study_passed": parent.trace["validation"]["passed"],
        "tune_is_unchanged": tune.events == parent.tune.events,
        "bass_is_shorter_than_study_010": bass_median < parent_bass_median,
        "bass_has_one_beat_opportunities": bass_short >= 8,
        "bass_still_uses_slow_lane": all(BASS_LANE.contains(event.pitch, tonic_midi=tonic_midi) for event in bass.events),
        "named_pattern_was_remembered": lock_trace["remembered"] == "rhythm-a",
        "pattern_was_locked_for_multiple_bars": len(locked) == len(_LOCK_TARGET_BARS),
        "locked_pattern_geometry_is_identical": len(signatures) >= 2 and all(signature == signatures[0] for signature in signatures[1:]),
        "locked_pattern_can_reanchor": len({application["anchor_degree"] for application in locked}) >= 2,
        "pattern_was_explicitly_unlocked": lock_trace["lock_state_after"] is None,
        "rhythm_stays_in_lane": all(RHYTHM_LANE.contains(event.pitch, tonic_midi=tonic_midi) for event in rhythm.events),
        "shared_scale_survives_locking": all(world.pitch_is_in_scale(event.pitch) for voice in (tune, bass, rhythm) for event in voice.events),
        "rhythm_remains_distributed": len(rhythm_bars) >= 10,
        "overall_vertical_floor_is_tolerable": texture.minimum >= 0.35,
    }
    trace["metrics"] = {
        "tune_events": len(tune.events),
        "bass_events": len(bass.events),
        "rhythm_events": len(rhythm.events),
        "study_010_bass_median": _fraction_json(parent_bass_median),
        "study_011_bass_median": _fraction_json(bass_median),
        "one_beat_bass_attacks": bass_short,
        "locked_pattern_applications": len(locked),
        "rhythm_active_bars": sorted(rhythm_bars),
        "vertical_weighted_mean": texture.weighted_mean,
        "vertical_minimum": texture.minimum,
    }
    trace["validation"] = {"passed": all(checks.values()), "checks": checks}

    return ThreeLaneStudyResult(
        config=parent.config,
        tune=tune,
        bass=bass,
        rhythm=rhythm,
        trace=trace,
    )


def write_study_011_files(
    output_dir: str | Path,
    config: IPMConfig | None = None,
    *,
    tonic_midi: int = 60,
) -> tuple[Path, Path]:
    result = compose_study_011(config, tonic_midi=tonic_midi)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    midi_path = output / "ipm-study-011.mid"
    trace_path = output / "ipm-study-011.trace.json"
    midi_path.write_bytes(
        render_midi(
            result.voices,
            tempo_bpm=result.config.tempo_bpm,
            beats_per_bar=result.config.beats_per_bar,
        )
    )
    trace_path.write_text(json.dumps(result.trace, indent=2) + "\n", encoding="utf-8")
    return midi_path, trace_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate IPM Study #011")
    parser.add_argument("--output", default="examples", help="output directory")
    parser.add_argument("--seed", type=int, default=2026081704)
    parser.add_argument("--tonic-midi", type=int, default=60)
    args = parser.parse_args()
    config = IPMConfig(seed=args.seed, tempo_bpm=58)
    result = compose_study_011(config, tonic_midi=args.tonic_midi)
    for path in write_study_011_files(args.output, config, tonic_midi=args.tonic_midi):
        print(path)
    print(json.dumps(result.trace["pattern_lock"], indent=2))
    print(json.dumps(result.trace["metrics"], indent=2))
    print(json.dumps(result.trace["validation"], indent=2))
    if not result.trace["validation"]["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

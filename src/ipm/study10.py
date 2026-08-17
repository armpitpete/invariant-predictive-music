"""Study #010: explicit tune, bass and rhythm lanes.

Study #009 established a musically viable short-note/arpeggio surface, but its two
subsidiary branches still represented historical response/harmony roles.  Study #010
turns the instrument into three explicit parts: TUNE, BASS and RHYTHM.  Every pitch is
expressed as an Aeolian scale degree and projected into a tonic-relative lane, so the
same abstract note can move to a new key without leaking out of its role's register.
"""

from __future__ import annotations

import argparse
import copy
import json
from dataclasses import dataclass
from fractions import Fraction
from math import exp
from pathlib import Path
from statistics import median
from typing import Any, Iterable

from .lanes import BASS_LANE, RHYTHM_LANE, TUNE_LANE, ScaleWorld
from .midi import render_midi
from .model import Beat, IPMConfig, NoteEvent, Voice
from .randomness import SeededRandom
from .sonority import interval_prior, score_texture, set_coherence
from .study import _event_json
from .study8 import compose_study_008
from .study9 import compose_study_009


@dataclass(frozen=True, slots=True)
class ThreeLaneStudyResult:
    config: IPMConfig
    tune: Voice
    bass: Voice
    rhythm: Voice
    trace: dict[str, Any]

    @property
    def voices(self) -> tuple[Voice, Voice, Voice]:
        return (self.tune, self.bass, self.rhythm)


def _fraction_json(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def _phase_bass_segments(phase: str) -> tuple[tuple[Beat, Beat], ...]:
    if phase in {"development", "climax"}:
        return ((Fraction(0), Fraction(2)), (Fraction(2), Fraction(2)))
    return ((Fraction(0), Fraction(4)),)


def _overlapping(events: Iterable[NoteEvent], start: Beat, end: Beat) -> tuple[NoteEvent, ...]:
    return tuple(event for event in events if event.onset < end and event.end > start)


def _overlap_weight(event: NoteEvent, start: Beat, end: Beat) -> float:
    overlap = min(event.end, end) - max(event.onset, start)
    return max(0.0, float(overlap))


def _circular_degree_distance(left: int, right: int, size: int = 7) -> int:
    raw = abs((left % size) - (right % size))
    return min(raw, size - raw)


def _bass_candidate_score(
    *,
    degree: int,
    pitch: int,
    tune_events: tuple[NoteEvent, ...],
    start: Beat,
    end: Beat,
    previous_degree: int | None,
    phase: str,
    final_segment: bool,
) -> float:
    if tune_events:
        weights = [_overlap_weight(event, start, end) for event in tune_events]
        total_weight = sum(weights)
        vertical = (
            sum(weight * interval_prior(pitch, event.pitch) for event, weight in zip(tune_events, weights, strict=True))
            / total_weight
            if total_weight > 0
            else 1.0
        )
    else:
        vertical = 1.0

    continuity = 1.0
    if previous_degree is not None:
        continuity = exp(-_circular_degree_distance(degree, previous_degree) / 1.7)

    tonic_pull = 1.0 if degree % 7 == 0 else 0.72
    if phase in {"development", "climax"}:
        tonic_pull = 0.82 if degree % 7 in {0, 4} else 0.68
    if final_segment:
        tonic_pull = 1.0 if degree % 7 == 0 else 0.0

    return 0.66 * vertical + 0.20 * continuity + 0.14 * tonic_pull


def _compose_bass(
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
        decisions: list[dict[str, Any]] = []
        for segment_index, (offset, span) in enumerate(_phase_bass_segments(phase)):
            start = Fraction(bar_index * 4) + offset
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
            final_segment = bar_index == 15 and segment_index == len(_phase_bass_segments(phase)) - 1
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
                selected = max(scored, key=lambda item: (item[0], -_circular_degree_distance(item[1], anchor_degree), -item[1]))
            score, degree, pitch = selected
            event = NoteEvent(
                onset=start,
                duration=span * Fraction(15, 16),
                pitch=pitch,
                velocity=58 if phase != "climax" else 64,
            )
            bass.add(event)
            decisions.append(
                {
                    "segment": segment_index,
                    "onset": _fraction_json(start),
                    "span": _fraction_json(span),
                    "anchor_degree": anchor_degree,
                    "selected_degree": degree,
                    "selected_pitch": pitch,
                    "selected_score": score,
                    "candidates": [
                        {"degree": candidate_degree, "pitch": candidate_pitch, "score": candidate_score}
                        for candidate_score, candidate_degree, candidate_pitch in scored
                    ],
                }
            )
            previous_degree = degree
        trace.append({"bar": bar_index, "phase": phase, "decisions": decisions})
    return bass, trace


_RHYTHM_PATTERNS: tuple[tuple[Fraction, ...], ...] = (
    (Fraction(0), Fraction(1, 4), Fraction(1, 2), Fraction(3, 4)),
    (Fraction(0), Fraction(1, 2), Fraction(3, 4), Fraction(5, 4)),
    (Fraction(0), Fraction(1, 4), Fraction(3, 4), Fraction(1)),
    (Fraction(0), Fraction(1, 2), Fraction(1), Fraction(3, 2)),
)
_RHYTHM_CONTOURS: tuple[tuple[int, ...], ...] = (
    (0, 2, 4, 2),
    (0, 4, 2, 4),
    (4, 2, 0, 2),
    (0, 2, 0, 4),
)
_RHYTHM_ACTIVE_BARS = frozenset({1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 12, 14})


def _active_pitch(voice: Voice, onset: Beat) -> int | None:
    for event in reversed(voice.events):
        if event.onset <= onset < event.end:
            return event.pitch
        if event.end <= onset:
            break
    return None


def _rhythm_candidate(
    *,
    world: ScaleWorld,
    tune: Voice,
    bass: Voice,
    bar_index: int,
    start_offset: Beat,
    pattern: tuple[Fraction, ...],
    contour: tuple[int, ...],
) -> tuple[float, tuple[NoteEvent, ...], int]:
    bar_start = Fraction(bar_index * 4)
    motif_start = bar_start + start_offset
    bass_pitch = _active_pitch(bass, motif_start)
    if bass_pitch is None:
        bass_pitch = min(bass.events, key=lambda event: abs(float(event.onset - motif_start))).pitch
    base_degree = world.lane_degree(bass_pitch, BASS_LANE)

    events: list[NoteEvent] = []
    scores: list[float] = []
    for relative_onset, degree_offset in zip(pattern, contour, strict=True):
        onset = motif_start + relative_onset
        pitch = world.project_degree(base_degree + degree_offset, RHYTHM_LANE)
        active = [candidate for candidate in (_active_pitch(tune, onset), _active_pitch(bass, onset)) if candidate is not None]
        vertical = set_coherence((*active, pitch)) if active else 1.0
        scores.append(vertical)
        events.append(
            NoteEvent(
                onset=onset,
                duration=Fraction(3, 16),
                pitch=pitch,
                velocity=54 + 3 * (len(events) % 2 == 0),
            )
        )
    variety = len({event.pitch for event in events}) / len(events)
    total = 0.82 * (sum(scores) / len(scores)) + 0.18 * variety
    return total, tuple(events), base_degree


def _compose_rhythm(
    tune: Voice,
    bass: Voice,
    bar_trace: list[dict[str, Any]],
    *,
    world: ScaleWorld,
    seed: int,
) -> tuple[Voice, list[dict[str, Any]]]:
    rhythm = Voice("RHYTHM")
    trace: list[dict[str, Any]] = []
    rng = SeededRandom(seed ^ 10000)

    for bar in bar_trace:
        bar_index = int(bar["bar"])
        phase = str(bar["phase"])
        if bar_index not in _RHYTHM_ACTIVE_BARS:
            trace.append({"bar": bar_index, "phase": phase, "selected": None})
            continue

        candidates: list[tuple[float, tuple[NoteEvent, ...], int, int, int, Fraction]] = []
        for pattern_index, pattern in enumerate(_RHYTHM_PATTERNS):
            pattern_end = max(pattern) + Fraction(1, 4)
            for start_offset in (Fraction(0), Fraction(1), Fraction(2)):
                if start_offset + pattern_end > 4:
                    continue
                for contour_index, contour in enumerate(_RHYTHM_CONTOURS):
                    score, events, base_degree = _rhythm_candidate(
                        world=world,
                        tune=tune,
                        bass=bass,
                        bar_index=bar_index,
                        start_offset=start_offset,
                        pattern=pattern,
                        contour=contour,
                    )
                    score += rng.random() * 0.008
                    candidates.append((score, events, base_degree, pattern_index, contour_index, start_offset))

        selected = max(candidates, key=lambda item: item[0])
        score, events, base_degree, pattern_index, contour_index, start_offset = selected
        for event in events:
            rhythm.add(event)
        trace.append(
            {
                "bar": bar_index,
                "phase": phase,
                "selected": {
                    "score": score,
                    "base_degree": base_degree,
                    "start_offset": _fraction_json(start_offset),
                    "pattern_index": pattern_index,
                    "contour_index": contour_index,
                    "degree_offsets": list(_RHYTHM_CONTOURS[contour_index]),
                    "events": [_event_json(event) for event in events],
                },
            }
        )
    return rhythm, trace


def compose_study_010(
    config: IPMConfig | None = None,
    *,
    tonic_midi: int = 60,
) -> ThreeLaneStudyResult:
    """Compose explicit tune, bass and rhythm lanes from one scalable pitch world."""

    requested = config or IPMConfig(seed=2026081704, tempo_bpm=58)
    parent = compose_study_009(requested, tonic_midi=tonic_midi)
    structural_parent = compose_study_008(requested, tonic_midi=tonic_midi)
    bar_trace = structural_parent.trace["sequential_bar_decisions"]
    world = ScaleWorld(tonic_midi)

    tune = Voice.from_events("TUNE", parent.main.events)
    bass, bass_trace = _compose_bass(tune, bar_trace, world=world)
    rhythm, rhythm_trace = _compose_rhythm(
        tune,
        bass,
        bar_trace,
        world=world,
        seed=requested.seed,
    )

    trace = copy.deepcopy(parent.trace)
    trace["study"] = "010"
    trace["parent_study"] = "009"
    trace["architecture"] = {
        "parts": ["TUNE", "BASS", "RHYTHM"],
        "scale": "Aeolian",
        "tonic_midi": tonic_midi,
        "intervals": list(world.intervals),
        "lanes": {
            lane.name: {
                "octave_offset": lane.octave_offset,
                "bounds": list(lane.bounds(tonic_midi)),
            }
            for lane in (TUNE_LANE, BASS_LANE, RHYTHM_LANE)
        },
        "pitch_rule": "abstract scale degree is projected into the destination lane",
    }
    trace["controlled_change"] = (
        "replace historical response/harmony branches with explicit BASS and RHYTHM parts; "
        "all three parts share scalable scale degrees but occupy separate tonic-relative lanes"
    )
    trace["bass_decisions"] = bass_trace
    trace["rhythm_decisions"] = rhythm_trace
    trace["voices"] = {
        "TUNE": [_event_json(event) for event in tune.events],
        "BASS": [_event_json(event) for event in bass.events],
        "RHYTHM": [_event_json(event) for event in rhythm.events],
    }

    texture = score_texture((tune, bass, rhythm))
    tune_low, tune_high = TUNE_LANE.bounds(tonic_midi)
    bass_low, bass_high = BASS_LANE.bounds(tonic_midi)
    rhythm_low, rhythm_high = RHYTHM_LANE.bounds(tonic_midi)
    rhythm_bars = {int(event.onset // 4) for event in rhythm.events}
    bass_durations = [event.duration for event in bass.events]
    rhythm_durations = [event.duration for event in rhythm.events]
    no_self_overlap = all(
        all(right.onset >= left.end for left, right in zip(voice.events, voice.events[1:], strict=False))
        for voice in (tune, bass, rhythm)
    )

    checks = {
        "parent_study_passed": parent.trace["validation"]["passed"],
        "exactly_three_explicit_parts": [voice.name for voice in (tune, bass, rhythm)] == ["TUNE", "BASS", "RHYTHM"],
        "tune_surface_from_accepted_study_009_is_preserved": tune.events == parent.main.events,
        "all_tune_notes_fit_tune_lane": all(tune_low <= event.pitch <= tune_high for event in tune.events),
        "all_bass_notes_fit_bass_lane": all(bass_low <= event.pitch <= bass_high for event in bass.events),
        "all_rhythm_notes_fit_rhythm_lane": all(rhythm_low <= event.pitch <= rhythm_high for event in rhythm.events),
        "every_note_belongs_to_shared_scale": all(world.pitch_is_in_scale(event.pitch) for voice in (tune, bass, rhythm) for event in voice.events),
        "same_degree_maps_cleanly_across_lanes": all(
            world.project_degree(degree, TUNE_LANE) - world.project_degree(degree, RHYTHM_LANE) == 12
            and world.project_degree(degree, TUNE_LANE) - world.project_degree(degree, BASS_LANE) == 24
            for degree in range(7)
        ),
        "bass_is_slow_structural_part": len(bass.events) >= 16 and bool(bass_durations) and median(bass_durations) >= Fraction(15, 8),
        "bass_finishes_on_tonic_degree": world.lane_degree(bass.events[-1].pitch, BASS_LANE) == 0,
        "rhythm_is_distributed_through_form": len(rhythm_bars) >= 10 and min(rhythm_bars) <= 2 and max(rhythm_bars) >= 12,
        "rhythm_uses_short_attacks": bool(rhythm_durations) and all(duration <= Fraction(3, 16) for duration in rhythm_durations),
        "rhythm_figures_are_arpeggiated": all(
            item["selected"] is None
            or len({event["pitch"] for event in item["selected"]["events"]}) >= 3
            for item in rhythm_trace
        ),
        "no_lane_overlaps_itself": no_self_overlap,
        "overall_vertical_floor_is_tolerable": texture.minimum >= 0.35,
        "final_tune_is_tonic": bool(tune.events) and world.degree_class(world.degree_from_pitch(tune.events[-1].pitch)) == 0,
    }
    trace["metrics"] = {
        "tune_events": len(tune.events),
        "bass_events": len(bass.events),
        "rhythm_events": len(rhythm.events),
        "rhythm_active_bars": sorted(rhythm_bars),
        "vertical_weighted_mean": texture.weighted_mean,
        "vertical_minimum": texture.minimum,
        "sonority_slices": texture.slices,
    }
    trace["validation"] = {"passed": all(checks.values()), "checks": checks}

    return ThreeLaneStudyResult(
        config=parent.config,
        tune=tune,
        bass=bass,
        rhythm=rhythm,
        trace=trace,
    )


def write_study_010_files(
    output_dir: str | Path,
    config: IPMConfig | None = None,
    *,
    tonic_midi: int = 60,
) -> tuple[Path, Path]:
    result = compose_study_010(config, tonic_midi=tonic_midi)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    midi_path = output / "ipm-study-010.mid"
    trace_path = output / "ipm-study-010.trace.json"
    midi_path.write_bytes(render_midi(result.voices, tempo_bpm=result.config.tempo_bpm, beats_per_bar=result.config.beats_per_bar))
    trace_path.write_text(json.dumps(result.trace, indent=2) + "\n", encoding="utf-8")
    return midi_path, trace_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate IPM Study #010")
    parser.add_argument("--output", default="examples", help="output directory")
    parser.add_argument("--seed", type=int, default=2026081704)
    parser.add_argument("--tonic-midi", type=int, default=60)
    args = parser.parse_args()
    config = IPMConfig(seed=args.seed, tempo_bpm=58)
    result = compose_study_010(config, tonic_midi=args.tonic_midi)
    for path in write_study_010_files(args.output, config, tonic_midi=args.tonic_midi):
        print(path)
    print(json.dumps(result.trace["architecture"], indent=2))
    print(json.dumps(result.trace["metrics"], indent=2))
    print(json.dumps(result.trace["validation"], indent=2))
    if not result.trace["validation"]["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

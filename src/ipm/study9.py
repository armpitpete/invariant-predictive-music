"""Study #009: short local attacks and rhythmic subsidiary arpeggios.

Listening review of Study #008 found two concrete failures: its nominally short
half-beat cells still sounded long at 58 BPM, and subsidiary branches were almost
absent (three sustained B_R notes, no B_H).  Study #009 keeps the slow whole-bar
composition but adds quarter-beat micro-bursts inside selected lead cells and replaces
inherited subsidiary notes with short arpeggiated branch motifs.
"""

from __future__ import annotations

import argparse
import copy
import json
from fractions import Fraction
from pathlib import Path
from typing import Any

from .bar_rhythm import BarCellKind
from .branch_arpeggio import BranchMotifScore, best_arpeggio
from .countervoice import SubsidiaryRole
from .midi import render_midi
from .micro_rhythm import aeolian_pool, realise_micro_bar
from .model import IPMConfig, NoteEvent, Voice
from .randomness import SeededRandom
from .study import StudyResult, _event_json
from .study4 import _occupancy_metrics
from .study8 import compose_study_008


def _fraction_json(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def _micro_main(
    bar_trace: list[dict[str, Any]],
    *,
    seed: int,
    tonic_midi: int,
) -> tuple[Voice, list[dict[str, Any]]]:
    rng = SeededRandom(seed ^ 9000)
    main = Voice("M")
    trace: list[dict[str, Any]] = []

    for bar in bar_trace:
        cells = tuple(
            (BarCellKind(cell["kind"]), Fraction(*cell["duration"]))
            for cell in bar["cells"]
        )
        events, decisions = realise_micro_bar(
            cells,
            tuple(bar["pitches"]),
            start=Fraction(bar["bar"] * 4),
            phase=bar["phase"],
            rng=rng,
            tonic_midi=tonic_midi,
        )
        for event in events:
            main.add(event)
        trace.append(
            {
                "bar": bar["bar"],
                "phase": bar["phase"],
                "structural_cells": bar["cells"],
                "decisions": [
                    {
                        "onset": _fraction_json(decision.onset),
                        "structural_duration": _fraction_json(decision.structural_duration),
                        "segments": [_fraction_json(value) for value in decision.segments],
                        "pitches": list(decision.pitches),
                        "has_short_attack": decision.has_short_attack,
                    }
                    for decision in decisions
                ],
                "realised_events": [_event_json(event) for event in events],
            }
        )
    return main, trace


def _rest_opportunities(
    bar_trace: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for bar in bar_trace:
        cursor = Fraction(bar["bar"] * 4)
        for cell in bar["cells"]:
            duration = Fraction(*cell["duration"])
            if cell["kind"] == BarCellKind.REST.value and duration >= Fraction(1, 2):
                result.append(
                    {
                        "bar": bar["bar"],
                        "phase": bar["phase"],
                        "start": cursor,
                        "span": min(duration, Fraction(1)),
                        "structural_rest": duration,
                    }
                )
            cursor += duration
    return result


def _first_note_opportunities(
    bar_trace: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for bar in bar_trace:
        if bar["phase"] not in {"establishment", "development", "climax"}:
            continue
        cursor = Fraction(bar["bar"] * 4)
        for cell in bar["cells"]:
            duration = Fraction(*cell["duration"])
            if cell["kind"] == BarCellKind.NOTE.value:
                result.append(
                    {
                        "bar": bar["bar"],
                        "phase": bar["phase"],
                        "start": cursor,
                        "span": min(duration, Fraction(1)),
                    }
                )
                break
            cursor += duration
    return result


def _motif_json(score: BranchMotifScore, *, bar: int, phase: str) -> dict[str, Any]:
    return {
        "bar": bar,
        "phase": phase,
        "role": score.motif.role.value,
        "score": score.total,
        "margins": list(score.margins),
        "note_scores": list(score.note_scores),
        "silence_scores": list(score.silence_scores),
        "chord_offsets": list(score.motif.chord_offsets),
        "contour": list(score.motif.contour),
        "events": [_event_json(event) for event in score.motif.events],
    }


def _select_response_motifs(
    main: Voice,
    bar_trace: list[dict[str, Any]],
    *,
    seed: int,
    tonic_midi: int,
    maximum: int = 4,
) -> tuple[Voice, list[dict[str, Any]], int]:
    rng = SeededRandom(seed ^ 9100)
    valid: list[tuple[BranchMotifScore, dict[str, Any]]] = []
    evaluated = 0
    for opportunity in _rest_opportunities(bar_trace):
        best, scored = best_arpeggio(
            role=SubsidiaryRole.RESPONSE,
            start=opportunity["start"],
            span=opportunity["span"],
            frozen_voices=(main,),
            phase=opportunity["phase"],
            rng=rng,
            tonic_midi=tonic_midi,
        )
        evaluated += len(scored)
        if best is not None:
            valid.append((best, opportunity))

    chosen = sorted(valid, key=lambda item: item[0].total, reverse=True)[:maximum]
    events = sorted(
        (event for score, _ in chosen for event in score.motif.events),
        key=lambda event: event.onset,
    )
    voice = Voice.from_events("B_R", events)
    trace = [
        _motif_json(score, bar=opportunity["bar"], phase=opportunity["phase"])
        for score, opportunity in sorted(chosen, key=lambda item: item[1]["start"])
    ]
    return voice, trace, len(valid)


def _select_harmony_motifs(
    main: Voice,
    response: Voice,
    bar_trace: list[dict[str, Any]],
    *,
    seed: int,
    tonic_midi: int,
    maximum: int = 2,
) -> tuple[Voice, list[dict[str, Any]], int]:
    rng = SeededRandom(seed ^ 9200)
    valid: list[tuple[BranchMotifScore, dict[str, Any]]] = []
    for opportunity in _first_note_opportunities(bar_trace):
        best, _ = best_arpeggio(
            role=SubsidiaryRole.HARMONY,
            start=opportunity["start"],
            span=opportunity["span"],
            frozen_voices=(main, response),
            phase=opportunity["phase"],
            rng=rng,
            tonic_midi=tonic_midi,
        )
        if best is not None:
            valid.append((best, opportunity))

    chosen = sorted(valid, key=lambda item: item[0].total, reverse=True)[:maximum]
    events = sorted(
        (event for score, _ in chosen for event in score.motif.events),
        key=lambda event: event.onset,
    )
    voice = Voice.from_events("B_H", events)
    trace = [
        _motif_json(score, bar=opportunity["bar"], phase=opportunity["phase"])
        for score, opportunity in sorted(chosen, key=lambda item: item[1]["start"])
    ]
    return voice, trace, len(valid)


def compose_study_009(
    config: IPMConfig | None = None,
    *,
    tonic_midi: int = 60,
) -> StudyResult:
    """Add genuinely short lead attacks and sparse arpeggiated subsidiary branches."""

    requested = config or IPMConfig(seed=2026081704, tempo_bpm=58)
    parent = compose_study_008(requested, tonic_midi=tonic_midi)
    bar_trace = parent.trace["sequential_bar_decisions"]
    main, micro_trace = _micro_main(
        bar_trace,
        seed=requested.seed,
        tonic_midi=tonic_midi,
    )
    response, response_trace, response_available = _select_response_motifs(
        main,
        bar_trace,
        seed=requested.seed,
        tonic_midi=tonic_midi,
    )
    harmony, harmony_trace, harmony_available = _select_harmony_motifs(
        main,
        response,
        bar_trace,
        seed=requested.seed,
        tonic_midi=tonic_midi,
    )

    trace = copy.deepcopy(parent.trace)
    trace["study"] = "009"
    trace["parent_study"] = "008"
    trace["controlled_change"] = (
        "selected structural bars are retained; some NOTE cells gain quarter-beat "
        "micro-bursts, and subsidiary voices are regenerated as arpeggiated motifs"
    )
    trace["micro_rhythm"] = micro_trace
    trace["branch_motifs"] = {
        "B_R": response_trace,
        "B_H": harmony_trace,
        "available": {
            "B_R": response_available,
            "B_H": harmony_available,
        },
    }
    trace["voices"] = {
        "M": [_event_json(event) for event in main.events],
        "B_R": [_event_json(event) for event in response.events],
        "B_H": [_event_json(event) for event in harmony.events],
    }
    trace["metrics"] = _occupancy_metrics((main, response, harmony))

    short_main = [event for event in main.events if event.duration <= Fraction(3, 16)]
    long_main = [event for event in main.events if event.duration >= Fraction(7, 8)]
    burst_cells = sum(
        decision["has_short_attack"]
        for bar in micro_trace
        for decision in bar["decisions"]
    )
    branch_trace = response_trace + harmony_trace
    branch_margins = [margin for motif in branch_trace for margin in motif["margins"]]
    pool = set(aeolian_pool(tonic_midi))
    no_self_overlap = all(
        all(
            right.onset >= left.end
            for left, right in zip(voice.events, voice.events[1:], strict=False)
        )
        for voice in (main, response, harmony)
    )

    checks = {
        "parent_study_passed": parent.trace["validation"]["passed"],
        "tempo_remains_slow": parent.config.tempo_bpm == 58,
        "lead_contains_true_quarter_beat_attacks": len(short_main) >= 8,
        "long_and_short_lead_values_coexist": bool(long_main) and bool(short_main),
        "micro_bursts_are_structural_subdivisions": burst_cells >= 6,
        "main_pitch_world_remains_one_octave_aeolian": all(
            event.pitch in pool for event in main.events
        ),
        "response_branch_is_available": response_available >= 2,
        "harmony_branch_is_available": harmony_available >= 1,
        "response_branch_is_audible": len(response_trace) >= 2 and len(response.events) >= 4,
        "harmony_branch_is_audible": len(harmony_trace) >= 1 and len(harmony.events) >= 2,
        "selected_branches_are_multi_note_figures": all(
            len(motif["events"]) >= 2
            and len({event["pitch"] for event in motif["events"]}) >= 2
            for motif in branch_trace
        ),
        "branch_attacks_are_short": all(
            Fraction(*event["duration"]) <= Fraction(3, 16)
            for motif in branch_trace
            for event in motif["events"]
        ),
        "response_register_preserved": all(48 <= event.pitch <= 59 for event in response.events),
        "harmony_register_preserved": all(36 <= event.pitch <= 47 for event in harmony.events),
        "every_selected_branch_attack_beats_silence": bool(branch_margins)
        and all(margin > 0 for margin in branch_margins),
        "no_voice_overlaps_itself": no_self_overlap,
        "final_tonic": bool(main.events) and main.events[-1].pitch == tonic_midi,
    }
    trace["study_009_summary"] = {
        "main_attacks": len(main.events),
        "short_main_attacks": len(short_main),
        "short_main_fraction": len(short_main) / len(main.events),
        "micro_burst_cells": burst_cells,
        "response_motifs": len(response_trace),
        "harmony_motifs": len(harmony_trace),
        "response_available": response_available,
        "harmony_available": harmony_available,
    }
    trace["validation"] = {"passed": all(checks.values()), "checks": checks}

    return StudyResult(
        config=parent.config,
        main=main,
        response=response,
        harmony=harmony,
        trace=trace,
    )


def write_study_009_files(
    output_dir: str | Path,
    config: IPMConfig | None = None,
    *,
    tonic_midi: int = 60,
) -> tuple[Path, Path]:
    result = compose_study_009(config, tonic_midi=tonic_midi)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    midi_path = output / "ipm-study-009.mid"
    trace_path = output / "ipm-study-009.trace.json"
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
    parser = argparse.ArgumentParser(description="Generate IPM Study #009")
    parser.add_argument("--output", default="examples", help="output directory")
    parser.add_argument("--seed", type=int, default=2026081704)
    args = parser.parse_args()
    config = IPMConfig(seed=args.seed, tempo_bpm=58)
    result = compose_study_009(config)
    for path in write_study_009_files(args.output, config):
        print(path)
    print(json.dumps(result.trace["study_009_summary"], indent=2))
    print(json.dumps(result.trace["validation"], indent=2))
    if not result.trace["validation"]["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

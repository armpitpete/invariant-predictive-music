"""Render the eight Composition Framework v0.1 experiments and matched controls."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass, replace
from pathlib import Path

from ipm.composition_framework import CompositionFrameworkConfig
from ipm.engine import (
    BassControls,
    InstrumentConfig,
    PatternLockSpec,
    RhythmControls,
    compose,
)
from ipm.midi import render_midi
from ipm.synth_engine import render_synth_wav, synth_manifest


@dataclass(frozen=True, slots=True)
class ExperimentProfile:
    slug: str
    carrier: str
    primary: str
    secondary: str
    seed: int
    bass: BassControls
    rhythm: RhythmControls
    negative_space: float = 0.55
    expressive_gesture: float = 0.55
    pattern_locks: tuple[PatternLockSpec, ...] = ()


BASE_SEED = 2026081704
PROFILES = (
    ExperimentProfile(
        "01-melody-led", "melody", "tenderness", "uncertainty", BASE_SEED + 1,
        BassControls(activity=0.18), RhythmControls(activity=0.12),
    ),

    ExperimentProfile(
        "02-harmony-led", "harmony", "warmth", "distance", BASE_SEED + 3,
        BassControls(activity=0.72, sustain=0.78, movement=0.22),
        RhythmControls(activity=0.08),
    ),
    ExperimentProfile(
        "03-rhythm-led", "rhythm", "anticipation", "uncertainty", BASE_SEED,
        BassControls(activity=0.18),
        RhythmControls(activity=0.82, complexity=0.75, syncopation=0.55),
    ),
    ExperimentProfile(
        "04-timbre-led", "timbre", "hope", "distance", BASE_SEED + 1,
        BassControls(activity=0.28), RhythmControls(activity=0.22),
    ),
    ExperimentProfile(
        "05-space-led", "space", "vulnerability", "restraint", BASE_SEED + 3,
        BassControls(activity=0.12), RhythmControls(activity=0.10),
        negative_space=0.85,
    ),
    ExperimentProfile(
        "06-quiet-payoff", "quiet-payoff", "tenderness", "relief", BASE_SEED,
        BassControls(activity=0.38), RhythmControls(activity=0.30),
        expressive_gesture=1.0,
    ),
    ExperimentProfile(
        "07-denied-expectation", "denied-expectation", "longing", "uncertainty",
        BASE_SEED + 2, BassControls(activity=0.32), RhythmControls(activity=0.28),
    ),
    ExperimentProfile(
        "08-transformed-repetition", "transformed-repetition", "nostalgia", "movement",
        BASE_SEED, BassControls(activity=1.0), RhythmControls(activity=0.25),
        pattern_locks=(PatternLockSpec("BASS", 0, 4, 6),),
    ),
)


def _framework(profile: ExperimentProfile, *, enabled: bool) -> CompositionFrameworkConfig:
    return CompositionFrameworkConfig(
        enabled=enabled,
        primary_emotion=profile.primary,
        secondary_emotion=profile.secondary,
        carrier=profile.carrier,
        negative_space=profile.negative_space,
        expressive_gesture=profile.expressive_gesture,
        transformation_strength=0.70 if profile.carrier == "transformed-repetition" else 0.55,
    )


def _config(profile: ExperimentProfile, *, enabled: bool) -> InstrumentConfig:
    return InstrumentConfig(
        seed=profile.seed,
        tempo_bpm=72,
        bars=8,
        bass=profile.bass,
        rhythm=profile.rhythm,
        pattern_locks=profile.pattern_locks,
        framework=_framework(profile, enabled=enabled),
    )


def _write_result(result, root: Path, label: str, sample_rate: int) -> dict:
    trace_path = root / f"{label}.trace.json"
    midi_path = root / f"{label}.mid"
    wav_path = root / f"{label}.wav"
    trace_path.write_text(json.dumps(result.trace, indent=2) + "\n", encoding="utf-8")
    midi_path.write_bytes(
        render_midi(
            result.voices,
            tempo_bpm=result.config.tempo_bpm,
            beats_per_bar=result.config.beats_per_bar,
        )
    )
    render_synth_wav(result, wav_path, sample_rate=sample_rate)
    audio_hash = hashlib.sha256(wav_path.read_bytes()).hexdigest()
    return {
        "trace": str(trace_path),
        "midi": str(midi_path),
        "wav": str(wav_path),
        "wav_sha256": audio_hash,
        "validation": result.trace["validation"],
        "framework": result.trace["composition_framework"],
    }


def _compare(profile: ExperimentProfile, framework: dict, control: dict) -> dict:
    fm = framework["framework"]["metrics"]
    cm = control["framework"]["metrics"]
    plan = framework["framework"]["structural_plan"]
    checks = {
        "framework_engine_valid": framework["validation"]["passed"],
        "control_engine_valid": control["validation"]["passed"],
        "framework_trace_valid": framework["framework"]["integration_validation"]["passed"],
        "audio_conditions_differ": framework["wav_sha256"] != control["wav_sha256"],
        "denied_expectation_has_no_arrival": (
            profile.carrier != "denied-expectation" or "arrival" not in plan
        ),
        "transformed_repetition_observed": (
            profile.carrier != "transformed-repetition"
            or fm["explicit_pattern_returns"] > 0
        ),
    }
    return {
        "profile": profile.slug,
        "carrier": profile.carrier,
        "target": [profile.primary, profile.secondary],
        "checks": checks,
        "passed": all(checks.values()),
        "framework_metrics": fm,
        "control_metrics": cm,
        "metric_deltas": {
            "mean_negative_space": fm["mean_negative_space"] - cm["mean_negative_space"],
            "consequence_coverage": fm["consequence_coverage"] - cm["consequence_coverage"],
            "transformed_returns": fm["transformed_returns"] - cm["transformed_returns"],
            "intensity_significance_correlation": (
                fm["intensity_significance_correlation"]
                - cm["intensity_significance_correlation"]
            ),
        },
    }


def render_pack(output: Path, *, sample_rate: int) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for profile in PROFILES:
        root = output / profile.slug
        root.mkdir(parents=True, exist_ok=True)
        framework_result = compose(_config(profile, enabled=True))
        control_result = compose(_config(profile, enabled=False))
        framework = _write_result(framework_result, root, "framework", sample_rate)
        control = _write_result(control_result, root, "control", sample_rate)
        comparison = _compare(profile, framework, control)
        (root / "comparison.json").write_text(
            json.dumps(comparison, indent=2) + "\n", encoding="utf-8"
        )
        rows.append(comparison)


    summary = {
        "version": "0.1",
        "sample_rate": sample_rate,
        "profiles": len(rows),
        "passed": all(row["passed"] for row in rows),
        "passed_profiles": sum(row["passed"] for row in rows),
        "failed_profiles": [row["profile"] for row in rows if not row["passed"]],
        "synth_manifest": synth_manifest(sample_rate),
        "comparisons": rows,
        "human_validation_required": True,
        "claim_boundary": (
            "These comparisons verify implementation and structural proxies only. "
            "They do not establish perceived emotion, preference or memorability."
        ),
    }
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )

    lines = [
        "# Composition Framework v0.1 — Test Results",
        "",
        f"- Profiles: {summary['profiles']}",
        f"- Passing implementation profiles: {summary['passed_profiles']}/{summary['profiles']}",
        f"- Sample rate: {sample_rate} Hz",
        f"- Overall implementation gate: {'PASS' if summary['passed'] else 'FAIL'}",
        "",
        "## Per-profile checks",
        "",
        "| Profile | Carrier | Gate | Audio differs from control |",
        "|---|---|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['profile']} | {row['carrier']} | "
            f"{'PASS' if row['passed'] else 'FAIL'} | "
            f"{'yes' if row['checks']['audio_conditions_differ'] else 'no'} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            "PASS means the integration behaved as specified and produced controlled differences.",
            "It does **not** mean the intended emotion was perceived.",
            "The blinded listener protocol is the next evidence gate.",
        ]
    )
    (output / "COMPOSITION_FRAMEWORK_V0_1_TEST_RESULTS.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("experiments/composition-framework-v0.1"),
    )
    parser.add_argument("--sample-rate", type=int, default=22_050)
    args = parser.parse_args()
    summary = render_pack(args.output, sample_rate=args.sample_rate)
    print(json.dumps(
        {
            "passed": summary["passed"],
            "passed_profiles": summary["passed_profiles"],
            "profiles": summary["profiles"],
            "failed_profiles": summary["failed_profiles"],
        },
        indent=2,
    ))
    if not summary["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

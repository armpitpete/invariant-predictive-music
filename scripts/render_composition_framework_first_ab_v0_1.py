"""Render the first narrow Composition Framework v0.1 A/B evidence pair."""
from __future__ import annotations

import hashlib
import json
import shutil
import wave
from pathlib import Path

from ipm.composition_framework import CompositionFrameworkConfig
from ipm.engine import InstrumentConfig, compose
from ipm.midi import render_midi
from ipm.synth_engine import render_synth_wav, synth_manifest

SEED = 2026081704
SAMPLE_RATE = 16_000
OUTPUT = Path("experiments/composition-framework-v0.1/first-ab")


def framework_config(enabled: bool) -> CompositionFrameworkConfig:
    return CompositionFrameworkConfig(
        enabled=enabled,
        primary_emotion="tenderness",
        secondary_emotion="uncertainty",
        carrier="balanced",
        negative_space=1.0,
        expressive_gesture=0.0,
        transformation_strength=0.80,
        timbral_strength=0.0,
        consequence_horizon_bars=3,
        structural_override=(
            "introduction",
            "recognition",
            "complication",
            "suspension",
            "arrival",
            "aftermath",
        ),
    )


def instrument_config(enabled: bool) -> InstrumentConfig:
    return InstrumentConfig(
        seed=SEED,
        tempo_bpm=58,
        bars=16,
        framework=framework_config(enabled),
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_signature(result) -> list[tuple]:
    return [
        (
            event.pitch,
            event.onset.numerator,
            event.onset.denominator,
        )
        for event in result.tune.events
    ]


def wav_metadata(path: Path) -> dict:
    with wave.open(str(path), "rb") as wav:
        frames = wav.getnframes()
        rate = wav.getframerate()
        return {
            "frames": frames,
            "sample_rate": rate,
            "channels": wav.getnchannels(),
            "sample_width": wav.getsampwidth(),
            "duration_seconds": frames / rate,
        }


def write_result(result, root: Path, label: str) -> dict:
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
    render_synth_wav(result, wav_path, sample_rate=SAMPLE_RATE)
    return {
        "trace": str(trace_path),
        "midi": str(midi_path),
        "wav": str(wav_path),
        "wav_sha256": sha256(wav_path),
        "midi_sha256": sha256(midi_path),
        "wav_metadata": wav_metadata(wav_path),
        "validation": result.trace["validation"],
        "framework": result.trace["composition_framework"],
    }


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    control_result = compose(instrument_config(False))
    framework_result = compose(instrument_config(True))
    control = write_result(control_result, OUTPUT, "control")
    framework = write_result(framework_result, OUTPUT, "framework")
    fm = framework["framework"]["metrics"]
    cm = control["framework"]["metrics"]
    obligations = framework["framework"]["obligation_ledger"]
    transformations = framework["framework"]["transformations"]

    checks = {
        "same_seed": control_result.config.seed == framework_result.config.seed,
        "same_tempo": control_result.config.tempo_bpm == framework_result.config.tempo_bpm,
        "same_bar_count": control_result.config.bars == framework_result.config.bars,
        "same_source_pitch_onsets": source_signature(control_result) == source_signature(framework_result),
        "same_lane_names": [v.name for v in control_result.voices] == [v.name for v in framework_result.voices],
        "same_render_duration": control["wav_metadata"]["frames"] == framework["wav_metadata"]["frames"],
        "control_engine_valid": control["validation"]["passed"],
        "framework_engine_valid": framework["validation"]["passed"],
        "framework_trace_valid": framework["framework"]["integration_validation"]["passed"],
        "audio_conditions_differ": control["wav_sha256"] != framework["wav_sha256"],
        "actual_transformation_present": len(transformations) == 1,
        "held_resolution_present": any(
            row["operation"] == "held-resolution-duration-extension"
            for row in transformations
        ),
        "negative_space_increased_in_suspension": (
            fm["mean_suspension_space"] > cm["mean_suspension_space"]
        ),
        "important_moments_have_space": framework["framework"]["evaluation"][
            "important_moments_have_space"
        ],
        "obligations_accounted_for": (
            len(obligations) == fm["deviations"]
            and all(row["status"] != "unresolved" for row in obligations)
        ),
        "timbre_held_fixed": framework_result.config.framework.timbral_strength == 0.0,
        "random_expression_held_off": framework_result.config.framework.expressive_gesture == 0.0,
    }
    comparison = {
        "experiment": "first-structural-ab-v0.1",
        "purpose": (
            "Test one causal structural intervention before expanding "
            "timbre or emotional-vocabulary execution."
        ),
        "estimated_form_seconds": 16 * 4 * 60 / 58,
        "sample_rate": SAMPLE_RATE,
        "checks": checks,
        "passed": all(checks.values()),
        "control": control,
        "framework": framework,
        "metric_deltas": {
            "mean_negative_space": fm["mean_negative_space"] - cm["mean_negative_space"],
            "mean_suspension_space": fm["mean_suspension_space"] - cm["mean_suspension_space"],
            "actual_transformations": fm["actual_transformations"] - cm["actual_transformations"],
        },
        "claim_boundary": (
            "PASS proves a controlled implementation difference only; "
            "it does not prove improved emotional effect."
        ),
    }
    (OUTPUT / "comparison.json").write_text(
        json.dumps(comparison, indent=2) + "\n", encoding="utf-8"
    )

    first_is_framework = hashlib.sha256(
        f"first-ab|{SEED}".encode("ascii")
    ).digest()[0] & 1
    order = ["framework", "control"] if first_is_framework else ["control", "framework"]
    blind_root = OUTPUT / "blind"
    blind_root.mkdir(parents=True, exist_ok=True)
    for index, condition in enumerate(order, start=1):
        shutil.copyfile(
            OUTPUT / f"{condition}.wav",
            blind_root / f"render-{index}.wav",
        )
    mapping = {
        "blind/render-1.wav": order[0],
        "blind/render-2.wav": order[1],
        "do_not_open_before_judgment": True,
    }
    (OUTPUT / "private-condition-map.json").write_text(
        json.dumps(mapping, indent=2) + "\n", encoding="utf-8"
    )
    worksheet = """# First blinded A/B judgment

Listen only to the two WAV files in this blind folder.
Do not browse the parent evidence folder or open private-condition-map.json
until the judgment below has been recorded.

1. Which render would you keep developing: 1 / 2 / no meaningful preference?
2. Where is the strongest moment in each?
3. What did you expect immediately before that moment?
4. Did the arrival feel earned, arbitrary, or neither?
5. Did any part feel unnecessarily busy?
6. Did the empty/quiet space feel useful or unfinished?
7. Did you recognise material returning in a changed form?
8. Which felt more coherent?
9. Which created stronger anticipation?
10. Which was more emotionally affecting?
"""
    (blind_root / "BLIND_LISTENING_WORKSHEET.md").write_text(
        worksheet, encoding="utf-8"
    )
    print(json.dumps({
        "passed": comparison["passed"],
        "checks": checks,
        "blind_files": [
            "blind/render-1.wav",
            "blind/render-2.wav",
        ],
        "mapping": "private-condition-map.json",
    }, indent=2))
    if not comparison["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

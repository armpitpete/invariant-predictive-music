"""Internal working-product gate for IPM v0.2.

This gate deliberately sits outside the listener-study machinery. It freezes a
small portfolio before listening, renders every piece through one production
path, and preserves enough provenance to regenerate or reject the batch.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import sys
import tempfile
import wave
from array import array
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .engine import (
    BassControls,
    ExperimentMode,
    InstrumentConfig,
    RhythmControls,
    compose,
)
from .midi import render_midi

GATE_ID = "ipm-working-product-v1"
SAMPLE_RATE = 44_100
CHANNELS = 2
SAMPLE_WIDTH = 2
PEAK_TARGET_DBFS = -1.5
TAIL_SECONDS = 1
REQUIRED_DECISION = "SHOW"
FAILURE_CLASSES = ("FORM", "MUSICAL", "RENDER", "OTHER")


@dataclass(frozen=True, slots=True)
class PortfolioSpec:
    piece_id: str
    seed_label: str
    seed: int
    profile: str
    config: InstrumentConfig


def _seed(label: str) -> int:
    digest = hashlib.sha256(f"{GATE_ID}:{label}".encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big") & 0x7FFFFFFF


def _profiles() -> dict[str, tuple[BassControls, RhythmControls]]:
    # Frozen before any portfolio listening. The active profile changes only
    # subsidiary activity, keeping the rest of the production controls fixed.
    return {
        "default": (
            BassControls(
                activity=0.46,
                sustain=0.62,
                movement=0.30,
                pattern_complexity=0.42,
                gate=0.88,
            ),
            RhythmControls(
                activity=0.40,
                complexity=0.56,
                syncopation=0.42,
                gate=0.75,
            ),
        ),
        "active": (
            BassControls(
                activity=0.62,
                sustain=0.62,
                movement=0.30,
                pattern_complexity=0.42,
                gate=0.88,
            ),
            RhythmControls(
                activity=0.55,
                complexity=0.56,
                syncopation=0.42,
                gate=0.75,
            ),
        ),
    }


def portfolio_specs() -> tuple[PortfolioSpec, ...]:
    specs: list[PortfolioSpec] = []
    for seed_label in ("A", "B", "C", "D"):
        seed = _seed(seed_label)
        for profile, (bass, rhythm) in _profiles().items():
            piece_id = f"{seed_label.lower()}-{profile}"
            specs.append(
                PortfolioSpec(
                    piece_id=piece_id,
                    seed_label=seed_label,
                    seed=seed,
                    profile=profile,
                    config=InstrumentConfig(
                        seed=seed,
                        tempo_bpm=58,
                        bars=16,
                        beats_per_bar=4,
                        tonic_midi=60,
                        mode=ExperimentMode.IPM,
                        tune_alternatives=18,
                        bass=bass,
                        rhythm=rhythm,
                    ),
                )
            )
    return tuple(specs)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _write_generation(output: Path, spec: PortfolioSpec) -> dict[str, Any]:
    result = compose(spec.config)
    if not result.trace["validation"]["passed"]:
        raise AssertionError(f"{spec.piece_id}: IPM validation failed")

    piece_dir = output / "pieces" / spec.piece_id
    piece_dir.mkdir(parents=True, exist_ok=True)
    midi_path = piece_dir / f"{spec.piece_id}.mid"
    trace_path = piece_dir / f"{spec.piece_id}.trace.json"

    midi = render_midi(
        result.voices,
        tempo_bpm=spec.config.tempo_bpm,
        beats_per_bar=spec.config.beats_per_bar,
    )
    midi_path.write_bytes(midi)
    trace_path.write_text(
        json.dumps(result.trace, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "piece_id": spec.piece_id,
        "seed_label": spec.seed_label,
        "seed": spec.seed,
        "profile": spec.profile,
        "config": {
            "seed": spec.config.seed,
            "tempo_bpm": spec.config.tempo_bpm,
            "bars": spec.config.bars,
            "beats_per_bar": spec.config.beats_per_bar,
            "tonic_midi": spec.config.tonic_midi,
            "mode": spec.config.mode.value,
            "tune_alternatives": spec.config.tune_alternatives,
            "bass": asdict(spec.config.bass),
            "rhythm": asdict(spec.config.rhythm),
        },
        "validation": result.trace["validation"],
        "metrics": result.trace["metrics"],
        "midi": str(midi_path.relative_to(output)),
        "trace": str(trace_path.relative_to(output)),
        "midi_sha256": _sha256_file(midi_path),
        "trace_sha256": _sha256_file(trace_path),
    }


def build_portfolio(output_dir: str | Path, *, source_revision: str) -> Path:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    rows = [_write_generation(output, spec) for spec in portfolio_specs()]
    if len(rows) != 8 or len({row["piece_id"] for row in rows}) != 8:
        raise AssertionError("working-product portfolio must contain exactly 8 unique pieces")

    manifest = {
        "gate_id": GATE_ID,
        "source_revision": source_revision,
        "frozen_before_listening": True,
        "selection_rule": (
            "four SHA-256-derived fixed seeds x two predeclared activity profiles; "
            "no seed or setting may be replaced after listening"
        ),
        "pass_rule": "all 8 pieces must receive SHOW; any FAIL keeps the gate closed",
        "pieces": rows,
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    review = {
        "gate_id": GATE_ID,
        "manifest_sha256": _sha256_file(manifest_path),
        "instruction": (
            "Listen to every complete WAV. Record SHOW or FAIL. "
            "Do not reseed, delete, replace, or tune an individual piece after hearing it."
        ),
        "show_question": (
            "Would I willingly send this exact WAV to a curious person as an example "
            "of current IPM, without explaining that it is broken?"
        ),
        "pass_rule": "8 SHOW / 0 FAIL",
        "failure_classes": list(FAILURE_CLASSES),
        "pieces": [
            {
                "piece_id": row["piece_id"],
                "decision": None,
                "failure_class": None,
                "failure_at_seconds": None,
                "notes": None,
            }
            for row in rows
        ],
    }
    (output / "review-sheet.json").write_text(
        json.dumps(review, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def _render_raw(
    midi_path: Path,
    wav_path: Path,
    *,
    soundfont: Path,
    fluidsynth: str,
) -> None:
    subprocess.run(
        [
            fluidsynth,
            "-ni",
            "-C",
            "no",
            "-R",
            "no",
            str(soundfont),
            str(midi_path),
            "-F",
            str(wav_path),
            "-r",
            str(SAMPLE_RATE),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _read_pcm(path: Path) -> bytes:
    with wave.open(str(path), "rb") as handle:
        if handle.getframerate() != SAMPLE_RATE:
            raise AssertionError("renderer sample rate drifted")
        if handle.getnchannels() != CHANNELS:
            raise AssertionError("renderer channel count drifted")
        if handle.getsampwidth() != SAMPLE_WIDTH:
            raise AssertionError("renderer is not 16-bit PCM")
        return handle.readframes(handle.getnframes())


def _fit_frames(pcm: bytes, frame_count: int) -> bytes:
    frame_width = CHANNELS * SAMPLE_WIDTH
    wanted = frame_count * frame_width
    if len(pcm) >= wanted:
        return pcm[:wanted]
    return pcm + bytes(wanted - len(pcm))


def _peak_abs(pcm: bytes) -> int:
    values = array("h")
    values.frombytes(pcm)
    if sys.byteorder != "little":
        values.byteswap()
    return max(max(values, default=0), -min(values, default=0))


def _normalise_pcm(pcm: bytes) -> tuple[bytes, float]:
    peak = _peak_abs(pcm)
    if peak <= 0:
        raise AssertionError("rendered piece is silent")
    target = 32767.0 * (10.0 ** (PEAK_TARGET_DBFS / 20.0))
    gain = target / peak
    if gain <= 0 or not math.isfinite(gain):
        raise AssertionError("normalisation gain is invalid")

    values = array("h")
    values.frombytes(pcm)
    if sys.byteorder != "little":
        values.byteswap()
    for index, value in enumerate(values):
        scaled = int(round(value * gain))
        values[index] = max(-32768, min(32767, scaled))
    if sys.byteorder != "little":
        values.byteswap()
    return values.tobytes(), gain


def _write_wav(path: Path, pcm: bytes) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(CHANNELS)
        handle.setsampwidth(SAMPLE_WIDTH)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes(pcm)


def _fluidsynth_version(fluidsynth: str) -> str:
    result = subprocess.run(
        [fluidsynth, "--version"],
        check=True,
        capture_output=True,
        text=True,
    )
    text = (result.stdout + result.stderr).strip().splitlines()
    return text[0] if text else "unknown"


def render_portfolio(
    output_dir: str | Path,
    *,
    soundfont: str | Path,
    fluidsynth: str = "fluidsynth",
) -> Path:
    output = Path(output_dir)
    soundfont_path = Path(soundfont)
    if not soundfont_path.is_file():
        raise FileNotFoundError(soundfont_path)
    if shutil.which(fluidsynth) is None:
        raise FileNotFoundError(fluidsynth)

    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows_by_id = {row["piece_id"]: row for row in manifest["pieces"]}

    for spec in portfolio_specs():
        row = rows_by_id[spec.piece_id]
        midi_path = output / row["midi"]
        piece_dir = midi_path.parent
        final_wav = piece_dir / f"{spec.piece_id}.wav"
        form_seconds = (
            spec.config.bars
            * spec.config.beats_per_bar
            * 60
            / spec.config.tempo_bpm
        )
        frame_count = round((form_seconds + TAIL_SECONDS) * SAMPLE_RATE)

        with tempfile.TemporaryDirectory(prefix=f"ipm-product-{spec.piece_id}-") as temp_name:
            temp = Path(temp_name)
            first = temp / "first.wav"
            second = temp / "second.wav"
            _render_raw(
                midi_path,
                first,
                soundfont=soundfont_path,
                fluidsynth=fluidsynth,
            )
            _render_raw(
                midi_path,
                second,
                soundfont=soundfont_path,
                fluidsynth=fluidsynth,
            )
            first_pcm = _fit_frames(_read_pcm(first), frame_count)
            second_pcm = _fit_frames(_read_pcm(second), frame_count)

        if first_pcm != second_pcm:
            raise AssertionError(f"{spec.piece_id}: renderer is not PCM-deterministic")
        final_pcm, gain = _normalise_pcm(first_pcm)
        _write_wav(final_wav, final_pcm)

        row["wav"] = str(final_wav.relative_to(output))
        row["raw_pcm_sha256"] = _sha256_bytes(first_pcm)
        row["wav_pcm_sha256"] = _sha256_bytes(final_pcm)
        row["wav_sha256"] = _sha256_file(final_wav)
        row["normalisation_gain"] = gain
        row["duration_frames"] = frame_count
        row["renderer_repeat_pcm_identical"] = True

    manifest["renderer"] = {
        "engine": "FluidSynth",
        "fluidsynth_version": _fluidsynth_version(fluidsynth),
        "soundfont": str(soundfont_path),
        "soundfont_sha256": _sha256_file(soundfont_path),
        "sample_rate": SAMPLE_RATE,
        "channels": CHANNELS,
        "sample_width_bytes": SAMPLE_WIDTH,
        "chorus": False,
        "reverb": False,
        "program": 0,
        "normalisation": {
            "method": "per-piece peak",
            "target_dbfs": PEAK_TARGET_DBFS,
        },
        "tail_seconds": TAIL_SECONDS,
        "repeat_render_pcm_identity_required": True,
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    review_path = output / "review-sheet.json"
    review = json.loads(review_path.read_text(encoding="utf-8"))
    review["manifest_sha256"] = _sha256_file(manifest_path)
    review["renderer_frozen"] = True
    review_path.write_text(
        json.dumps(review, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the internal IPM working-product gate")
    parser.add_argument("--output", default="working-product-gate")
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--soundfont")
    parser.add_argument("--fluidsynth", default="fluidsynth")
    args = parser.parse_args()

    manifest = build_portfolio(args.output, source_revision=args.source_revision)
    if args.soundfont:
        manifest = render_portfolio(
            args.output,
            soundfont=args.soundfont,
            fluidsynth=args.fluidsynth,
        )
    print(manifest)


if __name__ == "__main__":
    main()

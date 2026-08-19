"""PCM-isolated renderer for Counterfactual Episode v2.

This module is experiment/render-layer only. It regenerates the frozen qualified
episodes, renders one shared prefix, one target per condition, and one shared
suffix, then assembles the final WAVs from those exact PCM segments. The suffix
is rendered from a fresh synthesizer state, so target release/reverb/effect state
cannot leak across the suffix boundary. One common gain is computed per triplet
and applied to all five source segments before assembly.
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
from fractions import Fraction
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from . import experiment as v1
from .engine import ExperimentMode
from .experiment_v2_articulation import _episode_for_seed_v2_articulated
from .midi import render_midi
from .model import NoteEvent, Voice

SAMPLE_RATE = 44_100
CHANNELS = 2
SAMPLE_WIDTH = 2
PEAK_TARGET_DBFS = -1.5


def _round_fraction(value: Fraction) -> int:
    """Round a positive Fraction to nearest integer, with halves rounded up."""

    if value < 0:
        raise ValueError("sample positions must be non-negative")
    return (2 * value.numerator + value.denominator) // (2 * value.denominator)


def sample_boundaries(
    *,
    tempo_bpm: int,
    beats_per_bar: int,
    bars: int,
    target_bar: int,
    sample_rate: int = SAMPLE_RATE,
) -> tuple[int, int, int]:
    """Return exact rounded target-start, target-end, and episode-end frames."""

    if tempo_bpm <= 0 or beats_per_bar <= 0 or bars <= 0 or sample_rate <= 0:
        raise ValueError("tempo, bar geometry, and sample rate must be positive")
    if not 0 <= target_bar < bars:
        raise ValueError("target_bar escapes configured form")
    samples_per_beat = Fraction(sample_rate * 60, tempo_bpm)
    target_start = _round_fraction(samples_per_beat * target_bar * beats_per_bar)
    target_end = _round_fraction(samples_per_beat * (target_bar + 1) * beats_per_bar)
    episode_end = _round_fraction(samples_per_beat * bars * beats_per_bar)
    return target_start, target_end, episode_end


def _slice_shifted_events(
    events: Sequence[NoteEvent],
    *,
    start: Fraction,
    end: Fraction,
) -> tuple[NoteEvent, ...]:
    selected: list[NoteEvent] = []
    for event in events:
        if event.onset < start or event.onset >= end:
            continue
        if event.end > end:
            raise AssertionError("event crosses an experimental PCM boundary")
        selected.append(
            NoteEvent(
                onset=event.onset - start,
                duration=event.duration,
                pitch=event.pitch,
                velocity=event.velocity,
            )
        )
    return tuple(selected)


def _write_midi(path: Path, events: Sequence[NoteEvent], *, tempo_bpm: int, beats_per_bar: int) -> None:
    voice = Voice.from_events("TUNE", events)
    path.write_bytes(
        render_midi((voice,), tempo_bpm=tempo_bpm, beats_per_bar=beats_per_bar)
    )


def _render_component(
    midi_path: Path,
    wav_path: Path,
    *,
    soundfont: Path,
    fluidsynth: str,
) -> None:
    command = [
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
    ]
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _read_pcm(path: Path) -> bytes:
    with wave.open(str(path), "rb") as handle:
        if handle.getframerate() != SAMPLE_RATE:
            raise AssertionError("component WAV sample rate drifted")
        if handle.getnchannels() != CHANNELS:
            raise AssertionError("component WAV channel count drifted")
        if handle.getsampwidth() != SAMPLE_WIDTH:
            raise AssertionError("component WAV is not 16-bit PCM")
        return handle.readframes(handle.getnframes())


def _fit_frames(pcm: bytes, frame_count: int) -> bytes:
    frame_width = CHANNELS * SAMPLE_WIDTH
    wanted = frame_count * frame_width
    if len(pcm) >= wanted:
        return pcm[:wanted]
    return pcm + bytes(wanted - len(pcm))


def _peak_abs(pcm: bytes) -> int:
    if not pcm:
        return 0
    values = array("h")
    values.frombytes(pcm)
    if sys.byteorder != "little":
        values.byteswap()
    return max(max(values, default=0), -min(values, default=0))


def shared_peak_gain(segments: Iterable[bytes], *, peak_dbfs: float = PEAK_TARGET_DBFS) -> float:
    """Return one linear gain for the complete triplet, using a shared peak target."""

    peak = max((_peak_abs(segment) for segment in segments), default=0)
    if peak <= 0:
        raise ValueError("cannot normalise silent triplet")
    target = 32767.0 * (10.0 ** (peak_dbfs / 20.0))
    return target / peak


def scale_pcm(pcm: bytes, gain: float) -> bytes:
    if gain <= 0 or not math.isfinite(gain):
        raise ValueError("gain must be positive and finite")
    values = array("h")
    values.frombytes(pcm)
    if sys.byteorder != "little":
        values.byteswap()
    for index, value in enumerate(values):
        scaled = int(round(value * gain))
        values[index] = max(-32768, min(32767, scaled))
    if sys.byteorder != "little":
        values.byteswap()
    return values.tobytes()


def _write_pcm_wav(path: Path, pcm: bytes) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(CHANNELS)
        handle.setsampwidth(SAMPLE_WIDTH)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes(pcm)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _mode_order() -> tuple[ExperimentMode, ...]:
    return (
        ExperimentMode.PREDICTABLE,
        ExperimentMode.IPM,
        ExperimentMode.UNSTRUCTURED_SURPRISE,
    )


def render_isolated_pilot(
    pilot_dir: str | Path,
    *,
    soundfont: str | Path,
    fluidsynth: str = "fluidsynth",
) -> Path:
    """Replace participant WAVs with PCM-isolated Counterfactual Episode v2 audio."""

    pilot = Path(pilot_dir)
    soundfont_path = Path(soundfont)
    if not soundfont_path.is_file():
        raise FileNotFoundError(soundfont_path)
    if shutil.which(fluidsynth) is None:
        raise FileNotFoundError(fluidsynth)

    manifest_path = pilot / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    bars = int(manifest["bars"])
    target_bar = int(manifest["target_bar_zero_indexed"])
    blind_seed = int(manifest["blinding"]["blind_seed"])
    qualified_seeds = tuple(int(seed) for seed in manifest["selection"]["qualified_seeds"])
    criteria = v1.MatchCriteria(**manifest["criteria"])

    component_root = pilot / "researcher" / "audio-components"
    component_root.mkdir(parents=True, exist_ok=True)
    gate_rows: list[dict[str, object]] = []

    for seed in qualified_seeds:
        episode, audit = _episode_for_seed_v2_articulated(
            seed=seed,
            bars=bars,
            target_bar=target_bar,
            criteria=criteria,
        )
        if episode is None or not audit.passed:
            raise AssertionError(f"frozen qualified seed {seed} no longer qualifies")

        config = v1.pilot_config(seed=seed, bars=bars)
        target_start_beat = Fraction(target_bar * config.beats_per_bar)
        target_end_beat = target_start_beat + config.beats_per_bar
        episode_end_beat = Fraction(bars * config.beats_per_bar)
        target_start_frame, target_end_frame, episode_end_frame = sample_boundaries(
            tempo_bpm=config.tempo_bpm,
            beats_per_bar=config.beats_per_bar,
            bars=bars,
            target_bar=target_bar,
        )
        prefix_frames = target_start_frame
        target_frames = target_end_frame - target_start_frame
        suffix_frames = episode_end_frame - target_end_frame

        ipm_events = tuple(episode.variants[ExperimentMode.IPM].tune.events)
        prefix_events = _slice_shifted_events(
            ipm_events,
            start=Fraction(0),
            end=target_start_beat,
        )
        suffix_events = _slice_shifted_events(
            ipm_events,
            start=target_end_beat,
            end=episode_end_beat,
        )

        seed_dir = component_root / str(seed)
        seed_dir.mkdir(parents=True, exist_ok=True)
        prefix_midi = seed_dir / "prefix.mid"
        suffix_midi = seed_dir / "suffix.mid"
        _write_midi(
            prefix_midi,
            prefix_events,
            tempo_bpm=config.tempo_bpm,
            beats_per_bar=config.beats_per_bar,
        )
        _write_midi(
            suffix_midi,
            suffix_events,
            tempo_bpm=config.tempo_bpm,
            beats_per_bar=config.beats_per_bar,
        )

        target_midis: dict[ExperimentMode, Path] = {}
        for mode in _mode_order():
            target_events = _slice_shifted_events(
                tuple(episode.variants[mode].tune.events),
                start=target_start_beat,
                end=target_end_beat,
            )
            stimulus_id = v1._blind_id(blind_seed, seed, mode)
            target_midi = seed_dir / f"target-{stimulus_id}.mid"
            _write_midi(
                target_midi,
                target_events,
                tempo_bpm=config.tempo_bpm,
                beats_per_bar=config.beats_per_bar,
            )
            target_midis[mode] = target_midi

        with tempfile.TemporaryDirectory(prefix=f"ipm-audio-{seed}-") as temp_name:
            temp = Path(temp_name)
            prefix_wav = temp / "prefix.wav"
            suffix_wav = temp / "suffix.wav"
            _render_component(prefix_midi, prefix_wav, soundfont=soundfont_path, fluidsynth=fluidsynth)
            _render_component(suffix_midi, suffix_wav, soundfont=soundfont_path, fluidsynth=fluidsynth)
            prefix_pcm = _fit_frames(_read_pcm(prefix_wav), prefix_frames)
            suffix_pcm = _fit_frames(_read_pcm(suffix_wav), suffix_frames)

            target_pcm: dict[ExperimentMode, bytes] = {}
            for mode, midi_path in target_midis.items():
                wav_path = temp / f"{mode.value}.wav"
                _render_component(midi_path, wav_path, soundfont=soundfont_path, fluidsynth=fluidsynth)
                target_pcm[mode] = _fit_frames(_read_pcm(wav_path), target_frames)

        gain = shared_peak_gain((prefix_pcm, suffix_pcm, *target_pcm.values()))
        prefix_scaled = scale_pcm(prefix_pcm, gain)
        suffix_scaled = scale_pcm(suffix_pcm, gain)
        target_scaled = {mode: scale_pcm(pcm, gain) for mode, pcm in target_pcm.items()}

        assembled: dict[ExperimentMode, bytes] = {}
        for mode in _mode_order():
            stimulus_id = v1._blind_id(blind_seed, seed, mode)
            final_pcm = prefix_scaled + target_scaled[mode] + suffix_scaled
            if len(final_pcm) != episode_end_frame * CHANNELS * SAMPLE_WIDTH:
                raise AssertionError("assembled PCM length drifted")
            _write_pcm_wav(pilot / "stimuli" / f"{stimulus_id}.wav", final_pcm)
            assembled[mode] = final_pcm

        prefix_size = target_start_frame * CHANNELS * SAMPLE_WIDTH
        suffix_offset = target_end_frame * CHANNELS * SAMPLE_WIDTH
        prefix_hashes = {_sha256(pcm[:prefix_size]) for pcm in assembled.values()}
        suffix_hashes = {_sha256(pcm[suffix_offset:]) for pcm in assembled.values()}
        target_hashes = {
            mode.value: _sha256(
                assembled[mode][prefix_size:suffix_offset]
            )
            for mode in _mode_order()
        }
        prefix_identical = len(prefix_hashes) == 1
        suffix_identical = len(suffix_hashes) == 1
        target_pitch_contrast_audible = (
            target_hashes[ExperimentMode.IPM.value]
            != target_hashes[ExperimentMode.UNSTRUCTURED_SURPRISE.value]
        )
        passed = prefix_identical and suffix_identical and target_pitch_contrast_audible
        gate_rows.append(
            {
                "seed": seed,
                "passed": passed,
                "target_start_frame": target_start_frame,
                "target_end_frame": target_end_frame,
                "episode_end_frame": episode_end_frame,
                "common_gain": gain,
                "prefix_pcm_sha256": next(iter(prefix_hashes)) if prefix_identical else None,
                "suffix_pcm_sha256": next(iter(suffix_hashes)) if suffix_identical else None,
                "target_pcm_sha256": target_hashes,
                "prefix_sample_identical": prefix_identical,
                "suffix_sample_identical": suffix_identical,
                "ipm_control_target_audio_differs": target_pitch_contrast_audible,
            }
        )
        if not passed:
            raise AssertionError(f"PCM isolation gate failed for seed {seed}")

    gate = {
        "experiment": "Counterfactual Episode v2 PCM isolation gate",
        "sample_rate": SAMPLE_RATE,
        "channels": CHANNELS,
        "sample_width_bytes": SAMPLE_WIDTH,
        "renderer_effects": {"chorus": False, "reverb": False},
        "normalization": {
            "scope": "one shared gain per three-condition seed triplet",
            "method": "peak",
            "target_dbfs": PEAK_TARGET_DBFS,
            "independent_per_condition_normalization": False,
        },
        "boundary_policy": {
            "prefix": "one rendered PCM segment reused across all three conditions",
            "target": "one separately rendered PCM segment per condition",
            "suffix": "one fresh-state rendered PCM segment reused across all three conditions",
            "target_effect_state_can_enter_suffix": False,
        },
        "required_seed_count": len(qualified_seeds),
        "passed_seed_count": sum(bool(row["passed"]) for row in gate_rows),
        "passed": all(bool(row["passed"]) for row in gate_rows),
        "seeds": gate_rows,
    }
    gate_path = pilot / "researcher" / "audio-isolation-gate.json"
    gate_path.write_text(json.dumps(gate, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    manifest["audio_isolation"] = {
        "gate": "researcher/audio-isolation-gate.json",
        "prefix_pcm_identical": True,
        "suffix_pcm_identical": True,
        "suffix_renderer_state_reset_after_target": True,
        "shared_triplet_gain": True,
        "peak_target_dbfs": PEAK_TARGET_DBFS,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return gate_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render PCM-isolated audio for the frozen Counterfactual Episode v2 pilot"
    )
    parser.add_argument("--pilot-dir", default="listening-pilot")
    parser.add_argument("--soundfont", required=True)
    parser.add_argument("--fluidsynth", default="fluidsynth")
    args = parser.parse_args()
    gate = render_isolated_pilot(
        args.pilot_dir,
        soundfont=args.soundfont,
        fluidsynth=args.fluidsynth,
    )
    print(gate)


if __name__ == "__main__":
    main()

"""Dependency-free preview WAV renderer for IPM Machine v0.

This is deliberately not the research renderer and not a replacement for a
real synth. It exists so the local machine can PLAY immediately without
requiring FluidSynth or a DAW.
"""

from __future__ import annotations

import math
import wave
from array import array
from pathlib import Path

from .engine import InstrumentResult

_SAMPLE_RATE = 22_050
_VOICE_GAIN = {"TUNE": 0.34, "BASS": 0.30, "RHYTHM": 0.20}


def _oscillator(voice: str, phase: float) -> float:
    sine = math.sin(phase)
    if voice == "BASS":
        return 0.82 * sine + 0.18 * math.sin(phase * 0.5)
    if voice == "RHYTHM":
        return 0.72 * sine + 0.28 * math.sin(phase * 2.0)
    return 0.78 * sine + 0.22 * math.sin(phase * 2.0)


def _envelope(position: float, duration: float, voice: str) -> float:
    attack = min(0.025 if voice != "RHYTHM" else 0.008, duration * 0.18)
    release = min(0.10 if voice != "RHYTHM" else 0.055, duration * 0.30)
    if attack > 0 and position < attack:
        return position / attack
    remaining = duration - position
    if release > 0 and remaining < release:
        return max(0.0, remaining / release)
    if voice == "RHYTHM":
        return math.exp(-2.0 * position / max(duration, 1e-6))
    return 1.0


def render_preview_wav(
    result: InstrumentResult,
    path: str | Path,
    *,
    sample_rate: int = _SAMPLE_RATE,
) -> Path:
    """Render a simple deterministic stereo WAV preview."""

    if sample_rate < 8_000:
        raise ValueError("sample_rate must be >= 8000")
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    seconds_per_beat = 60.0 / result.config.tempo_bpm
    total_beats = result.config.bars * result.config.beats_per_bar
    tail_seconds = 0.20
    sample_count = int((total_beats * seconds_per_beat + tail_seconds) * sample_rate)
    mono = array("f", [0.0]) * sample_count

    for voice in result.voices:
        gain = _VOICE_GAIN.get(voice.name, 0.20)
        for event in voice.events:
            start_seconds = float(event.onset) * seconds_per_beat
            duration_seconds = float(event.duration) * seconds_per_beat
            start = max(0, int(start_seconds * sample_rate))
            end = min(sample_count, int((start_seconds + duration_seconds) * sample_rate))
            if end <= start:
                continue
            frequency = 440.0 * (2.0 ** ((event.pitch - 69) / 12.0))
            velocity = max(0.0, min(1.0, event.velocity / 127.0))
            amplitude = gain * (0.45 + 0.55 * velocity)
            for index in range(start, end):
                elapsed = (index - start) / sample_rate
                phase = 2.0 * math.pi * frequency * elapsed
                mono[index] += (
                    amplitude
                    * _envelope(elapsed, duration_seconds, voice.name)
                    * _oscillator(voice.name, phase)
                )

    peak = max((abs(value) for value in mono), default=0.0)
    scale = 0.90 / peak if peak > 0.90 else 1.0
    frames = array("h")
    for value in mono:
        sample = int(max(-1.0, min(1.0, value * scale)) * 32767)
        frames.append(sample)
        frames.append(sample)

    with wave.open(str(destination), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(frames.tobytes())
    return destination

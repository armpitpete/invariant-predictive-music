"""Deterministic stereo synthesis engine for IPM Machine.

This is the machine's audible instrument, not a research renderer.  It gives
TUNE, BASS and RHYTHM deliberately different subtractive/additive voices and
renders the same engine for PLAY and FINISH.
"""

from __future__ import annotations

import math
import wave
from array import array
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .engine import InstrumentResult

SYNTH_ENGINE_VERSION = "1.0"
DEFAULT_SAMPLE_RATE = 44_100
_TABLE_SIZE = 4096
_TABLE_MASK = _TABLE_SIZE - 1
_SINE = tuple(math.sin(2.0 * math.pi * i / _TABLE_SIZE) for i in range(_TABLE_SIZE))
_CENTS_LINEAR = math.log(2.0) / 1200.0


@dataclass(frozen=True, slots=True)
class SynthPreset:
    """Fixed timbral voice definition for one IPM lane."""

    gain: float
    pan: float
    attack: float
    decay: float
    sustain: float
    release: float
    cutoff_hz: float
    partials: tuple[tuple[float, float], ...]
    detune_cents: float = 0.0
    vibrato_hz: float = 0.0
    vibrato_cents: float = 0.0
    space_send: float = 0.0

    def __post_init__(self) -> None:
        if self.gain <= 0.0:
            raise ValueError("gain must be positive")
        if not -1.0 <= self.pan <= 1.0:
            raise ValueError("pan must be in -1..1")
        if min(self.attack, self.decay, self.release) < 0.0:
            raise ValueError("ADSR times must be non-negative")
        if not 0.0 <= self.sustain <= 1.0:
            raise ValueError("sustain must be in 0..1")
        if self.cutoff_hz <= 0.0:
            raise ValueError("cutoff_hz must be positive")
        if not self.partials:
            raise ValueError("at least one oscillator partial is required")
        if not 0.0 <= self.space_send <= 1.0:
            raise ValueError("space_send must be in 0..1")


SYNTH_PRESETS: dict[str, SynthPreset] = {
    "TUNE": SynthPreset(
        gain=0.31,
        pan=-0.12,
        attack=0.018,
        decay=0.16,
        sustain=0.68,
        release=0.24,
        cutoff_hz=4_800.0,
        partials=((1.0, 1.0), (2.0, 0.23), (3.0, 0.11), (5.0, 0.045)),
        detune_cents=4.5,
        vibrato_hz=5.15,
        vibrato_cents=3.2,
        space_send=0.20,
    ),
    "BASS": SynthPreset(
        gain=0.36,
        pan=-0.02,
        attack=0.010,
        decay=0.19,
        sustain=0.78,
        release=0.30,
        cutoff_hz=1_050.0,
        partials=((1.0, 1.0), (2.0, 0.17), (3.0, 0.055)),
        detune_cents=2.0,
        space_send=0.055,
    ),
    "RHYTHM": SynthPreset(
        gain=0.24,
        pan=0.18,
        attack=0.003,
        decay=0.075,
        sustain=0.24,
        release=0.11,
        cutoff_hz=3_200.0,
        partials=((1.0, 1.0), (2.0, 0.31), (4.0, 0.13), (6.0, 0.045)),
        detune_cents=6.0,
        space_send=0.12,
    ),
}


@dataclass(frozen=True, slots=True)
class SynthRenderInfo:
    engine_version: str
    sample_rate: int
    channels: int
    sample_width_bits: int
    architecture: str
    presets: dict[str, dict[str, Any]]


def synth_manifest(sample_rate: int = DEFAULT_SAMPLE_RATE) -> dict[str, Any]:
    """Return the exact fixed synthesis contract used for a render."""

    return asdict(
        SynthRenderInfo(
            engine_version=SYNTH_ENGINE_VERSION,
            sample_rate=sample_rate,
            channels=2,
            sample_width_bits=16,
            architecture=(
                "polyphonic additive oscillators -> per-note 12 dB low-pass -> "
                "ADSR -> equal-power stereo pan -> deterministic stereo space -> "
                "DC block -> soft limiter"
            ),
            presets={name: asdict(preset) for name, preset in SYNTH_PRESETS.items()},
        )
    )


def _table_sine(phase: float) -> float:
    return _SINE[int(phase) & _TABLE_MASK]


def _midi_frequency(pitch: int) -> float:
    return 440.0 * (2.0 ** ((pitch - 69) / 12.0))


def _adsr_level(position: float, hold: float, preset: SynthPreset) -> float:
    if position < 0.0:
        return 0.0
    attack = preset.attack
    decay = preset.decay
    if position < hold:
        if attack > 0.0 and position < attack:
            return position / attack
        if decay > 0.0 and position < attack + decay:
            progress = (position - attack) / decay
            return 1.0 - (1.0 - preset.sustain) * max(0.0, min(1.0, progress))
        return preset.sustain

    if hold <= 0.0:
        release_start = 0.0
    elif attack > 0.0 and hold < attack:
        release_start = hold / attack
    elif decay > 0.0 and hold < attack + decay:
        progress = (hold - attack) / decay
        release_start = 1.0 - (1.0 - preset.sustain) * max(0.0, min(1.0, progress))
    else:
        release_start = preset.sustain

    if preset.release <= 0.0:
        return 0.0
    release_position = position - hold
    if release_position >= preset.release:
        return 0.0
    return release_start * (1.0 - release_position / preset.release)


def _equal_power_pan(pan: float) -> tuple[float, float]:
    angle = (pan + 1.0) * math.pi / 4.0
    return math.cos(angle), math.sin(angle)


def _render_note(
    left: array,
    right: array,
    *,
    start: int,
    hold_seconds: float,
    frequency: float,
    velocity: int,
    preset: SynthPreset,
    sample_rate: int,
    phase_seed: float,
) -> None:
    release_seconds = preset.release
    note_samples = max(1, int((hold_seconds + release_seconds) * sample_rate))
    end = min(len(left), start + note_samples)
    if end <= start:
        return

    velocity_unit = max(0.0, min(1.0, velocity / 127.0))
    amplitude = preset.gain * (0.36 + 0.64 * velocity_unit)
    pan_left, pan_right = _equal_power_pan(preset.pan)
    cutoff = min(
        sample_rate * 0.44,
        preset.cutoff_hz * (0.72 + 0.52 * velocity_unit),
    )
    alpha = 1.0 - math.exp(-2.0 * math.pi * cutoff / sample_rate)
    detune_factor = 1.0 + _CENTS_LINEAR * preset.detune_cents
    base_increment = frequency * _TABLE_SIZE / sample_rate
    detune_increment = base_increment * detune_factor
    lfo_increment = preset.vibrato_hz * _TABLE_SIZE / sample_rate
    partial_norm = sum(abs(weight) for _, weight in preset.partials) + 0.18

    phase = phase_seed
    detune_phase = phase_seed * 1.117 + 193.0
    lfo_phase = phase_seed * 0.37
    lp1 = 0.0
    lp2 = 0.0

    for index in range(start, end):
        position = (index - start) / sample_rate
        envelope = _adsr_level(position, hold_seconds, preset)
        if envelope <= 0.0 and position >= hold_seconds:
            break

        vibrato = 1.0
        if preset.vibrato_cents and preset.vibrato_hz:
            vibrato += _CENTS_LINEAR * preset.vibrato_cents * _table_sine(lfo_phase)
            lfo_phase += lfo_increment

        raw = sum(
            weight * _table_sine(phase * ratio)
            for ratio, weight in preset.partials
        )
        if preset.detune_cents:
            raw += 0.09 * _table_sine(detune_phase)
        raw /= partial_norm

        phase += base_increment * vibrato
        detune_phase += detune_increment * vibrato

        shaped = math.tanh(raw * 1.18) * envelope * amplitude
        lp1 += alpha * (shaped - lp1)
        lp2 += alpha * (lp1 - lp2)
        sample = lp2
        left[index] += sample * pan_left
        right[index] += sample * pan_right


def _apply_stereo_space(left: array, right: array, sample_rate: int) -> None:
    """Feed-forward short room taps; no random state and no feedback instability."""

    dry_left = array("f", left)
    dry_right = array("f", right)
    taps = (
        (0.071, 0.105, 0.035),
        (0.127, 0.072, 0.050),
        (0.211, 0.048, 0.060),
    )
    for delay_seconds, same_gain, cross_gain in taps:
        delay = max(1, int(delay_seconds * sample_rate))
        for index in range(delay, len(left)):
            left[index] += (
                same_gain * dry_left[index - delay]
                + cross_gain * dry_right[index - delay]
            )
            right[index] += (
                same_gain * dry_right[index - delay]
                + cross_gain * dry_left[index - delay]
            )


def _master_pcm(left: array, right: array) -> array:
    frames = array("h")
    previous_left_in = previous_right_in = 0.0
    previous_left_out = previous_right_out = 0.0
    dc = 0.995
    limiter_norm = math.tanh(1.32)

    for left_in, right_in in zip(left, right, strict=True):
        left_hp = left_in - previous_left_in + dc * previous_left_out
        right_hp = right_in - previous_right_in + dc * previous_right_out
        previous_left_in, previous_right_in = left_in, right_in
        previous_left_out, previous_right_out = left_hp, right_hp

        left_limited = 0.93 * math.tanh(1.32 * left_hp) / limiter_norm
        right_limited = 0.93 * math.tanh(1.32 * right_hp) / limiter_norm
        frames.append(int(max(-1.0, min(1.0, left_limited)) * 32767))
        frames.append(int(max(-1.0, min(1.0, right_limited)) * 32767))
    return frames


def render_synth_wav(
    result: InstrumentResult,
    path: str | Path,
    *,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
) -> Path:
    """Render IPM through the fixed Machine Synth Engine v1."""

    if sample_rate < 8_000:
        raise ValueError("sample_rate must be >= 8000")
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    seconds_per_beat = 60.0 / result.config.tempo_bpm
    total_beats = result.config.bars * result.config.beats_per_bar
    tail_seconds = max(preset.release for preset in SYNTH_PRESETS.values()) + 0.28
    sample_count = max(
        1,
        int((total_beats * seconds_per_beat + tail_seconds) * sample_rate),
    )
    left = array("f", [0.0]) * sample_count
    right = array("f", [0.0]) * sample_count

    for voice in result.voices:
        preset = SYNTH_PRESETS.get(voice.name)
        if preset is None:
            continue
        for ordinal, event in enumerate(voice.events):
            start_seconds = float(event.onset) * seconds_per_beat
            hold_seconds = max(0.001, float(event.duration) * seconds_per_beat)
            start = max(0, int(start_seconds * sample_rate))
            phase_seed = (
                event.pitch * 73.0
                + float(event.onset) * 151.0
                + ordinal * 97.0
            ) % _TABLE_SIZE
            _render_note(
                left,
                right,
                start=start,
                hold_seconds=hold_seconds,
                frequency=_midi_frequency(event.pitch),
                velocity=event.velocity,
                preset=preset,
                sample_rate=sample_rate,
                phase_seed=phase_seed,
            )

    _apply_stereo_space(left, right, sample_rate)
    frames = _master_pcm(left, right)
    with wave.open(str(destination), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(frames.tobytes())
    return destination

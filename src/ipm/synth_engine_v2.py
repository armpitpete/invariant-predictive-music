"""Machine Synth Engine v2: Evolving Resonant Field.

This module implements the frozen design in SYNTH_ENGINE_V2_DESIGN.md.
It is intentionally parallel to the failed v1 renderer: Machine PLAY/FINISH
must not switch to v2 until the v2 audible acceptance gate passes.
"""

from __future__ import annotations

import math
import wave
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from .engine import InstrumentResult

SYNTH_ENGINE_VERSION = "2.0"
DEFAULT_SAMPLE_RATE = 44_100
_MASK64 = (1 << 64) - 1
_LANE_ID = {"TUNE": 1, "BASS": 2, "RHYTHM": 3}
_PHRASE_BRIGHTNESS = (-0.08, 0.04, 0.10, -0.03)
_ARC_POS = np.array((0.00, 0.33, 0.67, 1.00), dtype=np.float64)
_ARC_BRIGHTNESS = np.array((0.34, 0.62, 0.82, 0.48), dtype=np.float64)
_ARC_MOTION = np.array((0.18, 0.34, 0.46, 0.24), dtype=np.float64)
_ARC_WIDTH = np.array((0.58, 0.78, 0.94, 0.68), dtype=np.float64)
_ARC_ROOM = np.array((0.18, 0.24, 0.31, 0.22), dtype=np.float64)
_LANE_DRY_GAIN = {"TUNE": 0.74, "BASS": 0.82, "RHYTHM": 0.68}
_ROOM_RETURN_GAIN = 0.58


@dataclass(frozen=True, slots=True)
class SharedState:
    brightness: float
    motion_depth: float
    stereo_width: float
    room_send: float


@dataclass(frozen=True, slots=True)
class EventVariation:
    value: float
    attack_scale: float
    decay_scale: float
    transient_scale: float
    pan_offset: float
    phase: float
    rate_scale: float


@dataclass(frozen=True, slots=True)
class SynthV2Manifest:
    engine_version: str
    sample_rate: int
    channels: int
    sample_width_bits: int
    engine_name: str
    contract_commit: str
    arc: dict[str, list[float]]
    phrase_brightness_offsets: tuple[float, ...]
    lane_dry_gain: dict[str, float]
    room_return_gain: float
    tune: dict[str, Any]
    bass: dict[str, Any]
    rhythm: dict[str, Any]
    room: dict[str, Any]
    master: dict[str, Any]


def synth_v2_manifest(sample_rate: int = DEFAULT_SAMPLE_RATE) -> dict[str, Any]:
    """Return the frozen Machine Synth Engine v2 render contract."""

    return asdict(
        SynthV2Manifest(
            engine_version=SYNTH_ENGINE_VERSION,
            sample_rate=sample_rate,
            channels=2,
            sample_width_bits=16,
            engine_name="Evolving Resonant Field v2",
            contract_commit="7fa85d05134ee0b1df5f34cf562a3c6b39a27f5b",
            arc={
                "position": _ARC_POS.tolist(),
                "brightness": _ARC_BRIGHTNESS.tolist(),
                "motion_depth": _ARC_MOTION.tolist(),
                "stereo_width": _ARC_WIDTH.tolist(),
                "room_send": _ARC_ROOM.tolist(),
            },
            phrase_brightness_offsets=_PHRASE_BRIGHTNESS,
            lane_dry_gain=dict(_LANE_DRY_GAIN),
            room_return_gain=_ROOM_RETURN_GAIN,
            tune={
                "modes": (
                    (1.000, 1.000, 1.00),
                    (2.010, 0.290, 0.72),
                    (3.970, 0.155, 0.49),
                    (5.120, 0.090, 0.35),
                    (7.080, 0.052, 0.24),
                ),
                "twin_cents": 3.7,
                "twin_gain": 0.115,
                "noise_transient_seconds": 0.038,
                "noise_transient_gain": 0.105,
                "adsr": (0.018, 0.145, 0.66, 0.310),
                "motion_rate_hz": 0.23,
                "slow_drift_hz": 0.071,
                "slow_drift_depth": 0.035,
                "air_moving_average": 9,
                "base_pan": -0.16,
                "twin_pan": 0.13,
                "room_factor": 0.27,
            },
            bass={
                "components": (
                    (0.500, 0.19),
                    (1.000, 1.00),
                    (2.000, 0.18),
                    (3.000, 0.070),
                    (5.000, 0.025),
                ),
                "drive": 1.55,
                "noise_transient_seconds": 0.026,
                "noise_transient_gain": 0.085,
                "adsr": (0.011, 0.190, 0.76, 0.360),
                "motion_rate_hz": 0.117,
                "base_pan": -0.025,
                "room_factor": 0.10,
            },
            rhythm={
                "noise_transient_seconds": 0.014,
                "noise_transient_gain": 0.22,
                "modal_ratios": (1.000, 1.470, 2.230, 3.650, 5.180),
                "modal_gains": (1.00, 0.42, 0.24, 0.13, 0.065),
                "modal_decays": (0.22, 0.17, 0.12, 0.085, 0.060),
                "drive": 1.32,
                "base_pan": 0.22,
                "room_factor": 0.22,
            },
            room={
                "length_seconds": 0.92,
                "late_start_seconds": 0.100,
                "late_decay_seconds": 0.245,
                "left_taps": ((0.023, 0.24), (0.041, 0.17), (0.067, 0.115), (0.089, 0.082)),
                "right_taps": ((0.029, 0.22), (0.047, 0.16), (0.071, 0.108), (0.097, 0.077)),
                "late_smooth_samples": 17,
                "final_smooth_samples": 11,
            },
            master={
                "soft_saturation_drive": 1.18,
                "peak_ceiling": 0.94,
                "dc_removal": "subtract-channel-mean",
            },
        )
    )


def _mix64(value: int) -> int:
    value = (value + 0x9E3779B97F4A7C15) & _MASK64
    value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & _MASK64
    value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & _MASK64
    return (value ^ (value >> 31)) & _MASK64


def _event_seed(lane: str, event: Any, ordinal: int) -> int:
    onset = event.onset
    value = _LANE_ID[lane]
    for component in (
        int(event.pitch),
        int(onset.numerator),
        int(onset.denominator),
        int(ordinal),
    ):
        value = _mix64(value ^ (component & _MASK64))
    return value


def _noise(count: int, seed: int) -> np.ndarray:
    if count <= 0:
        return np.zeros(0, dtype=np.float64)
    idx = np.arange(count, dtype=np.uint64) + np.uint64(seed & _MASK64)
    z = idx + np.uint64(0x9E3779B97F4A7C15)
    z = (z ^ (z >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)
    z = (z ^ (z >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)
    z = z ^ (z >> np.uint64(31))
    unit = (z >> np.uint64(11)).astype(np.float64) * (1.0 / float(1 << 53))
    return unit * 2.0 - 1.0


def _smooth(signal: np.ndarray, window: int) -> np.ndarray:
    if window <= 1 or signal.size == 0:
        return signal
    kernel = np.full(window, 1.0 / window, dtype=np.float64)
    return np.convolve(signal, kernel, mode="same")


def _shared_state(onset_beats: float, total_beats: float, beats_per_bar: int) -> SharedState:
    p = 0.0 if total_beats <= 0.0 else min(1.0, max(0.0, onset_beats / total_beats))
    brightness = float(np.interp(p, _ARC_POS, _ARC_BRIGHTNESS))
    motion = float(np.interp(p, _ARC_POS, _ARC_MOTION))
    width = float(np.interp(p, _ARC_POS, _ARC_WIDTH))
    room = float(np.interp(p, _ARC_POS, _ARC_ROOM))
    phrase_beats = max(1, beats_per_bar * 4)
    phrase_index = int(onset_beats // phrase_beats)
    brightness += _PHRASE_BRIGHTNESS[phrase_index % len(_PHRASE_BRIGHTNESS)]
    return SharedState(
        brightness=min(1.0, max(0.0, brightness)),
        motion_depth=motion,
        stereo_width=width,
        room_send=room,
    )


def _variation(seed: int) -> EventVariation:
    value = (((_mix64(seed) >> 11) / float(1 << 53)) * 2.0) - 1.0
    phase_unit = ((_mix64(seed ^ 0xD1B54A32D192ED03) >> 11) / float(1 << 53))
    rate_value = (((_mix64(seed ^ 0x94D049BB133111EB) >> 11) / float(1 << 53)) * 2.0) - 1.0
    return EventVariation(
        value=value,
        attack_scale=1.0 + 0.12 * value,
        decay_scale=1.0 + 0.09 * value,
        transient_scale=1.0 + 0.10 * value,
        pan_offset=0.035 * value,
        phase=2.0 * math.pi * phase_unit,
        rate_scale=1.0 + 0.06 * rate_value,
    )


def _midi_frequency(pitch: int) -> float:
    return 440.0 * (2.0 ** ((pitch - 69) / 12.0))


def _adsr(
    t: np.ndarray,
    hold: float,
    attack: float,
    decay: float,
    sustain: float,
    release: float,
) -> np.ndarray:
    envelope = np.empty_like(t)
    attack = max(1e-6, attack)
    decay = max(1e-6, decay)
    release = max(1e-6, release)
    attack_end = attack
    decay_end = attack + decay

    attack_mask = t < min(hold, attack_end)
    envelope[attack_mask] = t[attack_mask] / attack

    sustain_mask = (t >= attack_end) & (t < hold)
    decay_mask = sustain_mask & (t < decay_end)
    envelope[decay_mask] = 1.0 - (1.0 - sustain) * ((t[decay_mask] - attack_end) / decay)
    steady_mask = sustain_mask & ~decay_mask
    envelope[steady_mask] = sustain

    if hold < attack_end:
        release_start = hold / attack
    elif hold < decay_end:
        release_start = 1.0 - (1.0 - sustain) * ((hold - attack_end) / decay)
    else:
        release_start = sustain
    release_mask = t >= hold
    envelope[release_mask] = release_start * np.maximum(0.0, 1.0 - (t[release_mask] - hold) / release)
    return np.maximum(0.0, envelope)


def _pan(signal: np.ndarray, pan: float) -> tuple[np.ndarray, np.ndarray]:
    pan = min(1.0, max(-1.0, pan))
    angle = (pan + 1.0) * math.pi / 4.0
    return signal * math.cos(angle), signal * math.sin(angle)


def _tune_event(
    event: Any,
    ordinal: int,
    state: SharedState,
    sample_rate: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    seed = _event_seed("TUNE", event, ordinal)
    variation = _variation(seed)
    velocity = min(1.0, max(0.0, event.velocity / 127.0))
    hold = max(0.001, float(event.duration) * 60.0 / _CURRENT_TEMPO)
    release = 0.310
    count = max(1, int((hold + release) * sample_rate))
    t = np.arange(count, dtype=np.float64) / sample_rate
    f = _midi_frequency(event.pitch)
    base_decay = max(0.34, min(1.65, hold * 0.88 + 0.30)) * variation.decay_scale

    rate = 0.23 * variation.rate_scale
    depth = 0.10 + 0.22 * state.motion_depth
    lfo = np.sin(2.0 * math.pi * rate * t + variation.phase)
    group_a_gain = 1.0 + depth * lfo
    group_b_gain = 1.0 - depth * lfo

    modes = (
        (1.000, 1.000, 1.00),
        (2.010, 0.290, 0.72),
        (3.970, 0.155, 0.49),
        (5.120, 0.090, 0.35),
        (7.080, 0.052, 0.24),
    )
    main = np.zeros(count, dtype=np.float64)
    for mode_index, (ratio, gain, decay_multiplier) in enumerate(modes):
        phase = variation.phase * (0.41 + 0.23 * mode_index)
        decay = np.exp(-t / max(0.025, base_decay * decay_multiplier))
        motion = group_a_gain if mode_index < 2 else group_b_gain
        main += gain * motion * decay * np.sin(2.0 * math.pi * f * ratio * t + phase)

    twin_f = f * (2.0 ** (3.7 / 1200.0))
    twin = 0.115 * np.exp(-t / max(0.025, base_decay)) * np.sin(
        2.0 * math.pi * twin_f * t + variation.phase * 1.31
    )

    envelope = _adsr(
        t,
        hold,
        0.018 * variation.attack_scale,
        0.145,
        0.66,
        release,
    )
    slow_drift = 1.0 + 0.035 * np.sin(2.0 * math.pi * 0.071 * t + variation.phase * 0.73)
    main *= envelope * slow_drift * velocity
    twin *= envelope * slow_drift * velocity

    transient_count = min(count, max(1, int(0.038 * sample_rate)))
    transient = np.zeros(count, dtype=np.float64)
    transient_noise = _smooth(_noise(transient_count, seed ^ 0xA0761D6478BD642F), 5)
    transient_shape = np.exp(-np.arange(transient_count, dtype=np.float64) / (0.0105 * sample_rate))
    transient[:transient_count] = (
        transient_noise
        * transient_shape
        * 0.105
        * velocity
        * (0.74 + 0.42 * state.brightness)
        * variation.transient_scale
    )

    air = _smooth(_noise(count, seed ^ 0xE7037ED1A0B428DB), 9)
    air *= envelope * velocity * (0.018 + 0.022 * state.brightness)
    main += transient + air

    main_l, main_r = _pan(main, -0.16 * state.stereo_width + variation.pan_offset)
    twin_l, twin_r = _pan(twin, 0.13 * state.stereo_width + variation.pan_offset)
    left = main_l + twin_l
    right = main_r + twin_r
    room = ((main + twin) * 0.5) * (0.27 * state.room_send)
    return left, right, room


def _bass_event(
    event: Any,
    ordinal: int,
    state: SharedState,
    sample_rate: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    seed = _event_seed("BASS", event, ordinal)
    variation = _variation(seed)
    velocity = min(1.0, max(0.0, event.velocity / 127.0))
    hold = max(0.001, float(event.duration) * 60.0 / _CURRENT_TEMPO)
    release = 0.360
    count = max(1, int((hold + release) * sample_rate))
    t = np.arange(count, dtype=np.float64) / sample_rate
    f = _midi_frequency(event.pitch)

    rate = 0.117 * variation.rate_scale
    depth = 0.055 + 0.17 * state.motion_depth
    motion = np.sin(2.0 * math.pi * rate * t + variation.phase)
    lower_weight = 1.0 + depth * motion
    upper_weight = 1.0 - depth * motion
    brightness_mult = 0.62 + 0.58 * state.brightness

    lower = (
        0.19 * np.sin(2.0 * math.pi * f * 0.5 * t + variation.phase * 0.61)
        + 1.00 * np.sin(2.0 * math.pi * f * t + variation.phase)
    ) * lower_weight
    upper = (
        0.18 * np.sin(2.0 * math.pi * f * 2.0 * t + variation.phase * 1.17)
        + 0.070 * np.sin(2.0 * math.pi * f * 3.0 * t + variation.phase * 1.39)
        + 0.025 * np.sin(2.0 * math.pi * f * 5.0 * t + variation.phase * 1.73)
    ) * upper_weight * brightness_mult
    body = np.tanh((lower + upper) * 1.55)

    envelope = _adsr(
        t,
        hold,
        0.011 * variation.attack_scale,
        0.190,
        0.76,
        release,
    )
    body *= envelope * velocity

    transient_count = min(count, max(1, int(0.026 * sample_rate)))
    transient = np.zeros(count, dtype=np.float64)
    noise = _smooth(_noise(transient_count, seed ^ 0x8EBC6AF09C88C6E3), 13)
    transient_shape = np.exp(-np.arange(transient_count, dtype=np.float64) / (0.0075 * sample_rate))
    transient[:transient_count] = noise * transient_shape * 0.085 * velocity * variation.transient_scale
    body += transient

    pan = -0.025 + max(-0.025, min(0.025, variation.pan_offset * 0.70))
    left, right = _pan(body, pan)
    room = body * (0.10 * state.room_send)
    return left, right, room


def _rhythm_event(
    event: Any,
    ordinal: int,
    state: SharedState,
    sample_rate: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    seed = _event_seed("RHYTHM", event, ordinal)
    variation = _variation(seed)
    velocity = min(1.0, max(0.0, event.velocity / 127.0))
    f = _midi_frequency(event.pitch)
    ratios = (1.000, 1.470, 2.230, 3.650, 5.180)
    gains = (1.00, 0.42, 0.24, 0.13, 0.065)
    decays = (0.22, 0.17, 0.12, 0.085, 0.060)
    decay_mult = (0.82 + 0.34 * velocity) * variation.decay_scale
    duration = max(float(event.duration) * 60.0 / _CURRENT_TEMPO, max(decays) * 5.0 * decay_mult)
    count = max(1, int(duration * sample_rate))
    t = np.arange(count, dtype=np.float64) / sample_rate
    upper_mult = 0.68 + 0.55 * state.brightness

    body = np.zeros(count, dtype=np.float64)
    for index, (ratio, gain, decay) in enumerate(zip(ratios, gains, decays, strict=True)):
        scaled_gain = gain if index < 2 else gain * upper_mult
        phase = variation.phase * (0.49 + index * 0.31)
        body += (
            scaled_gain
            * np.exp(-t / max(0.010, decay * decay_mult))
            * np.sin(2.0 * math.pi * f * ratio * t + phase)
        )

    transient_count = min(count, max(1, int(0.014 * sample_rate)))
    noise = np.zeros(count, dtype=np.float64)
    burst = _noise(transient_count, seed ^ 0x589965CC75374CC3)
    burst *= np.exp(-np.arange(transient_count, dtype=np.float64) / (0.0038 * sample_rate))
    noise[:transient_count] = burst * 0.22 * variation.transient_scale

    body = np.tanh((body + noise) * 1.32) * velocity
    pan = 0.22 * state.stereo_width + variation.pan_offset
    left, right = _pan(body, pan)
    room = body * (0.22 * state.room_send)
    return left, right, room


def _room_ir(sample_rate: int) -> tuple[np.ndarray, np.ndarray]:
    count = max(1, int(0.92 * sample_rate))
    left = np.zeros(count, dtype=np.float64)
    right = np.zeros(count, dtype=np.float64)
    for seconds, gain in ((0.023, 0.24), (0.041, 0.17), (0.067, 0.115), (0.089, 0.082)):
        index = min(count - 1, int(seconds * sample_rate))
        left[index] += gain
    for seconds, gain in ((0.029, 0.22), (0.047, 0.16), (0.071, 0.108), (0.097, 0.077)):
        index = min(count - 1, int(seconds * sample_rate))
        right[index] += gain

    late_start = min(count - 1, int(0.100 * sample_rate))
    late_count = count - late_start
    late_t = np.arange(late_count, dtype=np.float64) / sample_rate
    decay = np.exp(-late_t / 0.245)
    late_left = _smooth(_noise(late_count, 0x243F6A8885A308D3), 17) * decay
    late_right = _smooth(_noise(late_count, 0x13198A2E03707344), 17) * decay
    left[late_start:] += late_left
    right[late_start:] += late_right
    return _smooth(left, 11), _smooth(right, 11)


def _fft_convolve(signal: np.ndarray, impulse: np.ndarray) -> np.ndarray:
    out_len = signal.size + impulse.size - 1
    nfft = 1 << max(0, (out_len - 1).bit_length())
    spectrum = np.fft.rfft(signal, n=nfft)
    impulse_spectrum = np.fft.rfft(impulse, n=nfft)
    return np.fft.irfft(spectrum * impulse_spectrum, n=nfft)[:out_len]


def _append_at(destination: np.ndarray, start: int, signal: np.ndarray, gain: float = 1.0) -> None:
    if start >= destination.size or signal.size == 0:
        return
    end = min(destination.size, start + signal.size)
    destination[start:end] += signal[: end - start] * gain


def _write_pcm16(path: Path, left: np.ndarray, right: np.ndarray, sample_rate: int) -> None:
    if left.shape != right.shape:
        raise ValueError("stereo channel length mismatch")
    interleaved = np.empty(left.size * 2, dtype="<i2")
    interleaved[0::2] = np.round(np.clip(left, -1.0, 1.0) * 32767.0).astype("<i2")
    interleaved[1::2] = np.round(np.clip(right, -1.0, 1.0) * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(interleaved.tobytes())


_CURRENT_TEMPO = 58.0


def render_synth_v2_wav(
    result: InstrumentResult,
    path: str | Path,
    *,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
) -> Path:
    """Render one IPM result through frozen Evolving Resonant Field v2."""

    if sample_rate < 8_000:
        raise ValueError("sample_rate must be >= 8000")
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    global _CURRENT_TEMPO
    _CURRENT_TEMPO = float(result.config.tempo_bpm)
    seconds_per_beat = 60.0 / _CURRENT_TEMPO
    total_beats = float(result.config.bars * result.config.beats_per_bar)
    written_seconds = total_beats * seconds_per_beat
    base_tail = 0.45
    base_count = max(1, int((written_seconds + base_tail) * sample_rate))
    dry_left = np.zeros(base_count, dtype=np.float64)
    dry_right = np.zeros(base_count, dtype=np.float64)
    room_send = np.zeros(base_count, dtype=np.float64)

    before_events = tuple(
        (voice.name, tuple((event.onset, event.duration, event.pitch, event.velocity) for event in voice.events))
        for voice in result.voices
    )

    for voice in result.voices:
        if voice.name not in _LANE_ID:
            continue
        dry_gain = _LANE_DRY_GAIN[voice.name]
        for ordinal, event in enumerate(voice.events):
            onset_beats = float(event.onset)
            state = _shared_state(onset_beats, total_beats, result.config.beats_per_bar)
            start = max(0, int(onset_beats * seconds_per_beat * sample_rate))
            if voice.name == "TUNE":
                left, right, room = _tune_event(event, ordinal, state, sample_rate)
            elif voice.name == "BASS":
                left, right, room = _bass_event(event, ordinal, state, sample_rate)
            else:
                left, right, room = _rhythm_event(event, ordinal, state, sample_rate)
            _append_at(dry_left, start, left, dry_gain)
            _append_at(dry_right, start, right, dry_gain)
            _append_at(room_send, start, room, dry_gain)

    after_events = tuple(
        (voice.name, tuple((event.onset, event.duration, event.pitch, event.velocity) for event in voice.events))
        for voice in result.voices
    )
    if before_events != after_events:
        raise RuntimeError("synth v2 mutated written note events")

    ir_left, ir_right = _room_ir(sample_rate)
    wet_left = _fft_convolve(room_send, ir_left)
    wet_right = _fft_convolve(room_send, ir_right)
    final_count = max(dry_left.size, wet_left.size)
    left = np.zeros(final_count, dtype=np.float64)
    right = np.zeros(final_count, dtype=np.float64)
    left[: dry_left.size] = dry_left
    right[: dry_right.size] = dry_right
    left[: wet_left.size] += wet_left * _ROOM_RETURN_GAIN
    right[: wet_right.size] += wet_right * _ROOM_RETURN_GAIN

    if not np.all(np.isfinite(left)) or not np.all(np.isfinite(right)):
        raise RuntimeError("synth v2 generated non-finite audio")

    left -= float(np.mean(left))
    right -= float(np.mean(right))
    left = np.tanh(left * 1.18)
    right = np.tanh(right * 1.18)
    peak = max(float(np.max(np.abs(left))), float(np.max(np.abs(right))), 0.0)
    if peak > 0.94:
        scale = 0.94 / peak
        left *= scale
        right *= scale

    _write_pcm16(destination, left, right, sample_rate)
    return destination

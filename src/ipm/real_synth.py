"""Patch-driven polyphonic synthesizer for IPM Machine.

Unlike the historical fixed renderers, this module is a reusable synthesis
engine. Patches are ordinary serialisable data. The engine owns the DSP;
changing a patch does not require changing synthesis code or IPM composition.
"""

from __future__ import annotations

import json
import math
import wave
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from .engine import InstrumentResult

ENGINE_VERSION = "3.0"
DEFAULT_SAMPLE_RATE = 44_100
_MASK64 = (1 << 64) - 1

_WAVEFORMS = {"sine", "triangle", "saw", "square", "pulse", "noise"}
_LFO_WAVEFORMS = {"sine", "triangle", "saw", "square"}
_FILTER_MODES = {"lowpass", "highpass", "bandpass", "notch"}
_MOD_SOURCES = {"velocity", "keytrack", "amp_env", "filter_env", "lfo1", "lfo2"}
_MOD_DESTINATIONS = {"pitch", "cutoff", "amplitude", "pan", "osc_mix"}
_LANES = {"TUNE", "BASS", "RHYTHM"}


@dataclass(frozen=True, slots=True)
class EnvelopeSpec:
    attack: float = 0.01
    decay: float = 0.20
    sustain: float = 0.75
    release: float = 0.30

    def __post_init__(self) -> None:
        if min(self.attack, self.decay, self.release) < 0.0:
            raise ValueError("envelope times must be non-negative")
        if max(self.attack, self.decay, self.release) > 20.0:
            raise ValueError("envelope times must be <= 20 seconds")
        if not 0.0 <= self.sustain <= 1.0:
            raise ValueError("envelope sustain must be in 0..1")


@dataclass(frozen=True, slots=True)
class OscillatorSpec:
    waveform: str = "saw"
    octave: int = 0
    semitone: int = 0
    cents: float = 0.0
    gain: float = 0.7
    pulse_width: float = 0.5
    phase: float = 0.0

    def __post_init__(self) -> None:
        if self.waveform not in _WAVEFORMS:
            raise ValueError(f"unsupported oscillator waveform: {self.waveform}")
        if not -4 <= self.octave <= 4:
            raise ValueError("oscillator octave must be in -4..4")
        if not -24 <= self.semitone <= 24:
            raise ValueError("oscillator semitone must be in -24..24")
        if not -100.0 <= self.cents <= 100.0:
            raise ValueError("oscillator cents must be in -100..100")
        if not 0.0 <= self.gain <= 2.0:
            raise ValueError("oscillator gain must be in 0..2")
        if not 0.05 <= self.pulse_width <= 0.95:
            raise ValueError("pulse width must be in 0.05..0.95")
        if not 0.0 <= self.phase < 1.0:
            raise ValueError("oscillator phase must be in 0..1")


@dataclass(frozen=True, slots=True)
class FilterSpec:
    mode: str = "lowpass"
    cutoff_hz: float = 4_000.0
    resonance_q: float = 0.8
    key_tracking: float = 0.35
    env_amount_octaves: float = 1.25
    drive: float = 1.0

    def __post_init__(self) -> None:
        if self.mode not in _FILTER_MODES:
            raise ValueError(f"unsupported filter mode: {self.mode}")
        if not 20.0 <= self.cutoff_hz <= 20_000.0:
            raise ValueError("filter cutoff must be in 20..20000 Hz")
        if not 0.1 <= self.resonance_q <= 20.0:
            raise ValueError("filter resonance Q must be in 0.1..20")
        if not 0.0 <= self.key_tracking <= 2.0:
            raise ValueError("filter key tracking must be in 0..2")
        if not -8.0 <= self.env_amount_octaves <= 8.0:
            raise ValueError("filter envelope amount must be in -8..8 octaves")
        if not 0.0 <= self.drive <= 8.0:
            raise ValueError("filter drive must be in 0..8")


@dataclass(frozen=True, slots=True)
class LFOSpec:
    waveform: str = "sine"
    rate_hz: float = 0.25
    phase: float = 0.0
    bipolar: bool = True

    def __post_init__(self) -> None:
        if self.waveform not in _LFO_WAVEFORMS:
            raise ValueError(f"unsupported LFO waveform: {self.waveform}")
        if not 0.0 <= self.rate_hz <= 50.0:
            raise ValueError("LFO rate must be in 0..50 Hz")
        if not 0.0 <= self.phase < 1.0:
            raise ValueError("LFO phase must be in 0..1")


@dataclass(frozen=True, slots=True)
class ModRoute:
    source: str
    destination: str
    amount: float

    def __post_init__(self) -> None:
        if self.source not in _MOD_SOURCES:
            raise ValueError(f"unsupported modulation source: {self.source}")
        if self.destination not in _MOD_DESTINATIONS:
            raise ValueError(f"unsupported modulation destination: {self.destination}")
        if not -48.0 <= self.amount <= 48.0:
            raise ValueError("modulation amount must be in -48..48")


@dataclass(frozen=True, slots=True)
class EffectSends:
    chorus: float = 0.0
    delay: float = 0.0
    reverb: float = 0.0

    def __post_init__(self) -> None:
        for name in ("chorus", "delay", "reverb"):
            if not 0.0 <= getattr(self, name) <= 1.0:
                raise ValueError(f"{name} send must be in 0..1")


@dataclass(frozen=True, slots=True)
class SynthPatch:
    name: str
    version: int = 1
    oscillators: tuple[OscillatorSpec, ...] = field(
        default_factory=lambda: (OscillatorSpec(),)
    )
    amp_env: EnvelopeSpec = field(default_factory=EnvelopeSpec)
    filter_env: EnvelopeSpec = field(
        default_factory=lambda: EnvelopeSpec(attack=0.02, decay=0.35, sustain=0.25, release=0.40)
    )
    filter: FilterSpec = field(default_factory=FilterSpec)
    lfo1: LFOSpec = field(default_factory=LFOSpec)
    lfo2: LFOSpec = field(
        default_factory=lambda: LFOSpec(waveform="triangle", rate_hz=0.11, phase=0.25)
    )
    modulation: tuple[ModRoute, ...] = ()
    fm_amount: float = 0.0
    ring_amount: float = 0.0
    noise_level: float = 0.0
    unison_voices: int = 1
    unison_detune_cents: float = 0.0
    base_pan: float = 0.0
    stereo_width: float = 0.5
    sends: EffectSends = field(default_factory=EffectSends)

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("patch name must not be empty")
        if self.version <= 0:
            raise ValueError("patch version must be positive")
        if not 1 <= len(self.oscillators) <= 3:
            raise ValueError("patch must define 1..3 oscillators")
        if not 0.0 <= self.fm_amount <= 8.0:
            raise ValueError("FM amount must be in 0..8")
        if not 0.0 <= self.ring_amount <= 1.0:
            raise ValueError("ring amount must be in 0..1")
        if not 0.0 <= self.noise_level <= 1.0:
            raise ValueError("noise level must be in 0..1")
        if not 1 <= self.unison_voices <= 7:
            raise ValueError("unison voices must be in 1..7")
        if not 0.0 <= self.unison_detune_cents <= 50.0:
            raise ValueError("unison detune must be in 0..50 cents")
        if not -1.0 <= self.base_pan <= 1.0:
            raise ValueError("base pan must be in -1..1")
        if not 0.0 <= self.stereo_width <= 1.5:
            raise ValueError("stereo width must be in 0..1.5")


@dataclass(frozen=True, slots=True)
class PatchBank:
    patches: dict[str, SynthPatch]
    lane_map: dict[str, str]
    version: int = 1

    def __post_init__(self) -> None:
        if self.version <= 0:
            raise ValueError("patch-bank version must be positive")
        if not self.patches:
            raise ValueError("patch bank must contain at least one patch")
        missing_lanes = _LANES.difference(self.lane_map)
        if missing_lanes:
            raise ValueError(f"patch bank missing lane mappings: {sorted(missing_lanes)}")
        unknown_lanes = set(self.lane_map).difference(_LANES)
        if unknown_lanes:
            raise ValueError(f"unknown patch-bank lanes: {sorted(unknown_lanes)}")
        for lane, patch_name in self.lane_map.items():
            if patch_name not in self.patches:
                raise ValueError(f"lane {lane} references missing patch {patch_name!r}")

    def patch_for_lane(self, lane: str) -> SynthPatch:
        if lane not in self.lane_map:
            raise ValueError(f"no patch mapping for lane {lane}")
        return self.patches[self.lane_map[lane]]


def patch_to_dict(patch: SynthPatch) -> dict[str, Any]:
    return asdict(patch)


def patch_from_dict(data: dict[str, Any]) -> SynthPatch:
    return SynthPatch(
        name=str(data["name"]),
        version=int(data.get("version", 1)),
        oscillators=tuple(OscillatorSpec(**item) for item in data["oscillators"]),
        amp_env=EnvelopeSpec(**data["amp_env"]),
        filter_env=EnvelopeSpec(**data["filter_env"]),
        filter=FilterSpec(**data["filter"]),
        lfo1=LFOSpec(**data["lfo1"]),
        lfo2=LFOSpec(**data["lfo2"]),
        modulation=tuple(ModRoute(**item) for item in data.get("modulation", [])),
        fm_amount=float(data.get("fm_amount", 0.0)),
        ring_amount=float(data.get("ring_amount", 0.0)),
        noise_level=float(data.get("noise_level", 0.0)),
        unison_voices=int(data.get("unison_voices", 1)),
        unison_detune_cents=float(data.get("unison_detune_cents", 0.0)),
        base_pan=float(data.get("base_pan", 0.0)),
        stereo_width=float(data.get("stereo_width", 0.5)),
        sends=EffectSends(**data.get("sends", {})),
    )


def bank_to_dict(bank: PatchBank) -> dict[str, Any]:
    return {
        "version": bank.version,
        "patches": {name: patch_to_dict(patch) for name, patch in bank.patches.items()},
        "lane_map": dict(bank.lane_map),
    }


def bank_from_dict(data: dict[str, Any]) -> PatchBank:
    return PatchBank(
        version=int(data.get("version", 1)),
        patches={name: patch_from_dict(value) for name, value in data["patches"].items()},
        lane_map={str(k): str(v) for k, v in data["lane_map"].items()},
    )


def save_patch_bank(bank: PatchBank, path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(bank_to_dict(bank), indent=2) + "\n", encoding="utf-8")
    return destination


def load_patch_bank(path: str | Path) -> PatchBank:
    return bank_from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def _mix64(value: int) -> int:
    value = (value + 0x9E3779B97F4A7C15) & _MASK64
    value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & _MASK64
    value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & _MASK64
    return (value ^ (value >> 31)) & _MASK64


def _event_seed(lane: str, event: Any, ordinal: int) -> int:
    lane_id = {"TUNE": 1, "BASS": 2, "RHYTHM": 3}.get(lane, 7)
    value = lane_id
    for component in (
        int(event.pitch),
        int(event.onset.numerator),
        int(event.onset.denominator),
        int(event.duration.numerator),
        int(event.duration.denominator),
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


def _midi_frequency(pitch: int) -> float:
    return 440.0 * (2.0 ** ((pitch - 69) / 12.0))


def _poly_blep(phase: np.ndarray, dt: np.ndarray) -> np.ndarray:
    out = np.zeros_like(phase)
    safe_dt = np.maximum(dt, 1e-9)
    left = phase < safe_dt
    if np.any(left):
        x = phase[left] / safe_dt[left]
        out[left] = x + x - x * x - 1.0
    right = phase > 1.0 - safe_dt
    if np.any(right):
        x = (phase[right] - 1.0) / safe_dt[right]
        out[right] = x * x + x + x + 1.0
    return out


def _osc_wave(
    waveform: str,
    phase: np.ndarray,
    dt: np.ndarray,
    pulse_width: float,
    *,
    noise_seed: int,
) -> np.ndarray:
    phase = np.mod(phase, 1.0)
    if waveform == "sine":
        return np.sin(2.0 * math.pi * phase)
    if waveform == "triangle":
        return (2.0 / math.pi) * np.arcsin(np.sin(2.0 * math.pi * phase))
    if waveform == "noise":
        return _noise(phase.size, noise_seed)
    if waveform == "saw":
        return (2.0 * phase - 1.0) - _poly_blep(phase, dt)
    if waveform in {"square", "pulse"}:
        width = 0.5 if waveform == "square" else pulse_width
        out = np.where(phase < width, 1.0, -1.0)
        out += _poly_blep(phase, dt)
        shifted = np.mod(phase - width, 1.0)
        out -= _poly_blep(shifted, dt)
        return out
    raise ValueError(f"unsupported waveform: {waveform}")


def _lfo(spec: LFOSpec, t: np.ndarray) -> np.ndarray:
    phase = np.mod(spec.phase + t * spec.rate_hz, 1.0)
    if spec.waveform == "sine":
        value = np.sin(2.0 * math.pi * phase)
    elif spec.waveform == "triangle":
        value = (2.0 / math.pi) * np.arcsin(np.sin(2.0 * math.pi * phase))
    elif spec.waveform == "saw":
        value = 2.0 * phase - 1.0
    elif spec.waveform == "square":
        value = np.where(phase < 0.5, 1.0, -1.0)
    else:
        raise ValueError(f"unsupported LFO waveform: {spec.waveform}")
    return value if spec.bipolar else 0.5 * (value + 1.0)


def _envelope(spec: EnvelopeSpec, hold_seconds: float, sample_rate: int) -> np.ndarray:
    release = spec.release
    total = max(1.0 / sample_rate, hold_seconds + release)
    count = max(1, int(math.ceil(total * sample_rate)))
    t = np.arange(count, dtype=np.float64) / sample_rate
    env = np.zeros(count, dtype=np.float64)

    attack = max(spec.attack, 1.0 / sample_rate)
    decay = max(spec.decay, 1.0 / sample_rate)
    a_end = attack
    d_end = attack + decay

    before_release = t < hold_seconds
    attack_mask = before_release & (t < a_end)
    env[attack_mask] = t[attack_mask] / attack

    decay_mask = before_release & (t >= a_end) & (t < d_end)
    env[decay_mask] = 1.0 - (1.0 - spec.sustain) * ((t[decay_mask] - a_end) / decay)

    sustain_mask = before_release & (t >= d_end)
    env[sustain_mask] = spec.sustain

    if hold_seconds < a_end:
        release_start = hold_seconds / attack
    elif hold_seconds < d_end:
        release_start = 1.0 - (1.0 - spec.sustain) * ((hold_seconds - a_end) / decay)
    else:
        release_start = spec.sustain

    release_mask = ~before_release
    if spec.release <= 0.0:
        env[release_mask] = 0.0
    else:
        x = (t[release_mask] - hold_seconds) / spec.release
        env[release_mask] = release_start * np.maximum(0.0, 1.0 - x)
    return np.maximum(0.0, env)


def _source_values(
    patch: SynthPatch,
    event: Any,
    amp_env: np.ndarray,
    filter_env: np.ndarray,
    t: np.ndarray,
) -> dict[str, np.ndarray]:
    count = amp_env.size
    velocity = np.full(count, min(1.0, max(0.0, event.velocity / 127.0)), dtype=np.float64)
    keytrack_scalar = min(1.0, max(-1.0, (event.pitch - 60) / 24.0))
    return {
        "velocity": velocity,
        "keytrack": np.full(count, keytrack_scalar, dtype=np.float64),
        "amp_env": amp_env,
        "filter_env": filter_env,
        "lfo1": _lfo(patch.lfo1, t),
        "lfo2": _lfo(patch.lfo2, t),
    }


def _modulations(patch: SynthPatch, sources: dict[str, np.ndarray], count: int) -> dict[str, np.ndarray]:
    result = {
        destination: np.zeros(count, dtype=np.float64)
        for destination in _MOD_DESTINATIONS
    }
    for route in patch.modulation:
        result[route.destination] += sources[route.source] * route.amount
    return result


def _unison_offsets(voices: int, spread_cents: float) -> np.ndarray:
    if voices <= 1:
        return np.array((0.0,), dtype=np.float64)
    return np.linspace(-spread_cents, spread_cents, voices, dtype=np.float64)


def _render_oscillator(
    spec: OscillatorSpec,
    base_frequency: float,
    pitch_mod_semitones: np.ndarray,
    detune_cents: float,
    sample_rate: int,
    *,
    phase_mod: np.ndarray | None,
    noise_seed: int,
) -> np.ndarray:
    tuning = 12 * spec.octave + spec.semitone + (spec.cents + detune_cents) / 100.0
    frequency = base_frequency * np.power(2.0, (pitch_mod_semitones + tuning) / 12.0)
    frequency = np.minimum(frequency, sample_rate * 0.45)
    dt = np.clip(frequency / sample_rate, 1e-9, 0.45)
    phase = np.cumsum(dt) + spec.phase
    if phase_mod is not None:
        phase = phase + phase_mod
    return _osc_wave(spec.waveform, phase, dt, spec.pulse_width, noise_seed=noise_seed)


def _svf_filter(
    signal: np.ndarray,
    cutoff_hz: np.ndarray,
    mode: str,
    q: float,
    sample_rate: int,
) -> np.ndarray:
    if signal.size == 0:
        return signal
    out = np.empty_like(signal)
    ic1eq = 0.0
    ic2eq = 0.0
    k = 1.0 / max(0.1, q)
    nyquist_guard = sample_rate * 0.45
    for index, sample in enumerate(signal):
        cutoff = min(nyquist_guard, max(20.0, float(cutoff_hz[index])))
        g = math.tan(math.pi * cutoff / sample_rate)
        a1 = 1.0 / (1.0 + g * (g + k))
        a2 = g * a1
        a3 = g * a2
        v3 = float(sample) - ic2eq
        v1 = a1 * ic1eq + a2 * v3
        v2 = ic2eq + a2 * ic1eq + a3 * v3
        ic1eq = 2.0 * v1 - ic1eq
        ic2eq = 2.0 * v2 - ic2eq
        low = v2
        band = v1
        high = float(sample) - k * v1 - v2
        if mode == "lowpass":
            value = low
        elif mode == "highpass":
            value = high
        elif mode == "bandpass":
            value = band
        elif mode == "notch":
            value = high + low
        else:
            raise ValueError(f"unsupported filter mode: {mode}")
        out[index] = value
    return out


def _pan_arrays(signal: np.ndarray, pan: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    clipped = np.clip(pan, -1.0, 1.0)
    angle = (clipped + 1.0) * math.pi / 4.0
    return signal * np.cos(angle), signal * np.sin(angle)


def _render_voice_event(
    patch: SynthPatch,
    lane: str,
    event: Any,
    ordinal: int,
    tempo_bpm: float,
    sample_rate: int,
) -> tuple[np.ndarray, np.ndarray]:
    seconds_per_beat = 60.0 / tempo_bpm
    hold = max(1.0 / sample_rate, float(event.duration) * seconds_per_beat)
    amp_env = _envelope(patch.amp_env, hold, sample_rate)
    filter_env = _envelope(patch.filter_env, hold, sample_rate)
    count = max(amp_env.size, filter_env.size)
    if amp_env.size != count:
        amp_env = np.pad(amp_env, (0, count - amp_env.size))
    if filter_env.size != count:
        filter_env = np.pad(filter_env, (0, count - filter_env.size))
    t = np.arange(count, dtype=np.float64) / sample_rate
    sources = _source_values(patch, event, amp_env, filter_env, t)
    mods = _modulations(patch, sources, count)

    velocity_gain = 0.25 + 0.75 * sources["velocity"]
    amp_mod_gain = np.power(10.0, np.clip(mods["amplitude"], -48.0, 24.0) / 20.0)
    base_frequency = _midi_frequency(event.pitch)
    seed = _event_seed(lane, event, ordinal)

    left = np.zeros(count, dtype=np.float64)
    right = np.zeros(count, dtype=np.float64)
    offsets = _unison_offsets(patch.unison_voices, patch.unison_detune_cents)
    normalise_unison = 1.0 / math.sqrt(len(offsets))

    for unison_index, detune in enumerate(offsets):
        oscillator_signals: list[np.ndarray] = []
        fm_source: np.ndarray | None = None
        if len(patch.oscillators) >= 2 and patch.fm_amount > 0.0:
            fm_spec = patch.oscillators[1]
            fm_source = _render_oscillator(
                fm_spec,
                base_frequency,
                mods["pitch"],
                float(detune),
                sample_rate,
                phase_mod=None,
                noise_seed=seed ^ 0xA24BAED4963EE407 ^ unison_index,
            )
            fm_source = fm_source * (0.075 * patch.fm_amount)

        for osc_index, spec in enumerate(patch.oscillators):
            phase_mod = fm_source if osc_index == 0 else None
            signal = _render_oscillator(
                spec,
                base_frequency,
                mods["pitch"],
                float(detune),
                sample_rate,
                phase_mod=phase_mod,
                noise_seed=seed ^ (0x9FB21C651E98DF25 * (osc_index + 1)) ^ unison_index,
            )
            mix_mod = np.clip(mods["osc_mix"], -1.0, 1.0)
            if osc_index == 0:
                gain_mod = 1.0 + 0.45 * mix_mod
            elif osc_index == 1:
                gain_mod = 1.0 - 0.45 * mix_mod
            else:
                gain_mod = 1.0
            oscillator_signals.append(signal * spec.gain * gain_mod)

        combined = np.zeros(count, dtype=np.float64)
        for signal in oscillator_signals:
            combined += signal
        if len(oscillator_signals) >= 2 and patch.ring_amount > 0.0:
            ring = oscillator_signals[0] * oscillator_signals[1]
            combined = (1.0 - patch.ring_amount) * combined + patch.ring_amount * ring
        if patch.noise_level > 0.0:
            combined += _noise(count, seed ^ 0xD6E8FEB86659FD93 ^ unison_index) * patch.noise_level

        unison_position = 0.0 if len(offsets) <= 1 else (-1.0 + 2.0 * unison_index / (len(offsets) - 1))
        pan = np.clip(
            patch.base_pan
            + mods["pan"]
            + unison_position * 0.38 * patch.stereo_width,
            -1.0,
            1.0,
        )
        l, r = _pan_arrays(combined, pan)
        left += l * normalise_unison
        right += r * normalise_unison

    key_octaves = ((event.pitch - 60) / 12.0) * patch.filter.key_tracking
    cutoff_octaves = (
        key_octaves
        + filter_env * patch.filter.env_amount_octaves
        + mods["cutoff"]
    )
    cutoff = patch.filter.cutoff_hz * np.power(2.0, cutoff_octaves)
    drive = patch.filter.drive
    if drive > 0.0:
        left = np.tanh(left * drive)
        right = np.tanh(right * drive)

    left = _svf_filter(left, cutoff, patch.filter.mode, patch.filter.resonance_q, sample_rate)
    right = _svf_filter(right, cutoff, patch.filter.mode, patch.filter.resonance_q, sample_rate)
    final_gain = amp_env * velocity_gain * amp_mod_gain
    return left * final_gain, right * final_gain


def _append(destination: np.ndarray, start: int, signal: np.ndarray, gain: float = 1.0) -> None:
    if start >= destination.size or signal.size == 0:
        return
    end = min(destination.size, start + signal.size)
    destination[start:end] += signal[: end - start] * gain


def _chorus(left: np.ndarray, right: np.ndarray, sample_rate: int) -> tuple[np.ndarray, np.ndarray]:
    count = left.size
    if count == 0:
        return left, right
    indices = np.arange(count, dtype=np.float64)
    t = indices / sample_rate
    base = 0.014 * sample_rate
    depth = 0.0045 * sample_rate
    delay_l = base + depth * np.sin(2.0 * math.pi * 0.23 * t)
    delay_r = base + depth * np.sin(2.0 * math.pi * 0.19 * t + math.pi / 2.0)

    def delayed(signal: np.ndarray, delays: np.ndarray) -> np.ndarray:
        source_pos = indices - delays
        return np.interp(source_pos, indices, signal, left=0.0, right=0.0)

    wet_l = delayed(right, delay_l)
    wet_r = delayed(left, delay_r)
    return wet_l, wet_r


def _stereo_delay(left: np.ndarray, right: np.ndarray, sample_rate: int) -> tuple[np.ndarray, np.ndarray]:
    wet_l = np.zeros_like(left)
    wet_r = np.zeros_like(right)
    for repeat in range(1, 7):
        gain = 0.42 * (0.38 ** (repeat - 1))
        delay_l = int(0.285 * sample_rate * repeat)
        delay_r = int(0.425 * sample_rate * repeat)
        if delay_l < left.size:
            wet_l[delay_l:] += right[: left.size - delay_l] * gain
        if delay_r < right.size:
            wet_r[delay_r:] += left[: right.size - delay_r] * gain
    return wet_l, wet_r


def _reverb_ir(sample_rate: int) -> tuple[np.ndarray, np.ndarray]:
    count = max(1, int(1.65 * sample_rate))
    t = np.arange(count, dtype=np.float64) / sample_rate
    decay = np.exp(-t / 0.48)
    left = _noise(count, 0x243F6A8885A308D3) * decay
    right = _noise(count, 0x13198A2E03707344) * decay
    smooth = max(3, int(sample_rate * 0.0007) | 1)
    kernel = np.ones(smooth, dtype=np.float64) / smooth
    left = np.convolve(left, kernel, mode="same")
    right = np.convolve(right, kernel, mode="same")
    for seconds, gain in ((0.017, 0.42), (0.031, 0.29), (0.047, 0.21), (0.071, 0.15)):
        index = min(count - 1, int(seconds * sample_rate))
        left[index] += gain
    for seconds, gain in ((0.021, 0.39), (0.037, 0.28), (0.053, 0.19), (0.079, 0.14)):
        index = min(count - 1, int(seconds * sample_rate))
        right[index] += gain
    peak = max(float(np.max(np.abs(left))), float(np.max(np.abs(right))), 1e-9)
    return left / peak, right / peak


def _fft_convolve(signal: np.ndarray, impulse: np.ndarray) -> np.ndarray:
    out_len = signal.size + impulse.size - 1
    if out_len <= 0:
        return np.zeros(0, dtype=np.float64)
    nfft = 1 << max(0, (out_len - 1).bit_length())
    return np.fft.irfft(
        np.fft.rfft(signal, n=nfft) * np.fft.rfft(impulse, n=nfft),
        n=nfft,
    )[:out_len]


def _event_ledger(result: InstrumentResult) -> tuple[Any, ...]:
    return tuple(
        (
            voice.name,
            tuple(
                (event.onset, event.duration, event.pitch, event.velocity)
                for event in voice.events
            ),
        )
        for voice in result.voices
    )


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


class RealSynthEngine:
    """General patch-driven offline polyphonic synth engine."""

    def __init__(self, *, sample_rate: int = DEFAULT_SAMPLE_RATE) -> None:
        if sample_rate < 8_000:
            raise ValueError("sample_rate must be >= 8000")
        self.sample_rate = sample_rate

    def render(
        self,
        result: InstrumentResult,
        path: str | Path,
        *,
        bank: PatchBank,
    ) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        before = _event_ledger(result)

        seconds_per_beat = 60.0 / float(result.config.tempo_bpm)
        total_beats = float(result.config.bars * result.config.beats_per_bar)
        written_seconds = total_beats * seconds_per_beat
        tail_seconds = 2.0
        base_count = max(1, int(math.ceil((written_seconds + tail_seconds) * self.sample_rate)))

        dry_l = np.zeros(base_count, dtype=np.float64)
        dry_r = np.zeros(base_count, dtype=np.float64)
        chorus_l = np.zeros(base_count, dtype=np.float64)
        chorus_r = np.zeros(base_count, dtype=np.float64)
        delay_l = np.zeros(base_count, dtype=np.float64)
        delay_r = np.zeros(base_count, dtype=np.float64)
        reverb_l = np.zeros(base_count, dtype=np.float64)
        reverb_r = np.zeros(base_count, dtype=np.float64)

        for voice in result.voices:
            if voice.name not in _LANES:
                continue
            patch = bank.patch_for_lane(voice.name)
            for ordinal, event in enumerate(voice.events):
                left, right = _render_voice_event(
                    patch,
                    voice.name,
                    event,
                    ordinal,
                    float(result.config.tempo_bpm),
                    self.sample_rate,
                )
                start = max(0, int(float(event.onset) * seconds_per_beat * self.sample_rate))
                _append(dry_l, start, left)
                _append(dry_r, start, right)
                if patch.sends.chorus > 0.0:
                    _append(chorus_l, start, left, patch.sends.chorus)
                    _append(chorus_r, start, right, patch.sends.chorus)
                if patch.sends.delay > 0.0:
                    _append(delay_l, start, left, patch.sends.delay)
                    _append(delay_r, start, right, patch.sends.delay)
                if patch.sends.reverb > 0.0:
                    _append(reverb_l, start, left, patch.sends.reverb)
                    _append(reverb_r, start, right, patch.sends.reverb)

        after = _event_ledger(result)
        if before != after:
            raise RuntimeError("real synth engine mutated IPM note events")

        wet_ch_l, wet_ch_r = _chorus(chorus_l, chorus_r, self.sample_rate)
        wet_del_l, wet_del_r = _stereo_delay(delay_l, delay_r, self.sample_rate)
        ir_l, ir_r = _reverb_ir(self.sample_rate)
        rev_l = _fft_convolve(0.5 * (reverb_l + reverb_r), ir_l)
        rev_r = _fft_convolve(0.5 * (reverb_l + reverb_r), ir_r)

        final_count = max(base_count, rev_l.size, rev_r.size)
        left = np.zeros(final_count, dtype=np.float64)
        right = np.zeros(final_count, dtype=np.float64)
        left[:base_count] = dry_l + 0.42 * wet_ch_l + 0.78 * wet_del_l
        right[:base_count] = dry_r + 0.42 * wet_ch_r + 0.78 * wet_del_r
        left[: rev_l.size] += 0.34 * rev_l
        right[: rev_r.size] += 0.34 * rev_r

        if not np.all(np.isfinite(left)) or not np.all(np.isfinite(right)):
            raise RuntimeError("real synth engine generated non-finite audio")
        left -= float(np.mean(left))
        right -= float(np.mean(right))
        left = np.tanh(left * 1.08)
        right = np.tanh(right * 1.08)
        peak = max(float(np.max(np.abs(left))), float(np.max(np.abs(right))), 0.0)
        if peak > 0.94:
            scale = 0.94 / peak
            left *= scale
            right *= scale

        _write_pcm16(destination, left, right, self.sample_rate)
        return destination


def render_real_synth_wav(
    result: InstrumentResult,
    path: str | Path,
    *,
    bank: PatchBank,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
) -> Path:
    return RealSynthEngine(sample_rate=sample_rate).render(result, path, bank=bank)


# Demonstration patches. These are data examples for one engine, not bespoke DSP paths.
CRYSTAL_MOTION = SynthPatch(
    name="crystal-motion",
    oscillators=(
        OscillatorSpec(waveform="saw", gain=0.48, cents=-3.0),
        OscillatorSpec(waveform="triangle", gain=0.38, octave=1, cents=4.0),
    ),
    amp_env=EnvelopeSpec(attack=0.018, decay=0.24, sustain=0.62, release=0.48),
    filter_env=EnvelopeSpec(attack=0.035, decay=0.55, sustain=0.18, release=0.62),
    filter=FilterSpec(mode="lowpass", cutoff_hz=2_900.0, resonance_q=1.05, key_tracking=0.45, env_amount_octaves=1.7, drive=1.12),
    lfo1=LFOSpec(waveform="sine", rate_hz=0.21, phase=0.0),
    lfo2=LFOSpec(waveform="triangle", rate_hz=0.073, phase=0.31),
    modulation=(
        ModRoute("lfo1", "cutoff", 0.42),
        ModRoute("lfo2", "pan", 0.22),
        ModRoute("velocity", "cutoff", 0.55),
        ModRoute("filter_env", "osc_mix", 0.24),
    ),
    fm_amount=0.28,
    noise_level=0.025,
    unison_voices=3,
    unison_detune_cents=7.5,
    base_pan=-0.10,
    stereo_width=0.90,
    sends=EffectSends(chorus=0.28, delay=0.14, reverb=0.34),
)

WARM_POLY = SynthPatch(
    name="warm-poly",
    oscillators=(
        OscillatorSpec(waveform="saw", gain=0.44, cents=-8.0),
        OscillatorSpec(waveform="pulse", gain=0.38, cents=7.0, pulse_width=0.42),
        OscillatorSpec(waveform="triangle", gain=0.17, octave=-1),
    ),
    amp_env=EnvelopeSpec(attack=0.055, decay=0.34, sustain=0.70, release=0.72),
    filter_env=EnvelopeSpec(attack=0.12, decay=0.80, sustain=0.34, release=0.85),
    filter=FilterSpec(mode="lowpass", cutoff_hz=1_650.0, resonance_q=0.72, key_tracking=0.28, env_amount_octaves=1.35, drive=1.35),
    lfo1=LFOSpec(waveform="triangle", rate_hz=0.16, phase=0.13),
    lfo2=LFOSpec(waveform="sine", rate_hz=0.048, phase=0.44),
    modulation=(
        ModRoute("lfo1", "pitch", 0.055),
        ModRoute("lfo2", "cutoff", 0.28),
        ModRoute("velocity", "amplitude", 2.4),
        ModRoute("keytrack", "pan", 0.12),
    ),
    unison_voices=5,
    unison_detune_cents=11.0,
    stereo_width=1.0,
    sends=EffectSends(chorus=0.38, delay=0.08, reverb=0.29),
)

FM_GLASS = SynthPatch(
    name="fm-glass",
    oscillators=(
        OscillatorSpec(waveform="sine", gain=0.75),
        OscillatorSpec(waveform="sine", gain=0.30, octave=2, semitone=7),
    ),
    amp_env=EnvelopeSpec(attack=0.006, decay=0.72, sustain=0.24, release=1.05),
    filter_env=EnvelopeSpec(attack=0.004, decay=0.46, sustain=0.08, release=0.70),
    filter=FilterSpec(mode="bandpass", cutoff_hz=4_800.0, resonance_q=1.65, key_tracking=0.68, env_amount_octaves=0.75, drive=0.92),
    lfo1=LFOSpec(waveform="sine", rate_hz=0.33, phase=0.18),
    lfo2=LFOSpec(waveform="sine", rate_hz=0.061, phase=0.57),
    modulation=(
        ModRoute("lfo1", "pitch", 0.035),
        ModRoute("lfo2", "pan", 0.31),
        ModRoute("velocity", "cutoff", 0.68),
    ),
    fm_amount=2.3,
    unison_voices=2,
    unison_detune_cents=3.2,
    stereo_width=0.72,
    sends=EffectSends(chorus=0.15, delay=0.24, reverb=0.46),
)

SUB_CURRENT = SynthPatch(
    name="sub-current",
    oscillators=(
        OscillatorSpec(waveform="sine", gain=0.72, octave=-1),
        OscillatorSpec(waveform="saw", gain=0.34),
    ),
    amp_env=EnvelopeSpec(attack=0.008, decay=0.22, sustain=0.82, release=0.38),
    filter_env=EnvelopeSpec(attack=0.01, decay=0.32, sustain=0.28, release=0.34),
    filter=FilterSpec(mode="lowpass", cutoff_hz=680.0, resonance_q=0.88, key_tracking=0.48, env_amount_octaves=1.55, drive=1.55),
    lfo1=LFOSpec(waveform="sine", rate_hz=0.095, phase=0.0),
    lfo2=LFOSpec(waveform="triangle", rate_hz=0.033, phase=0.2),
    modulation=(
        ModRoute("lfo1", "cutoff", 0.16),
        ModRoute("velocity", "cutoff", 0.48),
    ),
    unison_voices=1,
    base_pan=-0.03,
    stereo_width=0.18,
    sends=EffectSends(reverb=0.07),
)

KINETIC_METAL = SynthPatch(
    name="kinetic-metal",
    oscillators=(
        OscillatorSpec(waveform="square", gain=0.42, octave=1),
        OscillatorSpec(waveform="sine", gain=0.38, octave=2, semitone=7),
    ),
    amp_env=EnvelopeSpec(attack=0.002, decay=0.16, sustain=0.10, release=0.22),
    filter_env=EnvelopeSpec(attack=0.001, decay=0.12, sustain=0.02, release=0.18),
    filter=FilterSpec(mode="bandpass", cutoff_hz=3_400.0, resonance_q=2.25, key_tracking=0.52, env_amount_octaves=1.2, drive=1.42),
    lfo1=LFOSpec(waveform="square", rate_hz=0.41, phase=0.0),
    lfo2=LFOSpec(waveform="sine", rate_hz=0.087, phase=0.36),
    modulation=(
        ModRoute("lfo2", "pan", 0.30),
        ModRoute("velocity", "cutoff", 0.62),
    ),
    fm_amount=0.76,
    ring_amount=0.42,
    noise_level=0.12,
    unison_voices=2,
    unison_detune_cents=5.5,
    base_pan=0.16,
    stereo_width=0.88,
    sends=EffectSends(delay=0.12, reverb=0.24),
)

DEFAULT_PATCH_BANK = PatchBank(
    patches={
        patch.name: patch
        for patch in (CRYSTAL_MOTION, WARM_POLY, FM_GLASS, SUB_CURRENT, KINETIC_METAL)
    },
    lane_map={
        "TUNE": CRYSTAL_MOTION.name,
        "BASS": SUB_CURRENT.name,
        "RHYTHM": KINETIC_METAL.name,
    },
)


def tune_patch_bank(patch: SynthPatch) -> PatchBank:
    patches = dict(DEFAULT_PATCH_BANK.patches)
    patches[patch.name] = patch
    return PatchBank(
        patches=patches,
        lane_map={
            "TUNE": patch.name,
            "BASS": SUB_CURRENT.name,
            "RHYTHM": KINETIC_METAL.name,
        },
    )

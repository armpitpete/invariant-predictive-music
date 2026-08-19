from __future__ import annotations

import wave
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from ipm.real_synth import (
    CRYSTAL_MOTION,
    DEFAULT_PATCH_BANK,
    FM_GLASS,
    WARM_POLY,
    EffectSends,
    EnvelopeSpec,
    FilterSpec,
    LFOSpec,
    ModRoute,
    OscillatorSpec,
    PatchBank,
    SynthPatch,
    bank_from_dict,
    bank_to_dict,
    patch_from_dict,
    patch_to_dict,
    render_real_synth_wav,
    tune_patch_bank,
)


def _event(pitch: int, onset: int, duration: int, velocity: int = 88):
    return SimpleNamespace(
        pitch=pitch,
        onset=Fraction(onset),
        duration=Fraction(duration),
        velocity=velocity,
    )


def _result(*, tune=(), bass=(), rhythm=()):
    return SimpleNamespace(
        config=SimpleNamespace(tempo_bpm=120, bars=1, beats_per_bar=4),
        voices=(
            SimpleNamespace(name="TUNE", events=list(tune)),
            SimpleNamespace(name="BASS", events=list(bass)),
            SimpleNamespace(name="RHYTHM", events=list(rhythm)),
        ),
    )


def _ledger(result):
    return tuple(
        (
            voice.name,
            tuple((event.onset, event.duration, event.pitch, event.velocity) for event in voice.events),
        )
        for voice in result.voices
    )


def _samples(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as wav:
        assert wav.getnchannels() == 2
        assert wav.getsampwidth() == 2
        assert wav.getframerate() == 8_000
        return np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2")


def _dry_patch(name: str, waveform: str = "sine", *, filter_mode: str = "lowpass") -> SynthPatch:
    return SynthPatch(
        name=name,
        oscillators=(OscillatorSpec(waveform=waveform, gain=0.7),),
        amp_env=EnvelopeSpec(attack=0.005, decay=0.04, sustain=0.7, release=0.05),
        filter_env=EnvelopeSpec(attack=0.005, decay=0.04, sustain=0.2, release=0.05),
        filter=FilterSpec(
            mode=filter_mode,
            cutoff_hz=1_200.0,
            resonance_q=0.8,
            key_tracking=0.2,
            env_amount_octaves=0.3,
            drive=1.0,
        ),
        lfo1=LFOSpec(rate_hz=0.2),
        lfo2=LFOSpec(rate_hz=0.1),
        sends=EffectSends(),
    )


def _bank(patch: SynthPatch) -> PatchBank:
    return PatchBank(
        patches={patch.name: patch},
        lane_map={"TUNE": patch.name, "BASS": patch.name, "RHYTHM": patch.name},
    )


def test_patch_and_bank_serialisation_round_trip() -> None:
    assert patch_from_dict(patch_to_dict(CRYSTAL_MOTION)) == CRYSTAL_MOTION
    reconstructed = bank_from_dict(bank_to_dict(DEFAULT_PATCH_BANK))
    assert reconstructed == DEFAULT_PATCH_BANK


def test_invalid_patch_values_fail_validation() -> None:
    with pytest.raises(ValueError):
        OscillatorSpec(waveform="not-an-oscillator")
    with pytest.raises(ValueError):
        FilterSpec(mode="ladder-of-doom")
    with pytest.raises(ValueError):
        SynthPatch(name="bad", unison_voices=0)
    with pytest.raises(ValueError):
        ModRoute("lfo1", "not-a-destination", 1.0)


def test_identical_input_and_patch_bank_is_byte_deterministic_and_does_not_mutate(tmp_path: Path) -> None:
    result = _result(
        tune=(_event(64, 0, 1), _event(67, 1, 1, 76)),
        bass=(_event(43, 0, 2, 72),),
        rhythm=(_event(72, 2, 1, 68),),
    )
    before = _ledger(result)
    a = render_real_synth_wav(result, tmp_path / "a.wav", bank=DEFAULT_PATCH_BANK, sample_rate=8_000)
    middle = _ledger(result)
    b = render_real_synth_wav(result, tmp_path / "b.wav", bank=DEFAULT_PATCH_BANK, sample_rate=8_000)
    after = _ledger(result)

    assert before == middle == after
    assert a.read_bytes() == b.read_bytes()
    samples = _samples(a)
    assert samples.size > 0
    assert np.any(samples != 0)
    assert np.any(samples[0::2] != samples[1::2])


def test_same_tune_different_patch_data_changes_audio_without_changing_notes(tmp_path: Path) -> None:
    result = _result(tune=(_event(60, 0, 1), _event(64, 1, 1), _event(67, 2, 1)))
    before = _ledger(result)
    crystal = render_real_synth_wav(
        result,
        tmp_path / "crystal.wav",
        bank=tune_patch_bank(CRYSTAL_MOTION),
        sample_rate=8_000,
    )
    warm = render_real_synth_wav(
        result,
        tmp_path / "warm.wav",
        bank=tune_patch_bank(WARM_POLY),
        sample_rate=8_000,
    )
    glass = render_real_synth_wav(
        result,
        tmp_path / "glass.wav",
        bank=tune_patch_bank(FM_GLASS),
        sample_rate=8_000,
    )
    assert _ledger(result) == before
    assert crystal.read_bytes() != warm.read_bytes()
    assert crystal.read_bytes() != glass.read_bytes()
    assert warm.read_bytes() != glass.read_bytes()


def test_silence_is_valid_silence(tmp_path: Path) -> None:
    patch = _dry_patch("silent-capable")
    path = render_real_synth_wav(_result(), tmp_path / "silence.wav", bank=_bank(patch), sample_rate=8_000)
    samples = _samples(path)
    assert samples.size > 0
    assert np.all(samples == 0)


def test_all_required_oscillator_waveforms_execute(tmp_path: Path) -> None:
    result = _result(tune=(_event(60, 0, 1),))
    outputs = []
    for waveform in ("sine", "triangle", "saw", "square", "pulse", "noise"):
        patch = _dry_patch(f"osc-{waveform}", waveform)
        path = render_real_synth_wav(
            result,
            tmp_path / f"{waveform}.wav",
            bank=_bank(patch),
            sample_rate=8_000,
        )
        samples = _samples(path)
        assert np.any(samples != 0)
        outputs.append(path.read_bytes())
    assert len(set(outputs)) == len(outputs)


def test_all_required_filter_modes_execute_without_numerical_failure(tmp_path: Path) -> None:
    result = _result(tune=(_event(62, 0, 1),))
    for mode in ("lowpass", "highpass", "bandpass", "notch"):
        patch = _dry_patch(f"filter-{mode}", "saw", filter_mode=mode)
        path = render_real_synth_wav(
            result,
            tmp_path / f"{mode}.wav",
            bank=_bank(patch),
            sample_rate=8_000,
        )
        samples = _samples(path).astype(np.float64)
        assert np.all(np.isfinite(samples))
        assert np.any(samples != 0)


def test_modulation_matrix_is_data_driven(tmp_path: Path) -> None:
    result = _result(tune=(_event(65, 0, 2, 96),))
    base = _dry_patch("mod-base", "saw")
    modded = replace(
        base,
        name="modded",
        modulation=(
            ModRoute("lfo1", "cutoff", 1.1),
            ModRoute("lfo2", "pan", 0.55),
            ModRoute("velocity", "osc_mix", 0.4),
        ),
    )
    plain_path = render_real_synth_wav(result, tmp_path / "plain.wav", bank=_bank(base), sample_rate=8_000)
    modded_path = render_real_synth_wav(result, tmp_path / "modded.wav", bank=_bank(modded), sample_rate=8_000)
    assert plain_path.read_bytes() != modded_path.read_bytes()


def test_patch_bank_requires_complete_lane_mapping() -> None:
    patch = _dry_patch("one")
    with pytest.raises(ValueError):
        PatchBank(patches={patch.name: patch}, lane_map={"TUNE": patch.name})

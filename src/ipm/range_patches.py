"""Orthogonal patch data for Real Synth Engine v3 range acceptance.

These patches deliberately exercise different synthesis families while sharing
one unchanged DSP engine. They are acceptance fixtures, not a new engine.
"""

from __future__ import annotations

from .real_synth import (
    EffectSends,
    EnvelopeSpec,
    FilterSpec,
    LFOSpec,
    ModRoute,
    OscillatorSpec,
    SynthPatch,
)


DRY_SUBTRACTIVE_PLUCK = SynthPatch(
    name="dry-subtractive-pluck",
    oscillators=(
        OscillatorSpec(waveform="saw", gain=0.58, cents=-2.0),
        OscillatorSpec(waveform="pulse", gain=0.36, cents=3.0, pulse_width=0.27),
    ),
    amp_env=EnvelopeSpec(attack=0.002, decay=0.19, sustain=0.035, release=0.11),
    filter_env=EnvelopeSpec(attack=0.001, decay=0.24, sustain=0.02, release=0.12),
    filter=FilterSpec(
        mode="lowpass",
        cutoff_hz=620.0,
        resonance_q=1.10,
        key_tracking=0.24,
        env_amount_octaves=3.6,
        drive=1.28,
    ),
    lfo1=LFOSpec(waveform="sine", rate_hz=0.0),
    lfo2=LFOSpec(waveform="triangle", rate_hz=0.0),
    modulation=(
        ModRoute("velocity", "cutoff", 0.72),
        ModRoute("velocity", "amplitude", 2.0),
    ),
    fm_amount=0.0,
    ring_amount=0.0,
    noise_level=0.0,
    unison_voices=1,
    unison_detune_cents=0.0,
    base_pan=-0.06,
    stereo_width=0.10,
    sends=EffectSends(chorus=0.0, delay=0.0, reverb=0.025),
)


HOLLOW_ORGAN_REED = SynthPatch(
    name="hollow-organ-reed",
    oscillators=(
        OscillatorSpec(waveform="pulse", gain=0.58, pulse_width=0.34),
        OscillatorSpec(waveform="triangle", gain=0.32, octave=1),
    ),
    amp_env=EnvelopeSpec(attack=0.115, decay=0.16, sustain=0.91, release=0.34),
    filter_env=EnvelopeSpec(attack=0.30, decay=0.55, sustain=0.66, release=0.42),
    filter=FilterSpec(
        mode="notch",
        cutoff_hz=1_920.0,
        resonance_q=1.35,
        key_tracking=0.52,
        env_amount_octaves=0.20,
        drive=0.92,
    ),
    lfo1=LFOSpec(waveform="sine", rate_hz=4.6, phase=0.12),
    lfo2=LFOSpec(waveform="sine", rate_hz=0.13, phase=0.41),
    modulation=(
        ModRoute("lfo1", "pitch", 0.028),
        ModRoute("lfo2", "osc_mix", 0.09),
        ModRoute("velocity", "amplitude", 1.0),
    ),
    fm_amount=0.0,
    ring_amount=0.0,
    noise_level=0.018,
    unison_voices=1,
    unison_detune_cents=0.0,
    base_pan=0.04,
    stereo_width=0.08,
    sends=EffectSends(chorus=0.0, delay=0.0, reverb=0.035),
)


METALLIC_FM_BELL = SynthPatch(
    name="metallic-fm-bell",
    oscillators=(
        OscillatorSpec(waveform="sine", gain=0.78),
        OscillatorSpec(waveform="sine", gain=0.34, octave=2, semitone=7),
    ),
    amp_env=EnvelopeSpec(attack=0.001, decay=1.55, sustain=0.0, release=1.55),
    filter_env=EnvelopeSpec(attack=0.001, decay=0.72, sustain=0.0, release=0.95),
    filter=FilterSpec(
        mode="bandpass",
        cutoff_hz=5_650.0,
        resonance_q=2.65,
        key_tracking=0.72,
        env_amount_octaves=0.35,
        drive=0.82,
    ),
    lfo1=LFOSpec(waveform="sine", rate_hz=0.17, phase=0.0),
    lfo2=LFOSpec(waveform="sine", rate_hz=0.071, phase=0.35),
    modulation=(
        ModRoute("velocity", "cutoff", 0.48),
        ModRoute("lfo2", "pan", 0.08),
    ),
    fm_amount=4.85,
    ring_amount=0.0,
    noise_level=0.0,
    unison_voices=1,
    unison_detune_cents=0.0,
    base_pan=0.0,
    stereo_width=0.12,
    sends=EffectSends(chorus=0.0, delay=0.0, reverb=0.12),
)


RANGE_ACCEPTANCE_PATCHES = (
    DRY_SUBTRACTIVE_PLUCK,
    HOLLOW_ORGAN_REED,
    METALLIC_FM_BELL,
)

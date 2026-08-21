"""Frozen RealSynthEngine v4R1 pre-audition package definitions.

This module defines data only and performs no audition rendering.  It reuses the
already-frozen pre-v4 Tune ledger and fixes every reference patch, macro mapping,
R-C blinding procedure, R-D diagnostic fixture and R-E evolution curve before
any v4R1 human listening occurs.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from ipm.real_synth_v4 import (
    ENGINE_VERSION,
    MACRO_NAMES,
    EnvelopeSpecV4,
    EvolutionCurveV4,
    PatchBankV4,
    SynthPatchV4,
    patch_to_dict,
)

PACKAGE_VERSION = "0.1"
PACKAGE_PARENT = "9148ba552f236f865181996539cf839117f268b2"
DESIGN_FREEZE = "9189116cdf34937f1212d052378b36f5d4bd503f"
HISTORICAL_V4_FAIL = "3d247ef5696140b2b8f69764869fbb81e4aeb130"
LEDGER_PATH = Path("fixtures/real_synth_v4_gate_c/REAL_SYNTH_ENGINE_V4_GATE_C_TUNE_LEDGER_v0_1.json")
LEDGER_SHA256 = "1bee94ac3d65ce6a01efd6ec2921f2cae82238ddbeaaab79fcee38dc4726bd31"
LEDGER_EVENT_COUNT = 122
SAMPLE_RATE = 44_100
BLOCK_SIZE = 128
R_D_VALUES = (0.15, 0.50, 0.85)
R_D_NOTE_PITCH = 48
R_D_NOTE_VELOCITY = 100
R_D_CONTROL_PREROLL_SECONDS = 0.020
R_E_PHRASE_BARS = 4


def canonical_sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _env(a: float, d: float, s: float, r: float) -> EnvelopeSpecV4:
    return EnvelopeSpecV4(a, d, s, r)


def _lfos():
    return (
        {"waveform": "sine", "rate_hz": 0.43, "sync_beats": None, "modifier": "straight", "phase": 0.0, "bipolar": True, "scope": "voice"},
        {"waveform": "triangle", "rate_hz": 0.17, "sync_beats": None, "modifier": "straight", "phase": 0.25, "bipolar": True, "scope": "voice"},
    )


def reference_patches() -> dict[str, SynthPatchV4]:
    """Three final v4R1 family reference patches, frozen before listening."""
    neutral = (0.5,) * 8
    policy = ("continuous", "continuous", "continuous", "event_boundary", "continuous", "continuous", "continuous", "continuous")

    va = SynthPatchV4(
        name="v4r1-va-analog",
        polyphony=8,
        va=(
            {"waveform": "saw", "gain": 0.50, "octave": 0, "semitone": 0, "cents": -5.0, "phase": 0.0, "pulse_width": 0.50, "key_tracking": 1.0},
            {"waveform": "pulse", "gain": 0.32, "octave": 0, "semitone": 0, "cents": 4.0, "phase": 0.0, "pulse_width": 0.37, "key_tracking": 1.0},
        ),
        amp_env=_env(0.025, 0.18, 0.72, 0.35),
        env1=_env(0.005, 0.35, 0.25, 0.25),
        env2=_env(0.010, 0.30, 0.00, 0.20),
        lfos=_lfos(),
        filter={"mode": "lowpass", "cutoff_hz": 2300.0, "resonance_q": 0.85, "key_tracking": 0.30, "drive": 0.75},
        routes=(
            {"source": "env1", "destination": "filter_cutoff", "amount": 14.0, "unipolar": False},
            {"source": "velocity", "destination": "filter_cutoff", "amount": 3.0, "unipolar": False},
            {"source": "macro1", "destination": "filter_cutoff", "amount": 12.0, "unipolar": False},
            {"source": "macro6", "destination": "drive", "amount": 2.0, "unipolar": False},
        ),
        macro_defaults=neutral,
        macro_application=policy,
        note_evolution_seconds=0.85,
        evolution=(),
        base_pan=-0.03,
        base_width=0.52,
    )

    fm_ops = [
        {"mode": "ratio", "ratio": 1.0, "fixed_hz": 440.0, "coarse": 0, "fine_cents": 0.0, "level": 0.82, "velocity_sensitivity": 0.12, "key_tracking": 1.0, "envelope": "amp", "feedback": 0.0, "index": 1.8},
        {"mode": "ratio", "ratio": 2.0, "fixed_hz": 440.0, "coarse": 0, "fine_cents": 0.0, "level": 0.62, "velocity_sensitivity": 0.08, "key_tracking": 1.0, "envelope": "env1", "feedback": 0.0, "index": 2.5},
        {"mode": "ratio", "ratio": 3.0, "fixed_hz": 440.0, "coarse": 0, "fine_cents": 0.0, "level": 0.48, "velocity_sensitivity": 0.06, "key_tracking": 1.0, "envelope": "env1", "feedback": 0.0, "index": 2.0},
        {"mode": "ratio", "ratio": 5.0, "fixed_hz": 440.0, "coarse": 0, "fine_cents": 0.0, "level": 0.34, "velocity_sensitivity": 0.05, "key_tracking": 1.0, "envelope": "env2", "feedback": 0.0, "index": 1.6},
    ]
    fm = SynthPatchV4(
        name="v4r1-fm-digital",
        polyphony=8,
        va=(),
        fm={"enabled": True, "algorithm": "4>3>2>1", "gain": 0.52, "operators": fm_ops},
        amp_env=_env(0.018, 0.22, 0.68, 0.40),
        env1=_env(0.010, 0.45, 0.55, 0.30),
        env2=_env(0.010, 0.35, 0.30, 0.25),
        lfos=_lfos(),
        filter={"mode": "lowpass", "cutoff_hz": 6200.0, "resonance_q": 0.72, "key_tracking": 0.28, "drive": 0.62},
        routes=(
            {"source": "velocity", "destination": "fm_index", "amount": 1.5, "unipolar": False},
            {"source": "macro1", "destination": "filter_cutoff", "amount": 10.0, "unipolar": False},
            {"source": "macro5", "destination": "fm_index", "amount": 5.0, "unipolar": False},
            {"source": "macro6", "destination": "drive", "amount": 1.8, "unipolar": False},
        ),
        macro_defaults=neutral,
        macro_application=policy,
        note_evolution_seconds=1.10,
        evolution=(),
        base_pan=0.02,
        base_width=0.50,
    )

    modes = [
        {"ratio": 1.00, "fixed_hz": None, "gain": 0.78, "decay": 9.0, "detune_cents": 0.0, "velocity_sensitivity": 0.08, "brightness_sensitivity": 0.05, "excitation_sensitivity": 1.0},
        {"ratio": 1.50, "fixed_hz": None, "gain": 0.48, "decay": 7.5, "detune_cents": 1.0, "velocity_sensitivity": 0.08, "brightness_sensitivity": 0.18, "excitation_sensitivity": 1.0},
        {"ratio": 2.00, "fixed_hz": None, "gain": 0.34, "decay": 6.2, "detune_cents": -1.5, "velocity_sensitivity": 0.08, "brightness_sensitivity": 0.30, "excitation_sensitivity": 1.0},
        {"ratio": 2.72, "fixed_hz": None, "gain": 0.25, "decay": 5.2, "detune_cents": 2.0, "velocity_sensitivity": 0.08, "brightness_sensitivity": 0.42, "excitation_sensitivity": 1.0},
        {"ratio": 3.85, "fixed_hz": None, "gain": 0.18, "decay": 4.3, "detune_cents": -2.5, "velocity_sensitivity": 0.08, "brightness_sensitivity": 0.55, "excitation_sensitivity": 1.0},
        {"ratio": 5.20, "fixed_hz": None, "gain": 0.12, "decay": 3.6, "detune_cents": 3.0, "velocity_sensitivity": 0.08, "brightness_sensitivity": 0.68, "excitation_sensitivity": 1.0},
    ]
    modal = SynthPatchV4(
        name="v4r1-modal-wood",
        polyphony=8,
        va=(),
        modal={"enabled": True, "send": 1.0, "return_gain": 0.68, "modes": modes},
        exciter={"enabled": True, "kind": "filtered_noise", "level": 0.22, "duration": 0.020, "smoothing": 4},
        amp_env=_env(0.012, 0.16, 0.76, 0.42),
        env1=_env(0.010, 0.30, 0.30, 0.25),
        env2=_env(0.010, 0.25, 0.15, 0.20),
        lfos=_lfos(),
        filter={"mode": "lowpass", "cutoff_hz": 7200.0, "resonance_q": 0.68, "key_tracking": 0.24, "drive": 0.58},
        routes=(
            {"source": "velocity", "destination": "modal_gain", "amount": 1.2, "unipolar": False},
            {"source": "macro1", "destination": "filter_cutoff", "amount": 8.0, "unipolar": False},
            {"source": "macro6", "destination": "drive", "amount": 1.6, "unipolar": False},
        ),
        macro_defaults=neutral,
        macro_application=policy,
        note_evolution_seconds=1.25,
        evolution=(),
        base_pan=0.0,
        base_width=0.56,
    )
    return {"VA": va, "FM": fm, "MODAL": modal}


def r_c_bank(patch: SynthPatchV4) -> PatchBankV4:
    """R-C is deliberately dry: family identity cannot come from ambience."""
    return PatchBankV4(
        {patch.name: patch}, {"TUNE": patch.name},
        chorus={"rate": 0.25, "depth": 0.003, "base_delay": 0.012, "feedback": 0.05, "wet": 0.0},
        delay={"left": 0.25, "right": 0.375, "feedback": 0.25, "cross": 0.10, "damping": 0.25, "wet": 0.0},
        reverb={"decay": 1.35, "damping": 0.40, "predelay": 0.020, "width": 0.90, "wet": 0.0},
    )


def r_d_bank(patch: SynthPatchV4) -> PatchBankV4:
    """R-D permits one fixed ambience path so SPACE has testable authority."""
    return PatchBankV4(
        {patch.name: patch}, {"TUNE": patch.name},
        chorus={"rate": 0.25, "depth": 0.003, "base_delay": 0.012, "feedback": 0.05, "wet": 0.0},
        delay={"left": 0.25, "right": 0.375, "feedback": 0.25, "cross": 0.10, "damping": 0.25, "wet": 0.0},
        reverb={"decay": 1.35, "damping": 0.40, "predelay": 0.020, "width": 0.90, "wet": 0.45},
    )


def r_e_patches() -> tuple[SynthPatchV4, SynthPatchV4]:
    static = reference_patches()["MODAL"]
    curves = (
        EvolutionCurveV4("note", "MOTION", ((0.00, -0.22), (0.25, 0.14), (0.65, -0.06), (1.00, 0.18))),
        EvolutionCurveV4("note", "CHARACTER", ((0.00, -0.14), (0.45, 0.12), (1.00, 0.20))),
        EvolutionCurveV4("phrase", "BRIGHTNESS", ((0.00, -0.18), (0.35, 0.14), (0.72, 0.20), (1.00, -0.08))),
        EvolutionCurveV4("phrase", "SPACE", ((0.00, -0.12), (0.50, 0.08), (1.00, 0.16))),
        EvolutionCurveV4("piece", "WIDTH", ((0.00, -0.22), (0.30, -0.06), (0.68, 0.22), (1.00, 0.08))),
        EvolutionCurveV4("piece", "CHARACTER", ((0.00, -0.10), (0.42, 0.04), (0.76, 0.18), (1.00, -0.02))),
    )
    return static, replace(static, name="v4r1-modal-wood-evolving", evolution=curves)


def r_e_bank(patch: SynthPatchV4) -> PatchBankV4:
    bank = r_d_bank(patch)
    return replace(bank, reverb={**bank.reverb, "wet": 0.36})


def macro_mapping_manifest() -> dict[str, Any]:
    return {
        "BRIGHTNESS": {"policy": "continuous", "authority": "patch macro1→filter_cutoff plus modal brightness_sensitivity", "semantic": "higher spectral/modal brightness"},
        "BODY": {"policy": "continuous", "authority": "engine spectral-weight shift plus modal low-mode weighting", "semantic": "greater low/fundamental/resonant weight"},
        "MOTION": {"policy": "continuous", "authority": "engine macro-scaled LFO1 cutoff movement plus LFO2 VA micro-pitch movement", "semantic": "greater internal movement"},
        "ATTACK": {"policy": "event_boundary", "authority": "new/retriggered amp-envelope attack-time scaling", "semantic": "faster/sharper articulation as value rises"},
        "CHARACTER": {"policy": "continuous", "authority": "VA waveform-complexity mix / FM index authority / modal upper-mode participation", "semantic": "greater spectral/timbral complexity"},
        "DRIVE": {"policy": "continuous", "authority": "pre-filter tanh operating-level scalar plus patch drive route", "semantic": "greater saturation/nonlinearity"},
        "WIDTH": {"policy": "continuous", "authority": "stereo side-generation depth", "semantic": "greater stereo width"},
        "SPACE": {"policy": "continuous", "authority": "reverb-send depth into fixed R-D/R-E ambience network", "semantic": "greater ambience/effect depth"},
    }


def r_c_blinding_procedure() -> dict[str, Any]:
    return {
        "labels": ["blind-1", "blind-2", "blind-3"],
        "families": ["VA", "FM", "MODAL"],
        "procedure": "At R-C materialisation, generate 32 random bytes; use their integer value to shuffle the three families; store nonce+mapping only in a private mapping artifact; publish only blind WAV labels and SHA-256 commitment to canonical nonce+mapping. Reveal mapping only after owner PASS/FAIL is frozen.",
        "commitment": "sha256(canonical_json({nonce_hex,mapping}))",
        "no_seed_shopping": True,
        "mapping_must_precede_listening": True,
    }


def load_frozen_ledger(root: Path) -> dict[str, Any]:
    payload = json.loads((root / LEDGER_PATH).read_text(encoding="utf-8"))
    if payload.get("tune_event_count") != LEDGER_EVENT_COUNT or len(payload.get("tune_events", [])) != LEDGER_EVENT_COUNT:
        raise RuntimeError("v4R1 Tune ledger event-count drift")
    if payload.get("tune_event_ledger_sha256") != LEDGER_SHA256 or canonical_sha(payload["tune_events"]) != LEDGER_SHA256:
        raise RuntimeError("v4R1 Tune ledger hash drift")
    return payload


def structural_manifest(root: Path) -> dict[str, Any]:
    if ENGINE_VERSION != "4R1":
        raise RuntimeError("pre-audition package requires engine 4R1")
    ledger = load_frozen_ledger(root)
    patches = reference_patches()
    static, evolving = r_e_patches()
    mappings = macro_mapping_manifest()
    if tuple(mappings) != MACRO_NAMES:
        raise RuntimeError("all eight macros must be mapped in frozen order")
    return {
        "status": "FROZEN_INPUTS_NOT_YET_AUDITIONED",
        "package_version": PACKAGE_VERSION,
        "package_parent": PACKAGE_PARENT,
        "design_freeze": DESIGN_FREEZE,
        "historical_v4_fail": HISTORICAL_V4_FAIL,
        "engine_version": ENGINE_VERSION,
        "human_audition_performed": False,
        "audition_audio_created": False,
        "sample_rate": SAMPLE_RATE,
        "block_size": BLOCK_SIZE,
        "ledger": {
            "path": str(LEDGER_PATH),
            "sha256": LEDGER_SHA256,
            "event_count": LEDGER_EVENT_COUNT,
            "tempo_bpm": ledger["tempo_bpm"],
            "bars": ledger["bars"],
            "beats_per_bar": ledger["beats_per_bar"],
        },
        "reference_patches": {family: {"name": p.name, "sha256": canonical_sha(patch_to_dict(p)), "note_evolution_seconds": p.note_evolution_seconds, "macro_application": list(p.macro_application)} for family, p in patches.items()},
        "macro_mappings": mappings,
        "r_c": {"bank_policy": "dry", "blinding": r_c_blinding_procedure(), "question": "Do these sound like three genuinely different instruments whose identities come from three different synthesis families, rather than three presets of essentially the same voice?"},
        "r_d": {
            "values": list(R_D_VALUES), "pitch": R_D_NOTE_PITCH, "velocity": R_D_NOTE_VELOCITY,
            "control_preroll_seconds": R_D_CONTROL_PREROLL_SECONDS,
            "diagnostics_contract": "REAL_SYNTH_ENGINE_V4R1_CONTROL_DIAGNOSTICS_v0_1.md",
            "families": ["VA", "FM", "MODAL"],
            "human_question": "Does this control make a clearly perceptible and musically useful change in the intended direction without destroying the patch identity?",
        },
        "r_e": {
            "static_patch_sha256": canonical_sha(patch_to_dict(static)),
            "evolving_patch_sha256": canonical_sha(patch_to_dict(evolving)),
            "condition_diff": ["name", "evolution"],
            "phrase_bars": R_E_PHRASE_BARS,
            "curve_count": len(evolving.evolution),
            "curves": [dict(scope=c.scope, target=c.target, anchors=[list(a) for a in c.anchors]) for c in evolving.evolution],
            "targets": sorted({c.target for c in evolving.evolution}),
            "scopes": sorted({c.scope for c in evolving.evolution}),
            "human_questions": [
                "Can you hear coherent sonic development over time in EVOLVING that is absent or materially weaker in STATIC?",
                "Does that development preserve recognition of the same written musical material rather than sounding like a hidden replacement composition?",
            ],
        },
    }

from __future__ import annotations

import wave
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from ipm.synth_engine_v2 import (
    SYNTH_ENGINE_VERSION,
    _shared_state,
    render_synth_v2_wav,
    synth_v2_manifest,
)


def _event(pitch: int, onset: int, duration: int, velocity: int = 80):
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


def _event_snapshot(result):
    return tuple(
        (
            voice.name,
            tuple((event.onset, event.duration, event.pitch, event.velocity) for event in voice.events),
        )
        for voice in result.voices
    )


def test_v2_manifest_is_exact_and_identifies_frozen_parent() -> None:
    manifest = synth_v2_manifest()
    assert manifest["engine_version"] == SYNTH_ENGINE_VERSION == "2.0"
    assert manifest["engine_name"] == "Evolving Resonant Field v2"
    assert manifest["contract_commit"] == "7fa85d05134ee0b1df5f34cf562a3c6b39a27f5b"
    assert manifest["sample_rate"] == 44_100
    assert manifest["channels"] == 2
    assert manifest["tune"]["twin_cents"] == 3.7
    assert manifest["bass"]["drive"] == 1.55
    assert manifest["rhythm"]["drive"] == 1.32
    assert manifest["room"]["length_seconds"] == 0.92


def test_v2_shared_state_has_piece_and_phrase_motion() -> None:
    start = _shared_state(0.0, 64.0, 4)
    phrase_two = _shared_state(16.0, 64.0, 4)
    late = _shared_state(44.0, 64.0, 4)
    assert start != phrase_two
    assert phrase_two != late
    assert late.stereo_width > start.stereo_width
    assert late.motion_depth > start.motion_depth


def test_v2_render_is_deterministic_stereo_and_does_not_mutate_events(tmp_path: Path) -> None:
    result = _result(
        tune=(_event(64, 0, 1, 88), _event(67, 1, 1, 76)),
        bass=(_event(43, 0, 2, 72),),
        rhythm=(_event(72, 2, 1, 68),),
    )
    before = _event_snapshot(result)
    first = render_synth_v2_wav(result, tmp_path / "a.wav", sample_rate=8_000)
    middle = _event_snapshot(result)
    second = render_synth_v2_wav(result, tmp_path / "b.wav", sample_rate=8_000)
    after = _event_snapshot(result)

    assert before == middle == after
    assert first.read_bytes() == second.read_bytes()

    with wave.open(str(first), "rb") as wav:
        assert wav.getnchannels() == 2
        assert wav.getsampwidth() == 2
        assert wav.getframerate() == 8_000
        frames = wav.readframes(wav.getnframes())

    samples = np.frombuffer(frames, dtype="<i2")
    assert samples.size > 0
    assert np.any(samples != 0)
    assert np.any(samples[0::2] != samples[1::2])
    assert int(np.max(samples)) <= 32767
    assert int(np.min(samples)) >= -32768


def test_v2_can_render_silence_as_valid_finite_pcm(tmp_path: Path) -> None:
    path = render_synth_v2_wav(_result(), tmp_path / "silence.wav", sample_rate=8_000)
    with wave.open(str(path), "rb") as wav:
        frames = wav.readframes(wav.getnframes())
    samples = np.frombuffer(frames, dtype="<i2")
    assert samples.size > 0
    assert np.all(samples == 0)

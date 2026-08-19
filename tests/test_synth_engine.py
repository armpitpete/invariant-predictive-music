from __future__ import annotations

import wave
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace

from ipm.synth_engine import (
    DEFAULT_SAMPLE_RATE,
    SYNTH_ENGINE_VERSION,
    SYNTH_PRESETS,
    render_synth_wav,
    synth_manifest,
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
            SimpleNamespace(name="TUNE", events=tuple(tune)),
            SimpleNamespace(name="BASS", events=tuple(bass)),
            SimpleNamespace(name="RHYTHM", events=tuple(rhythm)),
        ),
    )


def test_synth_contract_is_explicit_and_lane_specific() -> None:
    manifest = synth_manifest()
    assert manifest["engine_version"] == SYNTH_ENGINE_VERSION
    assert manifest["sample_rate"] == DEFAULT_SAMPLE_RATE
    assert manifest["channels"] == 2
    assert set(manifest["presets"]) == {"TUNE", "BASS", "RHYTHM"}
    assert SYNTH_PRESETS["TUNE"] != SYNTH_PRESETS["BASS"]
    assert SYNTH_PRESETS["BASS"] != SYNTH_PRESETS["RHYTHM"]
    assert SYNTH_PRESETS["TUNE"].pan < SYNTH_PRESETS["RHYTHM"].pan


def test_synth_render_is_deterministic_stereo_pcm(tmp_path: Path) -> None:
    result = _result(
        tune=(_event(64, 0, 1, 88), _event(67, 1, 1, 76)),
        bass=(_event(43, 0, 2, 72),),
        rhythm=(_event(72, 2, 1, 68),),
    )
    left = render_synth_wav(result, tmp_path / "a.wav", sample_rate=8_000)
    right = render_synth_wav(result, tmp_path / "b.wav", sample_rate=8_000)
    assert left.read_bytes() == right.read_bytes()

    with wave.open(str(left), "rb") as wav:
        assert wav.getnchannels() == 2
        assert wav.getsampwidth() == 2
        assert wav.getframerate() == 8_000
        frames = wav.readframes(wav.getnframes())
    assert any(frames)


def test_synth_render_preserves_real_stereo_difference(tmp_path: Path) -> None:
    result = _result(
        tune=(_event(64, 0, 1),),
        rhythm=(_event(76, 1, 1),),
    )
    path = render_synth_wav(result, tmp_path / "stereo.wav", sample_rate=8_000)
    with wave.open(str(path), "rb") as wav:
        frames = wav.readframes(wav.getnframes())
    samples = memoryview(frames).cast("h")
    assert any(samples[index] != samples[index + 1] for index in range(0, len(samples), 2))


def test_synth_can_render_silence_without_invalid_pcm(tmp_path: Path) -> None:
    path = render_synth_wav(_result(), tmp_path / "silence.wav", sample_rate=8_000)
    with wave.open(str(path), "rb") as wav:
        assert wav.getnchannels() == 2
        frames = wav.readframes(wav.getnframes())
    assert set(frames) <= {0}

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from ipm.machine import (
    MachineCandidate,
    MachineControls,
    MachineEngine,
    _activity_controls,
    choose_candidate_by_surprise,
    finish_snapshot,
    next_root_seed,
)


def test_machine_controls_validate_unit_interval() -> None:
    MachineControls(activity=0.0, surprise=1.0)
    with pytest.raises(ValueError):
        MachineControls(activity=-0.01)
    with pytest.raises(ValueError):
        MachineControls(surprise=1.01)


def test_activity_knob_controls_existing_density_governors() -> None:
    low_bass, low_rhythm = _activity_controls(0.0)
    high_bass, high_rhythm = _activity_controls(1.0)
    assert low_bass.activity < high_bass.activity
    assert low_rhythm.activity < high_rhythm.activity
    assert 0.0 <= low_bass.activity <= 1.0
    assert 0.0 <= high_rhythm.activity <= 1.0


def test_surprise_target_selects_ranked_candidate() -> None:
    candidates = [
        MachineCandidate(seed=1, result=None, mean_surprise_bits=3.0),  # type: ignore[arg-type]
        MachineCandidate(seed=2, result=None, mean_surprise_bits=1.0),  # type: ignore[arg-type]
        MachineCandidate(seed=3, result=None, mean_surprise_bits=2.0),  # type: ignore[arg-type]
    ]
    assert choose_candidate_by_surprise(candidates, 0.0).seed == 2
    assert choose_candidate_by_surprise(candidates, 0.5).seed == 3
    assert choose_candidate_by_surprise(candidates, 1.0).seed == 1


def test_next_root_seed_is_deterministic_and_moves() -> None:
    first = next_root_seed(1234)
    assert first == next_root_seed(1234)
    assert first != 1234


def _fake_result(config):
    trace = {
        "tune_decisions": [
            {"selected": {"surprise_bits": float(config.seed % 10 + 1)}}
        ],
        "validation": {"passed": True, "checks": {}},
        "metrics": {},
        "voices": {"TUNE": [], "BASS": [], "RHYTHM": []},
    }
    return SimpleNamespace(config=config, trace=trace, voices=())


def test_hold_pins_selected_seed_across_activity_changes() -> None:
    engine = MachineEngine(candidate_count=3, compose_fn=_fake_result)
    initial = engine.render(
        root_seed=99,
        controls=MachineControls(activity=0.2, surprise=1.0),
    )
    held = engine.render(
        root_seed=99,
        controls=MachineControls(activity=0.9, surprise=0.0, hold=True),
        held_seed=initial.selected_seed,
    )
    assert held.selected_seed == initial.selected_seed
    assert held.held_seed == initial.selected_seed


def test_finish_writes_midi_wav_trace_and_manifest(tmp_path: Path) -> None:
    engine = MachineEngine(candidate_count=1)
    snapshot = engine.render(
        root_seed=2026081704,
        controls=MachineControls(),
    )
    paths = finish_snapshot(snapshot, tmp_path)
    assert set(paths) == {"midi", "wav", "trace", "manifest"}
    assert Path(paths["midi"]).read_bytes().startswith(b"MThd")
    assert Path(paths["wav"]).read_bytes().startswith(b"RIFF")
    assert '"machine_version": "0"' in Path(paths["manifest"]).read_text(
        encoding="utf-8"
    )

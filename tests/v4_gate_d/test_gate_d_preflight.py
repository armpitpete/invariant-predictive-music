from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import render_real_synth_v4_gate_d as gate_d


def test_gate_c_pass_is_frozen_before_gate_d():
    result = json.loads((ROOT / gate_d.GATE_C_RESULT_PATH).read_text(encoding="utf-8"))
    assert result["status"] == "PASS"
    assert result["owner_judgment"] == "PASS"
    assert result["pre_audition_render_head"] == gate_d.GATE_C_PRE_AUDITION_HEAD
    assert result["implementation_commit"] == gate_d.EXPECTED_IMPLEMENTATION_COMMIT


def test_plain_tune_is_pre_v4_and_exact():
    payload = gate_d.load_frozen_ledger(ROOT)
    assert payload["tune_event_count"] == 122
    assert payload["tune_event_ledger_sha256"] == gate_d.EXPECTED_LEDGER_SHA256
    assert payload["historic_source"]["selected_seed"] == 1693196453


def test_gate_d_does_not_reenter_composition_selection():
    text = (ROOT / "scripts/render_real_synth_v4_gate_d.py").read_text(encoding="utf-8")
    forbidden = ("MachineEngine", "candidate_count", "selected_seed =", "from ipm.engine", "from ipm.machine", "A5")
    for token in forbidden:
        assert token not in text


def test_gate_ab_engine_bytes_remain_exact():
    provenance = gate_d.verify_provenance(ROOT)
    assert provenance["implementation_commit"] == gate_d.EXPECTED_IMPLEMENTATION_COMMIT
    assert len(provenance["source_sha256"]) == 9


def test_static_is_exact_gate_c_modal_and_only_evolution_differs():
    static, evolving = gate_d.gate_d_patches()
    static_dict = gate_d.patch_to_dict(static)
    evolving_dict = gate_d.patch_to_dict(evolving)
    assert gate_d._canonical_sha(static_dict) == gate_d.EXPECTED_GATE_C_MODAL_PATCH_SHA256
    assert {key for key in static_dict if static_dict[key] != evolving_dict[key]} == {"evolution"}
    assert static.evolution == ()


def test_evolving_has_nonzero_note_phrase_piece_scopes():
    _, evolving = gate_d.gate_d_patches()
    assert {curve.scope for curve in evolving.evolution} == {"note", "phrase", "piece"}
    for curve in evolving.evolution:
        values = [value for _, value in curve.anchors]
        assert max(values) != min(values)
        assert any(value != 0 for value in values)


def test_written_schedule_identical_and_contains_only_notes():
    payload = gate_d.load_frozen_ledger(ROOT)
    events, total = gate_d.written_note_events(payload)
    assert len(events) == 244
    assert total > 0
    assert {event.kind for event in events} == {"note_on", "note_off"}
    assert gate_d._canonical_sha(payload["tune_events"]) == gate_d.EXPECTED_LEDGER_SHA256


def test_short_stateful_render_is_finite_nonzero_and_evolution_changes_audio():
    static, evolving = gate_d.gate_d_patches()
    events = [
        gate_d.ScheduledEventV4(0, "note_on", ("test", "TUNE", 60, 100)),
        gate_d.ScheduledEventV4(gate_d.SAMPLE_RATE, "note_off", ("test",)),
    ]
    frames = gate_d.SAMPLE_RATE * 2
    kwargs = dict(tempo=58.0, beats_per_bar=4, bars=16, collect_transport=False)
    a, _ = gate_d.render_condition(static, events, frames, **kwargs)
    b, _ = gate_d.render_condition(evolving, events, frames, **kwargs)
    assert a.shape == b.shape == (2, frames)
    assert np.isfinite(a).all() and np.isfinite(b).all()
    assert np.any(a) and np.any(b)
    assert not np.array_equal(a, b)

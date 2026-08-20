from __future__ import annotations

import inspect
from pathlib import Path

import numpy as np

import scripts.render_real_synth_v4_gate_c as gate_c
from ipm.real_synth_v4 import OfflineHostV4, ScheduledEventV4, technical_bank


def test_gate_c_committed_ledger_is_exact_and_pre_v4():
    root = Path(__file__).resolve().parents[2]
    payload = gate_c.load_frozen_ledger(root)
    assert payload["historic_source"]["root_seed"] == 987762706
    assert payload["historic_source"]["selected_seed"] == 1693196453
    assert payload["tempo_bpm"] == 58
    assert payload["bars"] == 16
    assert payload["beats_per_bar"] == 4
    assert payload["tune_event_count"] == 122
    assert payload["tune_event_ledger_sha256"] == gate_c.EXPECTED_LEDGER_SHA256
    assert gate_c._canonical_sha(payload["tune_events"]) == gate_c.EXPECTED_LEDGER_SHA256


def test_gate_c_render_path_cannot_reenter_composition_or_selection():
    source = inspect.getsource(gate_c)
    lowered = source.lower()
    assert "from ipm.engine" not in lowered
    assert "import ipm.engine" not in lowered
    assert "machineengine" not in lowered
    assert "compose(" not in lowered
    assert "candidate_selection" not in lowered
    assert "select_seed" not in lowered


def test_gate_c_uses_exact_gate_ab_engine_bytes():
    root = Path(__file__).resolve().parents[2]
    provenance = gate_c.verify_gate_ab_engine_bytes(root)
    assert provenance["implementation_commit"] == gate_c.EXPECTED_IMPLEMENTATION_COMMIT
    assert provenance["freeze_commit"] == gate_c.GATE_AB_FREEZE_COMMIT
    assert len(provenance["source_sha256"]) == 9


def test_gate_c_reference_patches_are_dry_orthogonal_and_evolution_free():
    patches = gate_c.reference_patches()
    assert set(patches) == {"VA", "FM", "MODAL"}
    checks = gate_c.validate_family_fixtures(patches)
    assert len({checks[name]["patch_sha256"] for name in checks}) == 3
    for family in checks:
        assert checks[family]["space"] <= 0.20
        assert checks[family]["chorus_wet"] <= 0.10
        assert checks[family]["delay_wet"] <= 0.10
        assert checks[family]["reverb_wet"] == 0.0


def test_gate_c_schedule_is_one_transport_plus_same_122_note_pairs():
    root = Path(__file__).resolve().parents[2]
    payload = gate_c.load_frozen_ledger(root)
    events, total_frames = gate_c.scheduled_events(payload)
    assert len(events) == 1 + 2 * 122
    assert events[0].kind == "transport" and events[0].sample == 0
    assert sum(event.kind == "note_on" for event in events) == 122
    assert sum(event.kind == "note_off" for event in events) == 122
    assert total_frames > max(event.sample for event in events)


def test_gate_c_blind_order_is_frozen_permutation_without_duplication():
    first = gate_c.blind_order()
    second = gate_c.blind_order()
    assert first == second
    assert sorted(first) == ["FM", "MODAL", "VA"]
    assert len(set(first)) == 3


def test_gate_c_family_topologies_generate_finite_distinct_mechanical_output():
    event = [
        ScheduledEventV4(0, "transport", (58, 0.0, 0.0, 0.0, 0.0)),
        ScheduledEventV4(1, "note_on", ("probe", "TUNE", 60, 96)),
        ScheduledEventV4(1600, "note_off", ("probe",)),
    ]
    hashes = []
    for patch in gate_c.reference_patches().values():
        audio = OfflineHostV4(
            sample_rate=gate_c.SAMPLE_RATE,
            block_size=gate_c.BLOCK_SIZE,
        ).render(technical_bank(patch), event, 2400)
        assert np.all(np.isfinite(audio))
        assert np.any(np.abs(audio) > 0)
        hashes.append(gate_c._sha256_bytes(OfflineHostV4.pcm16_bytes(audio)))
    assert len(set(hashes)) == 3

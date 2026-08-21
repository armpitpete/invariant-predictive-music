from __future__ import annotations

import json

from scripts.materialize_real_synth_v4_gate_c_fixture import (
    EXPECTED_BEATS_PER_BAR,
    EXPECTED_BARS,
    EXPECTED_TEMPO_BPM,
    EXPECTED_TUNE_EVENT_COUNT,
    EXPECTED_TUNE_LEDGER_SHA256,
    GATE_AB_FREEZE_COMMIT,
    V4_IMPLEMENTATION_COMMIT,
    event_ledger,
    ledger_sha256,
    materialise,
)


def test_gate_c_historic_tune_ledger_is_exact():
    config, ledger = event_ledger()
    assert config.tempo_bpm == EXPECTED_TEMPO_BPM
    assert config.bars == EXPECTED_BARS
    assert config.beats_per_bar == EXPECTED_BEATS_PER_BAR
    assert len(ledger) == EXPECTED_TUNE_EVENT_COUNT
    assert ledger_sha256(ledger) == EXPECTED_TUNE_LEDGER_SHA256


def test_gate_c_materialiser_is_non_audition_and_provenance_bound(tmp_path):
    out = materialise(tmp_path / "ledger.json")
    payload = json.loads(out.read_text())
    assert payload["human_audition_performed"] is False
    assert payload["audio_created"] is False
    assert payload["v4_implementation_commit"] == V4_IMPLEMENTATION_COMMIT
    assert payload["gate_ab_freeze_commit"] == GATE_AB_FREEZE_COMMIT
    assert payload["tune_event_count"] == EXPECTED_TUNE_EVENT_COUNT
    assert payload["tune_event_ledger_sha256"] == EXPECTED_TUNE_LEDGER_SHA256
    assert "must not invoke MachineEngine" in payload["boundary"]

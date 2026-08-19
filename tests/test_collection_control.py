import json
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from ipm.collection_control import audit, ingest, init_store, reserve, sha256_bytes, validate_export


def write_export(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data, indent=2) + "\n")
    return path


def shift_enrolment(export: dict, timestamp: str) -> dict:
    item = deepcopy(export)
    old = item["enrolled_at_utc"]
    item["enrolled_at_utc"] = timestamp
    changed_main = False
    changed_play = False
    for event in item["audit"]:
        if event["event"] == "main_block_started" and event.get("at") == old and not changed_main:
            event["at"] = timestamp
            changed_main = True
        if event["event"] == "playback_started" and event.get("at") == old and not changed_play:
            event["at"] = timestamp
            changed_play = True
    assert changed_main and changed_play
    return item


def offset_utc(timestamp: str, *, hours: int) -> str:
    value = datetime.fromisoformat(timestamp.replace("Z", "+00:00")) + timedelta(hours=hours)
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def test_reservation_is_single_use(tmp_path, participant_bundle):
    db = tmp_path / "control.sqlite3"
    init_store(db, participant_bundle)
    row = reserve(db, "P001", "invite-001", "synthetic")
    assert row["status"] == "reserved"
    with pytest.raises(ValueError, match="already reserved"):
        reserve(db, "P001", "invite-002", "synthetic")
    with pytest.raises(ValueError, match="must not contain an email"):
        reserve(db, "P002", "person@example.com", "email")
    with pytest.raises(ValueError, match="already bound"):
        reserve(db, "P002", "invite-001", "synthetic")


def test_complete_export_validates_against_frozen_schedule(participant_bundle, synthetic_exports):
    export = json.loads((synthetic_exports / "P001-synthetic-export.json").read_text())
    result = validate_export(participant_bundle, export)
    assert result["participant_id"] == "P001"
    assert result["terminal_state"] == "complete"
    assert result["participant_interface_source_revision"] == export["participant_interface_source_revision"]

    old_version = deepcopy(export)
    old_version["export_version"] = 1
    old_version.pop("participant_interface_source_revision", None)
    with pytest.raises(ValueError, match="unexpected export version"):
        validate_export(participant_bundle, old_version)

    wrong_revision = deepcopy(export)
    wrong_revision["participant_interface_source_revision"] = "0" * 40
    with pytest.raises(ValueError, match="participant interface revision mismatch"):
        validate_export(participant_bundle, wrong_revision)

    bad = deepcopy(export)
    bad["responses"][0]["stimulus_id"] = "stim-tampered"
    with pytest.raises(ValueError, match="response CSV content|response order"):
        validate_export(participant_bundle, bad)


def test_ingest_requires_central_reservation(tmp_path, participant_bundle, synthetic_exports):
    db = tmp_path / "control.sqlite3"
    init_store(db, participant_bundle)
    with pytest.raises(ValueError, match="not been centrally reserved"):
        ingest(db, participant_bundle, tmp_path / "store", synthetic_exports / "P001-synthetic-export.json")


def test_cross_device_duplicates_preserve_all_and_keep_earliest_enrolment(tmp_path, participant_bundle, synthetic_exports):
    db = tmp_path / "control.sqlite3"
    store = tmp_path / "store"
    init_store(db, participant_bundle)
    reserve(db, "P001", "invite-001", "synthetic")
    original_path = synthetic_exports / "P001-synthetic-export.json"
    original = json.loads(original_path.read_text())
    original_sha = sha256_bytes(original_path.read_bytes())
    first = ingest(db, participant_bundle, store, original_path)
    assert first["canonical_export_sha256"] == original_sha

    later_timestamp = offset_utc(original["enrolled_at_utc"], hours=1)
    later_path = write_export(tmp_path / "later.json", shift_enrolment(original, later_timestamp))
    later_sha = sha256_bytes(later_path.read_bytes())
    second = ingest(db, participant_bundle, store, later_path)
    assert second["duplicate_participation"] is True
    assert second["canonical_export_sha256"] == original_sha

    earlier_timestamp = offset_utc(original["enrolled_at_utc"], hours=-1)
    earlier_path = write_export(tmp_path / "earlier.json", shift_enrolment(original, earlier_timestamp))
    earlier_sha = sha256_bytes(earlier_path.read_bytes())
    third = ingest(db, participant_bundle, store, earlier_path)
    assert third["canonical_export_sha256"] == earlier_sha
    assert third["enrolled_submission_count"] == 3
    for digest in (original_sha, later_sha, earlier_sha):
        assert (store / "submissions" / "P001" / f"{digest}.json").exists()
    report = audit(db)
    assert report["participants_with_duplicate_enrolled_submissions"] == ["P001"]
    assert report["submission_count"] == 3


@pytest.fixture
def participant_bundle():
    import os

    value = Path(os.environ.get("IPM_PARTICIPANT_BUNDLE", "participant-web"))
    if not value.exists():
        pytest.skip("participant bundle not supplied")
    return value


@pytest.fixture
def synthetic_exports():
    import os

    value = Path(os.environ.get("IPM_SYNTHETIC_EXPORTS", "participant-browser-acceptance"))
    if not value.exists():
        pytest.skip("synthetic browser exports not supplied")
    return value

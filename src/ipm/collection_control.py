from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TERMINAL_STATES = {"complete", "technical-failure", "withdrawn"}
RATING_FIELDS = (
    "retrospective_sense_0_100",
    "surprise_0_100",
    "coherence_0_100",
    "liking_0_100",
    "hear_again_0_100",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_utc(value: str | None) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError("timestamp must be a non-empty UTC ISO-8601 string or null")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def open_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA journal_mode = WAL")
    return db


def load_schedules(bundle_dir: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for filename in sorted((bundle_dir / "schedules").glob("P[0-9][0-9][0-9].json")):
        item = json.loads(filename.read_text())
        pid = item["participant_id"]
        if pid in result:
            raise ValueError(f"duplicate schedule for {pid}")
        result[pid] = item
    if set(result) != {f"P{i:03d}" for i in range(1, 37)}:
        raise ValueError("bundle must contain exactly P001-P036 schedules")
    return result


def init_store(db_path: Path, bundle_dir: Path) -> None:
    schedules = load_schedules(bundle_dir)
    with open_db(db_path) as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS participants (
                participant_id TEXT PRIMARY KEY,
                counterbalance_group INTEGER NOT NULL,
                source_schedule_sha256 TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'available',
                reserved_at_utc TEXT,
                invitation_reference TEXT UNIQUE,
                invitation_channel TEXT,
                canonical_enrolled_at_utc TEXT,
                canonical_export_sha256 TEXT,
                canonical_terminal_state TEXT,
                submission_count INTEGER NOT NULL DEFAULT 0,
                enrolled_submission_count INTEGER NOT NULL DEFAULT 0,
                last_submission_at_utc TEXT
            );
            CREATE TABLE IF NOT EXISTS submissions (
                export_sha256 TEXT PRIMARY KEY,
                participant_id TEXT NOT NULL REFERENCES participants(participant_id),
                received_at_utc TEXT NOT NULL,
                enrolled_at_utc TEXT,
                terminal_state TEXT NOT NULL,
                source_schedule_sha256 TEXT NOT NULL,
                raw_relative_path TEXT NOT NULL UNIQUE
            );
            """
        )
        for pid, schedule in schedules.items():
            db.execute(
                """
                INSERT INTO participants(participant_id, counterbalance_group, source_schedule_sha256)
                VALUES(?,?,?)
                ON CONFLICT(participant_id) DO UPDATE SET
                  counterbalance_group=excluded.counterbalance_group,
                  source_schedule_sha256=excluded.source_schedule_sha256
                """,
                (pid, schedule["counterbalance_group"], schedule["source_schedule_sha256"]),
            )


def reserve(db_path: Path, participant_id: str, invitation_reference: str, invitation_channel: str) -> dict[str, Any]:
    if "@" in invitation_reference or not invitation_reference.strip():
        raise ValueError("invitation_reference must be opaque and must not contain an email address")
    if not invitation_channel.strip():
        raise ValueError("invitation_channel is required")
    now = utc_now()
    with open_db(db_path) as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM participants WHERE participant_id=?", (participant_id,)).fetchone()
        if row is None:
            raise ValueError(f"unknown participant ID {participant_id}")
        if row["status"] != "available":
            raise ValueError(f"{participant_id} is already {row['status']}")
        prior = db.execute("SELECT participant_id FROM participants WHERE invitation_reference=?", (invitation_reference,)).fetchone()
        if prior is not None:
            raise ValueError(f"invitation_reference is already bound to {prior['participant_id']}")
        db.execute(
            """
            UPDATE participants
            SET status='reserved', reserved_at_utc=?, invitation_reference=?, invitation_channel=?
            WHERE participant_id=?
            """,
            (now, invitation_reference, invitation_channel, participant_id),
        )
        db.commit()
        return dict(db.execute("SELECT * FROM participants WHERE participant_id=?", (participant_id,)).fetchone())


def _csv_rows(text: str) -> tuple[list[str], list[dict[str, str]]]:
    reader = csv.DictReader(text.splitlines())
    return list(reader.fieldnames or []), list(reader)


def _as_csv_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def validate_export(bundle_dir: Path, export: dict[str, Any]) -> dict[str, Any]:
    config = json.loads((bundle_dir / "config.json").read_text())
    pid = export.get("participant_id")
    schedule_path = bundle_dir / "schedules" / f"{pid}.json"
    if not isinstance(pid, str) or not schedule_path.exists():
        raise ValueError("export participant_id is not a frozen P001-P036 ID")
    schedule = json.loads(schedule_path.read_text())
    if export.get("export_version") != 1:
        raise ValueError("unexpected export version")
    if export.get("frozen_listener_artifact") != config["frozen_listener_artifact"]:
        raise ValueError("frozen listener artifact identity mismatch")
    if export.get("source_schedule_sha256") != schedule["source_schedule_sha256"]:
        raise ValueError("source schedule hash mismatch")
    participant = export.get("participant") or {}
    if participant.get("participant_id") != pid:
        raise ValueError("participant row ID mismatch")
    if participant.get("counterbalance_group") != schedule["counterbalance_group"]:
        raise ValueError("counterbalance group mismatch")
    for field in ("duplicate_participation", "record_usable", "exclusion_reason"):
        if participant.get(field) != "":
            raise ValueError(f"participant-side researcher field {field} must be blank on intake")
    participant_header, participant_rows = _csv_rows(export.get("participant_csv", ""))
    response_header, response_csv_rows = _csv_rows(export.get("responses_csv", ""))
    if participant_header != config["participant_schema_header"].split(",") or len(participant_rows) != 1:
        raise ValueError("participant CSV schema mismatch")
    if response_header != config["response_schema_header"].split(","):
        raise ValueError("response CSV schema mismatch")
    if participant_rows[0] != {field: _as_csv_text(participant.get(field)) for field in participant_header}:
        raise ValueError("participant CSV content does not match JSON participant row")
    terminal = export.get("terminal_state")
    if terminal not in TERMINAL_STATES:
        raise ValueError("only terminal exports are accepted for return")

    responses = export.get("responses")
    audit = export.get("audit")
    if not isinstance(responses, list) or not isinstance(audit, list):
        raise ValueError("responses and audit must be lists")
    if len(responses) > 12:
        raise ValueError("too many response rows")
    expected_csv_rows = [{field: _as_csv_text(row.get(field)) for field in response_header} for row in responses]
    if response_csv_rows != expected_csv_rows:
        raise ValueError("response CSV content does not match JSON response rows")
    expected_prefix = schedule["trials"][: len(responses)]
    for row, trial in zip(responses, expected_prefix):
        if row.get("participant_id") != pid or row.get("trial") != trial["trial"] or row.get("stimulus_id") != trial["stimulus_id"]:
            raise ValueError("response order or stimulus identity drifted from frozen schedule")
        for field in RATING_FIELDS:
            value = row.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 100:
                raise ValueError(f"invalid rating {field}")

    enrolled = export.get("enrolled_at_utc")
    enrolled_dt = parse_utc(enrolled)
    playback_starts = [event for event in audit if event.get("event") == "playback_started"]
    main_starts = [event for event in audit if event.get("event") == "main_block_started"]
    if enrolled_dt is None:
        if playback_starts or main_starts:
            raise ValueError("unenrolled export cannot contain main-block start events")
    else:
        if not main_starts or not playback_starts:
            raise ValueError("enrolled export is missing main-block/playback start audit")
        if main_starts[0].get("at") != enrolled or playback_starts[0].get("at") != enrolled:
            raise ValueError("enrolment boundary does not equal first main-block playback start")
        expected_played = schedule["trials"][: len(playback_starts)]
        for event, trial in zip(playback_starts, expected_played):
            if event.get("trial") != trial["trial"] or event.get("stimulus_id") != trial["stimulus_id"] or event.get("wav_sha256") != trial["wav_sha256"]:
                raise ValueError("playback audit drifted from frozen schedule or WAV hash")
    for event_name in ("playback_completed", "ratings_submitted"):
        events = [event for event in audit if event.get("event") == event_name]
        expected_events = schedule["trials"][: len(events)]
        for event, trial in zip(events, expected_events):
            if event.get("trial") != trial["trial"] or event.get("stimulus_id") != trial["stimulus_id"]:
                raise ValueError(f"{event_name} audit drifted from frozen schedule")
    rating_events = [event for event in audit if event.get("event") == "ratings_submitted"]
    if len(rating_events) != len(responses):
        raise ValueError("ratings audit count does not equal response count")

    if terminal == "complete":
        if enrolled_dt is None or len(responses) != 12 or len(playback_starts) != 12:
            raise ValueError("complete export must contain one enrolled 12-trial main block")
        if participant.get("completed_main_block") != "true" or participant.get("playback_failure") != "false":
            raise ValueError("complete participant flags are inconsistent")
    return {"participant_id": pid, "schedule": schedule, "terminal_state": terminal, "enrolled_at_utc": enrolled}


def _refresh_participant(db: sqlite3.Connection, participant_id: str) -> None:
    rows = db.execute(
        "SELECT * FROM submissions WHERE participant_id=? ORDER BY CASE WHEN enrolled_at_utc IS NULL THEN 1 ELSE 0 END, enrolled_at_utc, received_at_utc, export_sha256",
        (participant_id,),
    ).fetchall()
    enrolled = [row for row in rows if row["enrolled_at_utc"] is not None]
    canonical = enrolled[0] if enrolled else None
    status = "received-enrolled" if canonical else ("received-unenrolled" if rows else "reserved")
    db.execute(
        """
        UPDATE participants SET status=?, canonical_enrolled_at_utc=?, canonical_export_sha256=?,
          canonical_terminal_state=?, submission_count=?, enrolled_submission_count=?, last_submission_at_utc=?
        WHERE participant_id=?
        """,
        (
            status,
            canonical["enrolled_at_utc"] if canonical else None,
            canonical["export_sha256"] if canonical else None,
            canonical["terminal_state"] if canonical else None,
            len(rows),
            len(enrolled),
            max((row["received_at_utc"] for row in rows), default=None),
            participant_id,
        ),
    )


def ingest(db_path: Path, bundle_dir: Path, store_dir: Path, export_path: Path) -> dict[str, Any]:
    raw = export_path.read_bytes()
    digest = sha256_bytes(raw)
    export = json.loads(raw)
    validated = validate_export(bundle_dir, export)
    pid = validated["participant_id"]
    now = utc_now()
    relative = Path("submissions") / pid / f"{digest}.json"
    destination = store_dir / relative

    with open_db(db_path) as db:
        db.execute("BEGIN IMMEDIATE")
        participant = db.execute("SELECT * FROM participants WHERE participant_id=?", (pid,)).fetchone()
        if participant is None:
            raise ValueError(f"unknown participant ID {pid}")
        if participant["reserved_at_utc"] is None:
            raise ValueError(f"{pid} has not been centrally reserved/issued")
        existing = db.execute("SELECT * FROM submissions WHERE export_sha256=?", (digest,)).fetchone()
        if existing is None:
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists() and destination.read_bytes() != raw:
                raise ValueError("content-addressed destination collision")
            if not destination.exists():
                destination.write_bytes(raw)
            db.execute(
                """
                INSERT INTO submissions(export_sha256,participant_id,received_at_utc,enrolled_at_utc,terminal_state,source_schedule_sha256,raw_relative_path)
                VALUES(?,?,?,?,?,?,?)
                """,
                (digest, pid, now, validated["enrolled_at_utc"], validated["terminal_state"], export["source_schedule_sha256"], str(relative)),
            )
        elif existing["participant_id"] != pid:
            raise ValueError("export SHA already belongs to another participant")
        _refresh_participant(db, pid)
        db.commit()
        participant = dict(db.execute("SELECT * FROM participants WHERE participant_id=?", (pid,)).fetchone())
        participant["duplicate_participation"] = participant["enrolled_submission_count"] > 1
        participant["ingested_export_sha256"] = digest
        participant["raw_relative_path"] = str(relative)
        return participant


def audit(db_path: Path) -> dict[str, Any]:
    with open_db(db_path) as db:
        participants = [dict(row) for row in db.execute("SELECT * FROM participants ORDER BY participant_id")]
        submissions = [dict(row) for row in db.execute("SELECT * FROM submissions ORDER BY participant_id, received_at_utc, export_sha256")]
    return {
        "participant_count": len(participants),
        "available": sum(row["status"] == "available" for row in participants),
        "reserved_or_received": sum(row["status"] != "available" for row in participants),
        "submission_count": len(submissions),
        "participants_with_duplicate_enrolled_submissions": [row["participant_id"] for row in participants if row["enrolled_submission_count"] > 1],
        "participants": participants,
        "submissions": submissions,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Researcher-side IPM participant reservation and response intake control")
    sub = parser.add_subparsers(dest="command", required=True)
    p_init = sub.add_parser("init")
    p_init.add_argument("--db", type=Path, required=True)
    p_init.add_argument("--bundle", type=Path, required=True)
    p_reserve = sub.add_parser("reserve")
    p_reserve.add_argument("--db", type=Path, required=True)
    p_reserve.add_argument("--participant-id", required=True)
    p_reserve.add_argument("--invitation-reference", required=True)
    p_reserve.add_argument("--invitation-channel", required=True)
    p_ingest = sub.add_parser("ingest")
    p_ingest.add_argument("--db", type=Path, required=True)
    p_ingest.add_argument("--bundle", type=Path, required=True)
    p_ingest.add_argument("--store", type=Path, required=True)
    p_ingest.add_argument("--export", type=Path, required=True)
    p_audit = sub.add_parser("audit")
    p_audit.add_argument("--db", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "init":
        init_store(args.db, args.bundle)
        result = audit(args.db)
    elif args.command == "reserve":
        result = reserve(args.db, args.participant_id, args.invitation_reference, args.invitation_channel)
    elif args.command == "ingest":
        result = ingest(args.db, args.bundle, args.store, args.export)
    else:
        result = audit(args.db)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

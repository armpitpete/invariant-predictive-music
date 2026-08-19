"""Participant-facing build and dry-run gate for Listening Experiment 1.

This module is experiment/protocol-layer only. It takes a rendered listening-pilot
artifact, verifies it byte-for-byte against the frozen participant contract, and
builds a standalone participant-safe web bundle containing only opaque schedules,
WAV stimuli, schemas, and the study UI. Researcher condition keys and qualification
metadata are intentionally excluded.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

_UI_FILES = ("index.html", "app.js", "protocol.mjs", "style.css")
_FORBIDDEN_PARTICIPANT_LABELS = ("unstructured-surprise", "predictable")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _read_schedule(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or tuple(rows[0].keys()) != ("trial", "stimulus_id"):
        raise ValueError(f"invalid participant schedule schema: {path}")
    return rows


def verify_frozen_participant_contract(
    pilot_dir: str | Path,
    contract_path: str | Path,
) -> dict[str, Any]:
    """Fail unless current pilot assets match the frozen pre-listening contract."""

    pilot = Path(pilot_dir)
    contract = _load_json(Path(contract_path))
    participant_ids = tuple(contract["participant_ids"])
    expected_ids = tuple(f"P{index:03d}" for index in range(1, 37))
    if participant_ids != expected_ids:
        raise AssertionError("participant ID set is not exactly P001-P036")

    participant_schema = pilot / "participant-schema.csv"
    response_schema = pilot / "response-schema.csv"
    if _sha256_file(participant_schema) != contract["participant_schema_sha256"]:
        raise AssertionError("participant schema drifted from frozen artifact")
    if _sha256_file(response_schema) != contract["response_schema_sha256"]:
        raise AssertionError("response schema drifted from frozen artifact")

    actual_wavs = sorted(path.name for path in (pilot / "stimuli").glob("*.wav"))
    expected_wavs = sorted(contract["stimulus_wav_sha256"])
    if actual_wavs != expected_wavs:
        raise AssertionError("participant WAV set drifted from frozen artifact")
    for filename, expected_hash in contract["stimulus_wav_sha256"].items():
        actual = _sha256_file(pilot / "stimuli" / filename)
        if actual != expected_hash:
            raise AssertionError(f"frozen WAV hash mismatch: {filename}")

    assignment_path = pilot / "researcher" / "participant-assignments.csv"
    with assignment_path.open("r", encoding="utf-8", newline="") as handle:
        assignments = {
            row["participant_id"]: int(row["counterbalance_group"])
            for row in csv.DictReader(handle)
        }
    if assignments != {
        participant_id: int(group)
        for participant_id, group in contract["counterbalance_group"].items()
    }:
        raise AssertionError("counterbalance assignments drifted from frozen artifact")

    all_stimuli: set[str] = set()
    schedule_records: dict[str, list[dict[str, str]]] = {}
    for participant_id in participant_ids:
        filename = f"{participant_id}.csv"
        schedule_path = pilot / "participant-schedules" / filename
        if _sha256_file(schedule_path) != contract["schedule_sha256"][filename]:
            raise AssertionError(f"frozen schedule hash mismatch: {filename}")
        rows = _read_schedule(schedule_path)
        if len(rows) != 12:
            raise AssertionError(f"{participant_id} does not have exactly 12 trials")
        if [int(row["trial"]) for row in rows] != list(range(1, 13)):
            raise AssertionError(f"{participant_id} trial numbering drifted")
        stimulus_ids = [row["stimulus_id"] for row in rows]
        if len(set(stimulus_ids)) != 12:
            raise AssertionError(f"{participant_id} repeats a stimulus")
        for stimulus_id in stimulus_ids:
            if f"{stimulus_id}.wav" not in contract["stimulus_wav_sha256"]:
                raise AssertionError(f"unknown frozen stimulus in {participant_id}: {stimulus_id}")
        all_stimuli.update(stimulus_ids)
        schedule_records[participant_id] = rows

    if len(all_stimuli) != 36:
        raise AssertionError("participant schedules do not cover exactly 36 opaque stimuli")

    return {
        "participant_ids": participant_ids,
        "assignments": assignments,
        "schedules": schedule_records,
        "contract": contract,
    }


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build_participant_web(
    pilot_dir: str | Path,
    *,
    ui_dir: str | Path,
    contract_path: str | Path,
    output_dir: str | Path,
    source_revision: str = "unknown",
) -> Path:
    """Build a standalone participant-safe web bundle from verified frozen assets."""

    pilot = Path(pilot_dir)
    ui = Path(ui_dir)
    output = Path(output_dir)
    if output.exists():
        raise FileExistsError(f"participant output already exists: {output}")

    verified = verify_frozen_participant_contract(pilot, contract_path)
    contract = verified["contract"]
    output.mkdir(parents=True)
    (output / "schedules").mkdir()
    (output / "stimuli").mkdir()
    (output / "schemas").mkdir()

    for name in _UI_FILES:
        source = ui / name
        if not source.is_file():
            raise FileNotFoundError(source)
        shutil.copyfile(source, output / name)

    for filename in sorted(contract["stimulus_wav_sha256"]):
        shutil.copyfile(pilot / "stimuli" / filename, output / "stimuli" / filename)

    shutil.copyfile(pilot / "participant-schema.csv", output / "schemas" / "participant-schema.csv")
    shutil.copyfile(pilot / "response-schema.csv", output / "schemas" / "response-schema.csv")

    schedule_manifest: dict[str, str] = {}
    for participant_id in verified["participant_ids"]:
        rows = verified["schedules"][participant_id]
        schedule = {
            "participant_id": participant_id,
            "counterbalance_group": verified["assignments"][participant_id],
            "source_schedule_sha256": contract["schedule_sha256"][f"{participant_id}.csv"],
            "trials": [
                {
                    "trial": int(row["trial"]),
                    "stimulus_id": row["stimulus_id"],
                    "wav_sha256": contract["stimulus_wav_sha256"][f"{row['stimulus_id']}.wav"],
                }
                for row in rows
            ],
        }
        path = output / "schedules" / f"{participant_id}.json"
        _write_json(path, schedule)
        schedule_manifest[path.name] = _sha256_file(path)

    config = {
        "contract_version": contract["contract_version"],
        "participant_interface_source_revision": source_revision,
        "frozen_listener_artifact": contract["frozen_listener_artifact"],
        "participant_ids": list(verified["participant_ids"]),
        "consent": contract["consent"],
        "ratings": contract["ratings"],
        "participant_schema_header": contract["participant_schema_header"],
        "response_schema_header": contract["response_schema_header"],
        "runtime_contract": {
            "single_playback": True,
            "seek_disabled": True,
            "replay_disabled": True,
            "ratings_after_playback_end_only": True,
            "wav_sha256_verified_before_playback": True,
            "automatic_network_submission": False,
        },
    }
    _write_json(output / "config.json", config)

    # Participant-facing text/config/schedules must not expose the named comparison labels.
    for path in [output / "config.json", *(output / "schedules").glob("*.json")]:
        lowered = path.read_text(encoding="utf-8").lower()
        for forbidden in _FORBIDDEN_PARTICIPANT_LABELS:
            if forbidden in lowered:
                raise AssertionError(f"participant bundle leaks condition label {forbidden!r}: {path}")

    file_hashes: dict[str, str] = {}
    for path in sorted(item for item in output.rglob("*") if item.is_file()):
        relative = path.relative_to(output).as_posix()
        file_hashes[relative] = _sha256_file(path)
    bundle_manifest = {
        "bundle_contract_version": 1,
        "participant_interface_source_revision": source_revision,
        "source_frozen_listener_artifact": contract["frozen_listener_artifact"],
        "participant_count": 36,
        "trial_count_per_participant": 12,
        "unique_stimulus_count": 36,
        "schedule_json_sha256": schedule_manifest,
        "file_sha256": file_hashes,
    }
    _write_json(output / "bundle-manifest.json", bundle_manifest)
    return output


def dry_run_participant_web(
    participant_web_dir: str | Path,
    *,
    pilot_dir: str | Path,
    contract_path: str | Path,
) -> dict[str, Any]:
    """Exercise all 36 frozen schedules and export schemas without listener data."""

    web = Path(participant_web_dir)
    verified = verify_frozen_participant_contract(pilot_dir, contract_path)
    contract = verified["contract"]
    manifest = _load_json(web / "bundle-manifest.json")

    manifest_hashes = manifest["file_sha256"]
    for relative, expected in manifest_hashes.items():
        path = web / relative
        if _sha256_file(path) != expected:
            raise AssertionError(f"participant bundle file changed after build: {relative}")

    response_header = contract["response_schema_header"].split(",")
    participant_header = contract["participant_schema_header"].split(",")
    expected_response_header = [
        "participant_id",
        "trial",
        "stimulus_id",
        "retrospective_sense_0_100",
        "surprise_0_100",
        "coherence_0_100",
        "liking_0_100",
        "hear_again_0_100",
    ]
    if response_header != expected_response_header:
        raise AssertionError("response export schema no longer matches participant UI fields")
    if participant_header != [
        "participant_id",
        "counterbalance_group",
        "music_making_years",
        "formal_music_training_years",
        "completed_main_block",
        "playback_failure",
        "duplicate_participation",
        "record_usable",
        "exclusion_reason",
    ]:
        raise AssertionError("participant export schema drifted")

    total_trials = 0
    participant_results = []
    for participant_id in verified["participant_ids"]:
        schedule = _load_json(web / "schedules" / f"{participant_id}.json")
        if schedule["source_schedule_sha256"] != contract["schedule_sha256"][f"{participant_id}.csv"]:
            raise AssertionError(f"schedule provenance drifted: {participant_id}")
        if schedule["counterbalance_group"] != verified["assignments"][participant_id]:
            raise AssertionError(f"group drifted: {participant_id}")
        rows = []
        for item in schedule["trials"]:
            stimulus_id = item["stimulus_id"]
            wav = web / "stimuli" / f"{stimulus_id}.wav"
            expected_hash = contract["stimulus_wav_sha256"][wav.name]
            if item["wav_sha256"] != expected_hash or _sha256_file(wav) != expected_hash:
                raise AssertionError(f"runtime WAV hash contract failed: {participant_id} trial {item['trial']}")
            rows.append(
                {
                    "participant_id": participant_id,
                    "trial": item["trial"],
                    "stimulus_id": stimulus_id,
                    "retrospective_sense_0_100": 50,
                    "surprise_0_100": 50,
                    "coherence_0_100": 50,
                    "liking_0_100": 50,
                    "hear_again_0_100": 50,
                }
            )
        if len(rows) != 12:
            raise AssertionError(f"dry-run response count failed: {participant_id}")
        if [row["stimulus_id"] for row in rows] != [item["stimulus_id"] for item in schedule["trials"]]:
            raise AssertionError(f"dry-run response order drifted: {participant_id}")
        total_trials += len(rows)
        participant_results.append(
            {
                "participant_id": participant_id,
                "schedule_sha256": schedule["source_schedule_sha256"],
                "trial_count": len(rows),
                "export_header_exact": list(rows[0]) == response_header,
                "passed": list(rows[0]) == response_header,
            }
        )

    report = {
        "gate": "participant-facing implementation dry-run",
        "passed": all(item["passed"] for item in participant_results),
        "frozen_listener_artifact": contract["frozen_listener_artifact"],
        "participant_interface_source_revision": manifest["participant_interface_source_revision"],
        "participant_count": len(participant_results),
        "total_trial_count": total_trials,
        "unique_stimulus_count": len(contract["stimulus_wav_sha256"]),
        "schedule_hashes_verified": 36,
        "wav_hashes_verified": 36,
        "participant_schema_verified": True,
        "response_schema_verified": True,
        "condition_labels_exposed": False,
        "participants": participant_results,
    }
    if not report["passed"] or total_trials != 432:
        raise AssertionError("participant-facing dry-run failed")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Build and dry-run the frozen participant listening interface")
    parser.add_argument("--pilot-dir", default="listening-pilot")
    parser.add_argument("--ui-dir", default="participant-ui")
    parser.add_argument("--contract", default="participant-ui/frozen-participant-contract.json")
    parser.add_argument("--output", default="participant-web")
    parser.add_argument("--dry-run-report")
    parser.add_argument("--source-revision", default="unknown")
    args = parser.parse_args()

    output = build_participant_web(
        args.pilot_dir,
        ui_dir=args.ui_dir,
        contract_path=args.contract,
        output_dir=args.output,
        source_revision=args.source_revision,
    )
    if args.dry_run_report:
        report = dry_run_participant_web(output, pilot_dir=args.pilot_dir, contract_path=args.contract)
        report_path = Path(args.dry_run_report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        _write_json(report_path, report)
    print(output)


if __name__ == "__main__":
    main()

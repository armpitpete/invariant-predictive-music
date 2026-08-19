import csv
import hashlib
import json
from pathlib import Path

import pytest

from ipm.experiment_participant import (
    build_participant_web,
    dry_run_participant_web,
    verify_frozen_participant_contract,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path: Path, ui_dir: Path):
    pilot = tmp_path / "pilot"
    (pilot / "stimuli").mkdir(parents=True)
    (pilot / "participant-schedules").mkdir()
    (pilot / "researcher").mkdir()
    participant_header = "participant_id,counterbalance_group,music_making_years,formal_music_training_years,completed_main_block,playback_failure,duplicate_participation,record_usable,exclusion_reason\r\n"
    response_header = "participant_id,trial,stimulus_id,retrospective_sense_0_100,surprise_0_100,coherence_0_100,liking_0_100,hear_again_0_100\r\n"
    (pilot / "participant-schema.csv").write_text(participant_header, encoding="utf-8", newline="")
    (pilot / "response-schema.csv").write_text(response_header, encoding="utf-8", newline="")

    stimulus_hashes = {}
    for index in range(36):
        name = f"stim-{index:012x}.wav"
        (pilot / "stimuli" / name).write_bytes(f"fake-wav-{index}".encode())
        stimulus_hashes[name] = _sha(pilot / "stimuli" / name)

    schedule_hashes = {}
    groups = {}
    stimuli = [name[:-4] for name in sorted(stimulus_hashes)]
    for index in range(1, 37):
        participant_id = f"P{index:03d}"
        groups[participant_id] = ((index - 1) % 3) + 1
        selected = [stimuli[(index - 1 + offset) % 36] for offset in range(12)]
        schedule = pilot / "participant-schedules" / f"{participant_id}.csv"
        schedule.write_text(
            "trial,stimulus_id\r\n" + "".join(f"{trial},{stimulus}\r\n" for trial, stimulus in enumerate(selected, 1)),
            encoding="utf-8",
            newline="",
        )
        schedule_hashes[schedule.name] = _sha(schedule)

    with (pilot / "researcher" / "participant-assignments.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\r\n")
        writer.writerow(["participant_id", "counterbalance_group"])
        for participant_id, group in groups.items():
            writer.writerow([participant_id, group])

    contract = {
        "contract_version": 1,
        "frozen_listener_artifact": {"artifact_id": 1, "artifact_sha256": "x", "source_revision": "y", "workflow_run": 1},
        "consent": {
            "version": "v1",
            "title": "Music listening study",
            "information": ["Info"],
            "checks": [{"id": "consent", "text": "I agree"}],
            "headphones_check": "I am using headphones.",
        },
        "ratings": [
            {"field": field, "label": field, "prompt": field, "min_anchor": "low", "max_anchor": "high"}
            for field in [
                "retrospective_sense_0_100",
                "surprise_0_100",
                "coherence_0_100",
                "liking_0_100",
                "hear_again_0_100",
            ]
        ],
        "participant_ids": [f"P{i:03d}" for i in range(1, 37)],
        "counterbalance_group": groups,
        "stimulus_wav_sha256": stimulus_hashes,
        "schedule_sha256": schedule_hashes,
        "participant_schema_sha256": _sha(pilot / "participant-schema.csv"),
        "response_schema_sha256": _sha(pilot / "response-schema.csv"),
        "participant_schema_header": participant_header.strip(),
        "response_schema_header": response_header.strip(),
    }
    contract_path = tmp_path / "contract.json"
    contract_path.write_text(json.dumps(contract), encoding="utf-8")
    return pilot, contract_path


def test_build_and_dry_run_keep_frozen_schedules_hashes_and_schemas(tmp_path):
    ui_dir = Path(__file__).resolve().parents[1] / "participant-ui"
    pilot, contract = _fixture(tmp_path, ui_dir)
    verified = verify_frozen_participant_contract(pilot, contract)
    assert len(verified["participant_ids"]) == 36

    web = build_participant_web(pilot, ui_dir=ui_dir, contract_path=contract, output_dir=tmp_path / "web")
    report = dry_run_participant_web(web, pilot_dir=pilot, contract_path=contract)
    assert report["passed"] is True
    assert report["participant_count"] == 36
    assert report["total_trial_count"] == 432
    assert report["condition_labels_exposed"] is False
    assert not (web / "researcher").exists()


def test_frozen_wav_tamper_fails_before_participant_bundle_is_built(tmp_path):
    ui_dir = Path(__file__).resolve().parents[1] / "participant-ui"
    pilot, contract = _fixture(tmp_path, ui_dir)
    first = next((pilot / "stimuli").glob("*.wav"))
    first.write_bytes(first.read_bytes() + b"tamper")
    with pytest.raises(AssertionError, match="frozen WAV hash mismatch"):
        verify_frozen_participant_contract(pilot, contract)

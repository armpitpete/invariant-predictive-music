import json
from dataclasses import asdict

from ipm.engine import ExperimentMode
from ipm.product_gate import GATE_ID, build_portfolio, portfolio_specs


def test_working_product_matrix_is_fixed_before_listening():
    specs = portfolio_specs()
    assert len(specs) == 8
    assert [spec.piece_id for spec in specs] == [
        "a-default",
        "a-active",
        "b-default",
        "b-active",
        "c-default",
        "c-active",
        "d-default",
        "d-active",
    ]
    assert len({spec.seed for spec in specs}) == 4
    assert all(spec.config.mode is ExperimentMode.IPM for spec in specs)
    assert all(spec.config.bars == 16 for spec in specs)
    assert all(spec.config.tempo_bpm == 58 for spec in specs)
    assert all(spec.config.tonic_midi == 60 for spec in specs)


def test_active_profile_changes_only_subsidiary_activity():
    by_id = {spec.piece_id: spec for spec in portfolio_specs()}
    for seed_label in ("a", "b", "c", "d"):
        default = by_id[f"{seed_label}-default"].config
        active = by_id[f"{seed_label}-active"].config

        default_bass = asdict(default.bass)
        active_bass = asdict(active.bass)
        assert default_bass.pop("activity") == 0.46
        assert active_bass.pop("activity") == 0.62
        assert default_bass == active_bass

        default_rhythm = asdict(default.rhythm)
        active_rhythm = asdict(active.rhythm)
        assert default_rhythm.pop("activity") == 0.40
        assert active_rhythm.pop("activity") == 0.55
        assert default_rhythm == active_rhythm


def test_portfolio_generation_is_byte_deterministic_and_unreviewed(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first_manifest = build_portfolio(first, source_revision="fixed-revision")
    second_manifest = build_portfolio(second, source_revision="fixed-revision")

    assert first_manifest.read_bytes() == second_manifest.read_bytes()
    left = json.loads(first_manifest.read_text())
    right = json.loads(second_manifest.read_text())
    assert left == right
    assert left["gate_id"] == GATE_ID
    assert left["frozen_before_listening"] is True
    assert len(left["pieces"]) == 8
    assert all(piece["validation"]["passed"] for piece in left["pieces"])

    for piece in left["pieces"]:
        for field in ("midi", "trace"):
            left_path = first / piece[field]
            right_path = second / piece[field]
            assert left_path.read_bytes() == right_path.read_bytes()

    review = json.loads((first / "review-sheet.json").read_text())
    assert review["pass_rule"] == "8 SHOW / 0 FAIL"
    assert len(review["pieces"]) == 8
    assert all(piece["decision"] is None for piece in review["pieces"])

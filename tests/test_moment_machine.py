import json

from ipm.moment_machine import MomentSession


def test_demo_load_render_chain_and_reload(tmp_path):
    session = MomentSession(tmp_path)
    state = session.load_demos()
    assert len(state["slots"]) == 4

    rendered = session.render_slot(
        {"slot": 1, "repeats": 4, "evolve": 0.5, "surprise": 0.7}
    )
    assert rendered["render"]["length_beats"] == 8.0
    assert rendered["render"]["cycle_strengths"][-2] >= 0.7

    state = session.set_chain({"slots": [1, 3, 2]})
    assert state["chain"] == [1, 3, 2]
    chain = session.render_current_chain(
        {"repeats": 1, "evolve": 0.0, "surprise": 0.0}
    )
    assert chain["render"]["length_beats"] == 6.0

    reloaded = MomentSession(tmp_path)
    assert reloaded.state()["chain"] == [1, 3, 2]
    assert len(reloaded.state()["slots"]) == 4


def test_clear_requires_explicit_confirmation(tmp_path):
    session = MomentSession(tmp_path)
    session.load_demos()
    try:
        session.clear({"slot": 1})
    except ValueError as exc:
        assert "confirm=true" in str(exc)
    else:
        raise AssertionError("clear should require explicit confirmation")
    assert any(item["slot"] == 1 for item in session.state()["slots"])


def test_state_file_is_readable_json(tmp_path):
    session = MomentSession(tmp_path)
    session.load_demos()
    payload = json.loads((tmp_path / "session.json").read_text(encoding="utf-8"))
    assert payload["format"] == "ipm-moment-session-v0"
    assert len(payload["slots"]) == 4

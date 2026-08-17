from fractions import Fraction

from ipm.model import IPMConfig
from ipm.study2 import compose_study_002


def test_study_002_passes_listening_driven_acceptance_gate() -> None:
    result = compose_study_002()
    assert result.trace["validation"]["passed"], result.trace["validation"]["checks"]


def test_study_002_is_exactly_sixteen_bars_at_108_bpm() -> None:
    result = compose_study_002()
    assert result.config.tempo_bpm == 108
    assert result.main.cursor == Fraction(64)


def test_study_002_breaks_the_repeated_duration_template() -> None:
    result = compose_study_002()
    patterns = {
        tuple(event.duration for event in result.main.events[bar * 4 : bar * 4 + 4])
        for bar in range(16)
    }
    assert len(patterns) >= 6
    assert max(event.duration for event in result.main.events) <= 2


def test_study_002_uses_euclidean_opportunities_without_filling_them_all() -> None:
    result = compose_study_002()
    counts = result.trace["euclidean_counts"]
    assert counts["proposed_attacks"] > counts["accepted_attacks"]
    assert counts["accepted_attacks"] > 0


def test_study_002_has_independent_countervoice_timing() -> None:
    result = compose_study_002()
    main_onsets = {event.onset for event in result.main.events}
    counter = (*result.response.events, *result.harmony.events)
    assert any(event.onset not in main_onsets for event in counter)
    assert any(
        event.onset < main_event.onset < event.end
        for event in counter
        for main_event in result.main.events
    )


def test_study_002_replays_deterministically() -> None:
    first = compose_study_002(IPMConfig(seed=2026081702, tempo_bpm=108))
    second = compose_study_002(IPMConfig(seed=2026081702, tempo_bpm=108))
    assert first.trace == second.trace

from ipm.moment import (
    MomentEvent,
    MutationControls,
    normalise_recording,
    render_chain,
    render_moment,
)


def _moment(slot: int = 1):
    return normalise_recording(
        slot=slot,
        events=(
            MomentEvent(note=60, velocity=80, start=3.0, duration=0.5),
            MomentEvent(note=64, velocity=90, start=3.5, duration=0.25),
            MomentEvent(note=67, velocity=100, start=4.0, duration=0.5),
            MomentEvent(note=64, velocity=86, start=4.5, duration=0.5),
        ),
        length_beats=5.0,
    )


def test_normalise_recording_starts_at_zero_and_preserves_shape():
    moment = _moment()
    assert moment.events[0].start == 0.0
    assert [event.start for event in moment.events] == [0.0, 0.5, 1.0, 1.5]
    assert moment.length_beats == 2.0


def test_exact_repetition_when_evolution_and_surprise_are_zero():
    moment = _moment()
    rendered = render_moment(moment, MutationControls(repeats=3))
    assert rendered.length_beats == 6.0
    for cycle in range(3):
        cycle_events = [event for event in rendered.events if event.cycle == cycle]
        assert [event.note for event in cycle_events] == [60, 64, 67, 64]
        assert [round(event.start - cycle * 2.0, 6) for event in cycle_events] == [0.0, 0.5, 1.0, 1.5]


def test_evolution_is_deterministic():
    moment = _moment()
    controls = MutationControls(repeats=5, evolve=0.8, surprise=0.4)
    assert render_moment(moment, controls) == render_moment(moment, controls)


def test_mutation_never_invents_new_pitch_classes():
    moment = _moment()
    rendered = render_moment(
        moment,
        MutationControls(repeats=8, evolve=1.0, surprise=1.0),
    )
    source_pitch_classes = {event.note % 12 for event in moment.events}
    assert {event.note % 12 for event in rendered.events} <= source_pitch_classes


def test_surprise_has_disruption_then_recovery_shape():
    moment = _moment()
    rendered = render_moment(
        moment,
        MutationControls(repeats=5, evolve=0.4, surprise=1.0),
    )
    strengths = rendered.cycle_strengths
    assert strengths[-2] == 1.0
    assert strengths[-1] < strengths[-2]


def test_chain_is_a_sentence_of_whole_moments():
    first = _moment(1)
    second = _moment(2)
    controls = MutationControls(repeats=2, evolve=0.0, surprise=0.0)
    rendered = render_chain((first, second), controls)
    assert rendered.length_beats == 8.0
    assert len(rendered.events) == 16
    assert min(event.start for event in rendered.events[8:]) >= 4.0

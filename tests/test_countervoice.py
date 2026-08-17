from fractions import Fraction

from ipm import (
    CandidateAction,
    CountervoicePolicy,
    NoteEvent,
    SeededRandom,
    StructuralPhase,
    SubsidiaryCandidate,
    SubsidiaryRole,
    Voice,
    choose_candidate,
    evaluate_candidate,
    target_density,
)


def voice(name: str, *events: tuple[Fraction | int, Fraction | int, int]) -> Voice:
    return Voice.from_events(
        name,
        [NoteEvent(Fraction(onset), Fraction(duration), pitch) for onset, duration, pitch in events],
    )


def test_phase_density_keeps_opening_and_ending_near_main_alone() -> None:
    assert target_density(StructuralPhase.OPENING) == 1.0
    assert target_density(StructuralPhase.ENDING) == 1.0
    assert target_density(StructuralPhase.CLIMAX) > target_density(StructuralPhase.DEVELOPMENT)


def test_consonant_response_can_beat_silence_when_two_voice_texture_is_wanted() -> None:
    main = voice("M", (0, 1, 60))
    branch = Voice("B_R")
    note = SubsidiaryCandidate(CandidateAction.NOTE, NoteEvent(Fraction(0), Fraction(1), 67))
    silence = SubsidiaryCandidate(CandidateAction.SILENCE)

    note_score = evaluate_candidate(
        note,
        role=SubsidiaryRole.RESPONSE,
        target_voice=branch,
        frozen_voices=[main],
        start=Fraction(0),
        end=Fraction(1),
        phase=StructuralPhase.DEVELOPMENT,
    )
    silence_score = evaluate_candidate(
        silence,
        role=SubsidiaryRole.RESPONSE,
        target_voice=branch,
        frozen_voices=[main],
        start=Fraction(0),
        end=Fraction(1),
        phase=StructuralPhase.DEVELOPMENT,
    )

    assert note_score.valid
    assert note_score.total > silence_score.total


def test_same_note_loses_to_silence_in_opening_density() -> None:
    main = voice("M", (0, 1, 60))
    branch = Voice("B_R")
    note = SubsidiaryCandidate(CandidateAction.NOTE, NoteEvent(Fraction(0), Fraction(1), 67))
    silence = SubsidiaryCandidate(CandidateAction.SILENCE)

    note_score = evaluate_candidate(
        note,
        role=SubsidiaryRole.RESPONSE,
        target_voice=branch,
        frozen_voices=[main],
        start=Fraction(0),
        end=Fraction(1),
        phase=StructuralPhase.OPENING,
    )
    silence_score = evaluate_candidate(
        silence,
        role=SubsidiaryRole.RESPONSE,
        target_voice=branch,
        frozen_voices=[main],
        start=Fraction(0),
        end=Fraction(1),
        phase=StructuralPhase.OPENING,
    )

    assert note_score.total < silence_score.total


def test_harmony_voice_rejects_severe_vertical_collision() -> None:
    main = voice("M", (0, 2, 60))
    response = voice("B_R", (0, 2, 67))
    harmony = Voice("B_H")
    clash = SubsidiaryCandidate(CandidateAction.NOTE, NoteEvent(Fraction(0), Fraction(2), 61))

    score = evaluate_candidate(
        clash,
        role=SubsidiaryRole.HARMONY,
        target_voice=harmony,
        frozen_voices=[main, response],
        start=Fraction(0),
        end=Fraction(2),
        phase=StructuralPhase.CLIMAX,
    )

    assert not score.valid
    assert score.reason == "vertical floor"


def test_note_candidate_rejects_self_overlap() -> None:
    main = voice("M", (0, 2, 60))
    response = voice("B_R", (0, 2, 67))
    overlapping = SubsidiaryCandidate(CandidateAction.NOTE, NoteEvent(Fraction(1), Fraction(1), 69))

    score = evaluate_candidate(
        overlapping,
        role=SubsidiaryRole.RESPONSE,
        target_voice=response,
        frozen_voices=[main],
        start=Fraction(1),
        end=Fraction(2),
        phase=StructuralPhase.DEVELOPMENT,
    )

    assert not score.valid
    assert score.reason == "self-overlap"


def test_continue_requires_an_existing_note_spanning_the_window() -> None:
    main = voice("M", (0, 2, 60))
    response = voice("B_R", (0, 2, 67))
    continuation = SubsidiaryCandidate(CandidateAction.CONTINUE)

    valid = evaluate_candidate(
        continuation,
        role=SubsidiaryRole.RESPONSE,
        target_voice=response,
        frozen_voices=[main],
        start=Fraction(1),
        end=Fraction(2),
        phase=StructuralPhase.DEVELOPMENT,
    )
    invalid = evaluate_candidate(
        continuation,
        role=SubsidiaryRole.RESPONSE,
        target_voice=Voice("B_R"),
        frozen_voices=[main],
        start=Fraction(1),
        end=Fraction(2),
        phase=StructuralPhase.DEVELOPMENT,
    )

    assert valid.valid
    assert not invalid.valid
    assert invalid.reason == "nothing to continue"


def test_choose_candidate_never_selects_note_that_does_not_beat_silence() -> None:
    main = voice("M", (0, 1, 60))
    branch = Voice("B_R")
    candidates = [
        SubsidiaryCandidate(CandidateAction.SILENCE),
        SubsidiaryCandidate(CandidateAction.NOTE, NoteEvent(Fraction(0), Fraction(1), 67)),
    ]

    for seed in range(25):
        decision = choose_candidate(
            candidates,
            role=SubsidiaryRole.RESPONSE,
            target_voice=branch,
            frozen_voices=[main],
            start=Fraction(0),
            end=Fraction(1),
            phase=StructuralPhase.OPENING,
            rng=SeededRandom(seed),
        )
        assert decision.selected.candidate.action is CandidateAction.SILENCE


def test_stochastic_choice_is_reproducible_and_main_texture_is_not_mutated() -> None:
    main = voice("M", (0, 1, 60))
    branch = Voice("B_R")
    candidates = [
        SubsidiaryCandidate(CandidateAction.SILENCE),
        SubsidiaryCandidate(CandidateAction.NOTE, NoteEvent(Fraction(0), Fraction(1), 64)),
        SubsidiaryCandidate(CandidateAction.NOTE, NoteEvent(Fraction(0), Fraction(1), 67)),
    ]

    first = choose_candidate(
        candidates,
        role=SubsidiaryRole.RESPONSE,
        target_voice=branch,
        frozen_voices=[main],
        start=Fraction(0),
        end=Fraction(1),
        phase=StructuralPhase.DEVELOPMENT,
        rng=SeededRandom(100),
    )
    second = choose_candidate(
        candidates,
        role=SubsidiaryRole.RESPONSE,
        target_voice=branch,
        frozen_voices=[main],
        start=Fraction(0),
        end=Fraction(1),
        phase=StructuralPhase.DEVELOPMENT,
        rng=SeededRandom(100),
    )

    assert first.selected.candidate == second.selected.candidate
    assert [(e.onset, e.duration, e.pitch) for e in main.events] == [(Fraction(0), Fraction(1), 60)]
    assert branch.events == []


def test_note_must_span_exact_decision_window() -> None:
    main = voice("M", (0, 1, 60))
    branch = Voice("B_R")
    candidate = SubsidiaryCandidate(CandidateAction.NOTE, NoteEvent(Fraction(0), Fraction(1, 2), 67))

    score = evaluate_candidate(
        candidate,
        role=SubsidiaryRole.RESPONSE,
        target_voice=branch,
        frozen_voices=[main],
        start=Fraction(0),
        end=Fraction(1),
        phase=StructuralPhase.DEVELOPMENT,
    )

    assert not score.valid
    assert score.reason == "note must span decision window"


def test_policy_rejects_invalid_temperature() -> None:
    try:
        CountervoicePolicy(selection_temperature=0)
    except ValueError as error:
        assert "selection_temperature" in str(error)
    else:
        raise AssertionError("expected policy validation failure")

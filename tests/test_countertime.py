from fractions import Fraction

from ipm.countertime import choose_timed_candidate, evaluate_timed_candidate, note_candidate
from ipm.countervoice import CountervoicePolicy, StructuralPhase, SubsidiaryRole
from ipm.model import NoteEvent, Voice
from ipm.randomness import SeededRandom


def voice(name: str, *events: tuple[Fraction | int, Fraction | int, int]) -> Voice:
    return Voice.from_events(
        name,
        [NoteEvent(Fraction(onset), Fraction(duration), pitch) for onset, duration, pitch in events],
    )


def test_offbeat_counter_note_is_not_forced_to_main_attack() -> None:
    main = voice("M", (0, 2, 60))
    response = Voice("B_R")
    candidate = note_candidate(
        onset=Fraction(1, 2),
        duration=Fraction(1, 2),
        pitch=67,
    )

    score = evaluate_timed_candidate(
        candidate,
        role=SubsidiaryRole.RESPONSE,
        target_voice=response,
        frozen_voices=(main,),
        phase=StructuralPhase.DEVELOPMENT,
    )

    assert score.note_score.valid
    assert score.valid
    assert candidate.note is not None
    assert candidate.note.onset != main.events[0].onset


def test_counter_note_can_cross_a_main_note_boundary() -> None:
    main = voice("M", (0, 1, 60), (1, 1, 67))
    response = Voice("B_R")
    candidate = note_candidate(
        onset=Fraction(1, 2),
        duration=Fraction(1),
        pitch=64,
    )

    score = evaluate_timed_candidate(
        candidate,
        role=SubsidiaryRole.RESPONSE,
        target_voice=response,
        frozen_voices=(main,),
        phase=StructuralPhase.DEVELOPMENT,
    )

    assert score.note_score.valid
    assert score.valid
    assert candidate.note is not None
    assert candidate.note.onset < main.events[0].end < candidate.note.end


def test_actual_overlap_still_rejects_a_cross_boundary_clash() -> None:
    main = voice("M", (0, 1, 60), (1, 1, 67))
    harmony = Voice("B_H")
    clash = note_candidate(
        onset=Fraction(1, 2),
        duration=Fraction(1),
        pitch=61,
        velocity=58,
    )

    score = evaluate_timed_candidate(
        clash,
        role=SubsidiaryRole.HARMONY,
        target_voice=harmony,
        frozen_voices=(main,),
        phase=StructuralPhase.CLIMAX,
    )

    assert not score.valid
    assert score.reason == "vertical floor"


def test_timed_note_must_still_outperform_silence_for_its_own_time() -> None:
    main = voice("M", (0, 2, 60))
    response = Voice("B_R")
    candidate = note_candidate(
        onset=Fraction(1, 2),
        duration=Fraction(1, 2),
        pitch=67,
    )

    score = evaluate_timed_candidate(
        candidate,
        role=SubsidiaryRole.RESPONSE,
        target_voice=response,
        frozen_voices=(main,),
        phase=StructuralPhase.OPENING,
    )

    assert not score.valid
    assert score.reason == "does not beat silence"
    assert score.improvement <= 0


def test_independent_timing_selection_is_seed_reproducible() -> None:
    main = voice("M", (0, 1, 60), (1, 1, 67))
    candidates = (
        note_candidate(onset=Fraction(1, 2), duration=Fraction(1, 2), pitch=64),
        note_candidate(onset=Fraction(3, 4), duration=Fraction(1, 2), pitch=67),
    )

    first = choose_timed_candidate(
        candidates,
        role=SubsidiaryRole.RESPONSE,
        target_voice=Voice("B_R"),
        frozen_voices=(main,),
        phase=StructuralPhase.DEVELOPMENT,
        rng=SeededRandom(23),
        policy=CountervoicePolicy(response_attack_cost=0.0),
    )
    second = choose_timed_candidate(
        candidates,
        role=SubsidiaryRole.RESPONSE,
        target_voice=Voice("B_R"),
        frozen_voices=(main,),
        phase=StructuralPhase.DEVELOPMENT,
        rng=SeededRandom(23),
        policy=CountervoicePolicy(response_attack_cost=0.0),
    )

    assert first.selected == second.selected

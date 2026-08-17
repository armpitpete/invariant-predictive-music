"""Independent-timing gate for subsidiary notes.

Counter-voice notes are evaluated over the time they actually occupy rather than
being forced to share a main-note boundary. Harmonic compatibility therefore
constrains real overlap while rhythmic alignment remains free.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import exp
from typing import Sequence

from .countervoice import (
    CandidateAction,
    CandidateScore,
    CountervoicePolicy,
    StructuralPhase,
    SubsidiaryCandidate,
    SubsidiaryRole,
    evaluate_candidate,
)
from .model import NoteEvent, Voice
from .randomness import SeededRandom


@dataclass(frozen=True, slots=True)
class TimedCandidateScore:
    """One proposed subsidiary note compared with silence over its own lifespan."""

    candidate: SubsidiaryCandidate
    note_score: CandidateScore
    silence_score: CandidateScore
    improvement: float
    valid: bool
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class TimedDecision:
    """Independent timing decision; ``selected`` is None when silence wins everywhere."""

    selected: TimedCandidateScore | None
    scored: tuple[TimedCandidateScore, ...]


def evaluate_timed_candidate(
    candidate: SubsidiaryCandidate,
    *,
    role: SubsidiaryRole,
    target_voice: Voice,
    frozen_voices: Sequence[Voice],
    phase: StructuralPhase,
    beats_per_bar: int = 4,
    policy: CountervoicePolicy = CountervoicePolicy(),
) -> TimedCandidateScore:
    """Judge a note against silence over the exact time occupied by that note."""

    if candidate.action is not CandidateAction.NOTE or candidate.note is None:
        raise ValueError("timed candidate must be a NOTE with a note event")

    note = candidate.note
    note_score = evaluate_candidate(
        candidate,
        role=role,
        target_voice=target_voice,
        frozen_voices=frozen_voices,
        start=note.onset,
        end=note.end,
        phase=phase,
        beats_per_bar=beats_per_bar,
        policy=policy,
    )
    silence_score = evaluate_candidate(
        SubsidiaryCandidate(CandidateAction.SILENCE),
        role=role,
        target_voice=target_voice,
        frozen_voices=frozen_voices,
        start=note.onset,
        end=note.end,
        phase=phase,
        beats_per_bar=beats_per_bar,
        policy=policy,
    )

    if not note_score.valid:
        return TimedCandidateScore(
            candidate,
            note_score,
            silence_score,
            float("-inf"),
            False,
            note_score.reason,
        )
    if not silence_score.valid:
        return TimedCandidateScore(
            candidate,
            note_score,
            silence_score,
            float("-inf"),
            False,
            "silence baseline unavailable",
        )

    improvement = note_score.total - silence_score.total
    valid = improvement > policy.improvement_epsilon
    return TimedCandidateScore(
        candidate,
        note_score,
        silence_score,
        improvement,
        valid,
        None if valid else "does not beat silence",
    )


def choose_timed_candidate(
    candidates: Sequence[SubsidiaryCandidate],
    *,
    role: SubsidiaryRole,
    target_voice: Voice,
    frozen_voices: Sequence[Voice],
    phase: StructuralPhase,
    rng: SeededRandom,
    beats_per_bar: int = 4,
    policy: CountervoicePolicy = CountervoicePolicy(),
) -> TimedDecision:
    """Choose among independently timed notes; return silence when none earn entry."""

    scored = tuple(
        evaluate_timed_candidate(
            candidate,
            role=role,
            target_voice=target_voice,
            frozen_voices=frozen_voices,
            phase=phase,
            beats_per_bar=beats_per_bar,
            policy=policy,
        )
        for candidate in candidates
    )
    eligible = tuple(score for score in scored if score.valid)
    if not eligible:
        return TimedDecision(None, scored)
    if len(eligible) == 1:
        return TimedDecision(eligible[0], scored)

    best = max(score.improvement for score in eligible)
    weights = [
        exp((score.improvement - best) / policy.selection_temperature)
        for score in eligible
    ]
    return TimedDecision(rng.weighted_choice(eligible, weights), scored)


def note_candidate(*, onset, duration, pitch: int, velocity: int = 68) -> SubsidiaryCandidate:
    """Convenience constructor for an independently timed subsidiary note."""

    return SubsidiaryCandidate(
        CandidateAction.NOTE,
        NoteEvent(onset=onset, duration=duration, pitch=pitch, velocity=velocity),
    )

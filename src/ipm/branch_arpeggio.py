"""Rhythmic arpeggio motifs for IPM subsidiary branches.

Previous listening studies screened isolated sustained subsidiary notes.  That made
branches technically possible but musically scarce and rhythmically inert.  This
module proposes short multi-note figures and accepts a motif only when every note in
the figure still beats silence under the existing subsidiary scoring law.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from statistics import mean
from typing import Sequence

from .countervoice import (
    CandidateAction,
    CountervoicePolicy,
    StructuralPhase,
    SubsidiaryCandidate,
    SubsidiaryRole,
    evaluate_candidate,
)
from .model import Beat, NoteEvent, Voice
from .register import PitchRegister
from .randomness import SeededRandom

_RESPONSE_REGISTER = PitchRegister(low=48, high=59, centre=55)
_HARMONY_REGISTER = PitchRegister(low=36, high=47, centre=43)
_AEOLIAN_TRIADS = (
    (0, 3, 7),   # i: C-Eb-G
    (5, 8, 0),   # iv: F-Ab-C
    (7, 10, 2),  # v: G-Bb-D
)
_CONTOURS = (
    (0, 1, 2, 1),
    (2, 1, 0, 1),
    (0, 2, 1, 2),
)


@dataclass(frozen=True, slots=True)
class BranchMotif:
    role: SubsidiaryRole
    events: tuple[NoteEvent, ...]
    chord_offsets: tuple[int, int, int]
    contour: tuple[int, ...]

    def __post_init__(self) -> None:
        if len(self.events) < 2:
            raise ValueError("branch motif needs at least two attacks")
        if any(
            right.onset < left.end
            for left, right in zip(self.events, self.events[1:], strict=False)
        ):
            raise ValueError("branch motif may not overlap itself")


@dataclass(frozen=True, slots=True)
class BranchMotifScore:
    motif: BranchMotif
    valid: bool
    total: float
    margins: tuple[float, ...]
    note_scores: tuple[float, ...]
    silence_scores: tuple[float, ...]
    reason: str | None = None


_DEFAULT_POLICY = CountervoicePolicy(
    vertical_weight=0.60,
    density_weight=0.40,
    response_vertical_floor=0.50,
    harmony_vertical_floor=0.55,
    response_attack_cost=0.01,
    harmony_attack_cost=0.015,
)


def _register(role: SubsidiaryRole) -> PitchRegister:
    return _RESPONSE_REGISTER if role is SubsidiaryRole.RESPONSE else _HARMONY_REGISTER


def _attack_count(span: Beat) -> int:
    return max(2, min(4, int(span / Fraction(1, 4))))


def _motif_from_shape(
    *,
    role: SubsidiaryRole,
    start: Beat,
    span: Beat,
    tonic_midi: int,
    chord_offsets: tuple[int, int, int],
    contour: tuple[int, ...],
) -> BranchMotif:
    attacks = _attack_count(span)
    shape = contour[:attacks]
    register = _register(role)
    projected: list[int] = []
    previous: int | None = None
    for index in shape:
        source_pitch = tonic_midi + chord_offsets[index]
        pitch = register.project_pitch(source_pitch, previous=previous)
        projected.append(pitch)
        previous = pitch

    velocity = 54 if role is SubsidiaryRole.RESPONSE else 47
    events = tuple(
        NoteEvent(
            onset=start + Fraction(index, 4),
            duration=Fraction(3, 16),
            pitch=pitch,
            velocity=velocity + (3 if index == 0 else 0),
        )
        for index, pitch in enumerate(projected)
    )
    return BranchMotif(
        role=role,
        events=events,
        chord_offsets=chord_offsets,
        contour=shape,
    )


def score_branch_motif(
    motif: BranchMotif,
    *,
    frozen_voices: Sequence[Voice],
    phase: str,
    policy: CountervoicePolicy = _DEFAULT_POLICY,
) -> BranchMotifScore:
    """Require every event in the motif to beat silence, then score the figure."""

    structural_phase = StructuralPhase(phase)
    target = Voice(motif.role.value)
    margins: list[float] = []
    note_scores: list[float] = []
    silence_scores: list[float] = []

    for event in motif.events:
        note = evaluate_candidate(
            SubsidiaryCandidate(CandidateAction.NOTE, event),
            role=motif.role,
            target_voice=target,
            frozen_voices=frozen_voices,
            start=event.onset,
            end=event.end,
            phase=structural_phase,
            policy=policy,
        )
        silence = evaluate_candidate(
            SubsidiaryCandidate(CandidateAction.SILENCE),
            role=motif.role,
            target_voice=target,
            frozen_voices=frozen_voices,
            start=event.onset,
            end=event.end,
            phase=structural_phase,
            policy=policy,
        )
        if not note.valid or not silence.valid:
            return BranchMotifScore(
                motif=motif,
                valid=False,
                total=0.0,
                margins=tuple(margins),
                note_scores=tuple(note_scores),
                silence_scores=tuple(silence_scores),
                reason=note.reason or silence.reason or "invalid subsidiary window",
            )
        margin = note.total - silence.total
        margins.append(margin)
        note_scores.append(note.total)
        silence_scores.append(silence.total)
        if margin <= policy.improvement_epsilon:
            return BranchMotifScore(
                motif=motif,
                valid=False,
                total=mean(margins),
                margins=tuple(margins),
                note_scores=tuple(note_scores),
                silence_scores=tuple(silence_scores),
                reason="motif contains an attack that does not beat silence",
            )
        target.add(event)

    return BranchMotifScore(
        motif=motif,
        valid=True,
        total=mean(margins),
        margins=tuple(margins),
        note_scores=tuple(note_scores),
        silence_scores=tuple(silence_scores),
    )


def best_arpeggio(
    *,
    role: SubsidiaryRole,
    start: Beat,
    span: Beat,
    frozen_voices: Sequence[Voice],
    phase: str,
    rng: SeededRandom,
    tonic_midi: int = 60,
    policy: CountervoicePolicy = _DEFAULT_POLICY,
) -> tuple[BranchMotifScore | None, tuple[BranchMotifScore, ...]]:
    """Score several diatonic arpeggio shapes and return the strongest valid motif."""

    if span < Fraction(1, 2):
        return None, ()

    scored = tuple(
        score_branch_motif(
            _motif_from_shape(
                role=role,
                start=start,
                span=span,
                tonic_midi=tonic_midi,
                chord_offsets=chord,
                contour=contour,
            ),
            frozen_voices=frozen_voices,
            phase=phase,
            policy=policy,
        )
        for chord in _AEOLIAN_TRIADS
        for contour in _CONTOURS
    )
    valid = tuple(item for item in scored if item.valid)
    if not valid:
        return None, scored

    best = max(item.total for item in valid)
    near_best = tuple(item for item in valid if item.total >= best - 0.015)
    weights = tuple(max(item.total, 1e-9) for item in near_best)
    return rng.weighted_choice(near_best, weights), scored

"""Subsidiary-voice candidate evaluation with silence as an explicit baseline."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import exp
from typing import Iterable, Sequence

from .model import Beat, NoteEvent, Voice, VoiceOverlapError
from .randomness import SeededRandom
from .sonority import ActiveNote, SonoritySlice, score_sonority


class CandidateAction(str, Enum):
    NOTE = "note"
    CONTINUE = "continue"
    SILENCE = "silence"


class SubsidiaryRole(str, Enum):
    RESPONSE = "B_R"
    HARMONY = "B_H"


class StructuralPhase(str, Enum):
    OPENING = "opening"
    ESTABLISHMENT = "establishment"
    DEVELOPMENT = "development"
    CLIMAX = "climax"
    RESOLUTION = "resolution"
    ENDING = "ending"


_PHASE_DENSITY: dict[StructuralPhase, float] = {
    StructuralPhase.OPENING: 1.0,
    StructuralPhase.ESTABLISHMENT: 1.6,
    StructuralPhase.DEVELOPMENT: 2.0,
    StructuralPhase.CLIMAX: 2.6,
    StructuralPhase.RESOLUTION: 1.7,
    StructuralPhase.ENDING: 1.0,
}


@dataclass(frozen=True, slots=True)
class CountervoicePolicy:
    """Role-specific scoring policy. Values are design defaults, not musical constants."""

    vertical_weight: float = 0.60
    density_weight: float = 0.40
    response_vertical_floor: float = 0.55
    harmony_vertical_floor: float = 0.65
    response_attack_cost: float = 0.03
    harmony_attack_cost: float = 0.06
    continue_bonus: float = 0.01
    selection_temperature: float = 0.12
    improvement_epsilon: float = 1e-9

    def __post_init__(self) -> None:
        if self.vertical_weight < 0 or self.density_weight < 0:
            raise ValueError("score weights must be non-negative")
        if self.vertical_weight + self.density_weight <= 0:
            raise ValueError("score weights must sum to a positive value")
        if not 0 <= self.response_vertical_floor <= 1:
            raise ValueError("response_vertical_floor must be in 0..1")
        if not 0 <= self.harmony_vertical_floor <= 1:
            raise ValueError("harmony_vertical_floor must be in 0..1")
        if self.response_attack_cost < 0 or self.harmony_attack_cost < 0:
            raise ValueError("attack costs must be non-negative")
        if self.selection_temperature <= 0:
            raise ValueError("selection_temperature must be positive")


@dataclass(frozen=True, slots=True)
class SubsidiaryCandidate:
    action: CandidateAction
    note: NoteEvent | None = None

    def __post_init__(self) -> None:
        if self.action is CandidateAction.NOTE and self.note is None:
            raise ValueError("NOTE candidate requires a note")
        if self.action is not CandidateAction.NOTE and self.note is not None:
            raise ValueError("only NOTE candidates may carry a note")


@dataclass(frozen=True, slots=True)
class CandidateScore:
    candidate: SubsidiaryCandidate
    total: float
    vertical: float
    density_fit: float
    minimum_vertical: float
    valid: bool
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class CandidateDecision:
    selected: CandidateScore
    silence: CandidateScore | None
    scored: tuple[CandidateScore, ...]


def target_density(phase: StructuralPhase) -> float:
    return _PHASE_DENSITY[phase]


def _copy_voice(voice: Voice) -> Voice:
    return Voice.from_events(voice.name, voice.events)


def _segments(
    voices: Iterable[Voice],
    *,
    start: Beat,
    end: Beat,
) -> tuple[tuple[Beat, Beat, tuple[ActiveNote, ...]], ...]:
    if start < 0 or end <= start:
        raise ValueError("window must have non-negative start and end after start")
    voice_list = tuple(voices)
    boundaries = {start, end}
    for voice in voice_list:
        for event in voice.events:
            if event.end <= start or event.onset >= end:
                continue
            boundaries.add(max(start, event.onset))
            boundaries.add(min(end, event.end))
    ordered = sorted(boundaries)
    result = []
    for segment_start, segment_end in zip(ordered, ordered[1:], strict=False):
        active = tuple(
            ActiveNote(voice=voice.name, event=event)
            for voice in voice_list
            for event in voice.events
            if event.onset <= segment_start and event.end >= segment_end
        )
        result.append((segment_start, segment_end, active))
    return tuple(result)


def _window_metrics(
    voices: Iterable[Voice],
    *,
    start: Beat,
    end: Beat,
    desired_density: float,
    beats_per_bar: int,
) -> tuple[float, float, float]:
    segments = _segments(voices, start=start, end=end)
    total_duration = float(end - start)
    vertical_acc = 0.0
    density_acc = 0.0
    minimum_vertical = 1.0
    for segment_start, segment_end, active in segments:
        duration = segment_end - segment_start
        weight = float(duration) / total_duration
        if active:
            vertical = score_sonority(
                SonoritySlice(segment_start, segment_end, active),
                beats_per_bar=beats_per_bar,
            ).vertical
        else:
            vertical = 1.0
        active_voices = len({note.voice for note in active})
        density_fit = max(0.0, 1.0 - abs(active_voices - desired_density) / max(desired_density, 1.0))
        vertical_acc += weight * vertical
        density_acc += weight * density_fit
        minimum_vertical = min(minimum_vertical, vertical)
    return vertical_acc, density_acc, minimum_vertical


def _window_has_target_activity(voice: Voice, *, start: Beat, end: Beat) -> bool:
    return any(event.onset < end and event.end > start for event in voice.events)


def evaluate_candidate(
    candidate: SubsidiaryCandidate,
    *,
    role: SubsidiaryRole,
    target_voice: Voice,
    frozen_voices: Sequence[Voice],
    start: Beat,
    end: Beat,
    phase: StructuralPhase,
    beats_per_bar: int = 4,
    policy: CountervoicePolicy = CountervoicePolicy(),
) -> CandidateScore:
    """Evaluate one subsidiary action without mutating the main or accepted voices."""

    desired_density = target_density(phase)
    candidate_voice = _copy_voice(target_voice)

    if candidate.action is CandidateAction.NOTE:
        assert candidate.note is not None
        if candidate.note.onset != start or candidate.note.end != end:
            return CandidateScore(candidate, 0.0, 0.0, 0.0, 0.0, False, "note must span decision window")
        try:
            candidate_voice.add(candidate.note)
        except VoiceOverlapError:
            return CandidateScore(candidate, 0.0, 0.0, 0.0, 0.0, False, "self-overlap")
    elif candidate.action is CandidateAction.CONTINUE:
        if not any(event.onset <= start and event.end >= end for event in candidate_voice.events):
            return CandidateScore(candidate, 0.0, 0.0, 0.0, 0.0, False, "nothing to continue")
    elif candidate.action is CandidateAction.SILENCE:
        if _window_has_target_activity(candidate_voice, start=start, end=end):
            return CandidateScore(candidate, 0.0, 0.0, 0.0, 0.0, False, "voice already sounding")

    texture_voices = (*frozen_voices, candidate_voice)
    vertical, density_fit, minimum_vertical = _window_metrics(
        texture_voices,
        start=start,
        end=end,
        desired_density=desired_density,
        beats_per_bar=beats_per_bar,
    )

    floor = (
        policy.response_vertical_floor
        if role is SubsidiaryRole.RESPONSE
        else policy.harmony_vertical_floor
    )
    if candidate.action is CandidateAction.NOTE and minimum_vertical < floor:
        return CandidateScore(
            candidate,
            0.0,
            vertical,
            density_fit,
            minimum_vertical,
            False,
            "vertical floor",
        )

    total_weight = policy.vertical_weight + policy.density_weight
    total = (
        policy.vertical_weight * vertical + policy.density_weight * density_fit
    ) / total_weight
    if candidate.action is CandidateAction.NOTE:
        total -= (
            policy.response_attack_cost
            if role is SubsidiaryRole.RESPONSE
            else policy.harmony_attack_cost
        )
    elif candidate.action is CandidateAction.CONTINUE:
        total += policy.continue_bonus

    return CandidateScore(candidate, total, vertical, density_fit, minimum_vertical, True)


def choose_candidate(
    candidates: Sequence[SubsidiaryCandidate],
    *,
    role: SubsidiaryRole,
    target_voice: Voice,
    frozen_voices: Sequence[Voice],
    start: Beat,
    end: Beat,
    phase: StructuralPhase,
    rng: SeededRandom,
    beats_per_bar: int = 4,
    policy: CountervoicePolicy = CountervoicePolicy(),
) -> CandidateDecision:
    """Choose stochastically, but never permit a new note that fails to beat silence."""

    scored = tuple(
        evaluate_candidate(
            candidate,
            role=role,
            target_voice=target_voice,
            frozen_voices=frozen_voices,
            start=start,
            end=end,
            phase=phase,
            beats_per_bar=beats_per_bar,
            policy=policy,
        )
        for candidate in candidates
    )
    valid = tuple(score for score in scored if score.valid)
    if not valid:
        raise ValueError("no valid subsidiary candidates")

    silence = next(
        (score for score in valid if score.candidate.action is CandidateAction.SILENCE),
        None,
    )
    if silence is not None:
        eligible = tuple(
            score
            for score in valid
            if score.candidate.action is not CandidateAction.NOTE
            or score.total > silence.total + policy.improvement_epsilon
        )
    else:
        eligible = valid

    if len(eligible) == 1:
        return CandidateDecision(eligible[0], silence, scored)

    best = max(score.total for score in eligible)
    weights = [exp((score.total - best) / policy.selection_temperature) for score in eligible]
    selected = rng.weighted_choice(eligible, weights)
    return CandidateDecision(selected, silence, scored)

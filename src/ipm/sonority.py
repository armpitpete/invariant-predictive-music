"""Active-sonority slicing and vertical compatibility scoring for IPM."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations
from math import exp
from typing import Iterable

from .model import Beat, NoteEvent, Voice

# A deliberately simple consonance prior. Context may redeem low-prior intervals.
_INTERVAL_PRIOR: dict[int, float] = {
    0: 0.78,
    1: 0.10,
    2: 0.35,
    3: 0.90,
    4: 0.95,
    5: 0.75,
    6: 0.15,
    7: 1.00,
    8: 0.90,
    9: 0.90,
    10: 0.35,
    11: 0.20,
}

_SET_PRIORS: tuple[tuple[frozenset[int], float], ...] = (
    (frozenset({0, 4, 7}), 1.00),  # major triad
    (frozenset({0, 3, 7}), 1.00),  # minor triad
    (frozenset({0, 2, 7}), 0.82),  # sus2
    (frozenset({0, 5, 7}), 0.82),  # sus4
    (frozenset({0, 3, 6}), 0.62),  # diminished triad
    (frozenset({0, 4, 8}), 0.58),  # augmented triad
)


@dataclass(frozen=True, slots=True)
class ActiveNote:
    """A note sounding during one sonority slice, tagged by voice."""

    voice: str
    event: NoteEvent


@dataclass(frozen=True, slots=True)
class SonoritySlice:
    """A maximal interval of time during which the active note set is unchanged."""

    start: Beat
    end: Beat
    notes: tuple[ActiveNote, ...]

    def __post_init__(self) -> None:
        if self.start < 0:
            raise ValueError("slice start must be non-negative")
        if self.end <= self.start:
            raise ValueError("slice end must be after start")
        if not self.notes:
            raise ValueError("sonority slice must contain at least one active note")

    @property
    def duration(self) -> Beat:
        return self.end - self.start

    @property
    def pitches(self) -> tuple[int, ...]:
        return tuple(note.event.pitch for note in self.notes)


@dataclass(frozen=True, slots=True)
class VerticalScore:
    """Inspectable vertical score for one active-sonority slice."""

    pairwise_min: float
    set_coherence: float
    vertical: float


@dataclass(frozen=True, slots=True)
class TextureScore:
    """Duration-weighted score across a sequence of active sonorities."""

    weighted_mean: float
    minimum: float
    duration: Beat
    slices: int


def slice_active_sonorities(voices: Iterable[Voice]) -> tuple[SonoritySlice, ...]:
    """Split voices wherever any note starts or ends and return sounding slices only."""

    voice_list = tuple(voices)
    boundaries = sorted(
        {
            boundary
            for voice in voice_list
            for event in voice.events
            for boundary in (event.onset, event.end)
        }
    )
    slices: list[SonoritySlice] = []
    for start, end in zip(boundaries, boundaries[1:], strict=False):
        active = tuple(
            ActiveNote(voice=voice.name, event=event)
            for voice in voice_list
            for event in voice.events
            if event.onset <= start and event.end >= end
        )
        if active:
            slices.append(SonoritySlice(start=start, end=end, notes=active))
    return tuple(slices)


def interval_class(pitch_a: int, pitch_b: int) -> int:
    """Return pitch-class distance in semitones, retaining directed-class equivalence."""

    return abs(pitch_a - pitch_b) % 12


def interval_prior(pitch_a: int, pitch_b: int) -> float:
    return _INTERVAL_PRIOR[interval_class(pitch_a, pitch_b)]


def metrical_strength(onset: Beat, beats_per_bar: int) -> float:
    """Coarse metrical strength: bar downbeat > integer beat > subdivision."""

    if beats_per_bar <= 0:
        raise ValueError("beats_per_bar must be positive")
    if onset.denominator == 1 and int(onset) % beats_per_bar == 0:
        return 1.0
    if onset.denominator == 1:
        return 0.75
    return 0.50


def contextual_pair_score(
    pitch_a: int,
    pitch_b: int,
    *,
    duration: Beat,
    onset: Beat,
    beats_per_bar: int = 4,
    duration_lambda: float = 1.0,
) -> float:
    """Score a simultaneous pitch pair with duration and metre-sensitive tolerance.

    Short or weak-beat clashes are discounted; long strong-beat clashes approach the
    underlying interval prior and therefore require later resolution logic to redeem them.
    """

    if duration <= 0:
        raise ValueError("duration must be positive")
    if duration_lambda <= 0:
        raise ValueError("duration_lambda must be positive")
    prior = interval_prior(pitch_a, pitch_b)
    exposure = 1.0 - exp(-duration_lambda * float(duration))
    strength = metrical_strength(onset, beats_per_bar)
    return 1.0 - (1.0 - prior) * exposure * strength


def _is_transposition_of(pitch_classes: frozenset[int], pattern: frozenset[int]) -> bool:
    return any(
        frozenset((pitch - root) % 12 for pitch in pitch_classes) == pattern
        for root in pitch_classes
    )


def set_coherence(pitches: Iterable[int]) -> float:
    """Score the whole pitch-class set rather than hiding bad combinations in averages."""

    pitch_tuple = tuple(pitches)
    if len(pitch_tuple) <= 1:
        return 1.0
    if len(pitch_tuple) == 2:
        return interval_prior(*pitch_tuple)

    pitch_classes = frozenset(pitch % 12 for pitch in pitch_tuple)
    if len(pitch_classes) < len(pitch_tuple):
        # Doubling can be useful, but a three-voice unison/octave stack carries less harmony.
        return 0.72
    for pattern, score in _SET_PRIORS:
        if _is_transposition_of(pitch_classes, pattern):
            return score

    pair_priors = [interval_prior(a, b) for a, b in combinations(pitch_tuple, 2)]
    return sum(pair_priors) / len(pair_priors)


def score_sonority(
    sonority: SonoritySlice,
    *,
    beats_per_bar: int = 4,
    pair_weight: float = 0.6,
    set_weight: float = 0.4,
) -> VerticalScore:
    """Score pairwise and whole-set compatibility for one sounding time slice."""

    if pair_weight < 0 or set_weight < 0 or pair_weight + set_weight <= 0:
        raise ValueError("score weights must be non-negative and sum to a positive value")

    pitches = sonority.pitches
    if len(pitches) <= 1:
        return VerticalScore(pairwise_min=1.0, set_coherence=1.0, vertical=1.0)

    pair_scores = [
        contextual_pair_score(
            a,
            b,
            duration=sonority.duration,
            onset=sonority.start,
            beats_per_bar=beats_per_bar,
        )
        for a, b in combinations(pitches, 2)
    ]
    pairwise_min = min(pair_scores)
    whole_set = set_coherence(pitches)
    total_weight = pair_weight + set_weight
    vertical = (pair_weight * pairwise_min + set_weight * whole_set) / total_weight
    return VerticalScore(
        pairwise_min=pairwise_min,
        set_coherence=whole_set,
        vertical=vertical,
    )


def score_texture(voices: Iterable[Voice], *, beats_per_bar: int = 4) -> TextureScore:
    """Duration-weight vertical compatibility across all sounding sonority slices."""

    slices = slice_active_sonorities(voices)
    if not slices:
        return TextureScore(weighted_mean=1.0, minimum=1.0, duration=Fraction(0), slices=0)

    scored = [(sonority, score_sonority(sonority, beats_per_bar=beats_per_bar)) for sonority in slices]
    total_duration = sum((sonority.duration for sonority, _ in scored), Fraction(0))
    weighted = sum(float(sonority.duration) * score.vertical for sonority, score in scored)
    return TextureScore(
        weighted_mean=weighted / float(total_duration),
        minimum=min(score.vertical for _, score in scored),
        duration=total_duration,
        slices=len(scored),
    )

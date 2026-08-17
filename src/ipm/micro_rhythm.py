"""Micro-rhythmic decoration for slow IPM bars.

A slow tempo does not imply that every attack must be long.  This layer preserves
an accepted bar's structural NOTE/REST cells, but some sounding cells may contain a
brief internal burst on a quarter-beat grid.  The structural cell still owns exactly
the same amount of time; the shorter attacks and their gate create local articulation
without accelerating the global tempo.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Sequence

from .bar_rhythm import BarCellKind
from .model import Beat, NoteEvent
from .randomness import SeededRandom

_AEOLIAN = (0, 2, 3, 5, 7, 8, 10)
_PHASE_SPLIT_PROBABILITY: dict[str, float] = {
    "opening": 0.34,
    "establishment": 0.46,
    "development": 0.58,
    "climax": 0.72,
    "resolution": 0.42,
    "ending": 0.26,
}
_PHASE_VELOCITY: dict[str, int] = {
    "opening": 70,
    "establishment": 74,
    "development": 79,
    "climax": 86,
    "resolution": 73,
    "ending": 66,
}


@dataclass(frozen=True, slots=True)
class MicroRhythmDecision:
    """One structural note cell and its chosen sounding subdivision."""

    onset: Beat
    structural_duration: Beat
    segments: tuple[Beat, ...]
    pitches: tuple[int, ...]

    def __post_init__(self) -> None:
        if self.onset < 0 or self.structural_duration <= 0:
            raise ValueError("micro-rhythm decision needs a valid structural window")
        if not self.segments or sum(self.segments, Fraction(0)) != self.structural_duration:
            raise ValueError("micro-rhythm segments must exactly fill the structural cell")
        if len(self.segments) != len(self.pitches):
            raise ValueError("every micro segment requires one pitch")

    @property
    def has_short_attack(self) -> bool:
        return any(segment == Fraction(1, 4) for segment in self.segments)


def aeolian_pool(tonic_midi: int = 60) -> tuple[int, ...]:
    return tuple(tonic_midi + offset for offset in _AEOLIAN)


def _neighbour(anchor: int, *, pool: Sequence[int], rng: SeededRandom) -> int:
    index = pool.index(anchor)
    if index == 0:
        return pool[1]
    if index == len(pool) - 1:
        return pool[-2]
    return pool[index + (1 if rng.random() < 0.5 else -1)]


def _segments_for_cell(
    duration: Beat,
    *,
    phase: str,
    rng: SeededRandom,
) -> tuple[Beat, ...]:
    if phase not in _PHASE_SPLIT_PROBABILITY:
        raise ValueError("unknown structural phase")
    if rng.random() >= _PHASE_SPLIT_PROBABILITY[phase]:
        return (duration,)

    if duration == Fraction(1, 2):
        return (Fraction(1, 4), Fraction(1, 4))
    if duration == Fraction(1):
        return rng.choice(
            (
                (Fraction(1, 2), Fraction(1, 4), Fraction(1, 4)),
                (Fraction(1, 4), Fraction(1, 2), Fraction(1, 4)),
                (Fraction(1, 4), Fraction(1, 4), Fraction(1, 2)),
            )
        )
    if duration == Fraction(3, 2):
        return rng.choice(
            (
                (Fraction(1), Fraction(1, 4), Fraction(1, 4)),
                (Fraction(1, 4), Fraction(1, 4), Fraction(1)),
                (Fraction(1, 2), Fraction(1, 2), Fraction(1, 4), Fraction(1, 4)),
            )
        )
    return (duration,)


def _micro_pitches(
    anchor: int,
    count: int,
    *,
    pool: Sequence[int],
    rng: SeededRandom,
) -> tuple[int, ...]:
    """Decorate an anchor but always return to it at the end of the cell."""

    if count == 1:
        return (anchor,)
    neighbour = _neighbour(anchor, pool=pool, rng=rng)
    if count == 2:
        return (neighbour, anchor)
    if count == 3:
        return (anchor, neighbour, anchor)
    if count == 4:
        other = _neighbour(anchor, pool=pool, rng=rng)
        return (anchor, neighbour, other, anchor)
    return tuple(anchor for _ in range(count - 1)) + (anchor,)


def realise_micro_bar(
    cells: Sequence[tuple[BarCellKind, Beat]],
    pitches: Sequence[int],
    *,
    start: Beat,
    phase: str,
    rng: SeededRandom,
    tonic_midi: int = 60,
) -> tuple[tuple[NoteEvent, ...], tuple[MicroRhythmDecision, ...]]:
    """Realise one accepted structural bar with occasional quarter-beat bursts."""

    note_cells = sum(kind is BarCellKind.NOTE for kind, _ in cells)
    if len(pitches) != note_cells:
        raise ValueError("one pitch anchor is required for each structural NOTE cell")

    pool = aeolian_pool(tonic_midi)
    if any(pitch not in pool for pitch in pitches):
        raise ValueError("micro-rhythm anchors must remain in the one-octave Aeolian pool")

    cursor = start
    pitch_index = 0
    events: list[NoteEvent] = []
    decisions: list[MicroRhythmDecision] = []
    base_velocity = _PHASE_VELOCITY[phase]

    for kind, duration in cells:
        if kind is BarCellKind.REST:
            cursor += duration
            continue

        anchor = pitches[pitch_index]
        pitch_index += 1
        segments = _segments_for_cell(duration, phase=phase, rng=rng)
        micro_pitches = _micro_pitches(anchor, len(segments), pool=pool, rng=rng)
        decisions.append(
            MicroRhythmDecision(
                onset=cursor,
                structural_duration=duration,
                segments=segments,
                pitches=micro_pitches,
            )
        )

        local = cursor
        for index, (segment, pitch) in enumerate(zip(segments, micro_pitches, strict=True)):
            gate = Fraction(3, 4) if segment == Fraction(1, 4) else Fraction(7, 8)
            velocity = max(
                48,
                min(102, base_velocity + (4 if index == 0 else -2 if index % 2 else 1)),
            )
            events.append(
                NoteEvent(
                    onset=local,
                    duration=segment * gate,
                    pitch=pitch,
                    velocity=velocity,
                )
            )
            local += segment
        cursor += duration

    return tuple(events), tuple(decisions)

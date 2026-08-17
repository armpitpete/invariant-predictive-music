"""Bar-level rhythmic grammar for IPM.

A bar is an exact time budget containing NOTE and REST cells. This sits above the
older note-duration partition layer: a four-beat bar may be one whole-bar note, two
half-bar notes, a note followed by space, space followed by a note, or a mixed
quarter/half/longer sequence. The bar boundary remains invariant while attack count,
rest amount, rest position, and duration mixture vary.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from itertools import product
from math import exp
from typing import Sequence

from .model import Beat, NoteEvent
from .randomness import SeededRandom


class BarCellKind(str, Enum):
    NOTE = "note"
    REST = "rest"


@dataclass(frozen=True, slots=True)
class BarCell:
    kind: BarCellKind
    duration: Beat

    def __post_init__(self) -> None:
        if self.duration <= 0:
            raise ValueError("bar-cell duration must be positive")


@dataclass(frozen=True, slots=True)
class BarPattern:
    span: Beat
    cells: tuple[BarCell, ...]

    def __post_init__(self) -> None:
        if self.span <= 0:
            raise ValueError("bar span must be positive")
        if not self.cells:
            raise ValueError("bar pattern needs at least one cell")
        if sum((cell.duration for cell in self.cells), Fraction(0)) != self.span:
            raise ValueError("bar cells must sum exactly to the bar span")
        if not any(cell.kind is BarCellKind.NOTE for cell in self.cells):
            raise ValueError("bar pattern must contain at least one note")
        if any(
            left.kind is BarCellKind.REST and right.kind is BarCellKind.REST
            for left, right in zip(self.cells, self.cells[1:], strict=False)
        ):
            raise ValueError("adjacent rests must be represented as one rest cell")

    @property
    def attacks(self) -> int:
        return sum(cell.kind is BarCellKind.NOTE for cell in self.cells)

    @property
    def rest_beats(self) -> Beat:
        return sum(
            (cell.duration for cell in self.cells if cell.kind is BarCellKind.REST),
            Fraction(0),
        )

    @property
    def note_beats(self) -> Beat:
        return self.span - self.rest_beats

    @property
    def rest_fraction(self) -> float:
        return float(self.rest_beats / self.span)


@dataclass(frozen=True, slots=True)
class BarRhythmPolicy:
    """Controls the grammar without imposing a fixed rhythm template."""

    grid: Beat = Fraction(1)
    max_cells: int = 4
    max_attacks: int = 4
    max_rest_fraction: float = 0.50
    attack_temperature: float = 0.70
    rest_temperature: float = 0.18
    complexity_temperature: float = 0.40
    equal_note_penalty: float = 0.90

    def __post_init__(self) -> None:
        if self.grid <= 0:
            raise ValueError("grid must be positive")
        if self.max_cells <= 0 or self.max_attacks <= 0:
            raise ValueError("cell and attack limits must be positive")
        if not 0 <= self.max_rest_fraction < 1:
            raise ValueError("max_rest_fraction must be in [0, 1)")
        if min(
            self.attack_temperature,
            self.rest_temperature,
            self.complexity_temperature,
        ) <= 0:
            raise ValueError("temperatures must be positive")
        if not 0 < self.equal_note_penalty <= 1:
            raise ValueError("equal_note_penalty must be in (0, 1]")


def _pulse_count(span: Beat, grid: Beat) -> int:
    pulses = span / grid
    if pulses.denominator != 1:
        raise ValueError("bar span must be exactly divisible by the rhythm grid")
    return pulses.numerator


def _compositions(total: int, parts: int) -> tuple[tuple[int, ...], ...]:
    if total <= 0 or parts <= 0 or parts > total:
        return ()
    if parts == 1:
        return ((total,),)
    result: list[tuple[int, ...]] = []
    for first in range(1, total - parts + 2):
        for tail in _compositions(total - first, parts - 1):
            result.append((first, *tail))
    return tuple(result)


def bar_patterns(
    span: Beat = Fraction(4),
    *,
    policy: BarRhythmPolicy = BarRhythmPolicy(),
) -> tuple[BarPattern, ...]:
    """Enumerate exact NOTE/REST realisations of one bar.

    The default quarter-note grid includes NOTE4, NOTE2+NOTE2, NOTE2+REST2,
    REST2+NOTE2, NOTE2+NOTE1+NOTE1, NOTE2+REST1+NOTE1, and many others. A finer
    half-beat grid can be enabled later without changing the abstraction.
    """

    pulses = _pulse_count(span, policy.grid)
    maximum_cells = min(policy.max_cells, pulses)
    result: list[BarPattern] = []
    for cell_count in range(1, maximum_cells + 1):
        for composition in _compositions(pulses, cell_count):
            for kinds in product(tuple(BarCellKind), repeat=cell_count):
                if not any(kind is BarCellKind.NOTE for kind in kinds):
                    continue
                if sum(kind is BarCellKind.NOTE for kind in kinds) > policy.max_attacks:
                    continue
                if any(
                    left is BarCellKind.REST and right is BarCellKind.REST
                    for left, right in zip(kinds, kinds[1:], strict=False)
                ):
                    continue
                cells = tuple(
                    BarCell(kind, Fraction(pulses_for_cell) * policy.grid)
                    for kind, pulses_for_cell in zip(kinds, composition, strict=True)
                )
                pattern = BarPattern(span, cells)
                if pattern.rest_fraction <= policy.max_rest_fraction:
                    result.append(pattern)
    return tuple(result)


def choose_bar_pattern(
    *,
    rng: SeededRandom,
    intensity: float,
    rest_target: float,
    span: Beat = Fraction(4),
    policy: BarRhythmPolicy = BarRhythmPolicy(),
) -> BarPattern:
    """Choose a bar under independent attack-density and rest governors."""

    if not 0 <= intensity <= 1:
        raise ValueError("intensity must be in 0..1")
    if not 0 <= rest_target <= policy.max_rest_fraction:
        raise ValueError("rest_target exceeds policy")

    candidates = bar_patterns(span, policy=policy)
    target_attacks = 1.0 + intensity * (policy.max_attacks - 1)
    weights: list[float] = []
    for pattern in candidates:
        attack_fit = exp(
            -abs(pattern.attacks - target_attacks) / policy.attack_temperature
        )
        rest_fit = exp(
            -abs(pattern.rest_fraction - rest_target) / policy.rest_temperature
        )
        note_durations = [
            float(cell.duration)
            for cell in pattern.cells
            if cell.kind is BarCellKind.NOTE
        ]
        duration_diversity = len(set(note_durations)) / len(note_durations)
        attack_complexity = (
            (pattern.attacks - 1) / max(1, policy.max_attacks - 1)
        )
        complexity = 0.75 * attack_complexity + 0.25 * duration_diversity
        complexity_fit = exp(
            -abs(complexity - intensity) / policy.complexity_temperature
        )
        weight = attack_fit * rest_fit * complexity_fit
        if pattern.attacks > 1 and len(set(note_durations)) == 1:
            weight *= policy.equal_note_penalty
        weights.append(weight)
    return rng.weighted_choice(candidates, weights)


def realise_bar_pattern(
    pattern: BarPattern,
    *,
    start: Beat,
    pitches: Sequence[int],
    velocities: Sequence[int] | None = None,
    gate: Fraction = Fraction(15, 16),
) -> tuple[NoteEvent, ...]:
    """Turn a NOTE/REST bar pattern into monophonic note events.

    One attack uses the bar's final melodic anchor. Multiple attacks sample the
    source anchors from first through last. Rests create literal empty time.
    """

    if start < 0:
        raise ValueError("bar start must be non-negative")
    if not pitches:
        raise ValueError("at least one pitch anchor is required")
    if velocities is not None and not velocities:
        raise ValueError("velocities may be omitted but not empty")
    if gate <= 0 or gate > 1:
        raise ValueError("gate must be in (0, 1]")

    attack_count = pattern.attacks
    if attack_count == 1:
        pitch_indices = (len(pitches) - 1,)
    else:
        pitch_indices = tuple(
            round(index * (len(pitches) - 1) / (attack_count - 1))
            for index in range(attack_count)
        )

    if velocities is None:
        velocity_values = (80,) * attack_count
    elif attack_count == 1:
        velocity_values = (velocities[-1],)
    else:
        velocity_values = tuple(
            velocities[
                round(index * (len(velocities) - 1) / (attack_count - 1))
            ]
            for index in range(attack_count)
        )

    result: list[NoteEvent] = []
    cursor = start
    attack_index = 0
    for cell in pattern.cells:
        if cell.kind is BarCellKind.NOTE:
            result.append(
                NoteEvent(
                    onset=cursor,
                    duration=cell.duration * gate,
                    pitch=pitches[pitch_indices[attack_index]],
                    velocity=velocity_values[attack_index],
                )
            )
            attack_index += 1
        cursor += cell.duration
    return tuple(result)

"""Reusable scalable lane patterns and explicit pattern locks.

A pattern stores time geometry and relative scale-degree contour, never absolute MIDI
pitches. The same locked idea can therefore be re-anchored against the current
harmony and projected into any compatible lane/key without escaping that lane.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .lanes import LaneSpec, ScaleWorld
from .model import Beat, NoteEvent


@dataclass(frozen=True, slots=True)
class PatternAttack:
    onset: Beat
    duration: Beat
    degree_offset: int

    def __post_init__(self) -> None:
        if self.onset < 0:
            raise ValueError("pattern onset must be non-negative")
        if self.duration <= 0:
            raise ValueError("pattern duration must be positive")

    @property
    def end(self) -> Beat:
        return self.onset + self.duration


@dataclass(frozen=True, slots=True)
class LanePattern:
    """One scalable musical figure relative to an abstract anchor degree."""

    span: Beat
    attacks: tuple[PatternAttack, ...]

    def __post_init__(self) -> None:
        if self.span <= 0:
            raise ValueError("pattern span must be positive")
        if not self.attacks:
            raise ValueError("pattern must contain at least one attack")
        ordered = tuple(sorted(self.attacks, key=lambda item: item.onset))
        if ordered != self.attacks:
            raise ValueError("pattern attacks must be onset ordered")
        if any(attack.end > self.span for attack in self.attacks):
            raise ValueError("pattern attack escapes its span")
        if any(
            right.onset < left.end
            for left, right in zip(self.attacks, self.attacks[1:], strict=False)
        ):
            raise ValueError("pattern attacks may not overlap")

    @property
    def signature(self) -> tuple[tuple[Beat, Beat, int], ...]:
        return tuple(
            (attack.onset, attack.duration, attack.degree_offset)
            for attack in self.attacks
        )


def capture_pattern(
    events: tuple[NoteEvent, ...],
    *,
    world: ScaleWorld,
    lane: LaneSpec,
    start: Beat,
    span: Beat,
) -> LanePattern:
    """Capture complete events inside one window as a scalable relative pattern."""

    selected = tuple(
        event
        for event in events
        if start <= event.onset and event.end <= start + span
    )
    if not selected:
        raise ValueError("capture window contains no complete events")
    degrees = [world.lane_degree(event.pitch, lane) for event in selected]
    anchor = degrees[0]
    attacks = tuple(
        PatternAttack(
            onset=event.onset - start,
            duration=event.duration,
            degree_offset=degree - anchor,
        )
        for event, degree in zip(selected, degrees, strict=True)
    )
    return LanePattern(span=span, attacks=attacks)


def realise_pattern(
    pattern: LanePattern,
    *,
    world: ScaleWorld,
    lane: LaneSpec,
    start: Beat,
    anchor_degree: int,
    velocity: int,
) -> tuple[NoteEvent, ...]:
    """Realise a locked pattern with the current anchor and lane projection."""

    return tuple(
        NoteEvent(
            onset=start + attack.onset,
            duration=attack.duration,
            pitch=world.project_degree(anchor_degree + attack.degree_offset, lane),
            velocity=velocity,
        )
        for attack in pattern.attacks
    )


@dataclass(slots=True)
class PatternBank:
    """Named patterns plus independent per-lane lock state."""

    patterns: dict[str, LanePattern] = field(default_factory=dict)
    locks: dict[str, str] = field(default_factory=dict)

    def remember(self, name: str, pattern: LanePattern) -> None:
        if not name:
            raise ValueError("pattern name must not be empty")
        self.patterns[name] = pattern

    def lock(self, lane: LaneSpec, name: str) -> None:
        if name not in self.patterns:
            raise KeyError(name)
        self.locks[lane.name] = name

    def unlock(self, lane: LaneSpec) -> None:
        self.locks.pop(lane.name, None)

    def locked_pattern(self, lane: LaneSpec) -> LanePattern | None:
        name = self.locks.get(lane.name)
        return None if name is None else self.patterns[name]

    def locked_name(self, lane: LaneSpec) -> str | None:
        return self.locks.get(lane.name)

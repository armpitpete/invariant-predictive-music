"""Core data structures and hard voice invariants for IPM."""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Iterable

Beat = Fraction


class VoiceOverlapError(ValueError):
    """Raised when one monophonic voice contains overlapping note events."""


@dataclass(frozen=True, slots=True)
class IPMConfig:
    """Minimal deterministic-generation configuration for the v0.1 engine."""

    seed: int
    tempo_bpm: int = 88
    bars: int = 16
    beats_per_bar: int = 4

    def __post_init__(self) -> None:
        if self.tempo_bpm <= 0:
            raise ValueError("tempo_bpm must be positive")
        if self.bars <= 0:
            raise ValueError("bars must be positive")
        if self.beats_per_bar <= 0:
            raise ValueError("beats_per_bar must be positive")


@dataclass(frozen=True, slots=True, order=True)
class NoteEvent:
    """One pitched event on a single voice timeline.

    Onset and duration are expressed as exact fractions of a quarter-note beat.
    """

    onset: Beat
    duration: Beat
    pitch: int
    velocity: int = 80

    def __post_init__(self) -> None:
        if self.onset < 0:
            raise ValueError("onset must be non-negative")
        if self.duration <= 0:
            raise ValueError("duration must be positive")
        if not 0 <= self.pitch <= 127:
            raise ValueError("pitch must be a MIDI note number in 0..127")
        if not 1 <= self.velocity <= 127:
            raise ValueError("velocity must be in 1..127")

    @property
    def end(self) -> Beat:
        return self.onset + self.duration


@dataclass(slots=True)
class Voice:
    """A monophonic voice that rejects self-overlap as a hard invariant."""

    name: str
    events: list[NoteEvent] = field(default_factory=list)

    def add(self, event: NoteEvent) -> None:
        if self.events and event.onset < self.events[-1].end:
            previous = self.events[-1]
            raise VoiceOverlapError(
                f"{self.name}: note at {event.onset} overlaps previous note ending at {previous.end}"
            )
        self.events.append(event)

    @classmethod
    def from_events(cls, name: str, events: Iterable[NoteEvent]) -> "Voice":
        voice = cls(name=name)
        for event in sorted(events, key=lambda item: item.onset):
            voice.add(event)
        return voice

    @property
    def cursor(self) -> Beat:
        return self.events[-1].end if self.events else Fraction(0)

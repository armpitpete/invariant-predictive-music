"""Register constraints for singer-like lead voices.

Register is a hard musical boundary. A candidate that lives outside the lead
ambitus must be transformed or rejected before main-voice scoring; octave drift
is not permitted to accumulate across phrases.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .model import NoteEvent


@dataclass(frozen=True, slots=True)
class PitchRegister:
    """Inclusive MIDI pitch window with a preferred centre."""

    low: int
    high: int
    centre: int | None = None

    def __post_init__(self) -> None:
        if not 0 <= self.low <= 127 or not 0 <= self.high <= 127:
            raise ValueError("register bounds must be MIDI pitches in 0..127")
        if self.high < self.low:
            raise ValueError("register high must be >= low")
        if self.high - self.low > 12:
            raise ValueError("lead register may not exceed one octave")
        centre = self.centre if self.centre is not None else (self.low + self.high) // 2
        if not self.low <= centre <= self.high:
            raise ValueError("register centre must lie inside the register")
        object.__setattr__(self, "centre", centre)

    @property
    def span(self) -> int:
        return self.high - self.low

    def contains_pitch(self, pitch: int) -> bool:
        return self.low <= pitch <= self.high

    def contains_events(self, events: Sequence[NoteEvent]) -> bool:
        return all(self.contains_pitch(event.pitch) for event in events)

    def ambitus(self, events: Sequence[NoteEvent]) -> int:
        if not events:
            return 0
        pitches = [event.pitch for event in events]
        return max(pitches) - min(pitches)

    def octave_equivalents(self, pitch: int) -> tuple[int, ...]:
        """Return octave-equivalent spellings of ``pitch`` inside this register."""

        pitch_class = pitch % 12
        return tuple(
            candidate
            for candidate in range(self.low, self.high + 1)
            if candidate % 12 == pitch_class
        )

    def project_pitch(self, pitch: int, *, previous: int | None = None) -> int:
        """Project a pitch into the register without changing its pitch class.

        Local continuity is the first tie-breaker; the register centre is the
        second. This removes cumulative octave drift while retaining tonal identity.
        """

        candidates = self.octave_equivalents(pitch)
        if not candidates:
            raise ValueError(
                f"pitch class {pitch % 12} has no representation in register "
                f"{self.low}..{self.high}"
            )
        anchor = previous if previous is not None else self.centre
        assert anchor is not None
        return min(
            candidates,
            key=lambda candidate: (
                abs(candidate - anchor),
                abs(candidate - self.centre),
                candidate,
            ),
        )

    def project_events(self, events: Sequence[NoteEvent]) -> tuple[NoteEvent, ...]:
        """Project a monophonic event sequence into the register.

        Timing, velocity and pitch class are preserved exactly. Pitch octave is
        chosen sequentially to minimise vocal jumps within the hard ambitus.
        """

        projected: list[NoteEvent] = []
        previous: int | None = None
        for event in events:
            pitch = self.project_pitch(event.pitch, previous=previous)
            projected.append(
                NoteEvent(
                    onset=event.onset,
                    duration=event.duration,
                    pitch=pitch,
                    velocity=event.velocity,
                )
            )
            previous = pitch
        return tuple(projected)

    def require_events(self, events: Sequence[NoteEvent]) -> None:
        if not self.contains_events(events):
            pitches = [event.pitch for event in events]
            raise ValueError(
                f"lead pitches {min(pitches)}..{max(pitches)} exceed hard register "
                f"{self.low}..{self.high}"
            )


# Current C-major listening-study lead: deliberately conservative and exactly
# one octave. This is an artistic target for the study, not a universal claim
# about female singers' ranges.
FEMALE_LEAD_C4_C5 = PitchRegister(low=60, high=72, centre=66)

"""Deterministic musical-moment primitives for the IPM Moment Engine prototype.

A moment is a recorded gesture treated as one playable object. Mutation is
structural and deterministic: it preserves the recorded pitch-class vocabulary
and uses repeat/evolve/surprise controls to create variation without becoming a
random-note generator.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable, Sequence

_GOLDEN_64 = 0x9E3779B97F4A7C15
_MASK_64 = 0xFFFFFFFFFFFFFFFF


@dataclass(frozen=True, slots=True)
class MomentEvent:
    note: int
    velocity: int
    start: float
    duration: float
    channel: int = 0

    def __post_init__(self) -> None:
        if not 0 <= self.note <= 127:
            raise ValueError("note must be in 0..127")
        if not 1 <= self.velocity <= 127:
            raise ValueError("velocity must be in 1..127")
        if self.start < 0:
            raise ValueError("start must be >= 0 beats")
        if self.duration <= 0:
            raise ValueError("duration must be > 0 beats")
        if not 0 <= self.channel <= 15:
            raise ValueError("channel must be in 0..15")

    def public(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class Moment:
    slot: int
    name: str
    events: tuple[MomentEvent, ...]
    length_beats: float
    seed: int

    def __post_init__(self) -> None:
        if not 1 <= self.slot <= 16:
            raise ValueError("slot must be in 1..16")
        if not self.events:
            raise ValueError("a moment must contain at least one event")
        if self.length_beats <= 0:
            raise ValueError("length_beats must be > 0")
        latest = max(event.start + event.duration for event in self.events)
        if latest > self.length_beats + 1e-9:
            raise ValueError("moment length must cover every event")
        if self.seed <= 0:
            raise ValueError("seed must be positive")

    def public(self, *, include_events: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "slot": self.slot,
            "name": self.name,
            "length_beats": self.length_beats,
            "seed": self.seed,
            "event_count": len(self.events),
        }
        if include_events:
            payload["events"] = [event.public() for event in self.events]
        return payload


@dataclass(frozen=True, slots=True)
class MutationControls:
    repeats: int = 1
    evolve: float = 0.0
    surprise: float = 0.0

    def __post_init__(self) -> None:
        if not 1 <= self.repeats <= 8:
            raise ValueError("repeats must be in 1..8")
        for name in ("evolve", "surprise"):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be in 0..1")


@dataclass(frozen=True, slots=True)
class RenderedEvent:
    note: int
    velocity: int
    start: float
    duration: float
    channel: int
    cycle: int
    source_index: int

    def public(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class MomentRender:
    events: tuple[RenderedEvent, ...]
    length_beats: float
    cycle_strengths: tuple[float, ...]

    def public(self) -> dict[str, Any]:
        return {
            "events": [event.public() for event in self.events],
            "length_beats": self.length_beats,
            "cycle_strengths": list(self.cycle_strengths),
        }


def _mix64(seed: int, *parts: int) -> int:
    value = seed & _MASK_64
    for part in parts:
        value = (value + _GOLDEN_64 + (part & _MASK_64)) & _MASK_64
        value ^= value >> 30
        value = (value * 0xBF58476D1CE4E5B9) & _MASK_64
        value ^= value >> 27
        value = (value * 0x94D049BB133111EB) & _MASK_64
        value ^= value >> 31
    return value


def _unit(seed: int, *parts: int) -> float:
    return (_mix64(seed, *parts) >> 11) / float(1 << 53)


def moment_seed(slot: int, events: Sequence[MomentEvent]) -> int:
    """Build a stable positive seed from slot and recorded event content."""

    seed = _mix64(0x4D4F4D454E54, slot)
    for index, event in enumerate(events):
        seed = _mix64(
            seed,
            index,
            event.note,
            event.velocity,
            round(event.start * 1000),
            round(event.duration * 1000),
            event.channel,
        )
    return int(seed & 0x7FFFFFFF) or 1


def normalise_recording(
    *,
    slot: int,
    events: Iterable[MomentEvent],
    length_beats: float | None = None,
    name: str | None = None,
) -> Moment:
    """Shift a captured gesture to beat zero and return a canonical Moment."""

    ordered = sorted(events, key=lambda event: (event.start, event.note, event.channel))
    if not ordered:
        raise ValueError("recording contains no completed notes")

    origin = ordered[0].start
    shifted = tuple(
        MomentEvent(
            note=event.note,
            velocity=event.velocity,
            start=round(event.start - origin, 6),
            duration=round(event.duration, 6),
            channel=event.channel,
        )
        for event in ordered
    )
    required = max(event.start + event.duration for event in shifted)
    if length_beats is None:
        final_length = required
    else:
        final_length = max(float(length_beats) - origin, required)
    final_length = round(final_length, 6)
    return Moment(
        slot=slot,
        name=(name or f"Moment {slot:02d}").strip() or f"Moment {slot:02d}",
        events=shifted,
        length_beats=final_length,
        seed=moment_seed(slot, shifted),
    )


def _cycle_strengths(controls: MutationControls) -> tuple[float, ...]:
    """Return a deterministic disturbance/recovery envelope per repeat."""

    if controls.repeats == 1:
        return (0.0,)

    strengths: list[float] = []
    shock_cycle = controls.repeats - 2 if controls.repeats >= 3 else None
    for cycle in range(controls.repeats):
        if cycle == 0:
            strength = 0.0
        else:
            progress = cycle / max(1, controls.repeats - 1)
            strength = controls.evolve * progress

        if shock_cycle is not None and cycle == shock_cycle:
            strength = max(strength, controls.surprise)

        if cycle == controls.repeats - 1 and controls.surprise > 0:
            strength *= max(0.05, 1.0 - 0.85 * controls.surprise)

        strengths.append(round(min(1.0, max(0.0, strength)), 6))
    return tuple(strengths)


def _clamp_velocity(velocity: int) -> int:
    return min(127, max(1, velocity))


def _mutate_event(
    moment: Moment,
    event: MomentEvent,
    *,
    source_index: int,
    cycle: int,
    strength: float,
) -> MomentEvent:
    if strength <= 0:
        return event

    note = event.note
    velocity = event.velocity
    start = event.start
    duration = event.duration

    if _unit(moment.seed, cycle, source_index, 1) < strength * 0.42:
        direction = -1 if _unit(moment.seed, cycle, source_index, 2) < 0.5 else 1
        candidate = note + 12 * direction
        if 0 <= candidate <= 127:
            note = candidate

    accent = int(round((12 + 16 * strength) * strength))
    if accent and _unit(moment.seed, cycle, source_index, 3) < strength * 0.72:
        direction = -1 if _unit(moment.seed, cycle, source_index, 4) < 0.5 else 1
        velocity = _clamp_velocity(velocity + direction * accent)

    if _unit(moment.seed, cycle, source_index, 5) < strength * 0.62:
        direction = -1 if _unit(moment.seed, cycle, source_index, 6) < 0.5 else 1
        drift = round(0.125 * strength * direction, 6)
        start = max(0.0, start + drift)

    if _unit(moment.seed, cycle, source_index, 7) < strength * 0.58:
        factor = 0.75 if _unit(moment.seed, cycle, source_index, 8) < 0.5 else 1.25
        duration = max(0.03, duration * (1.0 + (factor - 1.0) * strength))

    return MomentEvent(
        note=note,
        velocity=velocity,
        start=round(start, 6),
        duration=round(duration, 6),
        channel=event.channel,
    )


def render_moment(moment: Moment, controls: MutationControls) -> MomentRender:
    """Render one moment as repeated, deterministically evolving cycles."""

    strengths = _cycle_strengths(controls)
    rendered: list[RenderedEvent] = []
    for cycle, strength in enumerate(strengths):
        cycle_offset = cycle * moment.length_beats
        for source_index, event in enumerate(moment.events):
            mutated = _mutate_event(
                moment,
                event,
                source_index=source_index,
                cycle=cycle,
                strength=strength,
            )
            max_duration = max(0.03, moment.length_beats - mutated.start)
            duration = min(mutated.duration, max_duration)
            rendered.append(
                RenderedEvent(
                    note=mutated.note,
                    velocity=mutated.velocity,
                    start=round(cycle_offset + mutated.start, 6),
                    duration=round(duration, 6),
                    channel=mutated.channel,
                    cycle=cycle,
                    source_index=source_index,
                )
            )
    rendered.sort(key=lambda item: (item.start, item.note, item.channel))
    return MomentRender(
        events=tuple(rendered),
        length_beats=round(moment.length_beats * controls.repeats, 6),
        cycle_strengths=strengths,
    )


def render_chain(
    moments: Sequence[Moment],
    controls: MutationControls,
) -> MomentRender:
    """Render a sentence of moments without turning it into a step sequencer."""

    if not moments:
        raise ValueError("chain must contain at least one moment")
    events: list[RenderedEvent] = []
    offset = 0.0
    strengths: list[float] = []
    cycle_base = 0
    for moment in moments:
        rendered = render_moment(moment, controls)
        strengths.extend(rendered.cycle_strengths)
        for event in rendered.events:
            events.append(
                RenderedEvent(
                    note=event.note,
                    velocity=event.velocity,
                    start=round(event.start + offset, 6),
                    duration=event.duration,
                    channel=event.channel,
                    cycle=event.cycle + cycle_base,
                    source_index=event.source_index,
                )
            )
        offset += rendered.length_beats
        cycle_base += controls.repeats
    return MomentRender(
        events=tuple(events),
        length_beats=round(offset, 6),
        cycle_strengths=tuple(strengths),
    )


def moment_from_payload(payload: dict[str, Any]) -> Moment:
    events = tuple(
        MomentEvent(
            note=int(item["note"]),
            velocity=int(item["velocity"]),
            start=float(item["start"]),
            duration=float(item["duration"]),
            channel=int(item.get("channel", 0)),
        )
        for item in payload["events"]
    )
    return normalise_recording(
        slot=int(payload["slot"]),
        events=events,
        length_beats=float(payload.get("length_beats", 0.0)) or None,
        name=str(payload.get("name") or ""),
    )


def controls_from_payload(payload: dict[str, Any]) -> MutationControls:
    return MutationControls(
        repeats=int(payload.get("repeats", 1)),
        evolve=float(payload.get("evolve", 0.0)),
        surprise=float(payload.get("surprise", 0.0)),
    )

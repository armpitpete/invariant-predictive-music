"""Scalable pitch lanes for tune, rhythm and bass.

Musical ideas are expressed as scale degrees first.  A lane then projects the same
abstract degree into its own register.  This keeps harmonic relationships invariant
when the tonic changes and prevents one role from leaking into another role's range.
"""

from __future__ import annotations

from dataclasses import dataclass


AEOLIAN_INTERVALS: tuple[int, ...] = (0, 2, 3, 5, 7, 8, 10)


@dataclass(frozen=True, slots=True)
class LaneSpec:
    """One tonic-relative one-octave register."""

    name: str
    octave_offset: int

    def bounds(self, tonic_midi: int) -> tuple[int, int]:
        low = tonic_midi + 12 * self.octave_offset
        high = low + 11
        if not 0 <= low <= high <= 127:
            raise ValueError(f"lane {self.name} is outside MIDI range for tonic {tonic_midi}")
        return low, high

    def contains(self, pitch: int, *, tonic_midi: int) -> bool:
        low, high = self.bounds(tonic_midi)
        return low <= pitch <= high


TUNE_LANE = LaneSpec("TUNE", 0)
RHYTHM_LANE = LaneSpec("RHYTHM", -1)
BASS_LANE = LaneSpec("BASS", -2)
THREE_LANES: tuple[LaneSpec, LaneSpec, LaneSpec] = (
    TUNE_LANE,
    BASS_LANE,
    RHYTHM_LANE,
)


@dataclass(frozen=True, slots=True)
class ScaleWorld:
    """Tonic plus an interval pattern shared by every lane."""

    tonic_midi: int
    intervals: tuple[int, ...] = AEOLIAN_INTERVALS

    def __post_init__(self) -> None:
        if not 0 <= self.tonic_midi <= 127:
            raise ValueError("tonic must be a MIDI pitch")
        if not self.intervals or self.intervals[0] != 0:
            raise ValueError("scale intervals must begin at the tonic")
        if tuple(sorted(set(self.intervals))) != self.intervals:
            raise ValueError("scale intervals must be strictly increasing and unique")
        if any(not 0 <= interval <= 11 for interval in self.intervals):
            raise ValueError("scale intervals must lie inside one octave")
        for lane in THREE_LANES:
            lane.bounds(self.tonic_midi)

    @property
    def degrees_per_octave(self) -> int:
        return len(self.intervals)

    def degree_class(self, degree: int) -> int:
        return degree % self.degrees_per_octave

    def project_degree(self, degree: int, lane: LaneSpec) -> int:
        """Project any integer scale degree into one lane's tonic-relative octave."""

        low, _ = lane.bounds(self.tonic_midi)
        return low + self.intervals[self.degree_class(degree)]

    def degree_from_pitch(self, pitch: int) -> int:
        """Return the abstract scale degree for any in-scale pitch.

        The returned degree retains octave displacement relative to the tune tonic,
        while callers that only need harmonic identity can use ``degree_class``.
        """

        relative = pitch - self.tonic_midi
        octave, pitch_class = divmod(relative, 12)
        try:
            scale_index = self.intervals.index(pitch_class)
        except ValueError as exc:
            raise ValueError(f"pitch {pitch} is outside the current scale") from exc
        return octave * self.degrees_per_octave + scale_index

    def pitch_is_in_scale(self, pitch: int) -> bool:
        return (pitch - self.tonic_midi) % 12 in self.intervals

    def lane_degree(self, pitch: int, lane: LaneSpec) -> int:
        if not lane.contains(pitch, tonic_midi=self.tonic_midi):
            raise ValueError(f"pitch {pitch} does not fit lane {lane.name}")
        return self.degree_class(self.degree_from_pitch(pitch))

    def transpose_tonic(self, semitones: int) -> "ScaleWorld":
        return ScaleWorld(self.tonic_midi + semitones, self.intervals)

"""Surface-rhythm chooser for slow-pulse music.

A slow tempo must not imply a slow attack rate. This layer chooses NOTE/REST bar
patterns on a finer grid and explicitly penalises long note cells, allowing the
structural pulse to stay slow while the audible surface contains shorter attacks.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from math import exp

from .bar_rhythm import BarCellKind, BarPattern, BarRhythmPolicy, bar_patterns
from .model import Beat
from .randomness import SeededRandom


@dataclass(frozen=True, slots=True)
class SurfaceRhythmPolicy:
    grid: Beat = Fraction(1, 2)
    max_cells: int = 8
    max_attacks: int = 7
    max_rest_fraction: float = 0.50
    attack_temperature: float = 0.55
    rest_temperature: float = 0.16
    long_note_threshold: Beat = Fraction(1)
    long_note_penalty: float = 0.22
    very_long_threshold: Beat = Fraction(2)
    very_long_penalty: float = 0.18
    short_note_bonus: float = 1.55

    def __post_init__(self) -> None:
        if self.grid <= 0:
            raise ValueError("grid must be positive")
        if self.max_cells <= 0 or self.max_attacks <= 0:
            raise ValueError("cell and attack limits must be positive")
        if not 0 <= self.max_rest_fraction < 1:
            raise ValueError("max_rest_fraction must be in [0, 1)")
        if self.attack_temperature <= 0 or self.rest_temperature <= 0:
            raise ValueError("temperatures must be positive")
        if self.long_note_threshold <= 0 or self.very_long_threshold <= 0:
            raise ValueError("duration thresholds must be positive")
        if self.very_long_threshold < self.long_note_threshold:
            raise ValueError("very_long_threshold must not be below long_note_threshold")
        if not 0 < self.long_note_penalty <= 1:
            raise ValueError("long_note_penalty must be in (0, 1]")
        if not 0 < self.very_long_penalty <= 1:
            raise ValueError("very_long_penalty must be in (0, 1]")
        if self.short_note_bonus < 1:
            raise ValueError("short_note_bonus must be at least 1")

    def grammar_policy(self) -> BarRhythmPolicy:
        return BarRhythmPolicy(
            grid=self.grid,
            max_cells=self.max_cells,
            max_attacks=self.max_attacks,
            max_rest_fraction=self.max_rest_fraction,
        )


@lru_cache(maxsize=32)
def _legal_patterns(span: Beat, grammar_policy: BarRhythmPolicy) -> tuple[BarPattern, ...]:
    """Enumerate a grammar once; repeated stochastic choices reuse the same family."""

    return bar_patterns(span, policy=grammar_policy)


def choose_surface_pattern(
    *,
    rng: SeededRandom,
    target_attacks: float,
    rest_target: float,
    span: Beat = Fraction(4),
    policy: SurfaceRhythmPolicy = SurfaceRhythmPolicy(),
) -> BarPattern:
    """Choose a bar pattern with an explicit audible attack-rate objective.

    Long note cells remain legal, but each one pays a multiplicative penalty. Notes
    of one grid pulse receive a modest bonus. This makes sustained notes punctuation
    rather than the statistical default at slow tempos.
    """

    if target_attacks < 1 or target_attacks > policy.max_attacks:
        raise ValueError("target_attacks is outside policy")
    if not 0 <= rest_target <= policy.max_rest_fraction:
        raise ValueError("rest_target exceeds policy")

    candidates = _legal_patterns(span, policy.grammar_policy())
    weights: list[float] = []
    for pattern in candidates:
        attack_fit = exp(
            -abs(pattern.attacks - target_attacks) / policy.attack_temperature
        )
        rest_fit = exp(
            -abs(pattern.rest_fraction - rest_target) / policy.rest_temperature
        )

        note_cells = [
            cell for cell in pattern.cells if cell.kind is BarCellKind.NOTE
        ]
        short_count = sum(cell.duration <= policy.grid for cell in note_cells)
        long_count = sum(
            cell.duration > policy.long_note_threshold for cell in note_cells
        )
        very_long_count = sum(
            cell.duration >= policy.very_long_threshold for cell in note_cells
        )

        duration_weight = policy.short_note_bonus ** short_count
        duration_weight *= policy.long_note_penalty ** long_count
        duration_weight *= policy.very_long_penalty ** very_long_count

        weights.append(attack_fit * rest_fit * duration_weight)

    return rng.weighted_choice(candidates, weights)

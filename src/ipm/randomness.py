"""Deterministic stochastic source for all IPM branch sampling."""

from __future__ import annotations

import random
from collections.abc import Sequence
from typing import TypeVar

T = TypeVar("T")


class SeededRandom:
    """A single seeded source so a generation trace can be reproduced exactly."""

    def __init__(self, seed: int) -> None:
        self.seed = seed
        self._rng = random.Random(seed)

    def random(self) -> float:
        return self._rng.random()

    def choice(self, values: Sequence[T]) -> T:
        if not values:
            raise ValueError("cannot choose from an empty sequence")
        return self._rng.choice(values)

    def weighted_choice(self, values: Sequence[T], weights: Sequence[float]) -> T:
        if not values:
            raise ValueError("cannot choose from an empty sequence")
        if len(values) != len(weights):
            raise ValueError("values and weights must have equal length")
        if any(weight < 0 for weight in weights):
            raise ValueError("weights must be non-negative")
        if not any(weight > 0 for weight in weights):
            raise ValueError("at least one weight must be positive")
        return self._rng.choices(values, weights=weights, k=1)[0]

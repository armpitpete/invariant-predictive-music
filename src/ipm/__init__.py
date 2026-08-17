"""Invariant Predictive Music reference engine."""

from .model import IPMConfig, NoteEvent, Voice, VoiceOverlapError
from .randomness import SeededRandom
from .sonority import (
    ActiveNote,
    SonoritySlice,
    TextureScore,
    VerticalScore,
    contextual_pair_score,
    interval_class,
    interval_prior,
    metrical_strength,
    score_sonority,
    score_texture,
    set_coherence,
    slice_active_sonorities,
)

__all__ = [
    "ActiveNote",
    "IPMConfig",
    "NoteEvent",
    "SeededRandom",
    "SonoritySlice",
    "TextureScore",
    "VerticalScore",
    "Voice",
    "VoiceOverlapError",
    "contextual_pair_score",
    "interval_class",
    "interval_prior",
    "metrical_strength",
    "score_sonority",
    "score_texture",
    "set_coherence",
    "slice_active_sonorities",
]

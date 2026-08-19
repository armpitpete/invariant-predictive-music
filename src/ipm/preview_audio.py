"""Compatibility entrypoint for IPM Machine audio rendering.

Machine v0 originally used a simple preview oscillator.  PLAY and FINISH now
route through the deterministic Machine Synth Engine v1.  The old function
name is retained so the machine orchestration layer does not need to change.
"""

from __future__ import annotations

from pathlib import Path

from .engine import InstrumentResult
from .synth_engine import DEFAULT_SAMPLE_RATE, render_synth_wav


def render_preview_wav(
    result: InstrumentResult,
    path: str | Path,
    *,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
) -> Path:
    """Render the machine's proper stereo synth engine (compatibility name)."""

    return render_synth_wav(result, path, sample_rate=sample_rate)

"""Canonical v4R1 pre-audition diagnostic functions.

The metric definitions and frozen thresholds come from
REAL_SYNTH_ENGINE_V4R1_CONTROL_DIAGNOSTICS_v0_1.md. Audio is held in memory;
this module never writes an audition file.
"""
from __future__ import annotations

from run_real_synth_v4r1_pre_audition_preflight import (  # re-export frozen metrics
    metric_for, residual_ok, family_pass as _base_family_pass,
)


def effective_drive(patch, value: float) -> float:
    route = sum(float(r.get("amount", 0.0)) * value for r in patch.routes if r.get("source") == "macro6" and r.get("destination") == "drive")
    return float(patch.filter.get("drive", 1.0)) * 1.175 * (2.0 ** (5.0 * (value - .5))) + .1 * route


def family_pass(macro, values, patch):
    if macro != "DRIVE":
        return _base_family_pass(macro, values, patch)
    lo, mid, hi = (values[str(x)] for x in (.15, .50, .85))
    ilo, ihi = effective_drive(patch, .15), effective_drive(patch, .85)
    ok = ihi >= 1.35 * ilo and lo - hi >= .5
    return bool(ok), {"crest_delta_db": lo-hi, "internal_ratio": ihi/(ilo+1e-12), "effective_drive_low": ilo, "effective_drive_high": ihi}

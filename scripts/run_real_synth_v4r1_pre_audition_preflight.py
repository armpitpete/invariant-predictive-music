"""Mechanical preflight for the frozen v4R1 pre-audition package.

No WAV is written and no human audition is performed.  Audio exists only as
in-memory floating-point arrays used to evaluate the already-frozen control
diagnostics and structural R-C/R-E prerequisites.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np

from ipm.real_synth_v4 import MACRO_NAMES, OfflineHostV4, ScheduledEventV4, patch_to_dict

sys.path.insert(0, str(Path(__file__).resolve().parent))
from real_synth_v4r1_pre_audition_package import (  # noqa: E402
    BLOCK_SIZE,
    R_D_CONTROL_PREROLL_SECONDS,
    R_D_NOTE_PITCH,
    R_D_NOTE_VELOCITY,
    R_D_VALUES,
    SAMPLE_RATE,
    canonical_sha,
    macro_mapping_manifest,
    r_c_bank,
    r_d_bank,
    r_e_patches,
    reference_patches,
    structural_manifest,
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def render_macro(patch, macro: str, value: float, *, held: float = 4.0, tail: float = 1.5):
    preroll = round(R_D_CONTROL_PREROLL_SECONDS * SAMPLE_RATE)
    on = preroll
    off = on + round(held * SAMPLE_RATE)
    total = off + round(tail * SAMPLE_RATE)
    events = [
        ScheduledEventV4(0, "control", (macro, value)),
        ScheduledEventV4(on, "note_on", ("diag", "TUNE", R_D_NOTE_PITCH, R_D_NOTE_VELOCITY)),
        ScheduledEventV4(off, "note_off", ("diag",)),
    ]
    host = OfflineHostV4(sample_rate=SAMPLE_RATE, block_size=BLOCK_SIZE)
    out, pre = host.render(r_d_bank(patch), events, total, return_pre_master=True)
    if not np.all(np.isfinite(out)) or not np.all(np.isfinite(pre)):
        raise RuntimeError("non-finite diagnostic audio")
    return out, pre, on, off


def mono(x: np.ndarray) -> np.ndarray:
    return (x[0] + x[1]) / 2.0


def steady(x: np.ndarray, note_on: int) -> np.ndarray:
    lo = note_on + round(0.250 * SAMPLE_RATE)
    hi = note_on + round(3.500 * SAMPLE_RATE)
    return x[:, lo:hi]


def stft_frames(x: np.ndarray):
    n = 4096
    hop = 1024
    if len(x) < n:
        return np.zeros((0, n // 2 + 1)), np.fft.rfftfreq(n, 1 / SAMPLE_RATE)
    win = np.hanning(n)
    frames = []
    for start in range(0, len(x) - n + 1, hop):
        q = x[start:start+n]
        if np.sqrt(np.mean(q*q)) < 10 ** (-60 / 20):
            continue
        frames.append(np.abs(np.fft.rfft(q * win)))
    return np.asarray(frames), np.fft.rfftfreq(n, 1 / SAMPLE_RATE)


def band_mask(freqs, lo, hi):
    return (freqs >= lo) & (freqs <= hi)


def spectral_centroid(x):
    s, f = stft_frames(x); m = band_mask(f, 80, 10000)
    if len(s) == 0: return 0.0
    p = s[:, m] + 1e-12
    return float(np.median((p * f[m]).sum(axis=1) / p.sum(axis=1)))


def body_share(x):
    s, f = stft_frames(x)
    if len(s) == 0: return 0.0
    p = s * s
    low = p[:, band_mask(f, 80, 300)].sum()
    total = p[:, band_mask(f, 80, 6000)].sum() + 1e-12
    return float(low / total)


def spectral_flux(x):
    s, f = stft_frames(x); s = s[:, band_mask(f, 80, 10000)]
    if len(s) < 2: return 0.0
    s = s / (np.linalg.norm(s, axis=1, keepdims=True) + 1e-12)
    d = np.maximum(s[1:] - s[:-1], 0.0)
    return float(np.median(np.sqrt(np.sum(d*d, axis=1))))


def spectral_entropy(x):
    s, f = stft_frames(x); s = s[:, band_mask(f, 80, 10000)]
    if len(s) == 0: return 0.0
    p = s*s; p = p / (p.sum(axis=1, keepdims=True) + 1e-12)
    h = -(p * np.log(p + 1e-12)).sum(axis=1) / math.log(p.shape[1])
    return float(np.median(h))


def crest_factor_db(x):
    rms = math.sqrt(float(np.mean(x*x))) + 1e-12
    peak = float(np.max(np.abs(x))) + 1e-12
    return float(20 * math.log10(peak / rms))


def side_ratio(x):
    m = (x[0] + x[1]) / math.sqrt(2)
    s = (x[0] - x[1]) / math.sqrt(2)
    me = float(np.mean(m*m)); se = float(np.mean(s*s))
    return se / (me + se + 1e-12)


def t90_ms(x, note_on):
    q = mono(x[:, note_on:note_on + round(.300*SAMPLE_RATE)])
    n = max(1, round(.010*SAMPLE_RATE))
    sq = np.convolve(q*q, np.ones(n)/n, mode="valid")
    e = np.sqrt(np.maximum(sq, 0))
    target = .9 * float(np.max(e))
    idx = int(np.argmax(e >= target)) if np.any(e >= target) else len(e)-1
    return 1000.0 * idx / SAMPLE_RATE


def late_ratio(x, note_off):
    a0 = note_off - round(1.250*SAMPLE_RATE); a1 = note_off - round(.250*SAMPLE_RATE)
    b0 = note_off + round(.250*SAMPLE_RATE); b1 = note_off + round(1.250*SAMPLE_RATE)
    before = float(np.sum(x[:, a0:a1]**2)) + 1e-12
    after = float(np.sum(x[:, b0:b1]**2))
    return after / before


def effective_drive(patch, value):
    route = sum(float(r.get("amount", 0.0)) * value for r in patch.routes if r.get("source") == "macro6" and r.get("destination") == "drive")
    return float(patch.filter.get("drive", 1.0)) * (.35 + 1.65*value) + .1*route


def metric_for(macro, patch, value):
    held, tail = (1.0, 1.5) if macro == "ATTACK" else (2.0, 2.0) if macro == "SPACE" else (4.0, 1.5)
    out, pre, on, off = render_macro(patch, macro, value, held=held, tail=tail)
    if macro == "ATTACK": return t90_ms(pre, on)
    if macro == "SPACE": return late_ratio(out, off)
    q = steady(pre, on)
    m = mono(q)
    if macro == "BRIGHTNESS": return spectral_centroid(m)
    if macro == "BODY": return body_share(m)
    if macro == "MOTION": return spectral_flux(m)
    if macro == "CHARACTER": return spectral_entropy(m)
    if macro == "DRIVE": return crest_factor_db(m)
    if macro == "WIDTH": return side_ratio(q)
    raise KeyError(macro)


def family_pass(macro: str, values: dict[str, float], patch) -> tuple[bool, dict[str, Any]]:
    lo, mid, hi = (values[str(x)] for x in R_D_VALUES)
    if macro == "BRIGHTNESS":
        ok = hi >= 1.12*lo and mid >= .99*lo and hi >= .99*mid
        detail = {"ratio_hi_lo": hi/(lo+1e-12)}
    elif macro == "BODY":
        ok = hi-lo >= .04 and mid >= lo-.005 and hi >= mid-.005
        detail = {"delta_hi_lo": hi-lo}
    elif macro == "MOTION":
        ok = hi >= 1.25*lo and mid >= .97*lo and hi >= .97*mid
        detail = {"ratio_hi_lo": hi/(lo+1e-12)}
    elif macro == "ATTACK":
        ok = hi <= .75*lo and lo-hi >= 5.0 and mid <= lo+1.0 and hi <= mid+1.0
        detail = {"ratio_hi_lo": hi/(lo+1e-12), "delta_ms": lo-hi}
    elif macro == "CHARACTER":
        ok = hi-lo >= .05 and mid >= lo-.01 and hi >= mid-.01
        detail = {"delta_hi_lo": hi-lo}
    elif macro == "DRIVE":
        ilo, ihi = effective_drive(patch, .15), effective_drive(patch, .85)
        ok = ihi >= 1.35*ilo and lo-hi >= .5
        detail = {"crest_delta_db": lo-hi, "internal_ratio": ihi/(ilo+1e-12)}
    elif macro == "WIDTH":
        ok = hi-lo >= .05 and mid >= lo-.005 and hi >= mid-.005
        detail = {"delta_hi_lo": hi-lo}
    elif macro == "SPACE":
        ok = hi >= 1.50*lo and hi-lo >= .03 and mid >= .95*lo and hi >= .95*mid
        detail = {"ratio_hi_lo": hi/(lo+1e-12), "delta_hi_lo": hi-lo}
    else: raise KeyError(macro)
    return bool(ok), detail


def residual_ok(macro, lo, hi):
    if macro == "BRIGHTNESS": return hi >= .97*lo
    if macro == "BODY": return hi >= lo-.01
    if macro == "MOTION": return hi >= .95*lo
    if macro == "ATTACK": return hi <= lo+2.0
    if macro == "CHARACTER": return hi >= lo-.015
    if macro == "DRIVE": return hi <= lo+.25
    if macro == "WIDTH": return hi >= lo-.01
    if macro == "SPACE": return hi >= .90*lo
    return False


def run(root: Path):
    manifest = structural_manifest(root)
    patches = reference_patches()
    metrics: dict[str, Any] = {}
    overall = True
    for macro in MACRO_NAMES:
        fam = {}
        passes = 0
        residuals = []
        for family, patch in patches.items():
            vals = {str(x): metric_for(macro, patch, x) for x in R_D_VALUES}
            ok, detail = family_pass(macro, vals, patch)
            passes += int(ok)
            lo, hi = vals[str(.15)], vals[str(.85)]
            residuals.append(ok or residual_ok(macro, lo, hi))
            fam[family] = {"values": vals, "full_threshold_pass": ok, **detail}
        macro_ok = passes >= 2 and all(residuals)
        metrics[macro] = {"families": fam, "family_rule_pass": macro_ok, "full_pass_count": passes}
        overall &= macro_ok

    # R-C structural isolation and dry-bank policy, no rendering.
    va, fm, modal = patches["VA"], patches["FM"], patches["MODAL"]
    r_c_ok = bool(va.va and not va.fm.get("enabled") and not va.modal.get("enabled") and not fm.va and fm.fm.get("enabled") and not fm.modal.get("enabled") and not modal.va and not modal.fm.get("enabled") and modal.modal.get("enabled"))
    for p in patches.values():
        b = r_c_bank(p)
        r_c_ok &= b.chorus.get("wet", 0) == 0 and b.delay.get("wet", 0) == 0 and b.reverb.get("wet", 0) == 0 and not p.evolution

    # R-E must differ only in evolution data and span note/phrase/piece plus
    # timbral, movement and spatial perceptual dimensions.
    static, evolving = r_e_patches()
    sd, ed = patch_to_dict(static), patch_to_dict(evolving)
    differing = sorted(k for k in sd if sd[k] != ed[k])
    scopes = {c.scope for c in evolving.evolution}; targets = {c.target for c in evolving.evolution}
    r_e_ok = differing == ["evolution"] and scopes == {"note", "phrase", "piece"} and bool(targets & {"BRIGHTNESS", "BODY", "CHARACTER"}) and bool(targets & {"MOTION", "ATTACK"}) and bool(targets & {"WIDTH", "SPACE"})

    return {
        "status": "PASS" if overall and r_c_ok and r_e_ok else "FAIL",
        "human_audition_performed": False,
        "audition_audio_created": False,
        "wav_files_written": 0,
        "structural_manifest": manifest,
        "r_c_structural_preflight": "PASS" if r_c_ok else "FAIL",
        "r_d_mechanical_diagnostics": metrics,
        "r_e_structural_preflight": {"status": "PASS" if r_e_ok else "FAIL", "differing_patch_keys": differing, "scopes": sorted(scopes), "targets": sorted(targets)},
        "macro_mapping_sha256": canonical_sha(macro_mapping_manifest()),
    }


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--output", default="REAL_SYNTH_ENGINE_V4R1_PRE_AUDITION_PREFLIGHT_v0_1.json")
    args = ap.parse_args(); root = Path(__file__).resolve().parents[1]
    report = run(root); out = root / args.output; out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "r_c": report["r_c_structural_preflight"], "r_e": report["r_e_structural_preflight"]["status"], "output": str(out)}, indent=2))
    return 0 if report["status"] == "PASS" else 1

if __name__ == "__main__": raise SystemExit(main())

"""Materialise the frozen v4R1 R-D macro-authority audition later.

Not invoked by the pre-audition freeze. R-C must already be frozen PASS.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from ipm.real_synth_v4 import MACRO_NAMES, OfflineHostV4, ScheduledEventV4

sys.path.insert(0, str(Path(__file__).resolve().parent))
from real_synth_v4r1_freeze import require_frozen_package  # noqa: E402
from real_synth_v4r1_pre_audition_package import (  # noqa: E402
    BLOCK_SIZE, R_D_CONTROL_PREROLL_SECONDS, R_D_NOTE_PITCH, R_D_NOTE_VELOCITY,
    R_D_VALUES, SAMPLE_RATE, r_d_bank, reference_patches,
)
from real_synth_v4r1_diagnostics import family_pass, metric_for  # noqa: E402

R_C_RESULT_PATH=Path("REAL_SYNTH_ENGINE_V4R1_GATE_C_RESULT_v0_1.json")


def require_provenance(root:Path):
    freeze=require_frozen_package(root); rc=json.loads((root/R_C_RESULT_PATH).read_text())
    if rc.get("status")!="PASS" or rc.get("owner_judgment")!="PASS": raise RuntimeError("R-C is not frozen PASS")
    if rc.get("package_freeze_head")!=freeze.get("package_freeze_head"): raise RuntimeError("R-C package mismatch")
    return freeze,rc


def render_one(patch,macro,value):
    held,tail=(1.0,1.5) if macro=="ATTACK" else (2.0,2.0) if macro=="SPACE" else (4.0,1.5)
    pre=round(R_D_CONTROL_PREROLL_SECONDS*SAMPLE_RATE); on=pre; off=on+round(held*SAMPLE_RATE); total=off+round(tail*SAMPLE_RATE)
    events=[ScheduledEventV4(0,"control",(macro,value)),ScheduledEventV4(on,"note_on",("diag","TUNE",R_D_NOTE_PITCH,R_D_NOTE_VELOCITY)),ScheduledEventV4(off,"note_off",("diag",))]
    return OfflineHostV4(sample_rate=SAMPLE_RATE,block_size=BLOCK_SIZE).render(r_d_bank(patch),events,total)


def render(output_dir="real-synth-engine-v4r1-gate-d"):
    root=Path(__file__).resolve().parents[1]; freeze,_=require_provenance(root); out=root/output_dir; out.mkdir(parents=True,exist_ok=True)
    patches=reference_patches(); files={}; metrics={}
    for macro in MACRO_NAMES:
        metrics[macro]={}; files[macro]={}
        for family,patch in patches.items():
            vals={str(v):metric_for(macro,patch,v) for v in R_D_VALUES}; ok,detail=family_pass(macro,vals,patch); metrics[macro][family]={"values":vals,"full_threshold_pass":ok,**detail}; files[macro][family]={}
            for v in R_D_VALUES:
                audio=render_one(patch,macro,v); p=out/f"{macro.lower()}-{family.lower()}-{str(v).replace('.','p')}.wav"; OfflineHostV4(sample_rate=SAMPLE_RATE,block_size=BLOCK_SIZE).write_wav(audio,p); files[macro][family][str(v)]={"file":p.name,"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"frames":int(audio.shape[1])}
    acceptance={"gate":"RealSynthEngine v4R1 R-D macro/control authority","status":"READY_FOR_R_D_AUDITION_NOT_JUDGED","package_freeze_head":freeze["package_freeze_head"],"human_audition_performed":False,"judgments":{},"values":list(R_D_VALUES),"files":files,"mechanical_metrics":metrics,"question":"Does this control make a clearly perceptible and musically useful change in the intended direction without destroying the patch identity?"}
    (out/"acceptance.json").write_text(json.dumps(acceptance,sort_keys=True,indent=2)+"\n"); return out


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--output-dir",default="real-synth-engine-v4r1-gate-d"); a=ap.parse_args(); render(a.output_dir)

if __name__=="__main__": main()

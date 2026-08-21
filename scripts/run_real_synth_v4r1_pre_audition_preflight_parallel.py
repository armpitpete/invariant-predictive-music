"""Parallel runner for the frozen v4R1 no-audio preflight.

It preserves the metric definitions in run_real_synth_v4r1_pre_audition_preflight
and only parallelises independent family/macro/value renders.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ipm.real_synth_v4 import MACRO_NAMES, patch_to_dict  # noqa: E402
from real_synth_v4r1_pre_audition_package import (  # noqa: E402
    R_D_VALUES, canonical_sha, macro_mapping_manifest, r_c_bank, r_e_patches,
    reference_patches, structural_manifest,
)
from run_real_synth_v4r1_pre_audition_preflight import (  # noqa: E402
    family_pass, metric_for, residual_ok,
)


def _task(args):
    macro,family,value=args
    patch=reference_patches()[family]
    return macro,family,value,metric_for(macro,patch,value)


def run(root:Path):
    manifest=structural_manifest(root); patches=reference_patches(); tasks=[(m,f,v) for m in MACRO_NAMES for f in patches for v in R_D_VALUES]
    raw={m:{f:{} for f in patches} for m in MACRO_NAMES}
    workers=max(1,min(4,os.cpu_count() or 1))
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for macro,family,value,metric in ex.map(_task,tasks): raw[macro][family][str(value)]=metric
    metrics={}; overall=True
    for macro in MACRO_NAMES:
        fam={}; passes=0; residuals=[]
        for family,patch in patches.items():
            vals=raw[macro][family]; ok,detail=family_pass(macro,vals,patch); passes+=int(ok); lo,hi=vals[str(.15)],vals[str(.85)]; residuals.append(ok or residual_ok(macro,lo,hi)); fam[family]={"values":vals,"full_threshold_pass":ok,**detail}
        macro_ok=passes>=2 and all(residuals); metrics[macro]={"families":fam,"family_rule_pass":macro_ok,"full_pass_count":passes}; overall &= macro_ok
    va,fm,modal=patches["VA"],patches["FM"],patches["MODAL"]
    rc=bool(va.va and not va.fm.get("enabled") and not va.modal.get("enabled") and not fm.va and fm.fm.get("enabled") and not fm.modal.get("enabled") and not modal.va and not modal.fm.get("enabled") and modal.modal.get("enabled"))
    for p in patches.values():
        b=r_c_bank(p); rc &= b.chorus.get("wet",0)==0 and b.delay.get("wet",0)==0 and b.reverb.get("wet",0)==0 and not p.evolution
    static,evolving=r_e_patches(); sd,ed=patch_to_dict(static),patch_to_dict(evolving); differing=sorted(k for k in sd if sd[k]!=ed[k]); scopes={c.scope for c in evolving.evolution}; targets={c.target for c in evolving.evolution}
    re_ok=differing==["evolution"] and scopes=={"note","phrase","piece"} and bool(targets & {"BRIGHTNESS","BODY","CHARACTER"}) and bool(targets & {"MOTION","ATTACK"}) and bool(targets & {"WIDTH","SPACE"})
    return {"status":"PASS" if overall and rc and re_ok else "FAIL","human_audition_performed":False,"audition_audio_created":False,"wav_files_written":0,"structural_manifest":manifest,"r_c_structural_preflight":"PASS" if rc else "FAIL","r_d_mechanical_diagnostics":metrics,"r_e_structural_preflight":{"status":"PASS" if re_ok else "FAIL","differing_patch_keys":differing,"scopes":sorted(scopes),"targets":sorted(targets)},"macro_mapping_sha256":canonical_sha(macro_mapping_manifest()),"parallel_workers":workers}


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--output",default="REAL_SYNTH_ENGINE_V4R1_PRE_AUDITION_PREFLIGHT_v0_1.json"); a=ap.parse_args(); root=Path(__file__).resolve().parents[1]; d=run(root); (root/a.output).write_text(json.dumps(d,sort_keys=True,indent=2)+"\n"); print(json.dumps({"status":d["status"],"r_c":d["r_c_structural_preflight"],"r_e":d["r_e_structural_preflight"]["status"],"output":a.output},indent=2)); return 0 if d["status"]=="PASS" else 1

if __name__=="__main__": raise SystemExit(main())

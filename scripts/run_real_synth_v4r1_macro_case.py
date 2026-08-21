"""Run one frozen v4R1 R-D macro/family case without writing audio."""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from real_synth_v4r1_pre_audition_package import R_D_VALUES, reference_patches  # noqa: E402
from run_real_synth_v4r1_pre_audition_preflight import family_pass, metric_for, residual_ok  # noqa: E402


def _metric(args):
    macro,family,value=args
    return value,metric_for(macro,reference_patches()[family],value)


def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument('--macro',required=True); ap.add_argument('--family',required=True); ap.add_argument('--output',required=True); a=ap.parse_args()
    patches=reference_patches()
    if a.family not in patches: raise SystemExit(f'unknown family {a.family}')
    patch=patches[a.family]
    with ProcessPoolExecutor(max_workers=3) as ex:
        vals={str(v):metric for v,metric in ex.map(_metric,[(a.macro,a.family,v) for v in R_D_VALUES])}
    full,detail=family_pass(a.macro,vals,patch)
    residual=full or residual_ok(a.macro,vals[str(.15)],vals[str(.85)])
    d={'macro':a.macro,'family':a.family,'values':vals,'full_threshold_pass':bool(full),'residual_tolerance_pass':bool(residual),**detail,'human_audition_performed':False,'audition_audio_created':False,'wav_files_written':0}
    Path(a.output).write_text(json.dumps(d,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'macro':a.macro,'family':a.family,'full':full,'residual':residual},indent=2))
    return 0

if __name__=='__main__': raise SystemExit(main())

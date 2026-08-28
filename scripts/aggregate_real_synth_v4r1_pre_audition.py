"""Aggregate frozen per-macro/family mechanical evidence. No audio."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ipm.real_synth_v4 import MACRO_NAMES  # noqa: E402
from real_synth_v4r1_pre_audition_package import canonical_sha, macro_mapping_manifest  # noqa: E402


def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument('--cases-dir',default='macro-cases'); ap.add_argument('--structural',default='structural-preflight.json'); ap.add_argument('--output',default='REAL_SYNTH_ENGINE_V4R1_PRE_AUDITION_PREFLIGHT_v0_1.json'); a=ap.parse_args()
    structural=json.loads(Path(a.structural).read_text())
    cases=[]
    for p in sorted(Path(a.cases_dir).glob('*.json')): cases.append(json.loads(p.read_text()))
    if len(cases)!=24: raise RuntimeError(f'expected 24 macro/family cases, found {len(cases)}')
    by={m:{} for m in MACRO_NAMES}
    for c in cases:
        if c['macro'] not in by or c['family'] in by[c['macro']]: raise RuntimeError('duplicate/invalid case')
        by[c['macro']][c['family']]=c
    metrics={}; all_family_rules=True
    for macro in MACRO_NAMES:
        fam=by[macro]
        if set(fam)!={'VA','FM','MODAL'}: raise RuntimeError(f'missing family for {macro}')
        full_count=sum(bool(x['full_threshold_pass']) for x in fam.values())
        family_rule=full_count>=2 and all(bool(x['residual_tolerance_pass']) for x in fam.values())
        metrics[macro]={'families':fam,'full_pass_count':full_count,'family_rule_pass':family_rule}
        all_family_rules &= family_rule
    re_targets=set(structural['r_e']['targets'])
    re_target_full={m:bool(by[m]['MODAL']['full_threshold_pass']) for m in sorted(re_targets)}
    re_targets_pass=all(re_target_full.values())
    status='PASS' if structural['r_c_structural_preflight']=='PASS' and structural['r_e_structural_preflight']=='PASS' and all_family_rules and re_targets_pass else 'FAIL'
    out={
        'status':status,
        'human_audition_performed':False,
        'audition_audio_created':False,
        'wav_files_written':0,
        'structural_manifest':structural['manifest'],
        'r_c_structural_preflight':structural['r_c_structural_preflight'],
        'r_d_mechanical_diagnostics':metrics,
        'r_e_structural_preflight':structural['r_e_structural_preflight'],
        'r_e_target_full_threshold_pass':re_target_full,
        'macro_mapping_sha256':canonical_sha(macro_mapping_manifest()),
    }
    Path(a.output).write_text(json.dumps(out,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':status,'r_e_targets':re_target_full},indent=2))
    return 0 if status=='PASS' else 1

if __name__=='__main__': raise SystemExit(main())

"""Run RealSynthEngine v4 Gate A/B mechanical acceptance only.

Produces JSON evidence only. It creates no audition audio and performs no
human/audible gates (C onward).
"""
from __future__ import annotations
import argparse, hashlib, json, platform, subprocess, sys
from pathlib import Path
import numpy as np

GROUPS={"A":"test_gate_a_","B1":"b1_","B2":"b2_","B3":"b3_","B4":"b4_","B5":"b5_","B6":"b6_","B7":"b7_","B8":"b8_"}

def sha256(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1<<20),b''): h.update(c)
    return h.hexdigest()

def run_group(root:Path, selector:str):
    cmd=[sys.executable,'-m','pytest','-q','tests/v4_gate_ab','-k',selector]
    p=subprocess.run(cmd,cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    return {'status':'PASS' if p.returncode==0 else 'FAIL','returncode':p.returncode,'command':' '.join(cmd),'output':p.stdout.strip()}

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--implementation-commit',default='UNCOMMITTED'); ap.add_argument('--output',default='REAL_SYNTH_ENGINE_V4_GATE_AB_RESULTS_v0_1.json'); a=ap.parse_args()
    root=Path(__file__).resolve().parents[1]
    groups={k:run_group(root,v) for k,v in GROUPS.items()}
    gate_a=groups['A']['status']; gate_b='PASS' if all(groups[f'B{i}']['status']=='PASS' for i in range(1,9)) else 'FAIL'; overall='PASS' if gate_a==gate_b=='PASS' else 'FAIL'
    files={}
    for p in sorted((root/'src/ipm').glob('real_synth_v4*.py')): files[str(p.relative_to(root))]=sha256(p)
    for p in sorted((root/'tests/v4_gate_ab').glob('test_*.py')): files[str(p.relative_to(root))]=sha256(p)
    files[str(Path(__file__).resolve().relative_to(root))]=sha256(Path(__file__).resolve())
    report={'gate':'RealSynthEngine v4 Gate A / Gate B technical acceptance','status':overall,'architecture_commit':'a53980fb6b9358aee985cf4bdccd61d63bb36365','implementation_commit':a.implementation_commit,'human_audition_performed':False,'audition_audio_created':False,'gate_A':gate_a,'gate_B':gate_b,'subgates':groups,'environment':{'python':platform.python_version(),'platform':platform.platform(),'numpy':np.__version__},'files':files,'stop_rule':'No Gate C/D/E/F/G audition or human listening performed by this harness.'}
    out=root/a.output; out.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':overall,'gate_A':gate_a,'gate_B':gate_b,'output':str(out)},indent=2)); return 0 if overall=='PASS' else 1
if __name__=='__main__': raise SystemExit(main())

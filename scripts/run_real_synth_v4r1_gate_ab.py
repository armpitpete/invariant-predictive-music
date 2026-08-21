"""Run RealSynthEngine v4R1 R-A/R-B mechanical acceptance only.

This harness re-runs the complete historical v4 Gate A/B tests and then the
v4R1 delta assertions. It writes JSON evidence only: no WAVs, audition audio,
human judgments, or R-C onward artifacts are created.
"""
from __future__ import annotations
import argparse, hashlib, json, platform, subprocess, sys
from pathlib import Path
import numpy as np

OLD_GROUPS={"A":"test_gate_a_","B1":"b1_","B2":"b2_","B3":"b3_","B4":"b4_","B5":"b5_","B6":"b6_","B7":"b7_","B8":"b8_"}

def sha256(p:Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda:f.read(1<<20),b""): h.update(c)
    return h.hexdigest()

def run_pytest(root:Path,paths:list[str],selector:str|None=None):
    cmd=[sys.executable,"-m","pytest","-q",*paths]
    if selector: cmd += ["-k",selector]
    p=subprocess.run(cmd,cwd=root,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    return {"status":"PASS" if p.returncode==0 else "FAIL","returncode":p.returncode,"command":" ".join(cmd),"output":p.stdout.strip()}

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--implementation-commit",default="UNCOMMITTED")
    ap.add_argument("--output",default="REAL_SYNTH_ENGINE_V4R1_GATE_AB_RESULTS_v0_1.json")
    a=ap.parse_args()
    root=Path(__file__).resolve().parents[1]

    historical={k:run_pytest(root,["tests/v4_gate_ab"],v) for k,v in OLD_GROUPS.items()}
    revision_a=run_pytest(root,["tests/v4r1_gate_ab/test_r_a.py"],"r_a_")
    revision_b=run_pytest(root,["tests/v4r1_gate_ab/test_r_b.py"],"r_b_")

    gate_a="PASS" if historical["A"]["status"]=="PASS" and revision_a["status"]=="PASS" else "FAIL"
    old_b="PASS" if all(historical[f"B{i}"]["status"]=="PASS" for i in range(1,9)) else "FAIL"
    gate_b="PASS" if old_b=="PASS" and revision_b["status"]=="PASS" else "FAIL"
    overall="PASS" if gate_a==gate_b=="PASS" else "FAIL"

    files={}
    for p in sorted((root/"src/ipm").glob("real_synth_v4*.py")): files[str(p.relative_to(root))]=sha256(p)
    for folder in ("tests/v4_gate_ab","tests/v4r1_gate_ab"):
        for p in sorted((root/folder).glob("test_*.py")): files[str(p.relative_to(root))]=sha256(p)
    files[str(Path(__file__).resolve().relative_to(root))]=sha256(Path(__file__).resolve())

    report={
        "gate":"RealSynthEngine v4R1 R-A / R-B mechanical acceptance",
        "status":overall,
        "historical_architecture_commit":"a53980fb6b9358aee985cf4bdccd61d63bb36365",
        "v4r1_design_freeze_commit":"9189116cdf34937f1212d052378b36f5d4bd503f",
        "implementation_commit":a.implementation_commit,
        "human_audition_performed":False,
        "audition_audio_created":False,
        "gate_R_A":gate_a,
        "gate_R_B":gate_b,
        "historical_v4_groups":historical,
        "v4r1_delta":{"R_A":revision_a,"R_B":revision_b},
        "environment":{"python":platform.python_version(),"platform":platform.platform(),"numpy":np.__version__},
        "files":files,
        "stop_rule":"No R-C/R-D/R-E/R-F/R-G audition, WAV, or human listening performed by this harness."
    }
    out=root/a.output
    out.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"status":overall,"gate_R_A":gate_a,"gate_R_B":gate_b,"output":str(out)},indent=2))
    return 0 if overall=="PASS" else 1

if __name__=="__main__": raise SystemExit(main())

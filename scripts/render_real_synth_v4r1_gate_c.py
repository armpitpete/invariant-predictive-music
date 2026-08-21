"""Materialise the already-frozen v4R1 R-C family audition later.

This file is frozen before the first v4R1 human audition.  It is intentionally
NOT invoked by the pre-audition workflow.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import secrets
import sys
from fractions import Fraction
from pathlib import Path

from ipm.real_synth_v4 import OfflineHostV4, ScheduledEventV4

sys.path.insert(0, str(Path(__file__).resolve().parent))
from real_synth_v4r1_pre_audition_package import (  # noqa: E402
    BLOCK_SIZE, LEDGER_SHA256, SAMPLE_RATE, canonical_sha, load_frozen_ledger,
    r_c_bank, reference_patches,
)

FREEZE_PATH = Path("REAL_SYNTH_ENGINE_V4R1_PRE_AUDITION_FREEZE_v0_1.json")


def require_freeze(root: Path):
    d = json.loads((root/FREEZE_PATH).read_text())
    if d.get("status") != "FROZEN_PRE_AUDITION_PACKAGE" or d.get("human_audition_performed") is not False:
        raise RuntimeError("v4R1 pre-audition package is not frozen")
    return d


def events_from_ledger(payload):
    tempo = int(payload["tempo_bpm"]); spb = 60.0/tempo
    ev=[ScheduledEventV4(0,"transport",(tempo,0.0,0.0,0.0,0.0))]
    for i,x in enumerate(payload["tune_events"]):
        onset=Fraction(*x["onset"]); duration=Fraction(*x["duration"])
        on=round(float(onset)*spb*SAMPLE_RATE); off=round(float(onset+duration)*spb*SAMPLE_RATE)
        ev += [ScheduledEventV4(on,"note_on",(f"TUNE:{i}","TUNE",int(x["pitch"]),int(x["velocity"]))),ScheduledEventV4(off,"note_off",(f"TUNE:{i}",))]
    total=math.ceil(payload["bars"]*payload["beats_per_bar"]*spb*SAMPLE_RATE)+SAMPLE_RATE
    return ev,total


def render(output_dir="real-synth-engine-v4r1-gate-c", private_dir="real-synth-engine-v4r1-gate-c-private"):
    root=Path(__file__).resolve().parents[1]; freeze=require_freeze(root); ledger=load_frozen_ledger(root)
    if canonical_sha(ledger["tune_events"]) != LEDGER_SHA256: raise RuntimeError("ledger drift")
    patches=reference_patches(); events,total=events_from_ledger(ledger)
    nonce=secrets.token_bytes(32); order=list(patches); random.Random(int.from_bytes(nonce,"big")).shuffle(order)
    mapping={f"blind-{i+1}":family for i,family in enumerate(order)}
    private_payload={"nonce_hex":nonce.hex(),"mapping":mapping}
    commitment=canonical_sha(private_payload)
    out=root/output_dir; private=root/private_dir; blind=out/"blind"; blind.mkdir(parents=True,exist_ok=True); private.mkdir(parents=True,exist_ok=True)
    files={}
    for label,family in mapping.items():
        audio=OfflineHostV4(sample_rate=SAMPLE_RATE,block_size=BLOCK_SIZE).render(r_c_bank(patches[family]),events,total)
        path=blind/f"{label}.wav"; OfflineHostV4(sample_rate=SAMPLE_RATE,block_size=BLOCK_SIZE).write_wav(audio,path)
        files[label]={"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"frames":int(audio.shape[1])}
    (private/"mapping.json").write_text(json.dumps(private_payload,sort_keys=True,indent=2)+"\n")
    acceptance={
        "gate":"RealSynthEngine v4R1 R-C family separation","status":"READY_FOR_R_C_AUDITION_NOT_JUDGED",
        "package_freeze_head":freeze["package_freeze_head"],"mapping_commitment_sha256":commitment,
        "ledger_sha256":LEDGER_SHA256,"human_audition_performed":False,"owner_judgment":None,
        "files":files,"question":"Do these sound like three genuinely different instruments whose identities come from three different synthesis families, rather than three presets of essentially the same voice?"
    }
    (out/"acceptance.json").write_text(json.dumps(acceptance,sort_keys=True,indent=2)+"\n")
    return out,private


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--output-dir",default="real-synth-engine-v4r1-gate-c"); ap.add_argument("--private-dir",default="real-synth-engine-v4r1-gate-c-private"); a=ap.parse_args(); render(a.output_dir,a.private_dir)

if __name__=="__main__": main()

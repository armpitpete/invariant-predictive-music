"""Materialise the frozen v4R1 R-E STATIC/EVOLVING audition later.

Not invoked by the pre-audition freeze.  R-D must already be frozen PASS.  The
written Tune ledger is never regenerated or passed back through composition.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np

from ipm.real_synth_v4 import RealSynthEngineV4, patch_to_dict

sys.path.insert(0, str(Path(__file__).resolve().parent))
from real_synth_v4r1_pre_audition_package import (  # noqa: E402
    BLOCK_SIZE, LEDGER_SHA256, R_E_PHRASE_BARS, SAMPLE_RATE, canonical_sha,
    load_frozen_ledger, r_e_bank, r_e_patches,
)

FREEZE_PATH=Path("REAL_SYNTH_ENGINE_V4R1_PRE_AUDITION_FREEZE_v0_1.json")
R_D_RESULT_PATH=Path("REAL_SYNTH_ENGINE_V4R1_GATE_D_RESULT_v0_1.json")


def require_provenance(root:Path):
    freeze=json.loads((root/FREEZE_PATH).read_text()); rd=json.loads((root/R_D_RESULT_PATH).read_text())
    if freeze.get("status")!="FROZEN_PRE_AUDITION_PACKAGE": raise RuntimeError("package not frozen")
    if rd.get("status")!="PASS": raise RuntimeError("R-D is not frozen PASS")
    if rd.get("package_freeze_head")!=freeze.get("package_freeze_head"): raise RuntimeError("R-D package mismatch")
    return freeze,rd


def written_events(payload):
    tempo=float(payload["tempo_bpm"]); spb=60.0/tempo; ev=[]
    for i,x in enumerate(payload["tune_events"]):
        onset=Fraction(*x["onset"]); duration=Fraction(*x["duration"]); on=round(float(onset)*spb*SAMPLE_RATE); off=round(float(onset+duration)*spb*SAMPLE_RATE); nid=f"TUNE:{i}"
        ev += [(on,0,"on",(nid,"TUNE",int(x["pitch"]),int(x["velocity"]))),(off,1,"off",(nid,))]
    ev.sort(key=lambda x:(x[0],x[1])); total=math.ceil(payload["bars"]*payload["beats_per_bar"]*spb*SAMPLE_RATE)+SAMPLE_RATE
    return ev,total


def render_condition(patch,payload,events,total):
    tempo=float(payload["tempo_bpm"]); beats_per_bar=int(payload["beats_per_bar"]); bars=int(payload["bars"]); total_beats=bars*beats_per_bar
    e=RealSynthEngineV4(sample_rate=SAMPLE_RATE,block_size=BLOCK_SIZE); e.load_patch_bank(r_e_bank(patch)); chunks=[]; transport=[]; cursor=0; k=0
    while cursor<total:
        n=min(BLOCK_SIZE,total-cursor); beat=(cursor/SAMPLE_RATE)*(tempo/60.0); bar=beat/beats_per_bar; phrase=(bar%R_E_PHRASE_BARS)/R_E_PHRASE_BARS; piece=min(1.0,beat/total_beats)
        e.set_transport(tempo,beat,bar,phrase,piece); transport.append({"sample":cursor,"beat_position":beat,"bar_position":bar,"phrase_position":phrase,"piece_position":piece})
        while k<len(events) and events[k][0]<cursor+n:
            sample,_,kind,payload_event=events[k]
            if sample>=cursor:
                off=sample-cursor
                if kind=="on": e.note_on(*payload_event,sample_offset=off)
                else: e.note_off(*payload_event,sample_offset=off)
            k+=1
        chunks.append(e.process_block(n)); cursor+=n
    return np.concatenate(chunks,axis=1),transport


def render(output_dir="real-synth-engine-v4r1-gate-e"):
    root=Path(__file__).resolve().parents[1]; freeze,_=require_provenance(root); ledger=load_frozen_ledger(root)
    if canonical_sha(ledger["tune_events"])!=LEDGER_SHA256: raise RuntimeError("written ledger drift")
    static,evolving=r_e_patches(); sd,ed=patch_to_dict(static),patch_to_dict(evolving); diff=sorted(k for k in sd if sd[k]!=ed[k])
    if diff != ["evolution"]: raise RuntimeError(f"R-E condition patch drift: {diff}")
    events,total=written_events(ledger); a,ta=render_condition(static,ledger,events,total); b,tb=render_condition(evolving,ledger,events,total)
    if ta!=tb: raise RuntimeError("transport streams differ")
    out=root/output_dir; out.mkdir(parents=True,exist_ok=True); host_bank=r_e_bank(static)
    from ipm.real_synth_v4 import OfflineHostV4
    h=OfflineHostV4(sample_rate=SAMPLE_RATE,block_size=BLOCK_SIZE); pa=out/"STATIC.wav"; pb=out/"EVOLVING.wav"; h.write_wav(a,pa); h.write_wav(b,pb)
    automation={"ledger_sha256":LEDGER_SHA256,"control_events":[],"per_piece_manual_changes":[],"transport":ta,"evolution_curves":ed["evolution"]}
    (out/"automation-ledger.json").write_text(json.dumps(automation,sort_keys=True,indent=2)+"\n")
    acceptance={"gate":"RealSynthEngine v4R1 R-E musical evolution","status":"READY_FOR_R_E_AUDITION_NOT_JUDGED","package_freeze_head":freeze["package_freeze_head"],"human_audition_performed":False,"written_event_ledger_sha256":LEDGER_SHA256,"condition_diff":["evolution"],"transport_stream_identical":True,"manual_changes":False,"files":{"STATIC.wav":{"sha256":hashlib.sha256(pa.read_bytes()).hexdigest()},"EVOLVING.wav":{"sha256":hashlib.sha256(pb.read_bytes()).hexdigest()},"automation-ledger.json":{"sha256":hashlib.sha256((out/'automation-ledger.json').read_bytes()).hexdigest()}},"questions":["Can you hear coherent sonic development over time in EVOLVING that is absent or materially weaker in STATIC?","Does that development preserve recognition of the same written musical material rather than sounding like a hidden replacement composition?"]}
    (out/"acceptance.json").write_text(json.dumps(acceptance,sort_keys=True,indent=2)+"\n"); return out


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--output-dir",default="real-synth-engine-v4r1-gate-e"); a=ap.parse_args(); render(a.output_dir)

if __name__=="__main__": main()

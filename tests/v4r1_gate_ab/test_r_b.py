from __future__ import annotations
from dataclasses import replace
import numpy as np
import pytest
from ipm.real_synth_v4 import *

SR=44_100

def _render_with_state(patch,block,events,frames,transport=None):
    e=RealSynthEngineV4(sample_rate=SR,block_size=block); e.load_patch_bank(technical_bank(patch))
    ordered=sorted(events,key=lambda x:x.sample); idx=0; cur=0; out=[]
    while cur<frames:
        n=min(block,frames-cur)
        if transport is not None:
            beat=(cur/SR)*2.; e.set_transport(120,beat,beat/4.,(beat%16)/16.,min(1.,beat/32.))
        while idx<len(ordered) and ordered[idx].sample<cur+n:
            ev=ordered[idx]; off=ev.sample-cur
            if ev.kind=="note_on": e.note_on(*ev.payload,sample_offset=off)
            elif ev.kind=="note_off": e.note_off(*ev.payload,sample_offset=off)
            elif ev.kind=="control": e.control_change(*ev.payload,sample_offset=off)
            idx+=1
        out.append(e.process_block(n)); cur+=n
    return np.concatenate(out,axis=1),e

def test_r_b_note_evolution_is_block_size_deterministic():
    p=replace(technical_va_patch(),note_evolution_seconds=1.7,evolution=(EvolutionCurveV4("note","BRIGHTNESS",((0.,-.2),(.4,.15),(1.,.05))),))
    events=[ScheduledEventV4(13,"note_on",("n","TUNE",60,100)),ScheduledEventV4(6000,"note_off",("n",))]
    outputs={b:_render_with_state(p,b,events,8000,transport=True)[0] for b in (64,128,256,512)}
    ref=outputs[128]
    for out in outputs.values():
        d=out-ref
        assert out.shape==ref.shape
        assert np.max(np.abs(d))<=2e-5
        assert np.sqrt(np.mean(d*d))<=2e-6

def test_r_b_horizon_changes_only_evolution_timebase_not_note_scheduling():
    curves=(EvolutionCurveV4("note","BRIGHTNESS",((0.,-.2),(1.,.2))),)
    events=[ScheduledEventV4(23,"note_on",("n","TUNE",60,100)),ScheduledEventV4(5000,"note_off",("n",))]
    a,ea=_render_with_state(replace(technical_va_patch(),note_evolution_seconds=.5,evolution=curves),128,events,6500)
    b,eb=_render_with_state(replace(technical_va_patch(),note_evolution_seconds=2.,evolution=curves),128,events,6500)
    la=[(x["kind"],x.get("note_id"),x["sample"]) for x in ea.snapshot_state()["event_log"] if x["kind"].startswith("note_")]
    lb=[(x["kind"],x.get("note_id"),x["sample"]) for x in eb.snapshot_state()["event_log"] if x["kind"].startswith("note_")]
    assert la==lb==[("note_on","n",23),("note_off","n",5000)]
    assert not np.array_equal(a,b)

def test_r_b_phrase_piece_transport_does_not_move_written_events():
    p=replace(technical_va_patch(),evolution=(EvolutionCurveV4("phrase","BRIGHTNESS",((0.,-.2),(1.,.2))),EvolutionCurveV4("piece","WIDTH",((0.,-.2),(1.,.2)))))
    events=[ScheduledEventV4(17,"note_on",("a","TUNE",60,100)),ScheduledEventV4(1300,"note_off",("a",)),ScheduledEventV4(1457,"note_on",("b","TUNE",64,100)),ScheduledEventV4(3001,"note_off",("b",))]
    _,e=_render_with_state(p,128,events,4000,transport=True)
    got=[(x["kind"],x.get("note_id"),x["sample"]) for x in e.snapshot_state()["event_log"] if x["kind"].startswith("note_")]
    assert got==[("note_on","a",17),("note_off","a",1300),("note_on","b",1457),("note_off","b",3001)]

def test_r_b_continuous_control_and_evolution_paths_are_finite_and_continuous():
    p=replace(technical_va_patch(),note_evolution_seconds=1.3,evolution=(EvolutionCurveV4("note","BRIGHTNESS",((0.,-.15),(.5,.2),(1.,-.05))),EvolutionCurveV4("phrase","WIDTH",((0.,-.1),(1.,.1)))))
    events=[ScheduledEventV4(1,"note_on",("n","TUNE",60,100)),ScheduledEventV4(500,"control",("BRIGHTNESS",.85)),ScheduledEventV4(3500,"note_off",("n",))]
    out,_=_render_with_state(p,128,events,4500,transport=True)
    assert np.all(np.isfinite(out))
    der=np.abs(np.diff(out.mean(axis=0)))
    assert np.max(der)<.25

def test_r_b_attack_is_event_boundary_and_does_not_rewrite_completed_attack():
    p=replace(technical_va_patch(polyphony=2),evolution=(),amp_env=EnvelopeSpecV4(.020,.02,.65,.04))
    e=RealSynthEngineV4(sample_rate=SR,block_size=512); e.load_patch_bank(technical_bank(p))
    e.control_change("ATTACK",.15,0); e.process_block(256)
    e.note_on("slow","TUNE",60,100,0); e.process_block(1)
    slow=e.voices[0].amp.s.attack
    e.process_block(511)
    e.control_change("ATTACK",.85,0); e.process_block(256)
    assert e.voices[0].amp.s.attack==pytest.approx(slow)
    e.note_on("fast","TUNE",64,100,0); e.process_block(1)
    fast=e.voices[1].amp.s.attack
    assert fast<slow
    assert fast<=.75*slow
    assert slow-fast>=.005

def test_r_b_roundtrip_preserves_horizon_and_application_policy():
    app=list(DEFAULT_MACRO_APPLICATION); app[4]="new_notes_only"
    p=replace(technical_modal_patch(),note_evolution_seconds=3.25,macro_application=tuple(app))
    q=patch_from_dict(patch_to_dict(p))
    assert q==p and q.note_evolution_seconds==3.25 and q.macro_application[4]=="new_notes_only"
    b=technical_bank(p); assert bank_from_dict(bank_to_dict(b))==b

from __future__ import annotations
import inspect
from dataclasses import replace
from fractions import Fraction
from types import SimpleNamespace
import numpy as np
import pytest
from ipm.real_synth_v4 import *

SR=44_100

def events(): return [ScheduledEventV4(17,"note_on",("n1","TUNE",60,96)),ScheduledEventV4(811,"control",("BRIGHTNESS",.72)),ScheduledEventV4(1271,"note_on",("n2","TUNE",67,72)),ScheduledEventV4(2444,"note_off",("n1",)),ScheduledEventV4(3311,"note_off",("n2",))]
def render(patch,block=128,frames=6000,pre=False): return OfflineHostV4(sample_rate=SR,block_size=block).render(technical_bank(patch),events(),frames,return_pre_master=pre)

# Gate A
@pytest.mark.parametrize("p",[technical_va_patch(),technical_fm_patch(),technical_modal_patch()])
def test_b1_deterministic_pcm(p):
    a,b=render(p),render(p); assert np.array_equal(a,b); h=OfflineHostV4(sample_rate=SR,block_size=128); assert h.pcm16_bytes(a)==h.pcm16_bytes(b)

# B2
def test_b2_note_lifecycle_release_reset():
    e=RealSynthEngineV4(sample_rate=SR,block_size=128); e.load_patch_bank(technical_bank(technical_va_patch())); e.note_on("n","TUNE",60,100,7); b=e.process_block(128)
    assert np.allclose(b[:,:7],0) and np.any(np.abs(b[:,8:])>0) and e.snapshot_state()["event_log"][0]["sample"]==7
    e.note_off("n",11); e.process_block(128); v=e.snapshot_state()["voices"][0]; assert not v["held"] and v["amp_stage"] in {"release","idle"}; assert np.any(np.abs(e.process_block(128))>0)
    e.all_notes_off(); e.process_block(128); e.reset(SR,128); s=e.snapshot_state(); assert s["absolute_sample"]==0 and s["voices"]==[] and s["event_log"]==[]

# B3
def test_b3_block_continuity():
    p=replace(technical_va_patch(),va=({"waveform":"sine","gain":.2,"octave":0,"semitone":0,"cents":0.,"phase":0.,"pulse_width":.5,"key_tracking":1.},),amp_env=EnvelopeSpecV4(0,0,1,0),filter={"mode":"lowpass","cutoff_hz":12000.,"resonance_q":.7,"key_tracking":0.,"drive":0.},routes=(),evolution=())
    ev=[ScheduledEventV4(1,"note_on",("steady","TUNE",36,80))]
    outputs={n:OfflineHostV4(sample_rate=SR,block_size=n).render(technical_bank(p),ev,6000) for n in (64,128,256,512)}; ref=outputs[128]
    for size,a in outputs.items():
        d=a-ref; assert a.shape==ref.shape and np.max(np.abs(d))<=2e-5 and np.sqrt(np.mean(d*d))<=2e-6
        if size==128: continue
        der=np.diff(a.mean(axis=0),prepend=a.mean(axis=0)[0]); radius=round(.005*SR)
        for q in range(size,a.shape[1],size):
            lo,hi=max(0,q-radius),min(len(der),q+radius); rms=np.sqrt(np.mean(der[lo:hi]**2))+1e-12; assert abs(der[q])<=2*rms+1e-9

# B4

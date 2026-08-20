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
def test_b7_serialization_validation_migration_ledger_integrity():
    p=technical_modal_patch(); assert patch_from_dict(patch_to_dict(p))==p; b=technical_bank(p); assert bank_from_dict(bank_to_dict(b))==b
    with pytest.raises(ValueError): SynthPatchV4("bad",polyphony=0)
    v3={"name":"legacy","oscillators":[{"waveform":"saw","gain":.5,"pulse_width":.5,"phase":0.,"octave":0,"semitone":0,"cents":0.}],"amp_env":{"attack":.01,"decay":.2,"sustain":.7,"release":.3},"filter_env":{"attack":.02,"decay":.3,"sustain":.2,"release":.4},"filter":{"mode":"lowpass","cutoff_hz":3000.,"resonance_q":.8,"key_tracking":.35,"drive":1.},"lfo1":{"waveform":"sine","rate_hz":.2,"phase":0.,"bipolar":True},"lfo2":{"waveform":"triangle","rate_hz":.1,"phase":.2,"bipolar":True},"modulation":[{"source":"lfo1","destination":"cutoff","amount":.4}],"sends":{"chorus":.1,"delay":0.,"reverb":.2},"base_pan":-.1,"stereo_width":.8,"unison_voices":2}
    a,c=migrate_v3_patch(v3),migrate_v3_patch(v3); assert patch_to_dict(a)==patch_to_dict(c) and not a.fm["enabled"] and not a.modal["enabled"] and not a.evolution and np.any(np.abs(render(a,frames=2000))>0)
    result=SimpleNamespace(config=SimpleNamespace(tempo_bpm=120,bars=1,beats_per_bar=4),voices=(SimpleNamespace(name="TUNE",events=[SimpleNamespace(onset=Fraction(0),duration=Fraction(1),pitch=60,velocity=90)]),)); before=repr(result.voices[0].events[0].__dict__); ev,total=schedule_instrument_result(result,sample_rate=SR); OfflineHostV4(sample_rate=SR,block_size=128).render(technical_bank(technical_va_patch()),ev,min(total,3000)); assert repr(result.voices[0].events[0].__dict__)==before

# B8
def test_b8_fixed_gain_no_whole_piece_normalisation():
    p=technical_va_patch(); bank=technical_bank(p); phrase=[ScheduledEventV4(20,"note_on",("p","TUNE",60,80)),ScheduledEventV4(900,"note_off",("p",))]; loud=phrase+[ScheduledEventV4(2500,"note_on",("l1","TUNE",84,127)),ScheduledEventV4(2500,"note_on",("l2","TUNE",88,127)),ScheduledEventV4(3900,"note_off",("l1",)),ScheduledEventV4(3900,"note_off",("l2",))]; h=OfflineHostV4(sample_rate=SR,block_size=128); q,qp=h.render(bank,phrase,4500,return_pre_master=True); z,zp=h.render(bank,loud,4500,return_pre_master=True); assert np.max(np.abs(qp[:,:2000]-zp[:,:2000]))<=1e-9 and np.array_equal(q[:,:2000],z[:,:2000]) and np.max(np.abs(z))<=.98+1e-12; pcm=np.frombuffer(h.pcm16_bytes(z),dtype="<i2"); assert pcm.min()>=-32767 and pcm.max()<=32767

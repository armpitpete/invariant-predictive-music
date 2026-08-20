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
def test_b4_voice_stealing_rule_and_declick():
    e=RealSynthEngineV4(sample_rate=SR,block_size=128); p=technical_va_patch(polyphony=2); e.load_patch_bank(technical_bank(p)); e.note_on("a","TUNE",60,127,0); e.note_on("b","TUNE",64,80,1); e.process_block(128)
    e.note_off("a",0); e.process_block(64); level=e.snapshot_state()["voices"][0]["allocation_level"]; e.note_on("c","TUNE",67,100,0); e.process_block(1); log=e.snapshot_state()["allocation_log"][-1]
    assert log["voice_index"]==0 and log["stolen_note_id"]=="a" and log["stolen_allocation_level"]==pytest.approx(level) and log["steal_tail_samples"]==round(.005*SR)
    e.process_block(127); levels={v["note_id"]:v["allocation_level"] for v in e.snapshot_state()["voices"]}; expected=min(levels,key=levels.get); e.note_on("d","TUNE",72,110,0); e.process_block(1); assert e.snapshot_state()["allocation_log"][-1]["stolen_note_id"]==expected and np.all(np.isfinite(e.process_block(64)))

# B5
def test_b5_mono_retrigger_legato_portamento():
    p=technical_va_patch(voice_mode="mono_retrigger",portamento_seconds=.02); e=RealSynthEngineV4(sample_rate=SR,block_size=128); e.load_patch_bank(technical_bank(p)); e.note_on("a","TUNE",60,100,0); e.process_block(64); old=e.snapshot_state()["voices"][0]["amp_level"]; e.note_on("b","TUNE",72,100,0); e.process_block(1); v=e.snapshot_state()["voices"][0]; assert len(e.snapshot_state()["voices"])==1 and v["note_id"]=="b" and 60<v["current_pitch"]<72 and v["target_pitch"]==72 and v["amp_level"]<old
    p=replace(technical_va_patch(voice_mode="mono_legato",portamento_seconds=.02),amp_env=EnvelopeSpecV4(.001,.02,.8,.04,retrigger="legato")); e=RealSynthEngineV4(sample_rate=SR,block_size=128); e.load_patch_bank(technical_bank(p)); e.note_on("a","TUNE",60,100,0); e.process_block(64); old=e.snapshot_state()["voices"][0]["amp_level"]; e.note_on("b","TUNE",72,100,0); e.process_block(1); v=e.snapshot_state()["voices"][0]; assert 60<v["current_pitch"]<72 and v["amp_level"]>=old*.8

# B6
def test_b6_macro_schedule_smoothing_and_new_notes_patch_policy():
    p=technical_va_patch(); e=RealSynthEngineV4(sample_rate=SR,block_size=512); e.load_patch_bank(technical_bank(p)); e.note_on("n","TUNE",60,100,0)
    for off,val in ((50,.2),(150,.8),(250,.4)): e.control_change("BRIGHTNESS",val,off)
    assert np.all(np.isfinite(e.process_block(512))); logs=[x for x in e.snapshot_state()["event_log"] if x["kind"]=="control"]; assert [x["sample"] for x in logs]==[50,150,250] and all(x["ramp_samples"]==round(.005*SR) for x in logs)
    old=e.snapshot_state()["voices"][0]["patch_name"]; e.load_patch_bank(technical_bank(replace(p,name="replacement"))); e.process_block(1); assert e.snapshot_state()["voices"][0]["patch_name"]==old

# B7

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
def test_gate_a_state_machine_and_offline_host():
    s=inspect.getsource(OfflineHostV4.render); assert "RealSynthEngineV4" in s and "process_block" in s and "whole_note" not in s
def test_gate_a_families_algorithms_macros_evolution():
    assert technical_va_patch().va and technical_fm_patch().fm["enabled"] and technical_modal_patch().modal["enabled"]
    assert FM_ALGORITHMS==("4>3>2>1","(4+3+2)>1","(4>3)+(2>1)","(4>3>1)+(2>1)","(4>2>1)+(3>1)","4>(3+2)>1","(4>1)+(3>1)+(2>1)","4+3+2+1")
    base=technical_fm_patch()
    for a in FM_ALGORITHMS:
        fm=dict(base.fm); fm["algorithm"]=a; audio=render(replace(base,fm=fm),frames=1200); assert np.all(np.isfinite(audio)) and np.any(np.abs(audio)>0)
    assert MACRO_NAMES==("BRIGHTNESS","BODY","MOTION","ATTACK","CHARACTER","DRIVE","WIDTH","SPACE")
    assert {c.scope for c in technical_va_patch().evolution}=={"note","phrase","piece"}
def test_gate_a_no_a5_composition_feedback_and_patch_migration_exists():
    import ipm.real_synth_v4 as m
    s=inspect.getsource(m).lower(); assert "import a5" not in s and "select_seed" not in s and "candidate_selection" not in s
    assert callable(migrate_v3_patch) and DESIGN_COMMIT=="a53980fb6b9358aee985cf4bdccd61d63bb36365"

# B1

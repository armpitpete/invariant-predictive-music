from __future__ import annotations
from dataclasses import replace
import pytest
from ipm.real_synth_v4 import *

SR=44_100
V4R1_FREEZE="9189116cdf34937f1212d052378b36f5d4bd503f"

def _engine(patch, block=128):
    e=RealSynthEngineV4(sample_rate=SR,block_size=block)
    e.load_patch_bank(technical_bank(patch))
    return e

def test_r_a_revision_identity_and_explicit_note_horizon():
    p=technical_va_patch()
    assert ENGINE_VERSION=="4R1"
    assert DESIGN_COMMIT=="a53980fb6b9358aee985cf4bdccd61d63bb36365"
    assert V4R1_DESIGN_FREEZE_COMMIT==V4R1_FREEZE
    assert p.note_evolution_seconds==1.0
    assert .05<=p.note_evolution_seconds<=30.
    with pytest.raises(ValueError): replace(p,note_evolution_seconds=.049)
    with pytest.raises(ValueError): replace(p,note_evolution_seconds=30.001)

def test_r_a_note_position_uses_patch_horizon():
    p=replace(technical_va_patch(),note_evolution_seconds=2.0,evolution=())
    e=_engine(p); e.note_on("n","TUNE",60,100,0); e.process_block(1); v=e.voices[0]
    v.age=SR
    assert e._note_evolution_position(v,p)==pytest.approx(.5)
    v.age=2*SR
    assert e._note_evolution_position(v,p)==pytest.approx(1.)
    p2=replace(p,note_evolution_seconds=4.0)
    assert e._note_evolution_position(v,p2)==pytest.approx(.5)

def test_r_a_macro_application_classes_are_explicit_and_validated():
    p=technical_va_patch()
    assert p.macro_application==DEFAULT_MACRO_APPLICATION
    assert p.macro_application[3]=="event_boundary"
    q=replace(p,macro_application=("new_notes_only","continuous","continuous","event_boundary","continuous","continuous","continuous","continuous"))
    assert q.macro_application[0]=="new_notes_only"
    with pytest.raises(ValueError): replace(p,macro_application=("continuous",)*8)
    with pytest.raises(ValueError): replace(p,routes=p.routes+({"source":"macro4","destination":"filter_cutoff","amount":1.},))

def test_r_a_continuous_vs_new_notes_only_policy_on_held_voice():
    base=replace(technical_va_patch(),evolution=())
    continuous=_engine(base); continuous.note_on("n","TUNE",60,100,0); continuous.process_block(1); vc=continuous.voices[0]
    before=continuous._macros(vc,base)[0]
    continuous.control_change("BRIGHTNESS",.85,0); continuous.process_block(128); continuous.process_block(128)
    after=continuous._macros(vc,base)[0]
    assert after>before

    app=list(base.macro_application); app[0]="new_notes_only"
    frozen=replace(base,macro_application=tuple(app))
    held=_engine(frozen); held.note_on("n","TUNE",60,100,0); held.process_block(1); vh=held.voices[0]
    held_before=held._macros(vh,frozen)[0]
    held.control_change("BRIGHTNESS",.85,0); held.process_block(128); held.process_block(128)
    assert held._macros(vh,frozen)[0]==pytest.approx(held_before)
    held.note_on("n2","TUNE",64,100,0); held.process_block(1)
    assert held._macros(held.voices[1],frozen)[0]>held_before

def test_r_a_phrase_piece_are_host_authoritative_and_multi_curve_evolution_is_additive_only_to_sound():
    curves=(
        EvolutionCurveV4("note","MOTION",((0.,-.2),(1.,.2))),
        EvolutionCurveV4("phrase","BRIGHTNESS",((0.,-.15),(1.,.15))),
        EvolutionCurveV4("piece","WIDTH",((0.,-.1),(1.,.1))),
        EvolutionCurveV4("piece","SPACE",((0.,-.05),(1.,.05))),
    )
    p=replace(technical_va_patch(),note_evolution_seconds=2.,evolution=curves)
    e=_engine(p); e.set_transport(120,0,0,.25,.4); e.note_on("n","TUNE",60,100,17); e.process_block(128)
    v=e.voices[0]; a=e._macros(v,p)
    e.set_transport(120,4,1,.75,.8); b=e._macros(v,p)
    assert b[0]>a[0] and b[6]>a[6] and b[7]>a[7]
    note_logs=[x for x in e.snapshot_state()["event_log"] if x["kind"]=="note_on"]
    assert [(x["note_id"],x["sample"]) for x in note_logs]==[("n",17)]

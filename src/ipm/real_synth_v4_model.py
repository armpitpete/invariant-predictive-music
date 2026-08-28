"""RealSynthEngine v4/v4R1 stateful technical core.

Frozen architecture parent: a53980fb6b9358aee985cf4bdccd61d63bb36365.
v4R1 design freeze: 9189116cdf34937f1212d052378b36f5d4bd503f.
The same block state machine is used by interactive calls and OfflineHostV4.
No audition policy or A5/composition feedback is present here.
"""
from __future__ import annotations

import copy, json, math, wave
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal, Sequence
import numpy as np

ENGINE_VERSION = "4R1"
DESIGN_COMMIT = "a53980fb6b9358aee985cf4bdccd61d63bb36365"
V4R1_DESIGN_FREEZE_COMMIT = "9189116cdf34937f1212d052378b36f5d4bd503f"
DEFAULT_SAMPLE_RATE = 44_100
SUPPORTED_BLOCK_SIZES = (64, 128, 256, 512)
MACRO_NAMES = ("BRIGHTNESS","BODY","MOTION","ATTACK","CHARACTER","DRIVE","WIDTH","SPACE")
MACRO_APPLICATION_POLICIES = {"continuous","new_notes_only","event_boundary"}
DEFAULT_MACRO_APPLICATION = ("continuous","continuous","continuous","event_boundary","continuous","continuous","continuous","continuous")
FM_ALGORITHMS = ("4>3>2>1","(4+3+2)>1","(4>3)+(2>1)","(4>3>1)+(2>1)","(4>2>1)+(3>1)","4>(3+2)>1","(4>1)+(3>1)+(2>1)","4+3+2+1")
WAVEFORMS = {"sine","triangle","saw","square","pulse","noise"}
FILTER_MODES = {"lowpass","highpass","bandpass","notch"}
VOICE_MODES = {"poly","mono_retrigger","mono_legato"}
_MASK64=(1<<64)-1


def _clip(x: float, lo: float, hi: float) -> float: return min(hi,max(lo,float(x)))
def _mix64(x: int) -> int:
    x=(x+0x9E3779B97F4A7C15)&_MASK64; x=((x^(x>>30))*0xBF58476D1CE4E5B9)&_MASK64
    x=((x^(x>>27))*0x94D049BB133111EB)&_MASK64; return (x^(x>>31))&_MASK64
def _stable_seed(value: Any) -> int:
    h=0xCBF29CE484222325
    for b in str(value).encode(): h=((h^b)*0x100000001B3)&_MASK64
    return _mix64(h)
def _noise(seed: int, n: int) -> float: return (((_mix64(seed^n)>>11)/float(1<<53))*2.0)-1.0
def _freq(pitch: float) -> float: return 440.0*(2.0**((pitch-69.0)/12.0))


@dataclass(frozen=True, slots=True)
class EnvelopeSpecV4:
    attack: float=.01; decay: float=.2; sustain: float=.75; release: float=.3
    attack_curve: float=1.; decay_curve: float=1.; release_curve: float=1.; retrigger: str="restart"
    def __post_init__(self):
        if min(self.attack,self.decay,self.release)<0 or max(self.attack,self.decay,self.release)>30: raise ValueError("envelope time")
        if not 0<=self.sustain<=1 or min(self.attack_curve,self.decay_curve,self.release_curve)<=0: raise ValueError("envelope value")
        if self.retrigger not in {"restart","legato","continue"}: raise ValueError("retrigger")


@dataclass(frozen=True, slots=True)
class EvolutionCurveV4:
    scope: str; target: str; anchors: tuple[tuple[float,float],...]
    def __post_init__(self):
        if self.scope not in {"note","phrase","piece"} or self.target not in MACRO_NAMES or not 2<=len(self.anchors)<=8: raise ValueError("evolution")
        xs=[x for x,_ in self.anchors]
        if xs!=sorted(xs) or xs[0]<0 or xs[-1]>1 or any(not -1<=y<=1 for _,y in self.anchors): raise ValueError("evolution anchors")


@dataclass(frozen=True, slots=True)
class SynthPatchV4:
    name: str; version: int=4; polyphony: int=8; voice_mode: str="poly"
    portamento_seconds: float=0.; portamento_mode: str="legato_only"
    va: tuple[dict[str,Any],...]=field(default_factory=lambda:({"waveform":"saw","gain":.7,"octave":0,"semitone":0,"cents":0.,"phase":0.,"pulse_width":.5,"key_tracking":1.},))
    fm: dict[str,Any]=field(default_factory=lambda:{"enabled":False,"algorithm":"4>3>2>1","gain":.6,"operators":[{"mode":"ratio","ratio":1.,"fixed_hz":440.,"coarse":0,"fine_cents":0.,"level":1.,"velocity_sensitivity":0.,"key_tracking":1.,"envelope":"amp","feedback":0.,"index":1.} for _ in range(4)]})
    modal: dict[str,Any]=field(default_factory=lambda:{"enabled":False,"send":.6,"return_gain":.8,"modes":[{"ratio":1.,"fixed_hz":None,"gain":1.,"decay":.5,"detune_cents":0.,"velocity_sensitivity":0.,"brightness_sensitivity":0.,"excitation_sensitivity":1.}]})
    exciter: dict[str,Any]=field(default_factory=lambda:{"enabled":False,"kind":"white_noise","level":0.,"duration":.02,"smoothing":1})
    amp_env: EnvelopeSpecV4=field(default_factory=EnvelopeSpecV4)
    env1: EnvelopeSpecV4=field(default_factory=lambda:EnvelopeSpecV4(sustain=0.))
    env2: EnvelopeSpecV4=field(default_factory=lambda:EnvelopeSpecV4(sustain=0.))
    lfos: tuple[dict[str,Any],dict[str,Any]]=field(default_factory=lambda:({"waveform":"sine","rate_hz":.25,"sync_beats":None,"modifier":"straight","phase":0.,"bipolar":True,"scope":"voice"},{"waveform":"triangle","rate_hz":.11,"sync_beats":None,"modifier":"straight","phase":.25,"bipolar":True,"scope":"voice"}))
    filter: dict[str,Any]=field(default_factory=lambda:{"mode":"lowpass","cutoff_hz":5000.,"resonance_q":.8,"key_tracking":.25,"drive":1.})
    routes: tuple[dict[str,Any],...]=(); macro_defaults: tuple[float,...]=(0.5,)*8
    note_evolution_seconds: float=1.0
    macro_application: tuple[str,...]=DEFAULT_MACRO_APPLICATION
    evolution: tuple[EvolutionCurveV4,...]=(); base_pan: float=0.; base_width: float=.25
    chorus_send: float=0.; delay_send: float=0.; reverb_send: float=0.
    def __post_init__(self):
        if not self.name or self.version!=4 or not 1<=self.polyphony<=32 or self.voice_mode not in VOICE_MODES: raise ValueError("patch identity/voice")
        if not 0<=self.portamento_seconds<=2 or self.portamento_mode not in {"always","legato_only"}: raise ValueError("portamento")
        if not 0<=len(self.va)<=3 or len(self.routes)>32 or len(self.macro_defaults)!=8 or any(not 0<=x<=1 for x in self.macro_defaults): raise ValueError("patch structure")
        if not .05<=float(self.note_evolution_seconds)<=30.: raise ValueError("note evolution seconds")
        if len(self.macro_application)!=8 or any(x not in MACRO_APPLICATION_POLICIES for x in self.macro_application): raise ValueError("macro application")
        if self.macro_application[3]!="event_boundary" or any(x=="event_boundary" for i,x in enumerate(self.macro_application) if i!=3): raise ValueError("macro application class")
        if any(r.get("source")=="macro4" for r in self.routes): raise ValueError("ATTACK is event-boundary only")
        if any(o.get("waveform") not in WAVEFORMS for o in self.va): raise ValueError("waveform")
        if self.fm.get("algorithm") not in FM_ALGORITHMS or len(self.fm.get("operators",[]))!=4: raise ValueError("fm")
        modes=self.modal.get("modes",[])
        if self.modal.get("enabled") and not 1<=len(modes)<=16: raise ValueError("modal")
        if self.modal.get("enabled") and not self.va and not self.fm.get("enabled") and not self.exciter.get("enabled"): raise ValueError("modal requires excitation")
        if not self.va and not self.fm.get("enabled") and not self.modal.get("enabled") and not self.exciter.get("enabled"): raise ValueError("no source")
        if self.filter.get("mode") not in FILTER_MODES: raise ValueError("filter")
        if any(not 0<=x<=1 for x in (self.chorus_send,self.delay_send,self.reverb_send)): raise ValueError("send")


@dataclass(frozen=True, slots=True)
class PatchBankV4:
    patches: dict[str,SynthPatchV4]; lane_map: dict[str,str]; version: int=4
    chorus: dict[str,float]=field(default_factory=lambda:{"rate":.25,"depth":.003,"base_delay":.012,"feedback":.05,"wet":0.})
    delay: dict[str,float]=field(default_factory=lambda:{"left":.25,"right":.375,"feedback":.25,"cross":.1,"damping":.25,"wet":0.})
    reverb: dict[str,float]=field(default_factory=lambda:{"decay":.9,"damping":.45,"predelay":.015,"width":.8,"wet":0.})
    def __post_init__(self):
        if self.version!=4 or not self.patches or any(name not in self.patches for name in self.lane_map.values()): raise ValueError("bank")
    def patch_for_lane(self,lane:str)->SynthPatchV4:
        if lane not in self.lane_map: raise ValueError(f"unmapped lane {lane}")
        return self.patches[self.lane_map[lane]]


def patch_to_dict(p:SynthPatchV4)->dict[str,Any]: return asdict(p)
def patch_from_dict(d:dict[str,Any])->SynthPatchV4:
    d=copy.deepcopy(d)
    for key in ("amp_env","env1","env2"): d[key]=EnvelopeSpecV4(**d.get(key,{}))
    d["evolution"]=tuple(EvolutionCurveV4(x["scope"],x["target"],tuple(tuple(a) for a in x["anchors"])) for x in d.get("evolution",[]))
    for key in ("va","lfos","routes","macro_defaults","macro_application"):
        if key in d: d[key]=tuple(d[key])
    return SynthPatchV4(**d)
def bank_to_dict(b:PatchBankV4)->dict[str,Any]: return {"version":b.version,"patches":{k:patch_to_dict(v) for k,v in b.patches.items()},"lane_map":dict(b.lane_map),"chorus":dict(b.chorus),"delay":dict(b.delay),"reverb":dict(b.reverb)}
def bank_from_dict(d:dict[str,Any])->PatchBankV4: return PatchBankV4({k:patch_from_dict(v) for k,v in d["patches"].items()},dict(d["lane_map"]),int(d.get("version",4)),dict(d.get("chorus",{})),dict(d.get("delay",{})),dict(d.get("reverb",{})))
def save_patch_bank(b:PatchBankV4,path:str|Path)->Path:
    p=Path(path); p.write_text(json.dumps(bank_to_dict(b),sort_keys=True,indent=2)+"\n"); return p
def load_patch_bank(path:str|Path)->PatchBankV4: return bank_from_dict(json.loads(Path(path).read_text()))


def migrate_v3_patch(v3:dict[str,Any])->SynthPatchV4:
    sm={"velocity":"velocity","keytrack":"keytrack","amp_env":"amp_env","filter_env":"env1","lfo1":"lfo1","lfo2":"lfo2"}
    dm={"pitch":"va_pitch","cutoff":"filter_cutoff","amplitude":"vca","pan":"pan","osc_mix":"va_gain"}
    routes=tuple({"source":sm[r["source"]],"destination":dm[r["destination"]],"amount":float(r.get("amount",0.)),"unipolar":False} for r in v3.get("modulation",[]) if r.get("source") in sm and r.get("destination") in dm)
    va=tuple({"waveform":o.get("waveform","saw"),"gain":float(o.get("gain",.7)),"octave":int(o.get("octave",0)),"semitone":int(o.get("semitone",0)),"cents":float(o.get("cents",0.)),"phase":float(o.get("phase",0.)),"pulse_width":float(o.get("pulse_width",.5)),"key_tracking":1.} for o in v3.get("oscillators",[])) or SynthPatchV4("x").va
    def env(key,default):
        x=v3.get(key,{}); return EnvelopeSpecV4(float(x.get("attack",default.attack)),float(x.get("decay",default.decay)),float(x.get("sustain",default.sustain)),float(x.get("release",default.release)))
    f=v3.get("filter",{}); sends=v3.get("sends",{})
    l=[]
    for i,key in enumerate(("lfo1","lfo2")):
        x=v3.get(key,{}); l.append({"waveform":x.get("waveform","sine" if i==0 else "triangle"),"rate_hz":float(x.get("rate_hz",.25 if i==0 else .11)),"sync_beats":None,"modifier":"straight","phase":float(x.get("phase",0.)),"bipolar":bool(x.get("bipolar",True)),"scope":"voice"})
    return SynthPatchV4(name=str(v3["name"]),polyphony=max(1,min(32,int(v3.get("unison_voices",1))*4)),va=va,amp_env=env("amp_env",EnvelopeSpecV4()),env1=env("filter_env",EnvelopeSpecV4(sustain=.25)),lfos=tuple(l),filter={"mode":f.get("mode","lowpass"),"cutoff_hz":float(f.get("cutoff_hz",4000.)),"resonance_q":float(f.get("resonance_q",.8)),"key_tracking":float(f.get("key_tracking",.35)),"drive":float(f.get("drive",1.))},routes=routes,base_pan=float(v3.get("base_pan",0.)),base_width=float(v3.get("stereo_width",.5)),chorus_send=float(sends.get("chorus",0.)),delay_send=float(sends.get("delay",0.)),reverb_send=float(sends.get("reverb",0.)))

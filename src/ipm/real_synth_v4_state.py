from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Any
import numpy as np
from .real_synth_v4_model import EnvelopeSpecV4, SynthPatchV4, PatchBankV4, _clip

class _Env:
    def __init__(self,s:EnvelopeSpecV4,sr:int): self.s=s; self.sr=sr; self.stage="idle"; self.level=0.; self.n=0; self.start=0.
    def trigger(self,legato=False):
        if legato and self.s.retrigger in {"legato","continue"} and self.stage!="idle": return
        self.stage="attack"; self.n=0; self.start=0. if self.s.retrigger=="restart" else self.level
    def release(self):
        if self.stage!="idle": self.stage="release"; self.n=0; self.start=self.level
    def step(self)->float:
        s=self.s
        if self.stage=="idle": self.level=0.; return 0.
        if self.stage=="attack":
            total=max(1,round(s.attack*self.sr)); x=1. if s.attack==0 else min(1.,(self.n+1)/total); self.level=self.start+(1-self.start)*(x**s.attack_curve); self.n+=1
            if s.attack==0 or self.n>=total: self.level=1.; self.stage="decay"; self.n=0
        elif self.stage=="decay":
            total=max(1,round(s.decay*self.sr)); x=1. if s.decay==0 else min(1.,(self.n+1)/total); self.level=1+(s.sustain-1)*(x**s.decay_curve); self.n+=1
            if s.decay==0 or self.n>=total: self.level=s.sustain; self.stage="sustain"; self.n=0
        elif self.stage=="sustain": self.level=s.sustain
        else:
            total=max(1,round(s.release*self.sr)); x=1. if s.release==0 else min(1.,(self.n+1)/total); self.level=self.start*(1-x**s.release_curve); self.n+=1
            if s.release==0 or self.n>=total or self.level<=1e-12: self.level=0.; self.stage="idle"; self.n=0
        return self.level


@dataclass(slots=True)
class _Voice:
    index:int; sr:int; note_id:Any=None; lane:str=""; pitch:int=60; velocity:int=0; held:bool=False; age:int=0; patch:SynthPatchV4|None=None
    amp:_Env|None=None; env1:_Env|None=None; env2:_Env|None=None; current_pitch:float=60.; target_pitch:float=60.; glide_left:int=0; glide_step:float=0.
    va_phase:list[float]=field(default_factory=list); fm_phase:list[float]=field(default_factory=lambda:[0.]*4); fm_prev:list[float]=field(default_factory=lambda:[0.]*4)
    modal_phase:list[float]=field(default_factory=list); modal_amp:list[float]=field(default_factory=list); fi1:float=0.; fi2:float=0.; lfo_phase:list[float]=field(default_factory=lambda:[0.,0.])
    macro_start:tuple[float,...]=field(default_factory=lambda:(.5,)*8)
    seed:int=0; noise_n:int=0; last_l:float=0.; last_r:float=0.; tail_l:float=0.; tail_r:float=0.; tail_left:int=0; tail_total:int=0
    @property
    def idle(self): return self.patch is None or (not self.held and self.amp is not None and self.amp.stage=="idle")
    @property
    def allocation_level(self): return _clip((0. if self.amp is None else self.amp.level)*(.25+.75*_clip(self.velocity/127.,0,1)),0,1)


@dataclass(slots=True)
class _Ramp:
    current:float=.5; target:float=.5; left:int=0; step:float=0.
    def set(self,target:float,n:int): self.target=_clip(target,0,1); self.left=n; self.step=(self.target-self.current)/n if n else 0.; self.current=self.target if not n else self.current
    def advance(self):
        if self.left: self.current+=self.step; self.left-=1; self.current=self.target if not self.left else self.current
        return self.current


class _FX:
    def __init__(self,sr:int,bank:PatchBankV4):
        self.sr=sr; self.bank=bank; maxs=max(.1,bank.delay.get("left",.25),bank.delay.get("right",.375),bank.reverb.get("decay",.9)); self.n=math.ceil(maxs*sr)+8
        self.cl=np.zeros(self.n); self.cr=np.zeros(self.n); self.dl=np.zeros(self.n); self.dr=np.zeros(self.n); self.rl=np.zeros(self.n); self.rr=np.zeros(self.n); self.pos=0; self.phase=0.; self.rlp=[0.,0.]
    def read(self,a,d):
        x=(self.pos-d)%self.n; i=int(x); f=x-i; return float(a[i]*(1-f)+a[(i+1)%self.n]*f)
    def step(self,l,r,sends):
        c,d,v=self.bank.chorus,self.bank.delay,self.bank.reverb; cs,ds,rs=sends
        cd=(c.get("base_delay",.012)+c.get("depth",.003)*math.sin(2*math.pi*self.phase))*self.sr; cw_l=self.read(self.cr,cd); cw_r=self.read(self.cl,cd)
        self.cl[self.pos]=l*cs+c.get("feedback",.05)*cw_l; self.cr[self.pos]=r*cs+c.get("feedback",.05)*cw_r; self.phase=(self.phase+c.get("rate",.25)/self.sr)%1
        dl=max(1,round(d.get("left",.25)*self.sr)); dr=max(1,round(d.get("right",.375)*self.sr)); dw_l=self.read(self.dl,dl); dw_r=self.read(self.dr,dr)
        self.dl[self.pos]=l*ds+d.get("feedback",.25)*dw_l+d.get("cross",.1)*dw_r; self.dr[self.pos]=r*ds+d.get("feedback",.25)*dw_r+d.get("cross",.1)*dw_l
        pd=max(1,round(v.get("predelay",.015)*self.sr)); ql=self.read(self.rl,pd); qr=self.read(self.rr,pd); damp=v.get("damping",.45); self.rlp[0]+=(1-damp)*(ql-self.rlp[0]); self.rlp[1]+=(1-damp)*(qr-self.rlp[1])
        # Feedback returns once per predelay loop, not once per sample. Map the
        # declared decay time onto that loop and compensate the fixed 0.92
        # maximum eigenvalue of the stereo feedback matrix. The resulting loop
        # eigenvalue remains <1, so the tank is stable while decay has the
        # intended time-scale instead of collapsing in a few short loops.
        decay=max(1e-3,float(v.get("decay",.9))); matrix_gain=.92; loop_gain=math.exp(-(pd/self.sr)/decay); g=loop_gain/matrix_gain
        self.rl[self.pos]=l*rs+g*(.73*self.rlp[0]+.19*self.rlp[1]); self.rr[self.pos]=r*rs+g*(.73*self.rlp[1]+.19*self.rlp[0]); self.pos=(self.pos+1)%self.n
        # The compact two-line tank has a lower return density than a full
        # reverb network. Normalize only its output; decay, damping, send depth
        # and the stable internal feedback loop remain unchanged.
        rg=4.0
        return l+c.get("wet",0)*cw_l+d.get("wet",0)*dw_l+rg*v.get("wet",0)*self.rlp[0], r+c.get("wet",0)*cw_r+d.get("wet",0)*dw_r+rg*v.get("wet",0)*self.rlp[1]

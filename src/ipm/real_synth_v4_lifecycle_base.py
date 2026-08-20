from __future__ import annotations
import math
import numpy as np
from .real_synth_v4_model import *
from .real_synth_v4_model import _clip
from .real_synth_v4_state import _Voice, _Ramp, _FX

class _LifecycleBaseMixin:
    def __init__(self,*,sample_rate:int=DEFAULT_SAMPLE_RATE,block_size:int=128): self.bank=None; self.reset(sample_rate,block_size)
    def reset(self,sample_rate:int|None=None,block_size:int|None=None):
        if sample_rate is not None: self.sr=int(sample_rate)
        if block_size is not None:
            if block_size not in SUPPORTED_BLOCK_SIZES: raise ValueError("block size")
            self.block_size=int(block_size)
        self.sample=0; self.voices=[]; self.events=[]; self.seq=0; self.transport={"tempo_bpm":120.,"phrase_position":0.,"piece_position":0.}; self.ramps=[_Ramp() for _ in range(8)]; self.event_log=[]; self.allocation_log=[]; self.dc=[0.,0.,0.,0.]
        self.fx=_FX(self.sr,self.bank) if self.bank else None
    def load_patch_bank(self,bank:PatchBankV4): self.bank=bank; self.fx=_FX(self.sr,bank)
    def _q(self,offset,kind,*payload):
        if not 0<=offset<=self.block_size: raise ValueError("offset")
        self.events.append((int(offset),self.seq,kind,payload)); self.seq+=1
    def note_on(self,note_id,lane,pitch,velocity,sample_offset=0): self._q(sample_offset,"on",note_id,lane,int(pitch),int(velocity))
    def note_off(self,note_id,sample_offset=0): self._q(sample_offset,"off",note_id)
    def control_change(self,control_id,value,sample_offset=0):
        if control_id not in MACRO_NAMES: raise ValueError("macro")
        self._q(sample_offset,"control",control_id,float(value))
    def set_transport(self,tempo_bpm,beat_position=0.,bar_position=0.,phrase_position=0.,piece_position=0.): self.transport={"tempo_bpm":float(tempo_bpm),"beat_position":float(beat_position),"bar_position":float(bar_position),"phrase_position":_clip(phrase_position,0,1),"piece_position":_clip(piece_position,0,1)}
    def all_notes_off(self,immediate=False):
        for v in self.voices:
            if v.patch: v.held=False; [setattr(e,"stage","idle") if immediate else e.release() for e in (v.amp,v.env1,v.env2) if e]
        self.event_log.append({"sample":self.sample,"kind":"all_notes_off","immediate":immediate})
    def _pool(self,p):
        n=1 if p.voice_mode!="poly" else p.polyphony
        while len(self.voices)<n: self.voices.append(_Voice(len(self.voices),self.sr))
        return self.voices[:n]
    def _choose(self,p):
        pool=self._pool(p)
        if p.voice_mode!="poly": return pool[0]
        idle=[v for v in pool if v.idle]
        if idle: return min(idle,key=lambda v:v.index)
        released=[v for v in pool if not v.held]; use=released or pool
        return min(use,key=lambda v:(v.allocation_level,-v.age,v.index))

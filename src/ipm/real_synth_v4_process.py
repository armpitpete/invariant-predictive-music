from __future__ import annotations
import math
import numpy as np
from .real_synth_v4_model import ENGINE_VERSION, DESIGN_COMMIT, MACRO_NAMES, _clip

class _ProcessMixin:
    def _master(self,l,r):
        xl,xr,yl,yr=self.dc; nl=l-xl+.995*yl; nr=r-xr+.995*yr; self.dc=[l,r,nl,nr]; return _clip(math.tanh(nl*1.05)*.9,-.98,.98),_clip(math.tanh(nr*1.05)*.9,-.98,.98)
    def process_block(self,frame_count:int,*,return_pre_master=False):
        if not self.bank or not self.fx or not 1<=frame_count<=self.block_size: raise ValueError("engine not ready/frame count")
        by={}; rem=[]
        for off,seq,kind,payload in self.events:
            (by.setdefault(off,[]).append((seq,kind,payload)) if off<frame_count else rem.append((off-frame_count,seq,kind,payload)))
        self.events=rem; out=np.zeros((2,frame_count)); pre=np.zeros((2,frame_count))
        for i in range(frame_count):
            for _,kind,payload in sorted(by.get(i,[])): self._event(kind,payload)
            [r.advance() for r in self.ramps]; l=r=0.; sends=np.zeros(3); active=0
            for v in self.voices:
                if v.patch is None and not v.tail_left: continue
                vl,vr,s=self._voice_sample(v); l+=vl; r+=vr; sends+=s; active+=1 if abs(vl)+abs(vr)>0 else 0
            if active: sends/=active
            pre[:,i]=(l,r); wl,wr=self.fx.step(l,r,tuple(sends)); out[:,i]=self._master(wl,wr); self.sample+=1
        return (out,pre) if return_pre_master else out
    def snapshot_state(self):
        return {"engine_version":ENGINE_VERSION,"design_commit":DESIGN_COMMIT,"absolute_sample":self.sample,"sample_rate":self.sr,"block_size":self.block_size,"macros":[{"name":n,"current":r.current,"target":r.target,"remaining":r.left} for n,r in zip(MACRO_NAMES,self.ramps)],"voices":[{"index":v.index,"note_id":v.note_id,"pitch":v.pitch,"current_pitch":v.current_pitch,"target_pitch":v.target_pitch,"held":v.held,"idle":v.idle,"age_samples":v.age,"allocation_level":v.allocation_level,"amp_stage":None if v.amp is None else v.amp.stage,"amp_level":None if v.amp is None else v.amp.level,"steal_tail_remaining":v.tail_left,"patch_name":None if v.patch is None else v.patch.name} for v in self.voices],"event_log":list(self.event_log),"allocation_log":list(self.allocation_log)}



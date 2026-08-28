from __future__ import annotations
from dataclasses import replace
import numpy as np
from .real_synth_v4_model import *
from .real_synth_v4_model import _clip, _stable_seed
from .real_synth_v4_state import _Env

class _LifecycleStartMixin:
    def _macro_values_at_start(self,p):
        values=[_clip(d+r.current-.5,0,1) for d,r in zip(p.macro_defaults,self.ramps)]
        pos={"note":0.,"phrase":self.transport["phrase_position"],"piece":self.transport["piece_position"]}
        for c in p.evolution:
            i=MACRO_NAMES.index(c.target)
            if p.macro_application[i]=="continuous": continue
            xs=[a[0] for a in c.anchors]; ys=[a[1] for a in c.anchors]
            values[i]=_clip(values[i]+float(np.interp(pos[c.scope],xs,ys)),0,1)
        return tuple(values)
    def _attack_spec(self,p,macro_start):
        attack_value=macro_start[MACRO_NAMES.index("ATTACK")]
        attack_scale=2.0**(2.0*(.5-attack_value))
        return replace(p.amp_env,attack=min(30.,p.amp_env.attack*attack_scale))
    def _start(self,v,note_id,lane,pitch,velocity,p):
        active=v.patch is not None and v.held and not v.idle; legato=p.voice_mode=="mono_legato" and active; stolen=p.voice_mode=="poly" and not v.idle
        old_id,old_level,old_pitch=v.note_id,v.allocation_level,v.current_pitch
        if stolen: v.tail_l,v.tail_r=v.last_l,v.last_r; v.tail_total=v.tail_left=max(1,round(.005*self.sr))
        v.note_id,v.lane,v.pitch,v.velocity,v.held,v.age,v.patch=note_id,lane,pitch,max(0,min(127,velocity)),True,0,p
        v.macro_start=self._macro_values_at_start(p)
        if not legato or v.amp is None: v.amp,v.env1,v.env2=_Env(self._attack_spec(p,v.macro_start),self.sr),_Env(p.env1,self.sr),_Env(p.env2,self.sr)
        v.amp.trigger(legato); v.env1.trigger(legato); v.env2.trigger(legato); v.va_phase=[float(o.get("phase",0)) for o in p.va]; v.fm_phase=[0.]*4; v.fm_prev=[0.]*4; v.modal_phase=[0.]*len(p.modal.get("modes",[])); v.fi1=v.fi2=0.; v.seed=_stable_seed(note_id)^(pitch<<8)^(v.index<<16); v.noise_n=0
        exc=max(1e-6,float(p.exciter.get("level",0))) if p.exciter.get("enabled") else max(1e-6,sum(float(o.get("gain",0)) for o in p.va) or float(p.fm.get("gain",0)) or 1.)
        vel=v.velocity/127.; v.modal_amp=[float(m.get("gain",1))*(1+float(m.get("velocity_sensitivity",0))*(vel-.5))*float(m.get("excitation_sensitivity",1))*exc for m in p.modal.get("modes",[])]
        glide=p.voice_mode!="poly" and active and p.portamento_seconds>0
        v.current_pitch=old_pitch if glide else float(pitch); v.target_pitch=float(pitch); v.glide_left=max(1,round(p.portamento_seconds*self.sr)) if glide else 0; v.glide_step=(v.target_pitch-v.current_pitch)/v.glide_left if v.glide_left else 0.
        self.allocation_log.append({"sample":self.sample,"voice_index":v.index,"note_id":note_id,"stolen_note_id":old_id if stolen else None,"stolen_allocation_level":old_level if stolen else None,"steal_tail_samples":v.tail_total if stolen else 0})
    def _event(self,kind,payload):
        if not self.bank: raise RuntimeError("bank")
        if kind=="on": note,lane,pitch,vel=payload; v=self._choose(self.bank.patch_for_lane(lane)); self._start(v,note,lane,pitch,vel,self.bank.patch_for_lane(lane)); self.event_log.append({"sample":self.sample,"kind":"note_on","note_id":note,"voice":v.index})
        elif kind=="off":
            for v in self.voices:
                if v.note_id==payload[0] and v.held: v.held=False; [e.release() for e in (v.amp,v.env1,v.env2) if e]; self.event_log.append({"sample":self.sample,"kind":"note_off","note_id":payload[0],"voice":v.index}); break
        else:
            name,value=payload; n=max(1,round(.005*self.sr)); self.ramps[MACRO_NAMES.index(name)].set(value,n); self.event_log.append({"sample":self.sample,"kind":"control","control_id":name,"value":_clip(value,0,1),"ramp_samples":n})

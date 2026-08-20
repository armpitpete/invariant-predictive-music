from __future__ import annotations
from .real_synth_v4_model import *
from .real_synth_v4_model import _clip, _stable_seed
from .real_synth_v4_state import _Env

class _LifecycleStartMixin:
    def _start(self,v,note_id,lane,pitch,velocity,p):
        active=v.patch is not None and v.held and not v.idle; legato=p.voice_mode=="mono_legato" and active; stolen=p.voice_mode=="poly" and not v.idle
        old_id,old_level,old_pitch=v.note_id,v.allocation_level,v.current_pitch
        if stolen: v.tail_l,v.tail_r=v.last_l,v.last_r; v.tail_total=v.tail_left=max(1,round(.005*self.sr))
        v.note_id,v.lane,v.pitch,v.velocity,v.held,v.age,v.patch=note_id,lane,pitch,max(0,min(127,velocity)),True,0,p
        if not legato or v.amp is None: v.amp,v.env1,v.env2=_Env(p.amp_env,self.sr),_Env(p.env1,self.sr),_Env(p.env2,self.sr)
        v.amp.trigger(legato); v.env1.trigger(legato); v.env2.trigger(legato); v.va_phase=[float(o.get("phase",0)) for o in p.va]; v.fm_phase=[0.]*4; v.fm_prev=[0.]*4; v.modal_phase=[0.]*len(p.modal.get("modes",[])); v.fi1=v.fi2=0.; v.seed=_stable_seed(note_id)^(pitch<<8)^(v.index<<16); v.noise_n=0
        exc=max(1e-6,float(p.exciter.get("level",0))) if p.exciter.get("enabled") else max(1e-6,sum(float(o.get("gain",0)) for o in p.va) or float(p.fm.get("gain",0)) or 1.)
        vel=v.velocity/127.; bright=_clip(p.macro_defaults[0]+self.ramps[0].current-.5,0,1); v.modal_amp=[float(m.get("gain",1))*(1+float(m.get("velocity_sensitivity",0))*(vel-.5))*(1+float(m.get("brightness_sensitivity",0))*(bright-.5))*float(m.get("excitation_sensitivity",1))*exc for m in p.modal.get("modes",[])]
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

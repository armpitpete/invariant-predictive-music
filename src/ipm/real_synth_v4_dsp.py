from __future__ import annotations
import math
import numpy as np
from .real_synth_v4_model import _clip, _freq, _noise, MACRO_NAMES

class _VoiceDSPMixin:
    def _note_evolution_position(self,v,p):
        return _clip((v.age/self.sr)/float(p.note_evolution_seconds),0,1)
    def _macros(self,v,p):
        live=[_clip(d+r.current-.5,0,1) for d,r in zip(p.macro_defaults,self.ramps)]
        values=[live[i] if p.macro_application[i]=="continuous" else v.macro_start[i] for i in range(len(MACRO_NAMES))]
        pos={"note":self._note_evolution_position(v,p),"phrase":self.transport["phrase_position"],"piece":self.transport["piece_position"]}
        for c in p.evolution:
            i=MACRO_NAMES.index(c.target)
            if p.macro_application[i]!="continuous": continue
            xs=[a[0] for a in c.anchors]; ys=[a[1] for a in c.anchors]; values[i]=_clip(values[i]+float(np.interp(pos[c.scope],xs,ys)),0,1)
        return values
    def _lfo(self,v,spec,i):
        rate=float(spec.get("rate_hz",.25)); sync=spec.get("sync_beats")
        if sync: rate=self.transport["tempo_bpm"]/60/float(sync)*({"dotted":2/3,"triplet":1.5}.get(spec.get("modifier"),1.))
        phase=(float(spec.get("phase",0))+self.sample*rate/self.sr)%1 if spec.get("scope","voice")=="global" else v.lfo_phase[i]; v.lfo_phase[i]=(v.lfo_phase[i]+rate/self.sr)%1
        wf=spec.get("waveform","sine"); x=math.sin(2*math.pi*phase) if wf=="sine" else (2/math.pi)*math.asin(math.sin(2*math.pi*phase)) if wf=="triangle" else 2*phase-1 if wf=="saw" else (1 if phase<.5 else -1) if wf=="square" else _noise(v.seed^(i<<20),int(v.age*rate/self.sr))
        return x if spec.get("bipolar",True) else .5*(x+1)
    def _mods(self,v,p,amp,e1,e2,l1,l2,mac):
        out={k:0. for k in ("va_pitch","va_gain","pulse_width","fm_index","fm_level","modal_gain","modal_decay","filter_cutoff","filter_resonance","drive","vca","pan","width","chorus_send","delay_send","reverb_send")}
        src={"velocity":v.velocity/127.,"keytrack":_clip((v.pitch-60)/24,-1,1),"note_age":_clip(v.age/self.sr/30,0,1),"amp_env":amp,"env1":e1,"env2":e2,"lfo1":l1,"lfo2":l2,"note_position":self._note_evolution_position(v,p),"phrase_position":self.transport["phrase_position"],"piece_position":self.transport["piece_position"]}; src.update({f"macro{i+1}":x for i,x in enumerate(mac)})
        for r in p.routes:
            if r.get("source") not in src or r.get("destination") not in out: raise ValueError("mod route")
            x=src[r["source"]]; x=.5*(x+1) if r.get("unipolar") and x<0 else x; out[r["destination"]]+=x*float(r.get("amount",0))
        # v4R1 semantic macro authority. These paths alter synthesis state only;
        # they cannot add, remove, repitch or reschedule written note events.
        # BRIGHTNESS: centred family-independent cutoff authority, while
        # preserving any patch-declared brightness routes/sensitivities.
        out["filter_cutoff"]+=30.0*(mac[0]-.5)
        # BODY: high values lower the filter in addition to the explicit
        # fundamental reinforcement applied after source generation.
        out["filter_cutoff"]+=18.0*(.5-mac[1])
        # MOTION: a zero-mean faster deterministic movement path whose depth is
        # strongly macro-dependent; low values approach stillness.
        motion_wave=math.sin(2*math.pi*3.7*v.age/self.sr)
        motion_depth=20.0*(mac[2]**2)
        out["filter_cutoff"]+=motion_depth*motion_wave
        out["va_pitch"]+=.06*(mac[2]**2)*l2
        return out
    def _va(self,v,p,m,mac):
        z=0.; character=mac[4]
        for i,o in enumerate(p.va):
            pitch=60+(v.current_pitch-60)*float(o.get("key_tracking",1))+12*int(o.get("octave",0))+int(o.get("semitone",0))+float(o.get("cents",0))/100+m["va_pitch"]; f=min(self.sr*.45,_freq(pitch)); dt=f/self.sr; ph=v.va_phase[i]%1; wf=o.get("waveform","saw"); pw=_clip(float(o.get("pulse_width",.5))+.1*m["pulse_width"],.05,.95)
            if wf=="sine": raw=math.sin(2*math.pi*ph)
            elif wf=="triangle": raw=(2/math.pi)*math.asin(math.sin(2*math.pi*ph))
            elif wf=="noise": raw=_noise(v.seed^i,v.noise_n)
            elif wf=="saw": raw=2*ph-1
            else: raw=1. if ph<(pw if wf=="pulse" else .5) else -1.
            simple=math.sin(2*math.pi*ph); complex_mix=.20+.80*character; x=(1-complex_mix)*simple+complex_mix*raw
            v.va_phase[i]=(ph+dt)%1; z+=x*float(o.get("gain",.7))*max(0,1+.1*m["va_gain"])
        return z
    def _fm(self,v,p,env,m,mac):
        if not p.fm.get("enabled"): return 0.
        ops=p.fm["operators"]; scale=max(.05,(.40+1.45*mac[4])*(1+.1*m["fm_index"])); vel=v.velocity/127.
        def op(i,mod=0.):
            o=ops[i]; base=float(o.get("fixed_hz",440)) if o.get("mode","ratio")=="fixed_hz" else _freq(60+(v.current_pitch-60)*float(o.get("key_tracking",1)))*float(o.get("ratio",1)); f=min(self.sr*.45,base*2**((float(o.get("coarse",0))+float(o.get("fine_cents",0))/100)/12)); ph=v.fm_phase[i]; x=math.sin(2*math.pi*ph+mod+float(o.get("feedback",0))*v.fm_prev[i]); v.fm_phase[i]=(ph+f/self.sr)%1; v.fm_prev[i]=x; e=env[{"amp":0,"env1":1,"env2":2}[o.get("envelope","amp")]]; return x*float(o.get("level",1))*e*max(0,1+float(o.get("velocity_sensitivity",0))*(vel-.5))
        a=p.fm.get("algorithm"); idx=lambda i:float(ops[i].get("index",1))*scale
        if a=="4>3>2>1": o4=op(3); o3=op(2,idx(2)*o4); o2=op(1,idx(1)*o3); z=op(0,idx(0)*o2)
        elif a=="(4+3+2)>1": z=op(0,idx(0)*(op(3)+op(2)+op(1)))
        elif a=="(4>3)+(2>1)": o3=op(2,idx(2)*op(3)); z=o3+op(0,idx(0)*op(1))
        elif a=="(4>3>1)+(2>1)": o3=op(2,idx(2)*op(3)); z=op(0,idx(0)*(o3+op(1)))
        elif a=="(4>2>1)+(3>1)": o2=op(1,idx(1)*op(3)); z=op(0,idx(0)*(o2+op(2)))
        elif a=="4>(3+2)>1": o4=op(3); z=op(0,idx(0)*(op(2,idx(2)*o4)+op(1,idx(1)*o4)))
        elif a=="(4>1)+(3>1)+(2>1)": z=op(0,idx(0)*(op(3)*idx(3)+op(2)*idx(2)+op(1)*idx(1)))
        else: z=sum(op(i) for i in range(4))
        return z*float(p.fm.get("gain",.6))*max(0,1+.1*m["fm_level"])
    def _modal(self,v,p,mac,m):
        if not p.modal.get("enabled"): return 0.
        z=0.; gs=max(0,1+.1*m["modal_gain"]); ds=max(.05,1+.1*m["modal_decay"]); modes=p.modal["modes"]; denom=max(1,len(modes)-1)
        for i,o in enumerate(modes):
            f=float(o["fixed_hz"]) if o.get("fixed_hz") is not None else _freq(v.current_pitch)*float(o.get("ratio",1)); f=min(self.sr*.45,f*2**(float(o.get("detune_cents",0))/1200))
            rank=i/denom
            brightness_weight=max(0.,1+float(o.get("brightness_sensitivity",0))*(mac[0]-.5))
            body_weight=2.0**((mac[1]-.5)*(1-2*rank)*1.6)
            character_base=.35+1.45*mac[4]; character_weight=max(.05,character_base**rank)
            z+=math.sin(2*math.pi*v.modal_phase[i])*v.modal_amp[i]*gs*(.75+.5*mac[0])*brightness_weight*body_weight*character_weight
            v.modal_phase[i]=(v.modal_phase[i]+f/self.sr)%1; v.modal_amp[i]*=math.exp(-1/(max(.001,float(o.get("decay",.5))*ds)*self.sr))
        return z*float(p.modal.get("return_gain",.8))
    def _exciter(self,v,p):
        e=p.exciter; n=round(float(e.get("duration",.02))*self.sr)
        if not e.get("enabled") or v.age>=n: return 0.
        progress=v.age/max(1,n); x=1. if e.get("kind")=="click" and v.age==0 else _noise(v.seed^0xE11CE,v.noise_n); return x*float(e.get("level",0))*(1-progress)
    def _filter(self,v,x,p,m):
        f=p.filter; cutoff=_clip(float(f.get("cutoff_hz",5000))*2**(((v.current_pitch-60)/12*float(f.get("key_tracking",.25)))+.1*m["filter_cutoff"]),20,self.sr*.45); q=_clip(float(f.get("resonance_q",.8))+.1*m["filter_resonance"],.1,20); g=math.tan(math.pi*cutoff/self.sr); k=1/q; a1=1/(1+g*(g+k)); a2=g*a1; a3=g*a2; t=x-v.fi2; b=a1*v.fi1+a2*t; low=v.fi2+a2*v.fi1+a3*t; v.fi1=2*b-v.fi1; v.fi2=2*low-v.fi2; high=x-k*b-low; mode=f.get("mode","lowpass"); return low if mode=="lowpass" else high if mode=="highpass" else b if mode=="bandpass" else high+low
    def _voice_sample(self,v):
        p=v.patch
        if p is None or not v.amp: return 0.,0.,(0.,0.,0.)
        if v.glide_left: v.current_pitch+=v.glide_step; v.glide_left-=1; v.current_pitch=v.target_pitch if not v.glide_left else v.current_pitch
        amp,e1,e2=v.amp.step(),v.env1.step(),v.env2.step()
        if v.idle and not v.tail_left: v.patch=None; return 0.,0.,(0.,0.,0.)
        mac=self._macros(v,p); l1,l2=self._lfo(v,p.lfos[0],0),self._lfo(v,p.lfos[1],1); m=self._mods(v,p,amp,e1,e2,l1,l2,mac)
        source=self._va(v,p,m,mac)+self._fm(v,p,(amp,e1,e2),m,mac)+self._exciter(v,p)+float(p.modal.get("send",0))*self._modal(v,p,mac,m)
        body_boost=max(0.,mac[1]-.5)
        if body_boost:
            body_phase=(v.age*_freq(v.current_pitch)/self.sr)%1.0
            source+=1.5*body_boost*math.sin(2*math.pi*body_phase)
        drive=max(.02,float(p.filter.get("drive",1))*1.175*(2.0**(5.0*(mac[5]-.5)))+.1*m["drive"])
        source=math.tanh(source*drive)
        value=self._filter(v,source,p,m)*amp*max(0,1+.1*m["vca"])*(.25+.75*v.velocity/127.); pan=_clip(p.base_pan+.25*m["pan"],-1,1); a=(pan+1)*math.pi/4; l,r=value*math.cos(a),value*math.sin(a); width=_clip(p.base_width*(.15+1.70*mac[6])+.1*m["width"],0,1.5); side=value*.45*width*math.sin(2*math.pi*((v.seed&0xffff)/65536+.31*v.age/self.sr)); l+=side; r-=side
        if v.tail_left: q=v.tail_left/max(1,v.tail_total); l+=v.tail_l*q; r+=v.tail_r*q; v.tail_left-=1
        space_send=_clip((mac[7]-.15)/.70,0,1)
        v.last_l,v.last_r=l,r; v.age+=1; v.noise_n+=1; return l,r,(_clip(p.chorus_send+.05*m["chorus_send"],0,1),_clip(p.delay_send+.05*m["delay_send"],0,1),_clip(p.reverb_send+.05*m["reverb_send"]+space_send,0,1))

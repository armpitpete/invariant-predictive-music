from __future__ import annotations
import math, wave
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Literal, Sequence
import numpy as np
from .real_synth_v4_model import *
from .real_synth_v4_engine import RealSynthEngineV4

@dataclass(frozen=True,slots=True)
class ScheduledEventV4:
    sample:int; kind:Literal["note_on","note_off","control","transport"]; payload:tuple[Any,...]
    def __post_init__(self):
        if self.sample<0: raise ValueError("sample")


class OfflineHostV4:
    def __init__(self,*,sample_rate=DEFAULT_SAMPLE_RATE,block_size=128): self.sr=sample_rate; self.block_size=block_size
    def render(self,bank:PatchBankV4,events:Sequence[ScheduledEventV4],total_frames:int,*,return_pre_master=False):
        e=RealSynthEngineV4(sample_rate=self.sr,block_size=self.block_size); e.load_patch_bank(bank); ordered=sorted(enumerate(events),key=lambda x:(x[1].sample,x[0])); cur=0; outs=[]; pres=[]
        while cur<total_frames:
            n=min(self.block_size,total_frames-cur)
            for _,ev in (x for x in ordered if cur<=x[1].sample<cur+n):
                off=ev.sample-cur
                if ev.kind=="note_on": e.note_on(*ev.payload,sample_offset=off)
                elif ev.kind=="note_off": e.note_off(*ev.payload,sample_offset=off)
                elif ev.kind=="control": e.control_change(*ev.payload,sample_offset=off)
                elif off==0: e.set_transport(*ev.payload)
                else: raise ValueError("transport events must align to an offline block boundary")
            z=e.process_block(n,return_pre_master=return_pre_master); (outs.append(z[0]),pres.append(z[1])) if return_pre_master else outs.append(z); cur+=n
        out=np.concatenate(outs,axis=1) if outs else np.zeros((2,0)); return (out,np.concatenate(pres,axis=1)) if return_pre_master else out
    @staticmethod
    def pcm16_bytes(audio):
        x=np.empty(audio.shape[1]*2,dtype="<i2"); x[0::2]=np.round(np.clip(audio[0],-1,1)*32767).astype("<i2"); x[1::2]=np.round(np.clip(audio[1],-1,1)*32767).astype("<i2"); return x.tobytes()
    def write_wav(self,audio,path):
        p=Path(path); pcm=self.pcm16_bytes(audio)
        with wave.open(str(p),"wb") as w: w.setnchannels(2); w.setsampwidth(2); w.setframerate(self.sr); w.writeframes(pcm)
        return p


def schedule_instrument_result(result:Any,*,sample_rate=DEFAULT_SAMPLE_RATE):
    spb=60/float(result.config.tempo_bpm); events=[]; k=0
    for voice in result.voices:
        for n in voice.events:
            nid=f"{voice.name}:{k}"; on=round(float(n.onset)*spb*sample_rate); off=round(float(n.onset+n.duration)*spb*sample_rate); events += [ScheduledEventV4(on,"note_on",(nid,voice.name,int(n.pitch),int(n.velocity))),ScheduledEventV4(off,"note_off",(nid,))]; k+=1
    total=math.ceil(float(result.config.bars*result.config.beats_per_bar)*spb*sample_rate)+sample_rate; return events,total


def technical_va_patch(*,polyphony=4,voice_mode="poly",portamento_seconds=0.):
    return SynthPatchV4("technical-va",polyphony=polyphony,voice_mode=voice_mode,portamento_seconds=portamento_seconds,va=({"waveform":"saw","gain":.35,"octave":0,"semitone":0,"cents":0.,"phase":0.,"pulse_width":.5,"key_tracking":1.},{"waveform":"pulse","gain":.18,"octave":0,"semitone":0,"cents":3.,"phase":0.,"pulse_width":.4,"key_tracking":1.}),amp_env=EnvelopeSpecV4(.002,.02,.65,.04),env1=EnvelopeSpecV4(.005,.03,.2,.04),filter={"mode":"lowpass","cutoff_hz":3200.,"resonance_q":.8,"key_tracking":.25,"drive":.9},routes=({"source":"macro1","destination":"filter_cutoff","amount":2.},{"source":"macro3","destination":"va_pitch","amount":.03},{"source":"macro6","destination":"drive","amount":1.},{"source":"macro7","destination":"width","amount":1.},{"source":"macro8","destination":"reverb_send","amount":1.}),evolution=(EvolutionCurveV4("note","MOTION",((0.,-.05),(1.,.05))),EvolutionCurveV4("phrase","BRIGHTNESS",((0.,-.05),(1.,.05))),EvolutionCurveV4("piece","WIDTH",((0.,-.05),(1.,.05)))))
def technical_fm_patch():
    ops=[{"mode":"ratio","ratio":r,"fixed_hz":440.,"coarse":0,"fine_cents":0.,"level":l,"velocity_sensitivity":0.,"key_tracking":1.,"envelope":e,"feedback":0.,"index":i} for r,l,e,i in ((1,.8,"amp",2),(2,.6,"env1",2.5),(3,.5,"env1",2),(5,.45,"env2",1.5))]
    return SynthPatchV4("technical-fm",va=(),fm={"enabled":True,"algorithm":"4>3>2>1","gain":.5,"operators":ops},amp_env=EnvelopeSpecV4(.001,.04,.5,.04),env1=EnvelopeSpecV4(.001,.06,.1,.04),env2=EnvelopeSpecV4(.001,.03,0,.02),filter={"mode":"bandpass","cutoff_hz":5000.,"resonance_q":1.2,"key_tracking":.25,"drive":.8},routes=({"source":"macro5","destination":"fm_index","amount":2.},))
def technical_modal_patch():
    modes=[{"ratio":r,"fixed_hz":None,"gain":g,"decay":d,"detune_cents":0.,"velocity_sensitivity":0.,"brightness_sensitivity":0.,"excitation_sensitivity":1.} for r,g,d in ((1,.7,.18),(1.47,.35,.13),(2.31,.22,.09),(3.7,.12,.06))]
    return SynthPatchV4("technical-modal",va=(),modal={"enabled":True,"send":1.,"return_gain":.6,"modes":modes},exciter={"enabled":True,"kind":"filtered_noise","level":.18,"duration":.012,"smoothing":3},amp_env=EnvelopeSpecV4(.001,.03,.45,.05),filter={"mode":"lowpass","cutoff_hz":7000.,"resonance_q":.7,"key_tracking":.25,"drive":.7},routes=({"source":"macro2","destination":"modal_gain","amount":2.},{"source":"macro5","destination":"modal_decay","amount":2.}))
def technical_bank(patch): return PatchBankV4({patch.name:patch},{"TUNE":patch.name,"BASS":patch.name,"RHYTHM":patch.name})

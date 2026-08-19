"""Embedded local UI for IPM Machine v0."""

MACHINE_HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>IPM Machine v0</title>
<style>
:root { color-scheme: dark; --bg:#0d0f12; --panel:#151920; --panel2:#1b2028; --ink:#eef2f6; --muted:#9ca8b7; --line:#2b3440; }
* { box-sizing:border-box; }
body { margin:0; min-height:100vh; background:radial-gradient(circle at 50% 0,#1d222a 0,#0d0f12 46%); color:var(--ink); font-family:ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
main { width:min(1180px,96vw); margin:0 auto; padding:24px 0 40px; }
header { display:flex; align-items:end; justify-content:space-between; gap:18px; margin-bottom:18px; }
h1 { margin:0; font-size:clamp(30px,5vw,54px); letter-spacing:-.05em; font-weight:760; }
.sub { color:var(--muted); max-width:610px; line-height:1.45; }
.machine { border:1px solid var(--line); border-radius:24px; background:linear-gradient(180deg,var(--panel2),var(--panel)); padding:18px; box-shadow:0 24px 80px rgba(0,0,0,.34); }
.display { border:1px solid var(--line); background:#090b0e; border-radius:17px; padding:14px; }
.topline { display:flex; gap:18px; flex-wrap:wrap; justify-content:space-between; color:var(--muted); font:12px ui-monospace,SFMono-Regular,Menlo,monospace; margin-bottom:8px; }
canvas { width:100%; height:330px; display:block; border-radius:10px; background:linear-gradient(180deg,#0c1015,#080a0d); }
.legend { display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin-top:10px; font-size:12px; color:var(--muted); }
.legend b { color:var(--ink); font-weight:650; }
.controls { display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-top:16px; }
.control-panel { border:1px solid var(--line); border-radius:18px; padding:16px; background:rgba(9,11,14,.34); }
.knobrow { display:grid; grid-template-columns:1fr 1fr; gap:16px; }
.knob label { display:flex; justify-content:space-between; font-size:13px; letter-spacing:.04em; text-transform:uppercase; color:var(--muted); margin-bottom:9px; }
input[type=range] { width:100%; accent-color:#f3f5f7; }
.buttons { display:grid; grid-template-columns:repeat(5,1fr); gap:9px; margin-top:16px; }
button { border:1px solid #3a4553; color:var(--ink); background:#202731; border-radius:12px; min-height:48px; padding:8px 10px; font:700 12px ui-sans-serif,system-ui; letter-spacing:.06em; cursor:pointer; }
button:hover { background:#2a3340; }
button:disabled { opacity:.45; cursor:not-allowed; }
button.primary { background:#eef2f6; color:#11151a; border-color:#eef2f6; }
button.active { outline:2px solid #eef2f6; outline-offset:2px; }
.readout { display:grid; grid-template-columns:repeat(2,1fr); gap:10px; }
.card { background:#0d1116; border:1px solid var(--line); border-radius:12px; padding:12px; }
.card small { display:block; color:var(--muted); margin-bottom:4px; text-transform:uppercase; letter-spacing:.07em; }
.card strong { font:600 15px ui-monospace,SFMono-Regular,Menlo,monospace; }
.status { min-height:44px; margin-top:12px; color:var(--muted); font-size:13px; line-height:1.45; }
.downloads { display:flex; gap:8px; flex-wrap:wrap; margin-top:10px; }
.downloads a { color:var(--ink); border:1px solid var(--line); border-radius:9px; padding:7px 9px; text-decoration:none; font-size:12px; }
.note { margin-top:18px; color:var(--muted); font-size:12px; line-height:1.5; }
@media(max-width:760px){ .controls{grid-template-columns:1fr}.buttons{grid-template-columns:repeat(3,1fr)} .knobrow{grid-template-columns:1fr} canvas{height:280px} }
</style>
</head>
<body>
<main>
<header>
  <div><h1>IPM Machine <span style="color:#8e9aaa">v0</span></h1><div class="sub">A steering surface for the current deterministic Tune / Bass / Rhythm instrument. Make a world, alter its activity, choose its realised surprise level, hold its Tune identity, and finish a piece.</div></div>
</header>
<section class="machine">
  <div class="display">
    <div class="topline"><span id="seed">SEED —</span><span id="tempo">— BPM</span><span id="validation">ENGINE —</span></div>
    <canvas id="score" width="1100" height="330" aria-label="Tune, Bass and Rhythm event streams"></canvas>
    <div class="legend"><span><b>TUNE</b> predictive line</span><span><b>BASS</b> structural lane</span><span><b>RHYTHM</b> short pitched lane</span></div>
  </div>

  <div class="controls">
    <div class="control-panel">
      <div class="knobrow">
        <div class="knob"><label for="activity"><span>Activity</span><span id="activityValue">50</span></label><input id="activity" type="range" min="0" max="100" value="50"></div>
        <div class="knob"><label for="surprise"><span>Surprise</span><span id="surpriseValue">50</span></label><input id="surprise" type="range" min="0" max="100" value="50"></div>
      </div>
      <div class="buttons">
        <button id="newBtn">NEW</button>
        <button id="playBtn" class="primary">PLAY</button>
        <button id="stopBtn">STOP</button>
        <button id="holdBtn">HOLD</button>
        <button id="finishBtn">FINISH</button>
      </div>
      <div class="status" id="status">Building the first piece…</div>
      <div class="downloads" id="downloads"></div>
    </div>

    <div class="control-panel readout">
      <div class="card"><small>Selected seed</small><strong id="selectedSeed">—</strong></div>
      <div class="card"><small>Mean surprise</small><strong id="meanSurprise">— bits</strong></div>
      <div class="card"><small>Texture</small><strong id="texture">—</strong></div>
      <div class="card"><small>Events</small><strong id="events">—</strong></div>
    </div>
  </div>
  <div class="note"><b>HOLD</b> pins the current Tune seed. While held, ACTIVITY can reshape Bass/Rhythm without changing the Tune seed; the SURPRISE target is stored but only takes effect after HOLD is released. The built-in audio is a dependency-free preview synth. MIDI is the instrument-neutral output.</div>
</section>
</main>
<audio id="audio" preload="auto"></audio>
<script>
const $ = s => document.querySelector(s);
const audio = $('#audio');
let state = null;
let requestSerial = 0;

function f(n,d=2){ return Number(n).toFixed(d); }
function setBusy(on, message){
  for (const b of document.querySelectorAll('button')) b.disabled = on;
  $('#activity').disabled = on;
  $('#surprise').disabled = on || (state && state.controls.hold);
  if (message) $('#status').textContent = message;
}
function pitchRange(events){ if (!events.length) return [48,72]; const ps=events.map(e=>e.pitch); return [Math.min(...ps)-2, Math.max(...ps)+2]; }
function frac(v){ return v[0]/v[1]; }
function draw(){
  if(!state) return;
  const c=$('#score'), ctx=c.getContext('2d');
  const w=c.width,h=c.height; ctx.clearRect(0,0,w,h);
  const voices=['TUNE','BASS','RHYTHM'];
  const laneH=h/3; const totalBeats=state.bars*state.beats_per_bar;
  ctx.font='12px ui-monospace, monospace';
  voices.forEach((name,li)=>{
    const y0=li*laneH; ctx.fillStyle=li%2?'#0d1116':'#0b0e12'; ctx.fillRect(0,y0,w,laneH);
    ctx.fillStyle='#7f8b99'; ctx.fillText(name,10,y0+18);
    const ev=state.voices[name]||[]; const [pmin,pmax]=pitchRange(ev); const span=Math.max(1,pmax-pmin);
    ev.forEach(e=>{
      const x=frac(e.onset)/totalBeats*w; const ew=Math.max(2,frac(e.duration)/totalBeats*w);
      const py=(e.pitch-pmin)/span; const y=y0+laneH-15-py*(laneH-34);
      ctx.fillStyle=name==='TUNE'?'#eef2f6':name==='BASS'?'#aeb8c4':'#788697';
      ctx.fillRect(x,y,ew,4);
    });
    ctx.strokeStyle='#26303b'; ctx.beginPath(); ctx.moveTo(0,y0+laneH-.5); ctx.lineTo(w,y0+laneH-.5); ctx.stroke();
  });
  ctx.strokeStyle='#1d2630'; ctx.lineWidth=1;
  for(let bar=0;bar<=state.bars;bar++){ const x=bar/state.bars*w; ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,h);ctx.stroke(); }
}
function render(){
  $('#seed').textContent=`ROOT ${state.root_seed}`;
  $('#tempo').textContent=`${state.tempo_bpm} BPM`;
  $('#validation').textContent=state.validation.passed?'ENGINE PASS':'ENGINE FAIL';
  $('#selectedSeed').textContent=state.selected_seed;
  $('#meanSurprise').textContent=`${f(state.mean_surprise_bits,2)} bits`;
  const occ=state.metrics.texture_occupancy||{};
  const top=Object.entries(occ).sort((a,b)=>b[1]-a[1])[0];
  $('#texture').textContent=top?`${top[0]} ${Math.round(top[1]*100)}%`:'—';
  $('#events').textContent=`${state.metrics.tune_events}/${state.metrics.bass_events}/${state.metrics.rhythm_events}`;
  $('#activity').value=Math.round(state.controls.activity*100); $('#activityValue').textContent=Math.round(state.controls.activity*100);
  $('#surprise').value=Math.round(state.controls.surprise*100); $('#surpriseValue').textContent=Math.round(state.controls.surprise*100);
  $('#holdBtn').classList.toggle('active',state.controls.hold); $('#holdBtn').textContent=state.controls.hold?'HELD':'HOLD';
  $('#surprise').disabled=state.controls.hold;
  $('#status').textContent=state.hold_note || 'Ready. Change a control, start a new world, or finish this piece.';
  audio.src=state.audio_url+'?v='+Date.now(); draw();
}
async function api(path,payload={}){
  const serial=++requestSerial; setBusy(true,'Composing…');
  try{
    const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    const data=await r.json(); if(!r.ok) throw new Error(data.error||'Request failed');
    if(serial===requestSerial && data.controls){ state=data; render(); }
    return data;
  } catch(err){ $('#status').textContent=err.message; throw err; }
  finally{ setBusy(false); if(state) $('#surprise').disabled=state.controls.hold; }
}
let controlTimer;
function scheduleControls(){
  $('#activityValue').textContent=$('#activity').value; $('#surpriseValue').textContent=$('#surprise').value;
  clearTimeout(controlTimer); controlTimer=setTimeout(()=>api('/api/controls',{activity:$('#activity').value/100,surprise:$('#surprise').value/100}),260);
}
$('#activity').addEventListener('input',scheduleControls); $('#surprise').addEventListener('input',scheduleControls);
$('#newBtn').addEventListener('click',()=>api('/api/new',{activity:$('#activity').value/100,surprise:$('#surprise').value/100}));
$('#holdBtn').addEventListener('click',()=>api('/api/hold',{hold:!state.controls.hold,activity:$('#activity').value/100,surprise:$('#surprise').value/100}));
$('#playBtn').addEventListener('click',()=>audio.play()); $('#stopBtn').addEventListener('click',()=>{audio.pause();audio.currentTime=0;});
$('#finishBtn').addEventListener('click',async()=>{
  const data=await api('/api/finish');
  const box=$('#downloads'); box.innerHTML='';
  for(const [kind,url] of Object.entries(data.files)){ const a=document.createElement('a');a.href=url;a.textContent=kind.toUpperCase();a.setAttribute('download','');box.appendChild(a); }
  $('#status').textContent=`Finished seed ${data.selected_seed}. WAV, MIDI, trace and machine manifest are ready.`;
});
(async()=>{ const r=await fetch('/api/state'); state=await r.json(); render(); })();
</script>
</body>
</html>'''

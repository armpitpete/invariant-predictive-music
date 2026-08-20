# RealSynthEngine v4 — Architecture v0.1

Status: **FROZEN BEFORE IMPLEMENTATION OR AUDITION**

Repository: `armpitpete/invariant-predictive-music`
Parent repository head: `b2e36e5294a1fbbdc664607df9c1005343561ca3`
Parent v3 engine source blob: `cbdee4ae993a46346da1fd6b47621e5596cfc715` (`src/ipm/real_synth.py`)
Parent v2 evolving-field source blob: `692c7c45470bcc8c403020534867cbeb066aa5fd` (`src/ipm/synth_engine_v2.py`)

## 1. Purpose

RealSynthEngine v4 is the first version designed to be an **instrument engine**, not merely an offline renderer.

It combines three previously established properties:

1. **v3 modularity** — patches are ordinary data and the DSP engine is independent of any one sound;
2. **v2 musical evolution** — sound may evolve coherently within notes, across phrases and across a whole piece without altering written notes;
3. **stateful performance** — note-on, note-off, continuous controls and voice state persist across processing blocks.

The central invariant is:

> the synthesis engine may transform the sound of composed events, but it must not become a hidden composition engine.

## 2. Composition boundary

v4 may consume:

- lane or instrument identity;
- written pitch;
- note-on time;
- note-off time or duration;
- velocity;
- tempo and time-signature metadata;
- bar, phrase and piece position supplied by the host;
- explicit performance/control events;
- selected patch and patch-bank data.

v4 must not:

- add, remove, reorder or repitch written note events;
- change written note-on or note-off times;
- select a different IPM seed;
- change Tune/Bass/Rhythm composition parameters;
- feed synthesis state back into IPM/A5 composition selection;
- create hidden pitched accompaniment in order to rescue weak material;
- depend on network services at synthesis time.

Harmonics, subharmonics, inharmonic modes, noise, exciters and resonances remain timbral components of an existing written event, not new composition events.

## 3. Engine model

v4 is a **stateful block processor**.

### 3.1 Core API model

The conceptual API is:

- `reset(sample_rate, block_size)`
- `load_patch_bank(bank)`
- `note_on(note_id, lane, pitch, velocity, sample_offset=0)`
- `note_off(note_id, sample_offset=0)`
- `control_change(control_id, value, sample_offset=0)`
- `set_transport(tempo_bpm, beat_position, bar_position, phrase_position, piece_position)`
- `process_block(frame_count) -> stereo float buffer`
- `all_notes_off()`
- `snapshot_state()` for test/evidence only

Names may vary in implementation, but these semantics are mandatory.

### 3.2 One engine, two hosts

There must be only one synthesis state machine.

- **Realtime host** schedules performance events into successive blocks.
- **Offline host** converts an existing complete `InstrumentResult` or equivalent event ledger into the same event stream and processes it block by block.

The offline renderer must not use a separate whole-note DSP implementation.

## 4. Determinism model

For a fixed:

- engine version;
- patch bank;
- sample rate;
- block size;
- initial reset state;
- transport stream;
- note/control event stream;

the output must be byte-deterministic after final PCM quantisation in the reference environment.

All noise or stochastic-looking modulation must derive from deterministic engine/voice/event seeds. Wall-clock time, thread timing, process ID and global random state are forbidden inputs.

A reset followed by the same stream must reproduce the same result.

## 5. Voice manager

v4 owns explicit live voices.

Each voice must retain, at minimum:

- note identity;
- lane;
- pitch;
- velocity;
- active/released state;
- age in samples;
- oscillator/FM/modal phases;
- envelope stages and levels;
- filter state;
- LFO state where voice-scoped;
- deterministic noise state;
- pan/unison state;
- current macro/modulation state required for continuity.

### 5.1 Polyphony

Patch data defines `polyphony` in the range `1..32`.

### 5.2 Voice allocation

Deterministic allocation order:

1. use an idle voice if available, lowest voice index first;
2. otherwise steal the released voice with lowest instantaneous amplitude, then oldest age, then lowest voice index;
3. if all voices remain held, steal the lowest instantaneous amplitude, then oldest age, then lowest voice index.

For allocation purposes, each voice exposes a deterministic `allocation_level = amp_envelope_level * (0.25 + 0.75 * velocity_unit)`, clipped to `0..1`. “Lowest instantaneous amplitude” in the rule above means this exact `allocation_level`, not waveform peak measurement.

Voice stealing must use a fixed **5 ms de-click release/crossfade** before reuse. It may truncate timbral release but must not mutate the composition ledger.

### 5.3 Mono/legato modes

Patch data defines:

- `voice_mode`: `poly | mono_retrigger | mono_legato`;
- `portamento_seconds`: `0..2.0`;
- `portamento_mode`: `always | legato_only`.

Mono-legato changes continuous pitch state only; it may not create extra note events.

## 6. Synthesis sources

A patch may enable any combination of the following source modules. Disabled modules consume no musical authority.

### 6.1 Virtual-analogue oscillator bank

Keep and evolve the v3 oscillator family:

- sine;
- triangle;
- band-limited saw;
- band-limited square;
- band-limited pulse;
- deterministic noise.

Up to **3 VA oscillators** per voice.

Per oscillator patch data:

- waveform;
- octave/semitone/cents;
- gain;
- phase;
- pulse width;
- key tracking multiplier;

The exact anti-aliasing method is implementation-defined before implementation freeze, but must be deterministic and stable at the supported sample rates.

### 6.2 Four-operator FM bank

v4 contains one optional **4-operator phase-modulation/FM bank** per voice.

Each operator exposes:

- frequency mode: `ratio | fixed_hz`;
- ratio or fixed frequency;
- coarse/fine offset;
- output level;
- velocity sensitivity;
- key tracking;
- envelope assignment;
- feedback amount where permitted by the selected algorithm.

The patch selects exactly one of these frozen algorithms:

1. `4>3>2>1`
2. `(4+3+2)>1`
3. `(4>3)+(2>1)`
4. `(4>3>1)+(2>1)`
5. `(4>2>1)+(3>1)`
6. `4>(3+2)>1`
7. `(4>1)+(3>1)+(2>1)`
8. `4+3+2+1` (four carriers)

The algorithm controls routing only. Operator ratios, gains, envelopes and indices are patch data.

### 6.3 Modal/resonator bank

v4 contains one optional generic modal bank with **1..16 modes**.

Each mode defines:

- frequency ratio relative to the written note, or a fixed frequency;
- gain;
- decay time;
- detune cents;
- velocity sensitivity;
- brightness sensitivity;
- excitation sensitivity.

The bank is excited by the written event's existing source/exciter signal; it must not create independently scheduled pitched notes.

### 6.4 Exciter/noise module

Optional deterministic exciter types:

- white noise;
- smoothed noise;
- click/impulse;
- short filtered-noise burst.

Patch data controls level, duration/decay and spectral smoothing/filtering.

## 7. Signal graph

Per voice, the fixed v4 graph is:

`VA source + FM source + exciter -> source mixer -> modal/resonator send/return -> pre-filter drive -> multimode filter -> VCA -> stereo/pan -> dry bus + FX sends`

The source modules and modal bank may be disabled, but arbitrary user code or arbitrary graph cycles are not permitted in v4.

A patch therefore changes the active modules and parameters without changing DSP source code.

## 8. Envelopes

Each patch has exactly **two general modulation envelopes** plus a required amplifier envelope:

- `amp_env`;
- `env1`;
- `env2`.

Each supports:

- attack;
- decay;
- sustain;
- release;
- attack curve;
- decay curve;
- release curve;
- retrigger mode: `restart | legato | continue`.

Envelope time range: `0..30 s` per stage.

Either non-amp envelope may be routed through the modulation matrix.

## 9. LFOs and tempo state

Each patch has exactly **2 LFOs**.

Each LFO supports:

- sine;
- triangle;
- saw;
- square;
- sample-and-hold deterministic random;
- bipolar/unipolar;
- free-running Hz mode;
- tempo-synchronised mode.

Tempo divisions allowed:

`1/64, 1/32, 1/16, 1/8, 1/4, 1/2, 1, 2, 4` beats, each optionally dotted or triplet.

LFO scope is patch data: `voice | global`.

Global LFO phase must be transport-deterministic, not wall-clock based.

## 10. Modulation matrix

The v3 data-driven modulation principle is retained and expanded.

Maximum routes per patch: **32**.

Mandatory sources:

- velocity;
- key tracking;
- note age;
- amp envelope;
- env1;
- env2;
- LFO1;
- LFO2;
- macro1..macro8;
- note position;
- phrase position;
- piece position.

Mandatory destinations:

- VA oscillator pitch;
- VA oscillator gain/mix;
- pulse width;
- FM modulation index;
- FM operator level;
- modal gain;
- modal decay multiplier;
- filter cutoff;
- filter resonance;
- pre-filter drive;
- VCA level;
- pan;
- stereo width;
- chorus send;
- delay send;
- reverb send.

Each route defines source, destination, amount and optional unipolar mapping. No code change may be required to add/remove a route among supported endpoints.

## 11. Filter and drive

Retain the v3 stable state-variable multimode filter as the initial v4 filter family:

- low-pass;
- high-pass;
- band-pass;
- notch.

Patch controls:

- cutoff;
- resonance/Q;
- key tracking;
- envelope/modulation routing;
- pre-filter drive.

A second filter model is **not required** for v4. Adding one requires a later governed version or an explicitly frozen extension before audition.

## 12. Eight musician-facing macros

Every v4 patch exposes these exact macro names in the range `0..1`:

1. `BRIGHTNESS`
2. `BODY`
3. `MOTION`
4. `ATTACK`
5. `CHARACTER`
6. `DRIVE`
7. `WIDTH`
8. `SPACE`

A patch defines macro-to-parameter routes through the same modulation system or an equivalent serialisable mapping.

The macro names and semantic direction are fixed:

- increasing `BRIGHTNESS` must not make the patch systematically darker;
- increasing `BODY` must increase perceived low/fundamental/resonant weight;
- increasing `MOTION` must increase internal movement/modulation depth;
- increasing `ATTACK` must move toward sharper/faster/percussive articulation;
- increasing `CHARACTER` must increase spectral/inharmonic/timbral complexity;
- increasing `DRIVE` must increase nonlinearity/saturation;
- increasing `WIDTH` must increase perceived stereo width;
- increasing `SPACE` must increase ambience/effect depth.

Exact patch-specific mappings are data.

All host macro/control changes targeting continuous parameters are smoothed by a fixed **5 ms linear ramp** in the engine parameter layer. Discrete choices such as waveform, synthesis-family enablement, FM algorithm and voice mode are not continuously automatable in v4; host changes to those choices apply to **new notes only**.

## 13. Musical-time evolution

v4 generalises the successful v2 idea into patch data.

### 13.1 Evolution scopes

A patch may define deterministic breakpoint curves for:

- `note` position `0..1`;
- `phrase` position `0..1`;
- `piece` position `0..1`.

Each curve targets only:

- macro1..macro8;
- or explicitly supported modulation destinations.

### 13.2 Breakpoint format

Each curve contains `2..8` `(position, value)` anchors with linear interpolation in v4.

No adaptive fitting, learned curve or post-audition automation is permitted.

### 13.3 Transport authority

The host supplies phrase and piece position. v4 must not infer a new musical form by analysing pitches and then altering synthesis decisions.

## 14. Effects architecture

Effects are stateful block processors shared by the engine.

### 14.1 Chorus

Patch/bank data may define:

- rate;
- depth;
- base delay;
- stereo phase;
- feedback;
- wet level.

### 14.2 Stereo delay

Patch/bank data may define:

- left/right delay time in seconds or tempo divisions;
- feedback;
- cross-feedback;
- damping;
- wet level.

### 14.3 Reverb

v4 may use deterministic algorithmic or fixed synthetic-IR reverb, but data must expose at least:

- decay/time;
- damping/brightness;
- pre-delay;
- stereo width;
- wet level.

The implementation must not select different reverb assets per generated piece after listening.

## 15. Master stage

v4 removes v3 whole-render peak normalisation.

Fixed master order:

1. DC protection/removal;
2. fixed soft saturation/clip protection;
3. deterministic look-ahead or instantaneous safety limiter with fixed parameters;
4. output gain;
5. PCM conversion in the offline host.

The master may prevent numerical clipping but must not normalise each complete piece to its own peak or loudness.

## 16. Patch format

`SynthPatchV4` and `PatchBankV4` are named, versioned, JSON-compatible data objects.

A v4 patch contains at least:

- identity/version;
- voice mode/polyphony;
- VA source config;
- FM config;
- modal config;
- exciter config;
- envelopes;
- LFOs;
- filter/drive;
- modulation routes;
- macro mappings/defaults;
- evolution curves;
- pan/width;
- FX sends/parameters.

### 16.1 v3 migration

v4 must provide a deterministic migration function from valid v3 `SynthPatch` data into a v4-compatible patch using:

- the VA path;
- the two LFO slots;
- equivalent envelopes/filter/routes where representable;
- disabled FM/modal/evolution features unless explicitly represented in v3.

Migration must not claim sample-identical v3 audio; it must preserve patch intent/data meaning where representable.

## 17. Initial reference patch families

Before the first human v4 family audition, exactly three reference patch families must be frozen:

1. **VA** — subtractive/pulse/saw instrument using primarily VA source + filter;
2. **FM** — instrument whose identity depends primarily on the 4-op FM bank;
3. **MODAL** — instrument whose identity depends primarily on exciter + modal bank.

The same frozen written Tune ledger must be used for all three family renders.

These are acceptance fixtures, not the full factory library.

## 18. Supported operating modes

v4 architecture must support:

- deterministic offline rendering at 44.1 kHz;
- stateful block processing at 44.1 kHz;
- block sizes `64`, `128`, `256`, or `512` frames;
- future realtime host integration without changing the synthesis graph.

The first v4 acceptance does **not** require VST/AU packaging or external MIDI hardware.

## 19. Explicit non-goals

Not required for v4:

- sample playback/multisampling;
- granular synthesis;
- user-loaded wavetables;
- physical-model waveguide/string/bore solvers;
- arbitrary modular graphs or scripting;
- VST/AU/CLAP packaging;
- MPE;
- external MIDI clock;
- hardware control surface;
- AI-generated patches;
- A5 feedback into synthesis;
- cloud/network rendering.

## 20. Stop rule

This architecture is frozen before implementation.

Implementation may resolve ordinary low-level engineering details that do not change the architecture, but it may not after listening:

- add a new synthesis family;
- change the voice-allocation rule;
- change macro semantics;
- change the FM algorithm set;
- alter the signal graph;
- add adaptive/learned evolution;
- change the acceptance fixtures to a more flattering composition.

A required architectural change creates `v4.1` or a new governed version; it is not silently folded into v4 after audition.

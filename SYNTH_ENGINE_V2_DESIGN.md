# Machine Synth Engine v2 — Frozen Design

Status: **FROZEN BEFORE IMPLEMENTATION OR AUDITION**

Contract parent: `SYNTH_REPLACEMENT_CONTRACT_V2.md` at commit `7fa85d05134ee0b1df5f34cf562a3c6b39a27f5b`.

Engine name: **Evolving Resonant Field v2**

The design goal is not a neutral General MIDI renderer. The written IPM notes are the structural skeleton; the instrument must provide substantial musical interest through evolving timbre, articulation, texture and space without adding a replacement melody.

No parameter in this document may be tuned after hearing the v2 acceptance audition. If the resulting sound fails, v2 fails as designed.

## 1. Render format and implementation substrate

- internal processing: deterministic floating-point DSP using NumPy arrays;
- runtime dependency: `numpy>=2.0`;
- output sample rate: **44,100 Hz**;
- output channels: **stereo**;
- output format: **16-bit PCM WAV**;
- no network service;
- no SoundFont, DAW, external synthesizer or manually selected per-piece asset;
- all stochastic-looking material uses a deterministic event seed derived from lane, written pitch, onset and event ordinal.

## 2. Shared musical-time state

Let `p` be written onset divided by total written piece beats, clipped to `0..1`.

All lanes share a continuous four-anchor sonic arc. Parameters are linearly interpolated between these fixed anchors:

| piece position | brightness | motion depth | stereo width | room send |
|---|---:|---:|---:|---:|
| 0.00 | 0.34 | 0.18 | 0.58 | 0.18 |
| 0.33 | 0.62 | 0.34 | 0.78 | 0.24 |
| 0.67 | 0.82 | 0.46 | 0.94 | 0.31 |
| 1.00 | 0.48 | 0.24 | 0.68 | 0.22 |

This arc alters only timbre, modulation, spatial width and ambience. It does not alter written pitch, onset, duration or velocity.

Phrase state is the zero-based four-bar phrase index. Phrase state may offset event timbre by the fixed repeating sequence `(-0.08, +0.04, +0.10, -0.03)` in brightness units. For pieces longer than 16 bars the sequence repeats; it never selects notes.

## 3. Event micro-variation

Each event receives a deterministic scalar `v` in `[-1, +1]` from a 64-bit integer mix of:

`lane_id, pitch, numerator(onset), denominator(onset), ordinal`.

`v` may alter only timbral parameters, with these maxima:

- attack time: ±12%;
- modal decay time: ±9%;
- transient amount: ±10%;
- stereo position: ±0.035;
- modulation phase: unrestricted phase offset;
- modulation rate: ±6%.

It may not alter note timing, duration, pitch or MIDI velocity.

## 4. TUNE — glass/string evolving resonator

Identity: a struck-and-sustained electroacoustic voice with a soft glass/string body rather than a static oscillator lead.

### Tonal body

Written pitch frequency `f` excites modal partials:

`(ratio, base_gain, decay_multiplier)`

- `(1.000, 1.000, 1.00)`
- `(2.010, 0.290, 0.72)`
- `(3.970, 0.155, 0.49)`
- `(5.120, 0.090, 0.35)`
- `(7.080, 0.052, 0.24)`

A twin fundamental at **+3.7 cents** is mixed at gain `0.115`.

Base modal decay is `max(0.34, min(1.65, written_duration_seconds * 0.88 + 0.30))` seconds. Higher modal decays use the multipliers above.

### Attack/excitation

A deterministic filtered-noise transient of **38 ms** is mixed at base gain `0.105`, scaled by velocity and by `(0.74 + 0.42 * brightness)`.

The body amplitude envelope uses:

- attack `18 ms`;
- decay `145 ms`;
- sustain `0.66`;
- release `310 ms`.

### Within-note motion

Two spectral groups are modulated in opposite directions by a sine LFO:

- base rate `0.23 Hz`;
- depth `0.10 + 0.22 * motion_depth`;
- group A: fundamental + 2.010 partial;
- group B: remaining higher modes.

A second very slow amplitude drift at `0.071 Hz` and depth `0.035` applies to the whole note.

### Air layer

A low-level deterministic breath/noise layer follows the body envelope at gain `0.018 + 0.022 * brightness` and must be spectrally smoothed by a fixed 9-sample moving average.

### Stereo

Base pan `-0.16 * stereo_width`. The detuned twin is mirrored to `+0.13 * stereo_width`. Event micro-pan may shift both by at most ±0.035.

Base room send `0.27 * shared_room_send`.

## 5. BASS — warm wood/sub resonator

Identity: rounded, physical and slightly saturated; it must provide body rather than a generic sine/sub patch.

### Tonal body

Components attached to the written pitch:

- subharmonic `0.500 f`, gain `0.19`;
- fundamental `1.000 f`, gain `1.00`;
- second harmonic `2.000 f`, gain `0.18`;
- third harmonic `3.000 f`, gain `0.070`;
- fifth harmonic `5.000 f`, gain `0.025`.

The subharmonic is explicitly timbral and is not represented as a separate note event.

The raw body is driven through `tanh(x * 1.55)` before its amplitude envelope.

### Attack/excitation

A deterministic low-frequency thump/noise transient of **26 ms** is mixed at gain `0.085`.

Envelope:

- attack `11 ms`;
- decay `190 ms`;
- sustain `0.76`;
- release `360 ms`.

### Within-note motion

Harmonic tilt breathes at base `0.117 Hz`; motion depth is `0.055 + 0.17 * shared_motion_depth`. The fundamental/sub group and upper harmonics move inversely.

Brightness affects upper-harmonic gain by multiplier `0.62 + 0.58 * brightness`.

### Stereo

Base pan `-0.025`; width motion may move at most ±0.025. The bass remains perceptually central.

Base room send `0.10 * shared_room_send`.

## 6. RHYTHM — struck skin/metal resonator

Identity: short, tactile, resonant and textural rather than a pitched beep.

Each written rhythm event excites:

- deterministic noise burst of **14 ms**, gain `0.22`;
- modal ratios `(1.000, 1.470, 2.230, 3.650, 5.180)` relative to written pitch;
- modal gains `(1.00, 0.42, 0.24, 0.13, 0.065)`;
- modal decay times `(0.22, 0.17, 0.12, 0.085, 0.060)` seconds before velocity/micro-variation scaling.

Brightness multiplies upper three modal gains by `0.68 + 0.55 * brightness`.

Velocity affects both excitation amplitude and modal decay: decay multiplier `0.82 + 0.34 * velocity_unit`.

A short nonlinear body stage uses `tanh(x * 1.32)`.

Base pan `+0.22 * stereo_width`; event micro-pan may shift ±0.035.

Base room send `0.22 * shared_room_send`.

## 7. Deterministic spatial field

Each lane renders to a dry stereo bus and a mono room-send bus.

The room is a fixed synthetic stereo impulse response of **0.92 seconds** generated once per render from constants, not from the musical seed.

### Early reflections

Left taps `(seconds, gain)`:

- `(0.023, 0.24)`
- `(0.041, 0.17)`
- `(0.067, 0.115)`
- `(0.089, 0.082)`

Right taps:

- `(0.029, 0.22)`
- `(0.047, 0.16)`
- `(0.071, 0.108)`
- `(0.097, 0.077)`

### Late field

From 100 ms to 920 ms, a deterministic bipolar noise tail is multiplied by exponential decay with time constant `0.245 s`, then smoothed by a 17-sample moving average. Left and right use fixed different deterministic sequences.

The room output is high-frequency softened by an additional 11-sample moving average and mixed additively; there is no feedback network.

## 8. Master field

Dry lane nominal gains before room return:

- TUNE `0.74`;
- BASS `0.82`;
- RHYTHM `0.68`.

Room return gain: `0.58`.

Master processing order:

1. remove DC by subtracting each channel mean;
2. soft saturation `tanh(x * 1.18)`;
3. peak-normalise only if absolute peak exceeds `0.94`, scaling both channels together to `0.94`;
4. quantise to signed 16-bit PCM.

No per-piece EQ, mastering or gain riding is permitted.

## 9. Simple-material interest requirement

The first v2 audition must use the **same written Tune events from selected seed `1693196453`** used in Synth Sound Acceptance v1. No new root seed or candidate may be selected.

The Tune-solo file is judged first on:

> **Even if the note sequence is plain, is the sound itself interesting enough that I want to keep listening?**

Only after that judgment may Bass solo, Rhythm solo and full mix be judged under the broader Synth Sound Acceptance question.

## 10. Technical invariants

Implementation must prove:

- byte-identical WAV for identical input events and v2 render contract;
- written note event tuples are unchanged before/after synthesis;
- stereo channels are not identical for non-silent Tune/Rhythm material;
- no output NaN/Inf before quantisation;
- no clipping beyond signed PCM limits;
- v2 manifest contains the exact constants above and engine version `2.0`;
- v1 failed audition and renderer remain available as evidence; listener-study renderer remains untouched.

## 11. Stop rule

After this design is frozen, implementation may reproduce it but must not retune it after listening. The first sound-acceptance artifact is the v2 result. A FAIL requires a new governed version rather than covert preset iteration.

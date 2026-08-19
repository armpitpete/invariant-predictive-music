# IPM Real Synth Engine v3 — frozen contract

Status: **FROZEN BEFORE AUDITION**

This contract corrects the category error in Machine Synth Engine v1/v2. A fixed renderer with one designed timbre is not a synthesizer engine. v3 must be a reusable synthesis system in which **patches are data and the DSP engine is independent of any one sound**.

## Product requirement

The engine must be capable of rendering the same unchanged IPM note/event ledger into materially different, musically usable instruments by changing patch data alone.

A patch may be interesting or dull. The engine itself must not be synonymous with one patch.

## Composition boundary

The synth may consume only the already-composed event information available to audio rendering (lane, pitch, onset, duration, velocity, tempo/form metadata). It must not:

- add, remove, reorder or repitch composed note events;
- select a different IPM seed to flatter a patch;
- change Tune/Bass/Rhythm composition parameters;
- feed synthesis state back into IPM selection/scoring;
- alter listener-study rendering or recruitment state.

The renderer must assert that the event ledger is unchanged across rendering.

## Required synthesis architecture

### Polyphonic voice engine

- independent note voices with overlapping release tails;
- deterministic voice rendering for an identical event ledger + patch bank;
- sample-rate aware DSP;
- velocity and MIDI-key tracking available as modulation sources.

### Oscillator section

Each patch defines up to three oscillator slots. The engine must support at least:

- sine;
- triangle;
- band-limited saw;
- band-limited square/pulse;
- deterministic noise.

Each oscillator slot must expose patch data for:

- waveform;
- octave/semitone/cents tuning;
- gain;
- pulse width where applicable;
- phase offset.

The voice section must additionally expose:

- oscillator-2 → oscillator-1 phase/FM amount;
- oscillator ring-modulation amount;
- noise level;
- unison voice count and detune spread.

### Envelopes

At minimum:

- amplitude ADSR;
- filter ADSR;

with independently patchable attack, decay, sustain, release and filter-envelope depth.

### Filter

A resonant multimode filter supporting at least:

- low-pass;
- high-pass;
- band-pass;
- notch.

Patch data must expose:

- cutoff;
- resonance/Q;
- key tracking;
- envelope amount;
- drive.

The implementation must guard unstable/invalid cutoff and resonance ranges.

### LFO and modulation system

At least two LFOs per patch with patchable:

- waveform;
- rate;
- phase;
- bipolar/unipolar mode.

The modulation matrix must be data-driven. Supported sources must include:

- velocity;
- key tracking;
- amp envelope;
- filter envelope;
- LFO 1;
- LFO 2.

Supported destinations must include at least:

- pitch;
- filter cutoff;
- amplitude;
- pan;
- oscillator mix.

The engine must not require code changes to alter a modulation route.

### Stereo and effects buses

Patch/bank data must expose:

- per-patch base pan and stereo width;
- chorus send;
- delay send;
- reverb send.

The engine must provide deterministic built-in chorus, stereo delay and algorithmic room/reverb buses. Effects are part of the synthesis system, not hard-coded to one timbre.

## Patch system

A `SynthPatch` must be:

- serialisable to ordinary JSON-compatible data;
- reconstructable from that data;
- validated independently of rendering;
- named and versioned.

A `PatchBank` must map IPM lanes (`TUNE`, `BASS`, `RHYTHM`) to patch names. The same engine must permit different lane mappings without changing DSP code.

The repository must contain at least two intentionally different patches capable of rendering the **same Tune ledger** with different audio, to prove that v3 is an engine rather than a fixed sound.

## Technical acceptance tests

Before any human sound judgment, exact-head CI must prove:

1. patch serialisation round-trips without semantic change;
2. invalid patch values fail validation;
3. identical input + patch bank gives byte-identical WAV output;
4. changing only patch data changes the WAV while leaving the note ledger identical;
5. output is finite stereo PCM with nonzero content for nonempty input;
6. silence renders as valid silence;
7. filter modes and oscillator types execute without numerical failure;
8. modulation routes are interpreted from data rather than bespoke patch code;
9. rendering does not mutate the IPM event ledger.

## Human acceptance sequence

A technically passing engine is not automatically a good instrument.

After the engine implementation is frozen, audition patches may be designed and judged. The first human engine demonstration must render **one identical frozen Tune ledger through at least three substantially different patch definitions**.

That audition asks:

> Does this behave like a real synthesizer engine with distinct usable instruments, rather than one synth sound with cosmetic variations?

Only after that passes may Machine PLAY/FINISH be switched from the old compatibility renderer to v3.

## Explicit non-goals for v3

- VST/AU plugin packaging;
- realtime low-latency MIDI input;
- hardware control surface;
- sample/granular engine;
- arbitrary user scripting inside patches;
- changing IPM composition to rescue synthesis.

Those may follow later. They are not required to establish the real synth-engine boundary.
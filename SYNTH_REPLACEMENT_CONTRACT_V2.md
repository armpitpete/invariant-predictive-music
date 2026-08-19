# Machine Synth Replacement Contract v2

Status: **FROZEN BEFORE DESIGN**

This contract is derived only from the failed Synth Sound Acceptance v1 judgment:

> uncomfortable, toyish, flat, basic

It defines what a replacement synth must achieve before implementation. It does not prescribe one synthesis technology or permit changes to IPM composition.

## 1. Tonal comfort

The replacement must be suitable for sustained listening at ordinary headphone/speaker level without a persistent brittle, piercing, nasal, buzzy, scratchy or fatiguing character.

Acceptance evidence: in the frozen solo/full-mix audition, the owner does not identify the overall sound as uncomfortable or fatiguing.

## 2. Timbral credibility

Each lane must read as an intentional musical instrument/voice rather than an oscillator demonstration, placeholder patch, toy keyboard or test tone.

TUNE, BASS and RHYTHM must remain distinguishable by timbre without relying only on register or stereo position.

Acceptance evidence: each solo can be judged independently as a credible musical voice.

## 3. Dynamic and articulative depth

Notes must have musically useful internal shape. Velocity and event duration must affect more than simple output level. Attack, brightness, sustain/release behaviour and/or other articulation must create audible expressive variation while preserving the composed note events.

Acceptance evidence: repeated listening to the solo lanes reveals meaningful articulation rather than uniform note blocks.

## 4. Spatial and mix depth

The full mix must have front/back and/or width differentiation sufficient to avoid a flat stack of three voices. Space processing must support separation and cohesion without masking pitch/rhythm or producing an obvious cheap reverb effect.

Acceptance evidence: the full mix has audible depth and lane separation while still sounding like one instrument/system.

## 5. Timbral richness and character

The replacement must have enough spectral and temporal complexity that the sound is not reasonably described as basic. Character may come from synthesis, sampling, physical/modelling techniques, modulation, nonlinear processing or combinations of these, but it must remain deterministic for a fixed render contract.

Acceptance evidence: the solo voices have recognisable character and the full mix does not sound like three elementary synth patches layered together.

## 6. Full-mix integration

A synth that has attractive solo patches but an incoherent full mix fails. The three lane voices must occupy complementary ranges and dynamics and combine without one lane sounding pasted on, excessively dominant or disconnected.

Acceptance evidence: the exact full mix is independently acceptable, not inferred from solo acceptance.

## 7. Preservation constraints

The replacement must not:

- alter IPM note choice, timing, duration or velocity in the composition engine;
- change Tune scoring or candidate selection;
- change the frozen listener-study renderer or artifacts;
- use per-piece manual EQ, patch selection or mastering to rescue an audition;
- choose a different musical seed after hearing an audition result;
- depend on a network service at render time.

It may introduce a different local/offline synthesis architecture, fixed instrument assets, higher-quality DSP, deterministic effects and a richer fixed production chain if these are part of the frozen synth contract before audition.

## 8. Validation sequence

A replacement must pass, in order:

1. **Technical Synth Gate** — deterministic render, valid audio, exact contract/provenance, no composition mutation.
2. **Synth Sound Acceptance** — frozen Tune solo / Bass solo / Rhythm solo / full mix from one predeclared machine state.
3. **Machine Use Gate** — only after sound acceptance passes.

A technical PASS cannot override an audible FAIL.

## Protected design boundary

The next legitimate action after this freeze is to design **one** Machine Synth Engine v2 against this contract, then freeze its exact architecture/presets/assets before hearing its acceptance audition.

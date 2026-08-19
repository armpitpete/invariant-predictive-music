# Machine Synth Replacement Contract v2

Status: **RE-FROZEN BEFORE DESIGN**

This contract is derived from the failed Synth Sound Acceptance v1 judgment:

> uncomfortable, toyish, flat, basic

and the subsequent owner observation:

> The tune is not interesting therefore the sounds need to be interesting

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

## 6. Sound must carry musical interest

The current Tune material may be structurally simple or insufficiently interesting by itself. The replacement synth therefore must not behave as a neutral note player. It must make simple written material worth hearing through **sound design itself**, while preserving every composed note, onset, duration and velocity.

Musical interest may come from deterministic changes in spectral colour, transient/body/tail shape, texture, modulation, harmonic emphasis, noise components, saturation and spatial movement. It may respond to the written event context, phrase position and piece position, but it must not create a hidden replacement composition.

The sound must exhibit coherent evolution at three timescales:

- **within-note** — audible motion or internal life during sustained/decaying events;
- **phrase-scale** — related notes need not be timbrally identical blocks; articulation and colour may develop coherently across a phrase;
- **piece-scale** — the sonic world must have a perceptible arc or evolving state rather than remaining sonically static for the whole render.

Repeated pitches or simple motifs should therefore remain recognisably the same musical material while gaining changing colour and expressive consequence.

Acceptance evidence: the exact previously failed Tune material must be usable as a **simple-material stress test**. The replacement is not allowed to choose a more flattering seed. The owner must be able to judge the Tune solo as sonically interesting enough to keep listening even if the underlying note sequence remains plain.

## 7. Full-mix integration

A synth that has attractive solo patches but an incoherent full mix fails. The three lane voices must occupy complementary ranges and dynamics and combine without one lane sounding pasted on, excessively dominant or disconnected.

Acceptance evidence: the exact full mix is independently acceptable, not inferred from solo acceptance.

## 8. Preservation constraints

The replacement must not:

- alter IPM note choice, timing, duration or velocity in the composition engine;
- change Tune scoring or candidate selection;
- change the frozen listener-study renderer or artifacts;
- use per-piece manual EQ, patch selection or mastering to rescue an audition;
- choose a different musical seed after hearing an audition result;
- add new pitched note events or hidden melodic/harmonic material to make the Tune appear more interesting;
- depend on a network service at render time.

It may introduce a different local/offline synthesis architecture, fixed instrument assets, higher-quality DSP, deterministic effects and a richer fixed production chain if these are part of the frozen synth contract before audition. Harmonics, subharmonics, inharmonic/noise components and deterministic textural layers are allowed when they are part of the timbre of an existing written event rather than new compositional events.

## 9. Validation sequence

A replacement must pass, in order:

1. **Technical Synth Gate** — deterministic render, valid audio, exact contract/provenance, no composition mutation.
2. **Simple-Material Interest Gate** — the frozen previously rejected Tune must demonstrate coherent sonic interest without changing its written events.
3. **Synth Sound Acceptance** — frozen Tune solo / Bass solo / Rhythm solo / full mix from that same predeclared machine state.
4. **Machine Use Gate** — only after sound acceptance passes.

A technical PASS cannot override an audible FAIL. A more sophisticated synthesis architecture cannot substitute for audible interest.

## Protected design boundary

The next legitimate action after this re-freeze is to design **one** Machine Synth Engine v2 against this exact contract, then freeze its exact architecture/presets/assets before hearing its acceptance audition.

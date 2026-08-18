# IPM Working Product Gate v1

Status: **internal only**. This gate does not authorise recruitment, external listener contact, publication of participant materials, PR #24 merge, or any external testing.

## Purpose

Before reopening listener research, establish that the current IPM instrument can repeatedly produce complete music we would willingly show someone.

This gate tests the **product**, not the scientific hypothesis.

## What is already sufficient

The v0.2 production architecture already provides:

- deterministic seeded composition;
- explicit Tune/Bass/Rhythm controls;
- complete 16-bar form generation at a fixed tempo;
- MIDI generation through one dependency-free writer;
- trace-level decision evidence and validation;
- exact configuration and seed provenance;
- existing tests for determinism, lane separation, activity governors, silence competition, transposition and pattern locks.

The Counterfactual Episode work has separately demonstrated a usable FluidSynth/FluidR3_GM PCM rendering contract with chorus and reverb disabled. The product gate reuses that renderer contract only; it does not depend on participant-study selection, blinding, schedules or collection machinery.

## Missing product evidence

The repo does not yet establish that:

1. a **fixed, non-cherry-picked batch** of full IPM pieces is consistently showable;
2. every portfolio piece follows the **same audio production path**;
3. the rendered product can be regenerated deterministically under the recorded renderer contract;
4. failures are preserved as evidence instead of being repaired one output at a time.

## Frozen v1 portfolio

Exactly **8 pieces** are generated before any listening:

- four seeds derived from `SHA-256("ipm-working-product-v1:<label>")`:
  - A = `987762706`
  - B = `1627790159`
  - C = `1434366392`
  - D = `883758274`
- two predeclared profiles per seed:
  - `default`: current v0.2 defaults;
  - `active`: changes only Bass activity `0.46 -> 0.62` and Rhythm activity `0.40 -> 0.55`.

Everything else is fixed:

- mode: `ipm`
- bars: `16`
- tempo: `58 BPM`
- meter: `4/4`
- tonic MIDI: `60`
- Tune alternatives: `18`

No seed or profile may be deleted, replaced or changed after listening begins.

## Stable rendering path

Every piece is rendered as:

`IPM v0.2 -> deterministic MIDI -> FluidSynth -> FluidR3_GM.sf2 -> 44.1 kHz / stereo / 16-bit PCM -> fixed peak normalisation`

Renderer controls:

- MIDI program: `0` for all three lanes;
- FluidSynth chorus: off;
- FluidSynth reverb: off;
- one-second fixed tail after the 16-bar form;
- peak normalisation: `-1.5 dBFS` per complete piece.

For every piece the gate renders the same MIDI twice and requires the fitted raw PCM bytes to be identical. The manifest records the FluidSynth version, soundfont SHA-256, MIDI SHA-256, trace SHA-256, raw PCM SHA-256, final WAV SHA-256 and final PCM SHA-256.

## Listening rule

Listen to all eight complete WAVs. For each one record exactly:

- `SHOW`, or
- `FAIL` plus failure class, approximate time and short note.

Failure classes:

- `FORM` — the piece does not feel complete or structurally reaches a bad collapse/end;
- `MUSICAL` — the generated musical behaviour is not presentable as current IPM;
- `RENDER` — silence, clipping, stuck notes, broken audio or another production defect;
- `OTHER` — anything material not covered above.

The decision question is:

> Would I willingly send this exact WAV to a curious person as an example of current IPM, without explaining that it is broken?

This is not a favourite-song test. A piece can be unusual or less preferred and still be `SHOW`.

## Pass rule

**PASS = 8 SHOW / 0 FAIL.**

One failure keeps the Working Product Gate closed.

After a failure:

1. preserve the failed WAV, MIDI, trace and review record unchanged;
2. diagnose the failure class across the architecture;
3. make only a general instrument/rendering change justified by that diagnosis;
4. rerun regression on the failed v1 material;
5. use a new gate version with a newly derived, previously unheard seed set for the next final product decision.

Do not tune a single seed after hearing it and then count that repaired seed as a pass.

## External boundary

Passing this gate means only: **the current IPM product is internally presentable and repeatable enough to justify reconsidering listener testing.**

It does not itself authorise recruitment, external contact, data collection, PR #24 merge, or publication of study materials.

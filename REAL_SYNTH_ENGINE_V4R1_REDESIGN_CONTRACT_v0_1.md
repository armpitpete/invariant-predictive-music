# RealSynthEngine v4R1 — Redesign and Acceptance Contract v0.1

Status: **FROZEN BEFORE v4R1 IMPLEMENTATION OR NEW AUDITION**

Failure-analysis parent: `REAL_SYNTH_ENGINE_V4R1_FAILURE_ANALYSIS_v0_1.md`
Historical failed v4 result: `3d247ef5696140b2b8f69764869fbb81e4aeb130`

## 1. Purpose

v4R1 exists only because v4 Gate D failed.

The redesign claim is narrower than “make the synth sound better”:

> v4R1 must make musician-facing controls demonstrably effective and semantically correct before those controls are used as the substrate for musical-time evolution.

The composition boundary remains unchanged: synthesis may transform the sound of written events but may not become a hidden composition engine.

## 2. Historical evidence retained, not erased

The following v4 evidence remains historical fact:

- Gate A PASS;
- Gate B PASS;
- Gate C PASS;
- Gate D FAIL (`EVOLUTION`), owner observation “Both are detuned bells.”

v4R1 must not rewrite or replace those records.

Because v4R1 changes control/evolution semantics, v4 A/B/C evidence may be used as provenance and regression anchors but is **not automatically sufficient for v4R1 promotion**.

## 3. Frozen architecture invariants retained from v4

v4R1 retains:

- one stateful block-processing engine for offline and realtime hosts;
- deterministic reset/replay;
- written-event immutability;
- VA, 4-op FM and modal/resonator synthesis families;
- the eight musician-facing macro names:
  `BRIGHTNESS`, `BODY`, `MOTION`, `ATTACK`, `CHARACTER`, `DRIVE`, `WIDTH`, `SPACE`;
- patch/bank data rather than source-code-per-preset design;
- no synthesis feedback into IPM/A5 composition selection;
- no network dependency at synthesis time;
- no post-audition parameter tuning inside the accepted version.

## 4. Required v4R1 architecture corrections

### 4.1 Explicit note-evolution timebase

The hidden v4 convention `clip(note_age_seconds, 0, 1)` is removed.

Each patch must declare an explicit realtime-safe `note_evolution_seconds` horizon in the range `0.05..30.0` seconds.

For a live voice:

`note_evolution_position = clip(note_age_seconds / note_evolution_seconds, 0, 1)`

This position does not require knowing the future note-off time and therefore works in both realtime and offline hosts.

`note_age` remains available separately as a modulation source.

### 4.2 Explicit phrase/piece authority

The host remains authoritative for phrase and piece position.

For acceptance fixtures:

- phrase boundaries must be declared before rendering;
- phrase position is continuous `0..1` within the declared phrase and resets only at the declared boundary;
- piece position is monotonic `0..1` over the declared written piece span;
- the synth may not infer phrase boundaries or form from pitch content.

### 4.3 Continuous semantic macro authority

A macro used by musical-time evolution must affect currently sounding voices through a continuous DSP path where that semantic meaning requires continuous change.

Patch fields that imply continuous sensitivity must not be sampled only at note start unless their schema explicitly says `new_notes_only`.

In particular, modal per-mode brightness/complexity behaviour used for v4R1 acceptance must be continuously driven or explicitly excluded from the macro claim.

### 4.4 Semantic correctness is part of implementation

It is not sufficient for a macro merely to change audio.

Increasing:

- `BRIGHTNESS` must move toward greater high-frequency/modal-brightness content;
- `BODY` must increase fundamental/low/resonant weight;
- `MOTION` must increase audible internal modulation/movement;
- `ATTACK` must move toward a faster/sharper articulation;
- `CHARACTER` must increase spectral/inharmonic/timbral complexity rather than merely lengthening decay;
- `DRIVE` must increase nonlinearity/saturation;
- `WIDTH` must increase stereo width;
- `SPACE` must increase ambience/effect depth.

Every reference patch must have explicit data mappings sufficient to support the semantics it claims.

### 4.5 Evolution may coordinate multiple controls

A musical evolution state may drive multiple macro curves simultaneously.

For the v4R1 evolution acceptance fixture, the EVOLVING patch must exercise at least three independent perceptual dimensions across the complete note/phrase/piece design, with at least:

- one nonzero note-scope curve;
- two nonzero phrase-scope curves;
- three nonzero piece-scope curves.

At least one target must concern timbre (`BRIGHTNESS`, `BODY`, or `CHARACTER`), one internal movement/articulation (`MOTION` or `ATTACK`), and one spatial dimension (`WIDTH` or `SPACE`).

This is deliberately broader than failed v4 Gate D's one-target-per-scope fixture, but still may not alter written pitch, onset, duration or velocity.

## 5. Acceptance-order correction

v4R1 human gates run in this order:

1. **R-A — architecture/delta conformance**;
2. **R-B — technical/state regression**;
3. **R-C — synthesis-family regression**;
4. **R-D — macro/control authority**;
5. **R-E — musical evolution**;
6. **R-F — full-machine sound**;
7. **R-G — interaction**;
8. **performance envelope**.

The crucial correction is that **R-D precedes R-E**.

## 6. Global anti-tuning rule

Before the first v4R1 human audition, all of the following must be frozen together at one exact implementation head:

- v4R1 source;
- patch schema;
- reference VA/FM/MODAL patches;
- all eight macro mappings;
- the R-D control fixtures;
- the R-E STATIC/EVOLVING fixture and all evolution curves;
- acceptance scripts/tests;
- written event ledgers;
- randomisation/blinding mappings where used.

Human feedback from R-D may determine PASS/FAIL only. It may not be used to retune R-E because R-E is already frozen.

A human failure in any gate ends that v4R1 acceptance sequence.

## 7. R-A — architecture/delta conformance

Static tests/review must prove:

1. the original composition boundary remains intact;
2. v4R1 still uses one stateful engine for realtime/offline paths;
3. `note_evolution_seconds` is explicit patch data and validated;
4. note evolution uses the explicit horizon rather than a hidden one-second constant;
5. phrase/piece positions remain host-authoritative;
6. macro semantics have continuous supported DSP paths where required;
7. evolution can coordinate multiple curves without mutating written events;
8. no A5/composition-selection feedback path exists.

**PASS:** all eight at one exact commit.

## 8. R-B — technical/state regression

Re-run the v4 stateful technical properties affected by the delta, including:

- deterministic reset/replay;
- block continuity;
- note lifecycle;
- control ramping;
- patch/bank round-trip;
- event-ledger immutability;
- gain/master invariants.

Additionally prove:

- note-evolution position reaches the same deterministic values at block sizes 64/128/256/512;
- phrase/piece transport changes do not reschedule note events;
- continuous macro/evolution changes contain no NaN/Inf or state discontinuity beyond frozen tolerances.

## 9. R-C — synthesis-family regression

Use the same historical Gate C written Tune ledger unless implementation evidence makes it invalid.

The three frozen v4R1 family patches must still answer:

> Do these sound like three genuinely different instruments whose identities come from three different synthesis families, rather than three presets of essentially the same voice?

Allowed: `PASS | FAIL`.

R-C must PASS before macro audition.

## 10. R-D — macro/control authority gate

This gate is now a prerequisite for musical evolution.

### Fixture

For one frozen representative patch from each family, each macro is rendered/captured at:

- `0.15`;
- `0.50`;
- `0.85`;

All other macros remain at `0.50`; written material is identical.

### Mechanical direction requirements

Use frozen diagnostics appropriate to each semantic direction:

- BRIGHTNESS: spectral centroid/high-band measure rises;
- BODY: fundamental/low-band/resonant weight rises;
- MOTION: modulation/spectral-flux measure rises;
- ATTACK: attack-time-to-threshold falls;
- CHARACTER: frozen spectral/inharmonic complexity measure rises;
- DRIVE: harmonic/nonlinear distortion measure rises;
- WIDTH: stereo side/mid measure rises;
- SPACE: late/early or wet/dry measure rises.

The exact formulas and thresholds must be frozen before output values are inspected.

### Human question

For each macro:

> Does this control make a clearly perceptible and musically useful change in the intended direction without destroying the patch identity?

Allowed: `PASS | PARTIAL | FAIL`.

**R-D PASS:**

- no macro FAIL;
- at least 6/8 PASS;
- at most 2/8 PARTIAL;
- all mechanical semantic-direction requirements PASS;
- every macro used by R-E must individually receive human PASS, not PARTIAL.

## 11. R-E — musical evolution gate

Only after R-D passes may the frozen evolution pair be heard.

### Fixture

Use the same frozen plain Tune ledger used by failed v4 Gate D unless the contract is superseded before implementation.

Two conditions through the same frozen v4R1 modal or hybrid patch:

- `STATIC` — all musical-time evolution disabled at the neutral state;
- `EVOLVING` — the pre-frozen note/phrase/piece multi-curve evolution design active.

Everything else is identical.

### Mechanical requirements

Before listening prove:

- identical written-event hashes;
- identical transport stream;
- identical patch data except the evolution field/state;
- no host macro-control events used as manual automation;
- no per-piece hand edits;
- note, phrase and piece curves all traverse their declared positions;
- every evolution target already passed R-D;
- EVOLVING differs numerically from STATIC over multiple predeclared temporal windows rather than only at one transient or endpoint;
- automation ledger exported and hashed.

### Human questions

1. **Can you hear coherent sonic development over time in EVOLVING that is absent or materially weaker in STATIC?**
2. **Does that development preserve recognition of the same written musical material rather than sounding like a hidden replacement composition?**

Allowed each: `PASS | FAIL`.

**R-E PASS:** both PASS.

A FAIL is a v4R1 failure. Do not strengthen curves and rerun the same version.

## 12. R-F / R-G / performance

If R-E passes, continue with the original v4 full-machine sound, interaction and realtime-performance claims, updated only where required by the frozen v4R1 architecture delta.

No final promotion occurs unless every v4R1 gate passes.

## 13. Immediate implementation gate

The next implementation work is **not** to recreate Gate D audio.

It is to implement and mechanically verify the v4R1 architecture delta against this contract, beginning with:

1. explicit note-evolution horizon;
2. continuous semantic macro authority;
3. corrected modal/macro behaviour;
4. deterministic multi-curve evolution support;
5. R-D-before-R-E acceptance harnesses.

No human audition occurs until that complete package is frozen.

# RealSynthEngine v4R1 — Redesign and Acceptance Contract v0.2

Status: **FROZEN BEFORE v4R1 IMPLEMENTATION OR NEW AUDITION**

Supersedes: `REAL_SYNTH_ENGINE_V4R1_REDESIGN_CONTRACT_v0_1.md`
Hostile review: `REAL_SYNTH_ENGINE_V4R1_CONTRACT_HOSTILE_REVIEW_v0_1.md`
Failure analysis: `REAL_SYNTH_ENGINE_V4R1_FAILURE_ANALYSIS_v0_1.md`
Historical failed v4 result: `3d247ef5696140b2b8f69764869fbb81e4aeb130`

## 1. Purpose

v4R1 exists because v4 Gate D failed.

Its governing claim is:

> musician-facing controls must have demonstrable semantic and perceptual authority before those controls can be used as the substrate for musical-time evolution.

The redesign does not assume that one root cause has already been proven. It is constructed to eliminate the ambiguities exposed by failed Gate D.

## 2. Historical evidence remains intact

Historical v4 result:

- Gate A PASS;
- Gate B PASS;
- Gate C PASS;
- Gate D FAIL (`EVOLUTION`);
- owner observation: “Both are detuned bells.”

These records remain unchanged. v4R1 does not overwrite them.

## 3. Retained architecture invariants

v4R1 retains:

- one stateful block engine used by realtime and offline hosts;
- deterministic reset/replay;
- immutable written pitch/onset/duration/velocity event ledger;
- VA, 4-op FM and modal/resonator families;
- the eight macro names `BRIGHTNESS`, `BODY`, `MOTION`, `ATTACK`, `CHARACTER`, `DRIVE`, `WIDTH`, `SPACE`;
- data-defined patches/banks;
- no synthesis feedback into IPM/A5 composition selection;
- no network service at synthesis time;
- no post-audition tuning inside the accepted version.

## 4. Required architecture corrections

### 4.1 Explicit realtime-safe note evolution horizon

The hidden v4 convention `clip(note_age_seconds, 0, 1)` is removed.

Each patch declares `note_evolution_seconds` in `0.05..30.0` seconds.

`note_evolution_position = clip(note_age_seconds / note_evolution_seconds, 0, 1)`

This works without knowing the future note-off time and is therefore identical in concept for live and offline hosts.

`note_age` remains separately available as a modulation source.

### 4.2 Explicit phrase/piece authority

The host supplies phrase and piece position.

Acceptance fixtures freeze phrase boundaries before rendering. Phrase position resets only at declared phrase boundaries. Piece position is monotonic across the declared written piece span.

The synth may not infer form from pitches or change written events.

### 4.3 Macro application classes

Macros are classified by legitimate temporal semantics.

**Continuous where the patch claims continuous control:**

- BRIGHTNESS
- BODY
- MOTION
- CHARACTER
- DRIVE
- WIDTH
- SPACE

Those controls must affect currently sounding voices through continuous DSP paths wherever their patch mapping claims such control.

**Event/retrigger boundary:**

- ATTACK

ATTACK may determine the articulation of newly started or retriggered notes. It need not and must not retroactively rewrite an attack stage that has already occurred.

Phrase/piece evolution may target ATTACK by changing the articulation of subsequent written notes.

### 4.4 Semantic correctness

A macro does not pass merely because its bytes or samples change.

Increasing:

- BRIGHTNESS → greater high-frequency/modal-brightness content;
- BODY → greater fundamental/low/resonant weight;
- MOTION → greater audible internal modulation/movement;
- ATTACK → faster/sharper articulation for new/retriggered notes;
- CHARACTER → greater spectral/inharmonic/timbral complexity, not merely longer decay;
- DRIVE → greater nonlinearity/saturation;
- WIDTH → greater stereo width;
- SPACE → greater ambience/effect depth.

Patch data that declares continuous sensitivity must either be consumed continuously or explicitly declare a `new_notes_only` policy. Silent note-start-only sampling may not masquerade as continuous control.

### 4.5 Multi-dimensional evolution without arbitrary curve counts

The v4R1 evolution fixture must contain:

- at least one nonzero note-scope curve;
- at least one nonzero phrase-scope curve;
- at least one nonzero piece-scope curve;
- at least three independent perceptual dimensions across the complete evolution design.

The complete design must include at least:

- one timbral dimension: BRIGHTNESS, BODY or CHARACTER;
- one movement/articulation dimension: MOTION or ATTACK;
- one spatial dimension: WIDTH or SPACE.

There is no fixed requirement for two phrase curves or three piece curves. Curve count is not used as a proxy for musical effectiveness.

Every macro targeted by the evolution fixture must have received full R-D human `PASS` before R-E is judged.

## 5. Pre-implementation diagnostics specification gate

Before v4R1 synthesis source is changed, freeze a separate diagnostics specification defining for every macro:

1. the primary mechanical semantic metric;
2. the low/mid/high fixture values;
3. direction rule;
4. **minimum low-to-high effect-size threshold**;
5. replay/noise/tolerance handling;
6. applicability across VA/FM/MODAL families.

The thresholds must be frozen before any v4R1 implementation output is inspected.

This prevents a mathematically nonzero but perceptually negligible control from passing the mechanical gate.

## 6. Acceptance order

Human gates run:

1. R-A — full architecture conformance plus v4R1 delta;
2. R-B — complete v4 Gate B technical suite plus v4R1 additions;
3. R-C — synthesis-family regression;
4. R-D — macro/control authority;
5. R-E — musical evolution;
6. R-F — full-machine sound;
7. R-G — interaction;
8. performance envelope.

**R-D must pass before R-E is heard.**

## 7. Global freeze before first v4R1 human audition

Before any v4R1 human audition, freeze together at one exact head:

- all v4R1 source;
- schema and migrations;
- VA/FM/MODAL reference patches;
- all eight macro mappings;
- note-evolution horizons;
- R-C family fixture;
- R-D control fixtures;
- R-E STATIC/EVOLVING patch and all curves;
- written event ledgers;
- diagnostic code and thresholds;
- acceptance harnesses;
- blind/random mappings where used.

Human R-C or R-D feedback may only produce a PASS/FAIL/PARTIAL record. It may not be used to alter already-frozen later fixtures.

## 8. R-A — complete architecture conformance

Re-run the complete original v4 Gate A architecture assertions at the v4R1 exact head, then additionally prove:

1. explicit `note_evolution_seconds` exists and validates;
2. note evolution uses that field rather than a hidden constant;
3. phrase/piece remain host-authoritative;
4. macro application classes are explicit;
5. continuous semantic mappings operate continuously where claimed;
6. evolution can coordinate multiple curves without changing written events.

R-A PASS requires all original and all v4R1 assertions.

## 9. R-B — complete stateful technical regression

Re-run **all v4 B1–B8 tests** at the exact v4R1 implementation head.

Add tests proving:

- note-evolution position is deterministic across block sizes 64/128/256/512;
- changing `note_evolution_seconds` changes only the evolution timebase, not note scheduling;
- phrase/piece transport does not alter written note timing;
- continuous macro/evolution paths remain finite and state-continuous;
- ATTACK changes affect the next/retriggered attack according to the frozen policy without rewriting a completed attack;
- patch/bank round-trip preserves the new evolution-horizon/application-policy data.

## 10. R-C — synthesis-family regression

Use one predeclared frozen Tune ledger and three frozen v4R1 family patches.

Human question:

> Do these sound like three genuinely different instruments whose identities come from three different synthesis families, rather than three presets of essentially the same voice?

Allowed: `PASS | FAIL`.

R-C must PASS before R-D is heard.

## 11. R-D — macro/control authority

### Fixture

For one frozen representative patch from each family, each macro is tested at:

- 0.15
- 0.50
- 0.85

All other macros remain 0.50 and the written material is identical.

### Mechanical PASS prerequisites

For every macro:

- the diagnostic direction matches its frozen semantic direction;
- the low-to-high effect reaches the separately frozen minimum effect-size threshold;
- replay is deterministic;
- no unrelated written event changes;
- no NaN/Inf or forbidden discontinuity.

### Human question

For each macro:

> Does this control make a clearly perceptible and musically useful change in the intended direction without destroying the patch identity?

Allowed: `PASS | PARTIAL | FAIL`.

R-D PASS requires:

- no macro FAIL;
- at least 6/8 PASS;
- at most 2/8 PARTIAL;
- every mechanical threshold PASS;
- every macro used by R-E receives human PASS, not PARTIAL.

## 12. R-E — musical evolution

Only after R-D PASS may the already-frozen evolution comparison be heard.

### Fixture

Use the same frozen plain Tune ledger as failed v4 Gate D unless superseded by this contract before implementation begins.

Two conditions through the same frozen modal or hybrid v4R1 patch:

- STATIC — evolution disabled at the neutral state;
- EVOLVING — frozen note/phrase/piece curves active.

Everything else is identical.

### Mechanical prerequisites

Before listening prove:

- written event hashes identical;
- transport streams identical;
- condition patch data differs only in evolution enablement/data;
- no host hand-automation or per-piece manual changes;
- note, phrase and piece curves all traverse their declared timebases;
- all evolution targets have full R-D PASS;
- EVOLVING differs from STATIC in multiple predeclared temporal windows, not only one transient/end state;
- automation ledger is exported and hashed.

### Human questions

1. Can you hear coherent sonic development over time in EVOLVING that is absent or materially weaker in STATIC?
2. Does that development preserve recognition of the same written musical material rather than sounding like a hidden replacement composition?

Allowed each: `PASS | FAIL`.

R-E PASS requires both PASS.

A failure ends v4R1. Do not strengthen curves and rerun the same version.

## 13. R-F / R-G / performance

If R-E passes, continue the original v4 full-machine sound, interaction and performance claims against the exact frozen v4R1 head.

No final promotion occurs unless every v4R1 gate passes.

## 14. Immediate next gate

Before implementation, freeze `REAL_SYNTH_ENGINE_V4R1_CONTROL_DIAGNOSTICS_v0_1.md` with the exact semantic metrics and minimum effect-size thresholds.

Only after that document is frozen may v4R1 synthesis source change.

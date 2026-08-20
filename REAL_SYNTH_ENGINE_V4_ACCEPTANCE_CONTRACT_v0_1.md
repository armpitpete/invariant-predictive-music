# RealSynthEngine v4 — Acceptance Contract v0.1

Status: **FROZEN BEFORE IMPLEMENTATION OR AUDITION**

Architecture parent: `REAL_SYNTH_ENGINE_V4_ARCHITECTURE_v0_1.md`
Repository parent head: `b2e36e5294a1fbbdc664607df9c1005343561ca3`

## 1. Purpose of acceptance

The acceptance programme tests one claim:

> RealSynthEngine v4 is a genuine stateful musical instrument engine, not merely a more sophisticated offline WAV renderer.

No single technical test or attractive preset can establish this claim. v4 passes only by clearing the gates below in order.

## 2. Global rules

Across all gates:

- written composition events are frozen before synthesis evidence is opened;
- synthesis may not add/remove/reorder/repitch/reschedule composition events;
- v4 implementation, reference patches and acceptance harnesses are frozen before human audition;
- no post-audition parameter tuning is permitted within v4;
- a failed audible gate is a v4 failure, not permission to select a more flattering musical seed;
- v2/v3 evidence remains preserved;
- A5 composition scoring remains outside the synth acceptance lane;
- no network service may be used at synthesis time.

## 3. Gate A — architecture conformance

Before audio acceptance, static review must confirm that implementation provides the frozen v4 modules and does not substitute a second offline-only synthesis path.

Mandatory evidence:

1. one stateful engine owns voice state across blocks;
2. offline rendering drives that same engine with scheduled events;
3. all three synthesis families exist: VA, 4-op FM, modal/resonator;
4. eight required macros exist with frozen names;
5. note/phrase/piece evolution is represented as data;
6. no composition-selection or A5 feedback path exists in the synth;
7. patch/bank serialisation and v3 migration exist.

**PASS rule:** all seven assertions proven by code/tests at one exact commit.

Any miss is FAIL/BLOCKED; no audible audition occurs.

## 4. Gate B — stateful engine technical gate

### B1. Deterministic reset/replay

For each reference patch family:

- reset engine;
- replay the exact same scheduled transport/note/control stream twice;
- process using block size `128`;
- quantise using the frozen offline host.

**PASS:** byte-identical WAVs for each replay.

### B2. Note lifecycle

Synthetic note-on/note-off fixtures must prove:

- note-on begins a voice at the scheduled sample;
- note-off enters release rather than terminating the waveform immediately unless release=0;
- release continues across later blocks;
- `all_notes_off` follows the documented release/kill policy;
- reset clears all prior voice/filter/LFO/effect state.

**PASS:** exact assertions succeed with no sample-offset error greater than one sample.

### B3. Block continuity

Render the same deterministic event/control stream at block sizes `64`, `128`, `256`, `512`.

Cross-block-size outputs are **not required to be byte-identical**, because deterministic scheduling and floating-point accumulation order may differ. They must be perceptually/numerically equivalent under this frozen tolerance:

- sample alignment identical;
- same frame count;
- peak absolute sample difference after float rendering <= `2e-5`;
- RMS difference <= `2e-6`;
- no discontinuity spike at block boundaries exceeding `6 dB` above the local 5 ms derivative RMS unless a written note/control event occurs at that boundary.

All tolerance computation is mechanical before audition.

### B4. Voice allocation/stealing

Construct an event stream exceeding patch polyphony.

**PASS:** allocation and stealing exactly follow the frozen rule:

1. lowest-index idle voice;
2. released lowest-amplitude -> oldest -> lowest index;
3. held lowest-amplitude -> oldest -> lowest index.

The logged `allocation_level` must equal `amp_envelope_level * (0.25 + 0.75 * velocity_unit)` clipped to `0..1`; selection must be based on that value rather than waveform peaks. The 5 ms steal de-click must execute, output remain finite, and replay remain deterministic.

### B5. Mono/legato/portamento

For `mono_retrigger` and `mono_legato` fixtures:

**PASS:**

- only one active voice exists;
- retrigger policy follows patch data;
- portamento begins/ends at scheduled notes;
- pitch glide does not add a new composition event.

### B6. Parameter automation

For each of the eight macros, schedule at least three within-note value changes.

**PASS:**

- changes occur at scheduled sample offsets;
- output remains finite;
- no NaN/Inf;
- the engine applies the frozen 5 ms linear control ramp to every continuous macro change;
- discrete patch choices are unchanged for active voices and apply to new notes only.

### B7. Patch/bank integrity

**PASS:**

- v4 patch JSON round-trips semantically;
- invalid ranges fail validation;
- v3-to-v4 migration is deterministic;
- migrated patches load/render successfully;
- changing patch data never mutates the written event ledger.

### B8. Gain/master integrity

**PASS:**

- no whole-piece peak/loudness normalisation exists;
- identical local phrase rendered inside a quiet vs loud surrounding piece retains the same pre-master local gain within `1e-9` before limiter engagement;
- limiter prevents PCM overflow;
- non-limiting material is not globally rescaled because of later unrelated peaks.

**Gate B overall PASS:** B1-B8 all pass at one exact commit.

## 5. Gate C — synthesis-family separation

This gate establishes that v4 contains genuinely different synthesis mechanisms rather than cosmetic variants of one topology.

### Frozen fixture

Use exactly one predeclared Tune event ledger for all three reference families. The ledger must be frozen and hashed before any of the three renders are heard.

Exactly three Tune renders:

- `VA`
- `FM`
- `MODAL`

All use:

- identical written events;
- identical tempo/form;
- identical master stage;
- the same v4 engine commit;
- frozen reference patches.

No effects-heavy rescue is permitted: for this gate, each reference patch must have `SPACE <= 0.20` and chorus/delay wet <= `0.10` so family identity cannot be manufactured mainly by effects.

### Human question

> **Do these sound like three genuinely different instruments whose identities come from three different synthesis families, rather than three presets of essentially the same voice?**

Allowed judgments: `PASS | FAIL`.

**PASS:** owner judges PASS after blind/randomised audition order.

A FAIL ends family-acceptance work for v4. Do not retune reference patches inside v4 after hearing the failure.

## 6. Gate D — musical evolution gate

This gate tests the property previously demonstrated by the v2 evolving-field design, now as a generic v4 facility.

### Fixture

Use one frozen plain/simple Tune ledger.

Render exactly two conditions through the same frozen MODAL or hybrid reference patch:

- **STATIC** — note/phrase/piece evolution curves disabled at neutral values;
- **EVOLVING** — the patch's frozen note/phrase/piece evolution curves active.

Everything else is identical.

### Mechanical requirements

Before listening:

- written event ledgers must hash identically;
- macro/evolution automation ledger must be exported;
- EVOLVING must contain at least one nonzero change at each scope: note, phrase, piece;
- STATIC must contain none;
- neither render may invoke per-piece manual changes.

### Human questions

1. **Can you hear coherent sonic development over time in EVOLVING that is absent or materially weaker in STATIC?**
2. **Does that development preserve recognition of the same written musical material rather than sounding like a hidden replacement composition?**

Allowed judgments for each: `PASS | FAIL`.

**Gate D PASS:** both questions PASS.

## 7. Gate E — eight-macro instrument-control gate

This is the first direct test that v4 behaves like a steerable instrument rather than a static preset renderer.

### Fixture

Select one frozen representative patch from each family. For each macro, render or live-capture a fixed held chord/note phrase at three values:

- `0.15`
- `0.50`
- `0.85`

All other macros remain at `0.50`.

### Mechanical direction checks

Where measurable, direction must match semantics:

- BRIGHTNESS: spectral centroid median at 0.85 > 0.15 in >=2/3 family patches;
- BODY: low-band (<=250 Hz or first two harmonic/modal groups as applicable) energy share at 0.85 > 0.15 in >=2/3;
- MOTION: modulation/spectral-flux measure at 0.85 > 0.15 in >=2/3;
- ATTACK: attack-time-to-90%-peak at 0.85 < 0.15 in >=2/3;
- CHARACTER: patch-defined complexity diagnostic increases in >=2/3;
- DRIVE: nonlinear/harmonic-distortion diagnostic increases in >=2/3;
- WIDTH: stereo side/mid energy ratio at 0.85 > 0.15 in >=2/3;
- SPACE: late/early or wet/dry energy ratio at 0.85 > 0.15 in >=2/3.

Diagnostics and exact computation code must be frozen before values are opened.

### Human question

For each macro:

> **Does this control make a clearly perceptible and musically useful change in the intended direction without destroying the patch identity?**

Allowed: `PASS | PARTIAL | FAIL`.

**Gate E PASS:**

- no macro receives FAIL;
- at least 6/8 receive PASS;
- at most 2 receive PARTIAL;
- all eight mechanical direction checks pass.

## 8. Gate F — full-machine sound gate

Only after A-E pass may v4 be judged as the internal sound engine for the IPM Machine.

### Frozen fixture

Use one predeclared machine state and exact written TUNE/BASS/RHYTHM ledger.

Render/listen to:

1. Tune solo;
2. Bass solo;
3. Rhythm solo;
4. full mix.

No seed change, composition change, per-piece patch selection, EQ or mastering adjustment after audition begins.

### Human acceptance questions

For each solo:

> **Does this read as an intentional, musically usable instrument voice rather than a placeholder/test sound?**

For full mix:

> **Do the three voices form a coherent, comfortable and musically useful sonic system with enough depth and separation to keep working on the piece?**

Allowed judgments: `PASS | FAIL`.

**Gate F PASS:** all four PASS.

## 9. Gate G — instrument interaction gate

After sound acceptance, test v4 through the actual Machine or a minimal equivalent control surface.

Minimum interactive controls:

- note start/stop from a deterministic host or MIDI-like event source;
- preset selection;
- eight macros;
- panic/all-notes-off;
- play/stop transport for existing IPM material.

### Interaction requirements

- audible response begins without waiting for whole-piece rendering;
- held/released notes behave continuously;
- macro movement affects currently sounding voices where destination semantics allow;
- switching preset while notes are sounding follows one frozen policy: **new-notes-only** for v4 acceptance;
- panic returns engine to silence and clears active voices deterministically.

### Human question

> **Does this now behave like an instrument I can play/steer, rather than a system that merely exports audio files?**

Allowed: `PASS | FAIL`.

**Gate G PASS:** PASS.

## 10. Performance envelope

Realtime-grade performance is not the sole scientific goal, but v4 cannot claim instrument status if its architecture is unusable interactively.

Reference performance test environment must be frozen when implementation is ready.

Minimum v4 target at 44.1 kHz / 128-frame blocks:

- 16 active polyphonic voices using a representative VA patch: render factor <= 1.0 realtime;
- 8 active voices using representative FM patch: <= 1.0 realtime;
- 8 active voices using representative MODAL patch: <= 1.0 realtime;
- no missed/overrun block in a continuous 60-second deterministic benchmark.

If the reference environment cannot meet these targets, Gate G is BLOCKED even if offline rendering works.

## 11. Final promotion rule

RealSynthEngine v4 may replace the previous Machine playback/finish renderer only if:

- Gate A PASS;
- Gate B PASS;
- Gate C PASS;
- Gate D PASS;
- Gate E PASS;
- Gate F PASS;
- Gate G PASS;
- performance envelope PASS;
- exact implementation commit and all acceptance artifacts are frozen.

No partial gate may be overridden by an attractive final WAV.

## 12. Failure interpretation

A failure must be classified before any redesign:

- `ARCHITECTURE` — required module/state boundary absent or wrong;
- `TECHNICAL` — implementation violates deterministic/state/numerical contract;
- `FAMILY_RANGE` — synthesis families do not sound materially distinct;
- `EVOLUTION` — generic evolution does not create coherent musical development;
- `CONTROL` — macro surface is weak/misleading/unusable;
- `SOUND` — voices/full mix are not musically acceptable;
- `INTERACTION` — technically functioning engine does not behave like an instrument in use;
- `PERFORMANCE` — realtime processing target not met.

The failure category determines the next governed version. Do not repair a failed human gate by silently changing only the audition patch and rerunning the same v4 acceptance.

## 13. Stop rule

No v4 implementation may begin until this acceptance contract and the parent architecture are hashed and frozen together.

Once implementation begins, the following are locked for v4 acceptance:

- engine purpose/boundary;
- core event/block semantics;
- voice allocation rule;
- three synthesis families;
- eight macro names/semantics;
- FM algorithm set;
- evolution scopes;
- gate order and PASS rules.

A material change to any of these requires a newly versioned architecture/contract before further evidence is collected.

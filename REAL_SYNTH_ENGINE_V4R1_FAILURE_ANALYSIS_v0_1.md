# RealSynthEngine v4R1 — Gate D Failure Analysis v0.1

Status: **FROZEN BEFORE v4R1 IMPLEMENTATION OR NEW AUDITION**

Failed v4 result parent: `3d247ef5696140b2b8f69764869fbb81e4aeb130`
Failed v4 implementation: `9ca6e720f9a90d917b1420b794d76a07408cd7bb`
Failed Gate D pre-audition head: `974eb27f762beb09d1d8693b059a150ff83ab963`

## 1. What Gate D actually disproved

Gate D established one human fact:

> Under the frozen Gate D fixture, the v4 EVOLVING condition did **not** produce coherent sonic development that was audibly stronger than STATIC.

Owner observation before the verdict:

> “Both are detuned bells.”

Q1 was therefore `FAIL`. Q2 was not recorded because the gate had already failed.

This is a real v4 failure and must not be repaired by retuning the same patch, choosing another seed, or substituting another Gate D audition fixture.

## 2. What Gate D did not disprove

The failure does **not** establish that:

- the evolution data path was inactive;
- STATIC and EVOLVING were identical audio;
- phrase/piece transport failed mechanically;
- the written Tune changed;
- the v2 evolving-field result was false;
- all three v4 synthesis families fail;
- a generic evolution system is impossible.

Mechanical evidence already proved that STATIC and EVOLVING used the same written event ledger, differed only in the `evolution` field, and rendered to different WAV hashes.

## 3. Important acceptance-order defect exposed by the failure

Original v4 Gate D depended on macro/evolution targets being perceptually effective, but the acceptance sequence placed the eight-macro control gate **after** Gate D.

That means Gate D asked musical evolution to prove itself before the system had established that the controls being evolved had sufficient perceptual authority.

The Gate D failure is therefore valid, but its root cause is underdetermined between:

1. weak or semantically wrong control actuation;
2. weak musical-time semantics;
3. insufficient breadth/depth of the evolution design;
4. a combination of the above.

v4R1 must reverse that dependency: **control authority before evolution audition**.

## 4. Frozen source facts relevant to diagnosis

### 4.1 Note evolution is hard-clamped to a one-second horizon

Current v4 computes note evolution position as:

`clip(voice_age_samples / sample_rate, 0, 1)`

So `note` evolution reaches its final anchor after one second regardless of written duration or patch intent.

The architecture described note position as `0..1`, but did not freeze an explicit realtime-safe horizon model. v4 therefore embedded a hidden one-second interpretation.

### 4.2 Gate D evolved only one macro at each scope

The frozen Gate D curves were:

- note → `CHARACTER`;
- phrase → `BRIGHTNESS`;
- piece → `WIDTH`.

The same Gate C modal patch was used for STATIC and EVOLVING; only the evolution curves differed.

### 4.3 Gate D CHARACTER was not a direct complexity control

In the frozen Gate D modal patch, `CHARACTER` (`macro5`) routed to `modal_decay`.

That changes decay behaviour, but it is not the frozen semantic definition of CHARACTER: increasing spectral/inharmonic/timbral complexity.

Therefore Gate D's note-scope target was not a clean test of CHARACTER semantics.

### 4.4 Modal brightness sensitivity is sampled at note start

The modal mode fields include `brightness_sensitivity`, and voice start uses the then-current BRIGHTNESS value when initial modal amplitudes are created.

Later evolution of BRIGHTNESS does not recompute that per-mode sensitivity term continuously. During the sounding note, BRIGHTNESS still affects other paths such as filter cutoff and the generic modal amplitude factor, but not the full per-mode brightness sensitivity declared by patch data.

This weakens the claim that phrase BRIGHTNESS evolution exercised the intended modal timbre control throughout each note.

### 4.5 v2 used a materially richer evolution design

The previously accepted Evolving Resonant Field v2 used the same plain Tune seed `1693196453` and preserved written events, but its sound development combined:

- a four-anchor piece-scale arc over brightness, motion depth, stereo width and room send;
- phrase brightness offsets;
- deterministic event micro-variation;
- explicit within-note opposing spectral motion;
- slow amplitude drift;
- duration-aware modal decay;
- evolving spatial behaviour.

The v2 owner judgment passed the question of whether the plain material became interesting enough to keep listening.

This does not prove v4R1 should copy v2. It does prove that the failed v4 Gate D tested a much narrower evolution surface than the prior successful design.

## 5. Competing root-cause hypotheses

v4R1 work must distinguish these before implementation is accepted:

### H1 — control-authority failure

The macros used by evolution do not create sufficiently strong, semantically correct or continuously effective changes in the relevant family.

### H2 — time-semantics failure

The evolution clocks are poorly defined for an instrument engine, especially the hidden fixed one-second note horizon and phrase reset behaviour.

### H3 — evolution-orchestration failure

The generic mechanism works mechanically, but one target per scope is too narrow to create coherent musical development comparable to the prior v2 result.

### H4 — patch-specific masking

The modal patch identity is so dominant that the chosen evolution targets alter details without changing the perceived trajectory; this remains possible but cannot be used as permission to retune the failed v4 fixture.

## 6. Redesign rule

No v4R1 synthesis implementation may begin until a new architecture delta and acceptance contract are frozen.

The redesign must:

1. make control semantics and control authority testable before evolution;
2. define musical-time semantics explicitly rather than relying on a hidden one-second note convention;
3. permit coherent multi-parameter evolution while preserving the written composition boundary;
4. preserve the failed v4 Gate D result unchanged as evidence;
5. prohibit parameter selection based on listening to the failed Gate D files.

## 7. Evidence boundary

The failed v4 audition may be used only to establish the failure described above and the owner observation already recorded.

It may not be repeatedly replayed to tune v4R1 parameters.

Any v4R1 human audition must occur only after the v4R1 architecture, implementation, reference patches, fixtures and acceptance harness are independently frozen.

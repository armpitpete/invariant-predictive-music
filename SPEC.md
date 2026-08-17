# Invariant Predictive Music (IPM) — v0.2 Specification

**Status:** active design specification  
**Scope:** deterministic Tune/Bass/Rhythm reference instrument plus falsifiable listening controls  
**Supersedes:** the v0.1 `M → B_R → B_H` implementation architecture. Historical studies remain preserved in the repository.

---

## 1. Central hypothesis

IPM tests this proposition:

> Listeners should tend to prefer moderately surprising musical continuations that preserve learned structural invariants and become strongly justified by what follows over both highly predictable continuations and similarly surprising continuations with weaker structural continuity.

The intended causal chain is:

\[
\text{learnable structure}
\rightarrow
\text{prediction}
\rightarrow
\text{controlled violation}
\rightarrow
\text{invariant continuity}
\rightarrow
\text{retrospective integration}
\]

This is a hypothesis to test, not a definition of musical quality.

---

## 2. Governing laws

These laws sit above numerical weights and style heuristics.

### Law 1 — Prediction is the baseline

> **Prediction is the baseline. Surprise must improve on it.**

At every significant Tune decision, an expected continuation remains available as the control. A surprising continuation may replace it only when its full IPM score is better.

### Law 2 — Tune defines the musical world

> **The Tune establishes the primary predictive and melodic world. Bass and Rhythm are conditional on it.**

Generation order for v0.2 is:

\[
TUNE \rightarrow BASS \rightarrow RHYTHM
\]

Pattern-lock transformations may subsequently re-realise a subsidiary pattern, but they remain accountable to the already accepted musical context.

### Law 3 — Every subsidiary note competes with silence

> **Every sounding Bass or Rhythm note must justify sounding rather than remaining silent.**

For candidate event `x`:

\[
Q(x) > Q(\varnothing)
\]

A lane's activity setting governs whether that lane receives an opportunity to propose material. It never forces a weak proposal to sound.

For a multi-attack Rhythm or locked pattern, a strong average may not conceal a weak individual attack: every sounding attack must clear its silence test.

### Law 4 — Every note must justify the time it occupies

Pitch, onset, duration, gate and rest are musical decisions rather than post-processing decoration. Longer subsidiary durations carry a greater burden against silence.

---

## 3. Instrument architecture

The current instrument has exactly three functional lanes.

### TUNE

Purpose:

- teach melodic and rhythmic vocabulary;
- establish phrase direction;
- carry the prediction/surprise experiment;
- remain the principal perceptual identity.

Reference register at tonic MIDI 60: `C4–B4`.

### BASS

Purpose:

- provide slow structural support;
- reinforce or redirect harmonic interpretation;
- move less frequently than Tune/Rhythm by default;
- remain independently tweakable.

Reference register at tonic MIDI 60: `C2–B2`.

### RHYTHM

Purpose:

- provide short pitched/arpeggiated activity;
- create local pulse, syncopation and recurrence;
- remain subordinate to Tune and compatible with Bass.

Reference register at tonic MIDI 60: `C3–B3`.

Rhythm is pitched; v0.2 does not require drums.

---

## 4. Scale-degree-first pitch model

Musical pitch identity is represented as an abstract scale degree before MIDI projection.

For scale world `W`, degree `d`, and lane `L`:

\[
p = project_W(d,L)
\]

Changing the tonic moves all lanes together while preserving degree relationships.

The default world is Aeolian:

\[
(0,2,3,5,7,8,10)
\]

A lane may never leak outside its tonic-relative register.

---

## 5. Hard timing invariant

Each lane is monophonic with respect to itself:

\[
o_{i+1} \ge o_i+d_i
\]

Self-overlap is a hard rejection.

Different lanes may overlap. Their actual overlap intervals form the polyphonic texture.

---

## 6. Tune decision unit

The v0.2 Tune makes sequential whole-bar decisions.

A candidate bar jointly proposes:

- pitch sequence;
- note count;
- NOTE/REST time budget;
- onset positions;
- durations;
- phrase direction.

The selected structural bar may then receive micro-rhythmic subdivision while preserving the structural time budget.

Accepted history updates the next decision state.

---

## 7. Predictive probability

For each Tune bar, generate a pool of competing complete-bar candidates.

A base musical score estimates local expectation using current-history features such as:

- entry continuity;
- rhythmic continuity;
- recently learned interval vocabulary;
- phrase direction;
- internal variety;
- non-repetition;
- cadence.

Candidate scores are converted to a local probability distribution. The highest-probability candidate is the **Expected** baseline.

This probability model is an explicit design prior. It is not yet an empirically fitted human listener model.

---

## 8. Surprise

For candidate probability `P(x)`:

\[
S(x)=-\log_2P(x)
\]

IPM does not maximise surprise.

Calibrated surprise uses an inverted-U utility:

\[
U(S)=k e S e^{-kS}
\]

so both trivial prediction and extreme unpredictability can score poorly.

---

## 9. Invariants

The current bar-level invariant estimate deliberately ignores absolute pitch and considers recoverable structural relationships including:

- contour direction;
- recently learned interval-size vocabulary;
- attack-count shape;
- rest-density shape.

This allows transformations and transposition to preserve identity without literal repetition.

Invariant scoring remains experimental and replaceable.

---

## 10. Retrospective coherence and necessity

A Tune candidate receives a retrospective-coherence estimate from:

- invariant preservation;
- phrase integration;
- cadence/formal usefulness.

For local probability `P(x)` and retrospective coherence `C_R`:

\[
N(x)=[1-P(x)]C_R
\]

A low-probability event therefore receives credit only when it also integrates strongly.

The Tune trace must record probability, surprise, invariant similarity, retrospective coherence and retrospective necessity.

---

## 11. Expected / Revealing / Exploratory gate

From the Tune candidate pool:

### Expected

Highest local predictive probability.

### Revealing

Lower-probability candidate with strong invariant continuity.

### Exploratory

Lower-probability candidate from a wider invariant region, still structurally legal.

In `ipm` mode, a surprising branch may replace Expected only when its full IPM score exceeds the Expected baseline.

The branch classification and gate outcome must be recorded.

---

## 12. Falsification conditions

The same high-level instrument configuration supports three conditions.

### A — `predictable`

Always selects the Expected Tune baseline.

### B — `ipm`

Allows Revealing/Exploratory continuations to replace Expected only when the IPM gate is passed.

### C — `unstructured-surprise`

Selects a surprising continuation approximately matched to the IPM condition's surprise burden while preferring weaker invariant continuity.

The control should remain musically legal enough that the comparison tests the proposed mechanism rather than obvious corruption.

Listener tests should compare at least:

- preference;
- coherence;
- perceived surprise;
- memorability;
- emotional impact;
- desire to hear again.

---

## 13. Activity is a density governor

`activity` is not a quota and is not a direct musical-quality score.

For Bass and Rhythm it controls the probability that the lane receives a legitimate opportunity to propose material. The mapping is phase-sensitive:

- openings and endings are thinned;
- development and climax are more permissive;
- `activity = 0` gives no opportunities;
- `activity = 1` gives every opportunity.

A supplied random seed makes these opportunity decisions deterministic.

After an opportunity is granted, the proposed material still has to beat silence. Density permission and musical acceptance are therefore separate decisions.

This separation is permanent for v0.2.

---

## 14. Bass controls

Bass exposes five `[0,1]` controls:

- `activity` — frequency of Bass opportunities;
- `sustain` — bias toward longer/shorter structural cells;
- `movement` — static support versus degree movement;
- `pattern_complexity` — simple versus mixed bar partitions;
- `gate` — fraction of an allocated Bass span that actually sounds.

A Bass bar owns a four-beat time budget. Typical available shapes include:

- `4`
- `2+2`
- `1+1+2`
- `2+1+1`
- `1+1+1+1`

These are vocabulary options, not quotas.

For each granted Bass segment opportunity:

1. generate scale/legal candidates;
2. score vertical fit, continuity/movement and structural usefulness;
3. calculate a silence score for the same span;
4. increase the silence burden for longer spans;
5. sound only if the strongest candidate beats silence.

---

## 15. Rhythm controls

Rhythm exposes four `[0,1]` controls:

- `activity` — frequency of Rhythm-bar opportunities;
- `complexity` — breadth of available figure/contour vocabulary;
- `syncopation` — preference within legal rhythmic candidates;
- `gate` — sounding fraction of each short attack.

There is no fixed set of mandatory active bars.

For each bar:

1. the phase-shaped activity governor decides whether Rhythm gets an opportunity;
2. if it does, generate legal short pitched figures;
3. score them against active Tune/Bass context;
4. compare every attack with silence;
5. reject the whole figure if any sounding attack fails;
6. otherwise accept the strongest legal figure.

---

## 16. Pattern memory and locks

A reusable pattern stores:

- relative onset geometry;
- duration geometry;
- relative scale-degree contour.

It does **not** store absolute MIDI pitches.

A pattern may therefore be captured, named, locked and re-realised against a new harmonic anchor while preserving its recognisable geometry.

v0.2 engine-level lock windows are supported for subsidiary BASS and RHYTHM lanes. Tune pattern memory remains a research extension because forcing Tune repetition can bypass the prediction experiment.

A lock is an explicit structural decision and may override normal density opportunities inside its requested window, but it does **not** override Law 3: each re-anchored attack is re-screened against silence. If no anchor makes every attack acceptable, the locked lane remains silent for that application.

Lock state must be explicit and must be released after its configured window.

---

## 17. Vertical compatibility

Simultaneous music is evaluated over real overlap intervals.

The engine retains interval and complete-set sonority priors. These are compositional priors, not universal claims about consonance.

Vertical compatibility must never permit a pitch to escape its scale or lane.

---

## 18. Texture occupancy

Occupancy is a **measurement and governor problem, never a quota-filling problem**.

While Tune is sounding, v0.2 records the shares of:

- `TUNE`
- `TUNE+BASS`
- `TUNE+RHYTHM`
- `TUNE+BASS+RHYTHM`

For the default instrument configuration:

> **Tune alone must be the single most common texture. Three simultaneous parts must remain exceptional rather than the permanent surface.**

This is a regression requirement for the default sound, not a prohibition on deliberately choosing dense user settings.

No weak Bass/Rhythm event may be added merely to hit an occupancy target.

---

## 19. Determinism

A supplied random seed must reproduce the same result for the same implementation and configuration.

All compositional and density-governor stochastic choices use the seeded randomness layer.

Cross-Python-version bit-for-bit RNG identity is not claimed unless separately tested.

---

## 20. Decision trace

The trace is part of the product.

It must contain:

- engine version;
- random seed;
- experiment mode;
- lane controls;
- pattern locks;
- Tune candidate probabilities;
- selected Tune branch;
- surprise;
- invariant score;
- retrospective coherence/necessity;
- Bass/Rhythm opportunity probabilities and outcomes;
- Bass/Rhythm silence scores;
- accepted/rejected events;
- pattern-lock silence margins;
- actual texture occupancy;
- lane/register validation;
- vertical metrics.

A rendered MIDI without its decision trace is incomplete as a research artefact.

---

## 21. Historical studies

Studies #001–#011 are experimental records.

They preserve:

- failed listening controls;
- bugs and corrections;
- controlled musical experiments;
- the path by which Tune/Bass/Rhythm and pattern memory emerged.

They are not the v0.2 production call graph.

The current engine must run without calling any numbered Study module.

---

## 22. Acceptance boundary for v0.2

Required implementation properties:

- [ ] one direct configurable Tune/Bass/Rhythm engine;
- [ ] no runtime ancestry through numbered Studies;
- [ ] scale-degree-first lane projection;
- [ ] deterministic seeded output;
- [ ] explicit Tune predictive baseline;
- [ ] recorded surprise/invariant/retrospective scores;
- [ ] predictable/IPM/unstructured-surprise modes;
- [ ] Bass controls;
- [ ] Rhythm controls;
- [ ] phase-shaped subsidiary density opportunities;
- [ ] subsidiary silence competition after opportunity gating;
- [ ] every sounding Rhythm/locked attack individually beats silence;
- [ ] default Tune-alone texture is the single most common texture;
- [ ] pattern memory and explicit subsidiary lock/unlock;
- [ ] no self-overlap;
- [ ] actual vertical texture scoring;
- [ ] MIDI export;
- [ ] machine-readable trace;
- [ ] Python 3.11 and 3.13 CI.

Musical acceptance remains listening-dependent.

Theory acceptance requires controlled listener evidence and cannot be inferred from passing software tests.

---

## 23. Known research debt

Still not claimed complete:

- empirically fitted listener probabilities;
- formal structural-promise/debt ledger;
- full future-resolution modelling for dissonance;
- universal numerical weights;
- production instrumentation;
- realtime generation;
- GUI/DAW integration;
- drums;
- proof that IPM improves listener preference.

These omissions must remain visible rather than being silently re-described as solved.

---

## 24. Permanent project distinction

Three concepts must remain separate:

1. **Instrument roles:** `TUNE / BASS / RHYTHM`.
2. **Tune prediction branches:** `EXPECTED / REVEALING / EXPLORATORY`.
3. **Experimental conditions:** `predictable / ipm / unstructured-surprise`.

Conflating these layers recreates the architectural confusion v0.2 is intended to remove.

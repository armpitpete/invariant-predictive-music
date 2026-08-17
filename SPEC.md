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

At every significant Tune decision, an expected continuation is retained as the control. A surprising continuation may replace it only when its full IPM score is better.

### Law 2 — Tune defines the musical world

> **The Tune establishes the primary predictive and melodic world. Bass and Rhythm are conditional on it.**

Generation order for v0.2 is:

\[
TUNE \rightarrow BASS \rightarrow RHYTHM
\]

Pattern-lock transformations may subsequently re-realise a subsidiary pattern, but they must remain accountable to the already accepted musical context.

### Law 3 — Every subsidiary event competes with silence

> **Every Bass or Rhythm event must justify sounding rather than remaining silent.**

For a candidate `x`:

\[
Q(x) > Q(\varnothing)
\]

Activity controls may alter the silence threshold, but activity is a governor rather than a quota. Low occupancy never forces a weak event to sound.

### Law 4 — Every note must justify the time it occupies

Pitch, onset, duration, gate and rest are musical decisions rather than post-processing decoration.

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

Changing the tonic moves all lanes together while preserving the degree relationship.

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

Different lanes may overlap. Their actual overlap intervals form the vertical texture.

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

The candidate scores are converted to a local probability distribution.

The highest-probability candidate is the **Expected** baseline.

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

A candidate receives a retrospective-coherence estimate from:

- invariant preservation;
- phrase integration;
- cadence/formal usefulness.

For local probability `P(x)` and retrospective coherence `C_R`:

\[
N(x)=[1-P(x)]C_R
\]

A low-probability event receives credit only when it also integrates strongly.

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

The control need not be intentionally ugly; it should remain musically legal enough that the comparison tests the proposed mechanism rather than obvious corruption.

Listener tests should compare at least:

- preference;
- coherence;
- perceived surprise;
- memorability;
- emotional impact;
- desire to hear again.

---

## 13. Bass controls

Bass behaviour is parameterised rather than encoded as a numbered Study.

All controls are in `[0,1]`.

- `activity` — lowers/raises the burden for Bass to beat silence.
- `sustain` — biases toward longer/shorter structural cells.
- `movement` — biases static support versus degree movement.
- `pattern_complexity` — biases simple versus mixed bar partitions.
- `gate` — fraction of an allocated Bass span that actually sounds.

A Bass pattern owns a four-beat time budget. Typical available shapes include:

- `4`
- `2+2`
- `1+1+2`
- `2+1+1`
- `1+1+1+1`

These are vocabulary options, not quotas.

---

## 14. Rhythm controls

Rhythm is generated per bar from short pitched figures.

Controls:

- `activity`
- `complexity`
- `syncopation`
- `gate`

There is no fixed set of mandatory active bars in the v0.2 engine.

For every bar:

1. generate legal rhythmic candidates;
2. score them against active Tune/Bass context;
3. compare the strongest figure against silence;
4. sound it only if it wins.

---

## 15. Pattern memory and locks

A reusable pattern stores:

- relative onset geometry;
- duration geometry;
- relative scale-degree contour.

It does **not** store absolute MIDI pitches.

A pattern may therefore be captured, named, locked and re-realised against a new harmonic anchor while preserving its recognisable geometry.

v0.2 engine-level lock windows are supported for the subsidiary BASS and RHYTHM lanes. Tune pattern memory remains a research extension because forcing Tune repetition can bypass the prediction experiment.

Lock state must be explicit and must be released after its configured window.

---

## 16. Vertical compatibility

Simultaneous music is evaluated over real overlap intervals.

The engine retains interval and complete-set sonority priors. These are compositional priors, not universal claims about consonance.

Vertical compatibility must never permit a pitch to escape its scale or lane.

---

## 17. Density

There are no occupancy quotas.

Bass and Rhythm activity controls alter their opportunity/burden to sound, while silence remains a legal competitor.

The desirable qualitative tendency remains:

- Tune alone should be common;
- two-part texture should be ordinary;
- all three parts should not become an unexamined default.

If listening evidence later contradicts this tendency, the tendency may change without changing the central IPM hypothesis.

---

## 18. Determinism

A supplied random seed must reproduce the same result for the same implementation and configuration.

Every stochastic choice is made through the seeded randomness layer.

Cross-Python-version bit-for-bit RNG identity is not claimed unless separately tested.

---

## 19. Decision trace

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
- Bass/Rhythm silence scores;
- accepted events;
- lane/register validation;
- vertical metrics.

A rendered MIDI without its decision trace is incomplete as a research artefact.

---

## 20. Historical studies

Studies #001–#011 are experimental records.

They preserve:

- failed listening controls;
- bugs and corrections;
- controlled musical experiments;
- the path by which Tune/Bass/Rhythm and pattern memory emerged.

They are not the v0.2 production call graph.

The current engine must be able to run without calling any numbered Study module.

---

## 21. Acceptance boundary for v0.2

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
- [ ] subsidiary silence competition;
- [ ] pattern memory and explicit subsidiary lock/unlock;
- [ ] no self-overlap;
- [ ] actual vertical texture scoring;
- [ ] MIDI export;
- [ ] machine-readable trace;
- [ ] Python 3.11 and 3.13 CI.

Musical acceptance remains listening-dependent.

Theory acceptance requires controlled listener evidence and cannot be inferred from passing software tests.

---

## 22. Known research debt

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

## 23. Permanent project distinction

Three concepts must remain separate:

1. **Instrument roles:** `TUNE / BASS / RHYTHM`.
2. **Tune prediction branches:** `EXPECTED / REVEALING / EXPLORATORY`.
3. **Experimental conditions:** `predictable / ipm / unstructured-surprise`.

Conflating these layers recreates the architectural confusion v0.2 is intended to remove.

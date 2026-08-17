# Invariant Predictive Music (IPM) — Formal Specification

**Status:** v0.1 design specification  
**Scope:** deterministic reference generator for a short tonal/modal polyphonic study  
**Primary goal:** test whether prediction, controlled surprise, invariant preservation, retrospective integration, and disciplined silence can generate music that listeners prefer to simpler controls.

---

## 1. Governing laws

These laws sit above all heuristics, weights, style tables, and implementation choices.

### Law 1 — Prediction is the baseline

> **Prediction is the baseline. Surprise must improve on it.**

The main melody always has an expected continuation available as a control. A surprising continuation is accepted only when its projected musical value exceeds the expected branch.

For an expected branch `E` and a surprising branch `S`:

\[
Q(S) > Q(E)
\]

Surprise therefore carries a burden of proof.

### Law 2 — The main voice defines the world

> **The main voice defines the musical world. Counter-voices may enrich or challenge it, but must remain structurally accountable to it and to one another.**

Voice generation order is strict:

\[
M \rightarrow B_R \rightarrow B_H
\]

where:

- `M` — main predictive melody;
- `B_R` — responsive stochastic counter-voice;
- `B_H` — sparse harmonic/colour counter-voice.

A subsidiary voice never forces an already accepted main note to change. It must adapt, regenerate, continue, or remain silent.

### Law 3 — Every additional note competes with silence

> **Every additional note must justify why it is better than silence.**

For every subsidiary candidate event `x`, silence is evaluated over the same interval:

\[
Q(x) > Q(\varnothing)
\]

If this condition is not met, silence wins.

### Law 4 — Every note must justify the time it occupies

A musical event is not merely a pitch. Its onset and duration are part of its musical claim.

\[
Q(p,o,d) > Q(\text{silence over the same interval})
\]

Pitch, onset, and duration are therefore generated and evaluated jointly.

---

## 2. Central hypothesis

IPM tests the following compositional hypothesis:

> **Listeners should tend to prefer moderately surprising events that preserve latent structural invariants and receive strong subsequent musical justification over both highly predictable continuations and equally surprising but structurally unrelated continuations.**

The intended process is:

\[
\text{learnable structure}
\rightarrow
\text{prediction}
\rightarrow
\text{controlled violation}
\rightarrow
\text{retrospective integration}
\]

A compact formulation is:

> **Make the next event difficult enough to predict to remain interesting, recognisable at a deeper level, and retrospectively justified by what follows.**

---

## 3. Event representation

Each note event in voice `v` is:

\[
x_i^{(v)}=(p_i,o_i,d_i,a_i,h_i)
\]

where:

- `p_i` — pitch, preferably represented scale-relatively internally;
- `o_i` — onset time;
- `d_i` — duration;
- `a_i` — accent / metrical strength;
- `h_i` — harmonic context.

A rest is a first-class event:

\[
x=\varnothing
\]

A sounding note may also be continued rather than re-attacked.

For subsidiary voices, the action set is therefore:

\[
\{\text{attack},\text{continue},\text{rest}\}
\]

---

## 4. Hard monophonic voice constraint

Each individual voice owns one timeline and may not overlap itself.

For all adjacent events in voice `v`:

\[
o_{i+1}^{(v)} \ge o_i^{(v)} + d_i^{(v)}
\]

Equality means an immediate continuation to the next event. A strict inequality creates a rest.

Self-overlap is a hard rejection, not a soft penalty.

Different voices may overlap each other; those overlaps form the polyphonic texture and must be evaluated explicitly.

---

## 5. Voice hierarchy and roles

### 5.1 Main voice — `M`

Purpose:

- establish melodic identity;
- teach motifs and invariants;
- establish phrase direction;
- imply or participate in harmony;
- carry the principal prediction / surprise process.

The main voice is generated first and frozen before subsidiary voices are generated around it.

### 5.2 Responsive counter-voice — `B_R`

Purpose:

- answer or reinterpret the main voice;
- use contrary or oblique motion;
- introduce passing motion;
- quote or transform motif fragments;
- provide delayed imitation;
- create controlled, resolvable tension.

`B_R` has moderate stochastic freedom, but all candidates are conditional on the frozen main voice and current structural state.

### 5.3 Harmonic/colour counter-voice — `B_H`

Purpose:

- stabilise or clarify sonority;
- provide roots, thirds, fifths, sixths, or other contextually useful tones;
- sustain support tones;
- introduce sparse colour or suspensions with clear resolution;
- avoid competing with the main melodic identity.

`B_H` should normally use fewer attacks, longer durations, and more silence than `B_R`.

---

## 6. Texture and occupancy

Sub-branch occupancy is a **density governor, never a quota**.

The main voice alone should normally be the single most common texture. Three simultaneously active voices should be exceptional enough to feel structurally significant.

Initial reference ranges:

| Texture | Approximate share of main-voice time |
|---|---:|
| Main alone | 45–60% |
| Main + `B_R` | 20–30% |
| Main + `B_H` | 10–20% |
| All three voices | 5–15% |

Indicative individual occupancy governors:

- `B_R`: about 25–40%;
- `B_H`: about 15–25%.

These values are not targets that must be filled. If candidate events fail to beat silence, the voice remains silent even if occupancy is below the governor.

### Structural density curve

Define active voice count:

\[
D(t)=|A(t)|
\]

where `A(t)` is the set of sounding pitches at time `t`.

A typical density tendency may be:

\[
1 \rightarrow 2 \rightarrow 2 \rightarrow 3 \rightarrow 2 \rightarrow 1
\]

corresponding loosely to establishment, development, climax, release, and ending.

---

## 7. Main-voice candidate branches

At significant main-melody decisions, generate three candidate continuation classes.

### `E` — Expected

The continuation most supported by the listener model.

\[
E=\arg\max_x P_t(x)
\]

This is the baseline/control branch.

### `R` — Revealing

A less-predictable continuation that preserves important latent invariants and can be strongly integrated by the near future.

### `X` — Exploratory

A constrained stochastic continuation sampled from a wider but still musically legal candidate region.

Exploratory does **not** mean unconstrained random pitch selection.

Each candidate grows a short lookahead continuation before scoring. The selected branch may be expected, revealing, or exploratory, but prediction remains the default and surprise must earn replacement.

---

## 8. Listener / predictive model

At time `t`, the system maintains an explicit approximation of listener expectation:

\[
P_t(x)=P(x_{t+1}=x\mid x_{1:t})
\]

An initial reference implementation may combine several predictors:

- tonal / modal stability;
- interval continuation;
- motif continuation;
- rhythmic continuation;
- contour continuation;
- harmonic compatibility;
- phrase position.

A weighted log combination is acceptable:

\[
\log P_t(x)=\sum_k \alpha_k \log P_k(x)
\]

The exact weights are implementation parameters and must be recorded in traces.

---

## 9. Surprise

Prediction error for candidate event `x` is:

\[
S_t(x)=-\log_2 P_t(x)
\]

IPM does not maximise surprise. It seeks useful, calibrated surprise.

A simple initial utility curve may be:

\[
U(S)=S e^{-kS}
\]

This penalises both trivial predictability and extreme arbitrariness.

### Surprise budget across dimensions

A note may be surprising through pitch, duration, onset, or a combination.

\[
S_E=\alpha S_p + \beta S_d + \gamma S_o
\]

When one dimension consumes a large part of the surprise budget, the others should normally become more conservative.

In particular:

\[
S_p\uparrow \Rightarrow S_d\downarrow
\]

and conversely, unless formal position explicitly justifies a compound surprise.

---

## 10. Duration

Duration is not attached after pitch generation.

Generate:

\[
P(p,d,o\mid S_t)
\]

or an equivalent structured approximation.

Define a local rhythmic norm:

\[
\bar d_t
\]

and relative duration:

\[
r_t=\frac{d_t}{\bar d_t}
\]

Typical interpretation:

- `r = 0.5` — short;
- `r = 1` — locally expected;
- `r = 2` — held;
- `r = 4` — exceptional sustain.

Long duration increases structural importance and increases the burden on dissonant events to justify themselves.

---

## 11. Invariants

A motif or phrase is represented both by surface events and by extracted structural features:

\[
\phi(m)=
(\phi_{interval},\phi_{contour},\phi_{duration},\phi_{accent},\phi_{harmonic})
\]

Possible invariants include:

- interval relations;
- contour direction;
- rhythmic ratios;
- accent pattern;
- phrase shape;
- harmonic trajectory;
- recurring resolution behaviour.

Each invariant receives a preservation weight:

\[
w_j\in[0,1]
\]

Invariant similarity between motif `m` and transformation `m'` may be represented as:

\[
C_I(m,m')=
\frac{\sum_j w_j\,sim(\phi_j(m),\phi_j(m'))}{\sum_j w_j}
\]

The goal is not literal repetition. Surface features may change substantially while important invariants remain recoverable.

### Transformation quality

Let:

- `D_S(m,m')` — surface difference;
- `C_I(m,m')` — invariant similarity.

Then:

\[
T_Q=D_S\times C_I
\]

This favours transformations that are noticeably different yet structurally recognisable.

---

## 12. Active-sonority evaluation

Polyphonic compatibility is evaluated over **actual overlap intervals**, not merely note pairs in isolation.

At time `t`, define the active pitch set:

\[
A(t)=\{p_v(t)\mid v\text{ is sounding at }t\}
\]

Every attack, release, or pitch change creates a new interval over which the active sonority is evaluated.

### Pairwise compatibility

For all simultaneous voice pairs, calculate contextual interval compatibility `C_ij`.

A conservative aggregate is:

\[
C_{pair}=\min_{i\ne j} C_{ij}
\]

so one severe collision cannot be hidden by averaging.

### Whole-set compatibility

Also calculate:

\[
C_{set}(A(t))
\]

which judges the complete simultaneous pitch set rather than only independent intervals.

Overall vertical compatibility may begin as:

\[
C_V=w_p C_{pair}+w_s C_{set}
\]

subject to any hard collision filters.

---

## 13. Dissonance, duration, metre, and resolution

Consonance/dissonance tables are priors, not absolute laws.

The cost of a dissonance must depend on at least:

- interval / pitch-set context;
- duration of overlap;
- metrical strength;
- voice-leading;
- whether a credible resolution follows.

An initial duration weighting may use:

\[
D_{duration}=1-e^{-\lambda d}
\]

Let metrical strength be:

\[
m(t)\in[0,1]
\]

Then an initial dissonance cost may be approximated by:

\[
D^*=D_{interval}\,D_{duration}\,m(t)
\]

If future continuation provides a resolution score:

\[
R(x,X)\in[0,1]
\]

then:

\[
D_{effective}=D^*(1-R)
\]

Therefore a brief weak-beat passing clash or well-resolved suspension may outperform a static consonance.

> **Dissonance must have a destination or another explicit structural justification.**

---

## 14. Voice-leading and register

Each voice receives a preferred register function `R_v(p)`.

Repeated or purposeless voice crossing is penalised, but crossing is not categorically forbidden.

Successive relative motion between voices may be classified as:

- contrary;
- oblique;
- similar;
- parallel.

Use a contextual score `C_motion`, with a moderate default preference for contrary and oblique motion in `B_R`, without turning historical counterpoint conventions into universal hard laws.

Awkward leaps and persistent mechanical copying are penalised.

---

## 15. Structural promises and debt

Maintain a set of unresolved expectations:

\[
\Pi_t=\{\pi_1,\ldots,\pi_n\}
\]

Each promise may record:

\[
\pi_i=(q_i,s_i,a_i,r_i)
\]

where:

- `q_i` — expected event or resolution class;
- `s_i` — promise strength;
- `a_i` — age;
- `r_i` — expected resolution window or deadline.

Examples include:

- leading tone expecting tonic;
- dominant implication expecting resolution;
- unfinished motif expecting completion;
- sequence expecting continuation;
- unresolved suspension;
- call expecting a counter-voice answer;
- phrase expecting closure.

Structural debt can be represented as:

\[
D_\Pi(t)=\sum_i s_i g(a_i)
\]

Development may deliberately accumulate debt. Cadential and final regions should reduce strong outstanding debt.

---

## 16. Lookahead

Lookahead is mandatory for significant surprise and dissonance decisions.

For candidate event `x`, generate a short continuation:

\[
X=(x_t,x_{t+1},\ldots,x_{t+H})
\]

The horizon `H` may initially be a small number of events or one short phrase segment.

The engine must be able to ask:

> If this event is selected now, can what follows make it musically worthwhile?

Immediate local score alone is insufficient for accepting a surprising or dissonant event.

---

## 17. Retrospective coherence

For event `x` and its planned continuation `X`, define retrospective coherence:

\[
C_R(x,X)=
\beta_I C_I+
\beta_H C_H+
\beta_\Pi C_\Pi+
\beta_F C_F+
\beta_V C_V
\]

where components may include:

- invariant continuity;
- harmonic integration;
- promise resolution;
- formal usefulness;
- voice-leading / vertical integration.

Normalise as practical to:

\[
C_R\in[0,1]
\]

### Retrospective necessity

A useful diagnostic is:

\[
N(x,X)=[1-P_t(x)]C_R(x,X)
\]

This favours events that were not obvious beforehand but become strongly justified by their continuation.

---

## 18. Subsidiary stochastic generation

Counter-voices are stochastic only **inside the set of structurally legal and contextually scored possibilities**.

For subsidiary voice `v`:

\[
P(
 x^{(v)}
 \mid
 M,
 B_{<v},
 A(t),
 H_t,
 I_t,
 \Pi_t,
 D^*(t),
 F_t
)
\]

The generator must never sample subsidiary pitches uniformly from an unconstrained pitch set.

`B_H` is generated after `B_R` and is conditioned on both the main voice and accepted `B_R` state.

---

## 19. Candidate scoring

Exact weights are experimental parameters, not theory claims.

A subsidiary candidate continuation may initially use a score of the form:

\[
Q_B(x,X)=
 w_1C_V+
 w_2C_{motion}+
 w_3C_I+
 w_4C_R+
 w_5R_\Pi+
 w_6C_{density}+
 w_7U(S)-
 w_8A
\]

where `A` may include:

- voice crossing penalty;
- range penalty;
- unresolved dissonance penalty;
- register crowding;
- awkward leaps;
- mechanical copying;
- excessive density.

Self-overlap remains a hard rejection outside the numerical score.

Silence receives its own complete score `Q_B(∅)` and competes directly.

---

## 20. Selection

The reference engine should not always choose the absolute highest-scoring valid candidate.

Among valid candidates, a temperature-controlled softmax may be used:

\[
P(X)=\frac{e^{Q(X)/\tau}}{\sum_j e^{Q(X_j)/\tau}}
\]

A supplied random seed must make generation reproducible.

Temperature may vary by formal position, increasing through development and reducing toward resolution, but this behaviour must be traceable.

---

## 21. Formal position

Maintain a formal state `F_t` so generation does not collapse into local note-by-note optimisation.

Minimum useful regions for v0.1:

1. establishment;
2. development;
3. climax;
4. resolution.

The formal state may govern:

- target surprise;
- target density;
- permissible transformation distance;
- structural debt tolerance;
- expected phrase closure;
- counter-voice occupancy.

---

## 22. Reference generation cycle

```text
1. Choose deterministic run configuration:
   - random seed
   - key / mode
   - tempo
   - metre
   - length
   - seed motif

2. Extract initial motif invariants.

3. Establish a formal plan.

4. For each main-melody decision:
   a. Generate Expected continuation.
   b. Generate Revealing continuation.
   c. Generate constrained Exploratory continuation.
   d. Grow short lookahead futures for candidates.
   e. Score prediction, useful surprise, invariants,
      duration, promises, form, and retrospective coherence.
   f. Select the main continuation.
   g. Freeze accepted main events.

5. For responsive counter-voice B_R:
   a. Enumerate note / continue / silence candidates.
   b. Reject self-overlap.
   c. Evaluate actual overlaps against M.
   d. Score vertical sonority, duration-weighted dissonance,
      metre, voice-leading, invariants, future resolution,
      density, and silence.
   e. Accept/sample only from valid candidates that beat silence.
   f. Freeze accepted events.

6. For harmonic/colour voice B_H:
   a. Repeat against both M and accepted B_R.
   b. Prefer sparse activity, stable sonorities,
      longer support notes, useful suspensions, and silence.
   c. Accept/sample only from valid candidates that beat silence.
   d. Freeze accepted events.

7. Update:
   - listener model
   - invariant state
   - structural promises / debt
   - rhythmic norm
   - formal state
   - density state

8. Export events and complete decision trace.
```

---

## 23. Decision trace requirement

Every generated note must be explainable after the run.

The machine-readable trace must record at least:

- run seed;
- voice;
- pitch;
- onset;
- duration;
- action type (`attack`, `continue`, `rest`);
- formal position;
- relevant candidate set;
- predictive probability / surprise contribution;
- vertical compatibility;
- invariant score where applicable;
- density contribution;
- retrospective / lookahead contribution where applicable;
- silence score for subsidiary events;
- final candidate score;
- selection reason / stochastic draw state.

The trace is part of the product, not debug-only output.

---

## 24. Experimental controls

For the same seed material and high-level configuration, the reference system should be able to produce at least three comparable conditions:

### A — Predictable control

Primarily uses expected main continuations and conservative counter-voice behaviour.

### B — IPM

Uses the full expected / revealing / exploratory architecture with invariant-preserving surprise and retrospective integration.

### C — Unstructured-surprise control

Matches surprise approximately where practical, but weakens or removes invariant preservation / retrospective integration.

This allows the central claim to be tested rather than merely asserted.

Candidate listener measures include:

- preference;
- coherence;
- perceived surprise;
- memorability;
- emotional impact;
- desire to hear again.

---

## 25. v0.1 acceptance target

**Milestone:** generate one deterministic 16-bar, three-voice MIDI study from a seed motif, with every generated event traceable to this specification.

### Required

- [ ] deterministic output from a supplied random seed;
- [ ] 16-bar reference form;
- [ ] main voice with Expected / Revealing / Exploratory candidate generation;
- [ ] responsive counter-voice `B_R`;
- [ ] sparse harmonic/colour counter-voice `B_H`;
- [ ] no voice may overlap itself;
- [ ] pitch, onset, and duration treated as joint musical decisions;
- [ ] all actual inter-voice overlap intervals evaluated;
- [ ] pairwise and whole-active-set vertical evaluation;
- [ ] duration- and metre-sensitive dissonance treatment;
- [ ] lookahead for significant surprise / dissonance decisions;
- [ ] silence competes against every subsidiary event;
- [ ] main-alone remains the most common texture unless the generated evidence strongly justifies otherwise;
- [ ] three-voice texture remains exceptional rather than default;
- [ ] MIDI export;
- [ ] machine-readable decision trace;
- [ ] predictable, full-IPM, and unstructured-surprise control modes from the same seed/configuration.

### Not required for v0.1

- realtime generation;
- DAW plugin integration;
- production-quality instrumentation;
- orchestration;
- drums;
- GUI;
- machine-learned listener model;
- claim that any numerical weight is universal;
- claim that the system mathematically defines beauty.

---

## 26. Non-goals and epistemic limits

IPM does **not** assume that:

- consonance is universally good;
- dissonance is universally bad;
- Western tonal conventions are universal musical laws;
- a single scoring function can measure beauty;
- maximum surprise produces maximum interest;
- theoretical elegance is evidence that listeners will prefer the result.

Numerical tables and weights used by the reference implementation are experimental priors. They must remain separable from the governing laws and must be testable and replaceable.

---

## 27. Permanent design locks for v0.1

1. Prediction is the baseline; surprise must improve on it.
2. The main voice defines the musical world.
3. Subsidiary voices are constrained stochastic counter-voices, never unconstrained random melodies.
4. Voice generation order is `M → B_R → B_H`.
5. No voice may overlap itself.
6. Every subsidiary note competes directly with silence.
7. Every note must justify the time it occupies.
8. Simultaneous voices are judged over their real temporal overlaps.
9. Vertical evaluation considers both pairwise intervals and the complete active pitch set.
10. Dissonance evaluation is duration-, metre-, context-, and resolution-sensitive.
11. Significant surprise requires lookahead.
12. Important invariants must remain recoverable through transformation.
13. Counter-voice occupancy is governed, not quota-filled.
14. Main-alone should normally be the most common texture.
15. Three simultaneous voices should be exceptional enough to carry structural significance.
16. A supplied random seed must make the reference run reproducible.
17. Every accepted event must be represented in a machine-readable decision trace.

---

## 28. First implementation boundary

The next implementation step after this specification is accepted is **not** a full composer or plugin.

Build the smallest reference engine capable of proving or falsifying the v0.1 mechanism:

> **one deterministic 16-bar MIDI study + complete decision trace + three controlled generation modes.**

Anything that does not contribute directly to that milestone should be deferred.
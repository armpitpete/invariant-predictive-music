# Music-Formula Synthesis — Hostile Review v0.1

**Status:** PASS WITH MATERIAL LIMITATIONS  
**Synthesis under review:** `MUSIC_FORMULA_SYNTHESIS_v0_1.md`  
**Purpose:** try to disprove or narrow the attractive identity → prediction → integration explanation before it is treated as the project answer.

## Verdict

The broad mechanism survives, but the strongest safe statement is narrower than a universal “surprise sweet spot”.

Carry forward:

> **Music appears to derive part of its effect from learnable structure that supports prediction. Events can gain value when they productively violate a confident prediction or help resolve uncertainty without destroying the learned identity, and when later context integrates the resulting change.**

Do **not** carry forward a fixed uncertainty × surprise utility curve or fixed optimum.

---

## Finding 1 — the expectancy literature does not identify one universal utility surface

The literature supports treating probability, entropy/uncertainty and surprise as important variables, but it does not justify freezing one interaction direction as a universal law.

Examples:

- Cheung et al. (2019) found high pleasure for low-uncertainty/high-surprise chords and high-uncertainty/low-surprise chords.
- Gold et al. (2019) found nonlinear effects and evidence that uncertain contexts can favour more predictable outcomes.
- naturalistic listening work has also reported high-uncertainty/low-surprise and low-uncertainty/high-surprise preference regions.
- a 2025 large-sample study, *Predictive processes shape individual musical preferences*, reported an inverted-U relation plus an uncertainty/surprise interaction in a different direction: smaller surprises preferred in low-entropy melodies and larger surprises in high-entropy melodies.

Therefore the robust project-level inference is only:

> **expectation, uncertainty and surprise interact nonlinearly and contextually.**

The exact perceptual utility surface must be measured rather than inserted into the formula by assumption.

This is a material correction to any reading of the synthesis that implies a settled universal uncertainty/surprise optimum.

---

## Finding 2 — A5 has not yet earned unseen-song audio generalisation

A5 passed its frozen development hostile suite and held-out structural Axis S reorderings, which is real evidence of structural discrimination.

But Axis U remains blocked because the original audio → 28-feature extractor was not preserved. Reconstructing a plausible extractor and obtaining good unseen-song results would not be the same validation experiment unless exact equivalence is established to the frozen recovery criteria.

Therefore A5 may currently be called:

- a validated structural detector within its preserved development/Axis-S evidence;

but not:

- a generally validated audio measure across unseen songs.

---

## Finding 3 — current IPM probabilities are model expectations, not listener expectations

The IPM engine's candidate probabilities are generated from an explicit design prior. They are useful experimental variables, but they are not yet empirically fitted estimates of what a human listener expected.

This creates a possible false-positive route:

1. the composer defines its own probability model;
2. the composer creates candidates using the same musical priors;
3. the scorer identifies its own deviations;
4. a high IPM score can therefore demonstrate internal consistency without demonstrating human predictive cognition.

Human surprise manipulation checks and/or an independently trained expectation model are required before interpreting engine surprise as listener surprise.

---

## Finding 4 — “future predictive gain” can become tautological

The proposed quantity

\[
G_t=L(F_t|H_t)-L(F_t|H_t,e_t)
\]

is promising only if the future `F_t` is not constructed in a way that guarantees the event will explain it.

A deliberately copied or target-conditioned suffix can make almost any event retrospectively informative by construction.

Therefore any test of future predictive gain must include hostile controls such as:

- future generated independently of the target;
- target-conditioned future versus matched independently generated future;
- copied-vocabulary future versus structurally matched non-copy future;
- simple repetition / echo controls;
- suffixes matched for independent musical quality and predictive complexity.

A positive `G_t` is a computational observation, not human retrospective meaning.

---

## Finding 5 — Counterfactual Episode v2 tests a package, not two isolated causes

Experiment 1 deliberately attaches one common suffix generated from the IPM target state. Qualification also requires that this suffix integrate IPM more strongly than Control.

Thus IPM versus Control varies together in:

- local invariant continuity;
- actual future integration.

That is legitimate for testing the complete causal package, but a positive result cannot identify which component caused the listener effect.

The proposed 2 × 2 Experiment 2 remains justified.

---

## Finding 6 — Experiment 2 can still be confounded by suffix quality

The proposed identity × future-integration factorial is only diagnostic if `INTEGRATED` and `UNINTEGRATED` suffixes are not audibly different in generic quality for unrelated reasons.

Before listening, freeze matching constraints for suffixes including at least:

- duration and event count;
- onset/rhythm profile;
- register and pitch-range envelope;
- cadence/form role;
- broad information-content / entropy profile under an independent expectation model where possible;
- loudness/rendering path;
- independent base-quality measure not using the future-integration target criterion.

The strongest construction would use multiple matched suffixes per target and predeclared selection rules rather than hand-picking one “good integrated” and one “bad unintegrated” future.

---

## Finding 7 — musical value is broader than retrospective sense

Even if identity continuity and future integration causally raise retrospective sense, that does not establish a universal formula for:

- liking;
- beauty;
- emotional intensity;
- memorability;
- groove;
- originality;
- cultural meaning;
- commercial success.

Retrospective sense is a mechanism outcome. Preference and other musical consequences must remain separate outcomes.

---

## Falsifiers for the working law

The working law should be weakened or rejected if controlled evidence shows any of the following robustly:

1. surprise-matched low-identity targets are rated as retrospectively meaningful as high-identity targets;
2. matched integrated futures do not improve retrospective sense over unintegrated futures;
3. the identity × integration interaction is absent across well-powered, independently constructed stimuli;
4. human surprise ratings do not track the model's intended manipulation;
5. future-predictive gain is equally high for trivial repetition or deliberately corrupted but easy-to-predict controls;
6. an independently trained expectation model reverses the IPM condition ordering;
7. effects collapse outside the generator/style used to construct the stimuli.

Null or contrary results must remain results; they must not trigger post-listening retuning of the frozen stimulus set.

---

## Final hostile-review decision

**PASS WITH MATERIAL LIMITATIONS.**

The project has a credible mechanism hypothesis, not a discovered universal constant.

The next scientific priority is:

> **separate identity continuity from future integration experimentally, while measuring human expectation rather than assuming the engine's probability model is perceptually calibrated.**

Do not spend the next cycle inventing new scalar weights.
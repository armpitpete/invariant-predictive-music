# Music-Formula Synthesis v0.1

**Status:** design-only research synthesis  
**Parent:** `b2e36e5294a1fbbdc664607df9c1005343561ca3`  
**Purpose:** state the strongest answer currently supported by the A5 and IPM work, identify what remains unproved, and specify the next falsification target.

## Protected boundaries

This record does **not**:

- alter frozen A5, its weights, lags, hostile controls, or validation firewall;
- treat a reconstructed audio extractor as the lost original extractor;
- open A5 Axis U;
- alter Counterfactual Episode v2 or its frozen corpus/protocol;
- lift the explicit hold on external recruitment;
- alter the IPM production selector;
- claim a universal numerical formula for good music;
- claim listener preference has been demonstrated.

It is a synthesis and successor-design record only.

---

## 1. The answer we have actually found

The evidence no longer supports treating musical value as a single quantity of internal coherence.

The stronger working law is:

> **Music establishes a learnable identity, creates prediction from that identity, permits informative departures from prediction that still belong to the identity, and uses later material to integrate those departures.**

In compact form:

\[
\text{learnable identity}
\rightarrow
\text{prediction}
\rightarrow
\text{informative deviation or confirmation}
\rightarrow
\text{identity preservation}
\rightarrow
\text{retrospective integration}
\]

This is a mechanism hypothesis, not yet a universal scalar quality formula.

### Why this is stronger than “coherence”

Pure coherence rewards music for remaining orderly. That is necessary but not sufficient. A perfectly stable, repetitive system can be coherent and musically inert.

Pure surprise also fails. A sequence can be maximally unpredictable and cease to establish a usable musical world.

The useful region is relational: an event matters because of what the listener had learned before it and because of what the music subsequently does with it.

---

## 2. What A5 contributed

A5 should now be interpreted as an **identity/coherence substrate**, not a quality score.

Its top-level structure is:

\[
A_5(t)=[M(t)Q(t)G O]^{1/3}
\]

where the persistent fabric is `F = G × O` and the three conceptual pillars are:

- `M`: multi-scale recurrence / identity;
- `Q`: local embedded event quality;
- `F`: persistent relational fabric, including cross-stream accountability and ordered relational-state continuity.

A5 passed the frozen development hostile suite and the held-out structural Axis S reorderings. That is evidence that it detects meaningful organisation rather than merely smooth marginals or splice artefacts.

It is **not** evidence that maximising A5 makes better music.

The A5-C composition contract correctly preserved this distinction by allowing A5 only to veto a poor candidate under a predeclared rule rather than maximising the score.

### A5 unresolved validation debt

Axis U remains blocked because the original executable audio-to-28-feature extractor was not preserved. The recovered preprocessing/scaling evidence is insufficient to silently substitute a new extractor into the frozen validation firewall.

That blocked legacy test should remain blocked unless the original extractor is recovered or exact development-equivalence is independently established to the already frozen thresholds.

This provenance failure does not justify discarding the A5 structural results, but it limits claims of unseen-song audio generalisation.

---

## 3. What IPM contributed

IPM supplies the dynamic part A5 lacks.

For each candidate continuation, the current engine already records:

- predictive probability `P(x)`;
- surprise `S(x) = -log2 P(x)`;
- invariant similarity;
- retrospective coherence;
- retrospective necessity;
- a heuristic combined `ipm_score`.

The central IPM hypothesis is already close to the stronger music-formula law:

> moderately surprising continuations should be valuable when they preserve learned invariants and become justified by what follows.

The current numerical IPM score remains an engineering hypothesis. Its probability model is a design prior rather than a fitted human expectation model, and its weights are not universal constants.

Therefore:

> **Do not rename the current `ipm_score` as “the music formula”.**

The important result is the factorisation, not the present weights.

---

## 4. Independent theoretical convergence

Existing predictive-processing and music-expectancy work independently supports the same general direction:

- statistical models of musical expectation can represent event probability, uncertainty and information content;
- pleasure is not a monotonic function of surprise;
- predictive uncertainty and actual surprise interact;
- both surprising events in low-uncertainty contexts and confirming events in high-uncertainty contexts can be rewarding;
- familiarity and learning alter the response, arguing against a universal fixed “ideal complexity” value.

Relevant starting points:

- Pearce, M. T. — IDyOM / statistical learning and musical expectation;
- Cheung et al. (2019), *Current Biology*, “Uncertainty and Surprise Jointly Predict Musical Pleasure and Amygdala, Hippocampus, and Auditory Cortex Activity”;
- Gold et al. (2019), *Journal of Neuroscience*, “Predictability and Uncertainty in the Pleasure of Music: A Reward for Learning?”

The convergence is conceptual, not proof that the present IPM implementation is biologically or perceptually correct.

---

## 5. Better mathematical target: future predictive gain under identity

The next mathematical object should measure whether an event **earns its place by improving the model of what follows**, rather than merely assigning it a locally pleasing surprise value.

Let:

- `C_t` = identity/invariant continuity of event `e_t` with the learned musical world;
- `F_t` = a fixed future window after the event;
- `L(F_t | H_t)` = predictive code length of that future from history before seeing `e_t`;
- `L(F_t | H_t, e_t)` = predictive code length after incorporating `e_t`.

Define **future predictive gain**:

\[
G_t = L(F_t | H_t) - L(F_t | H_t,e_t)
\]

If `G_t > 0`, the event improved the model of what followed. It taught or clarified something that the subsequent music used.

A first mechanism component is then:

\[
R_t = C_t\,G_t
\]

This is deliberately **not** proposed as a complete quality score.

Why it is useful:

1. a locally surprising event receives no automatic reward;
2. a surprise can become valuable if later material makes it informative;
3. a high-uncertainty confirming event can also have positive gain by resolving uncertainty;
4. identity continuity prevents arbitrary future predictability from being mistaken for musical belonging;
5. the quantity is based on an actual observed future, unlike a purely prospective heuristic “necessity” score.

### Important falsification risk

`G_t` could reward trivial repetition or any event that merely narrows a weak model. It must therefore be tested against:

- literal repetition controls;
- low-information loops;
- arbitrary but easily predicted continuations;
- style changes with high local predictability but broken identity;
- events whose future gain arises only from a deliberately copied suffix.

A5-like identity constraints and hostile controls remain necessary.

---

## 6. What Counterfactual Episode v2 can prove

The existing frozen 36-listener pilot is a strong causal test of a **package**:

- identical learned prefix;
- one target intervention;
- IPM and Control approximately matched for surprise, local base quality, structural rhythm and audible articulation;
- Control has weaker learned-invariant similarity;
- all conditions receive the same suffix generated from the IPM target state;
- qualifying episodes require that this suffix integrates IPM more strongly than Control;
- primary human outcome is retrospective sense.

A positive IPM-minus-Control result would therefore support the claim that the IPM package creates greater retrospective sense than surprise-matched weaker-continuity material.

It would **not** cleanly separate two mechanisms that vary together:

1. local invariant preservation;
2. later integration by the suffix.

A null or contrary result would count directly against the package hypothesis and must not be repaired by retuning the corpus after listening.

The existing recruitment HOLD remains in force.

---

## 7. Next experiment: 2 × 2 identity × future-integration test

Do **not** modify Counterfactual Episode v2. Preserve it as Experiment 1.

A separate Experiment 2 should isolate the two currently bundled mechanisms.

### Factors

**Factor A — local identity continuity**

- `HIGH`: target preserves learned invariants;
- `LOW`: target has weaker invariant continuity.

Targets must be matched as closely as possible on:

- surprise;
- base musical quality;
- rhythm/articulation;
- note count;
- register/range;
- target loudness/rendering.

**Factor B — future integration**

- `INTEGRATED`: suffix makes substantial structural use of the target event;
- `UNINTEGRATED`: suffix is matched for independent musical quality but does not materially adopt/resolve the target's new information.

Suffix pairs should be matched on:

- length;
- activity/density;
- broad surprise burden;
- cadence/form function;
- rendering;
- non-target acoustic level.

### Four primary conditions

1. `HIGH × INTEGRATED`
2. `HIGH × UNINTEGRATED`
3. `LOW × INTEGRATED`
4. `LOW × UNINTEGRATED`

A predictable reference can be retained as a secondary calibration condition, but it should not replace the factorial mechanism test.

### Primary hypotheses

- identity main effect: HIGH > LOW on coherence / retrospective sense;
- future-integration main effect: INTEGRATED > UNINTEGRATED on retrospective sense;
- interaction: integration should be most effective when the target remains recognisably part of the learned musical world.

### Strongest outcome

The strongest support for the proposed law would be:

\[
HIGH\times INTEGRATED
>
HIGH\times UNINTEGRATED
\]

and

\[
HIGH\times INTEGRATED
>
LOW\times INTEGRATED
\]

with surprise successfully matched.

That would demonstrate separately that **belonging** and **what comes later** both matter.

---

## 8. Do not chase one universal scalar yet

The project should now distinguish three layers:

### Layer 1 — structural identity

Can a listener/model learn what musical world this is?

A5 is evidence toward this layer.

### Layer 2 — predictive-information dynamics

How does each event alter expectation, uncertainty and the predictive model?

IPM supplies the current experimental machinery for this layer.

### Layer 3 — perceptual/musical consequence

Do humans actually experience the predicted event as more coherent, retrospectively meaningful, memorable, desirable to hear again, or preferred?

Only controlled listener evidence can close this layer.

A scalar formula, if one exists, should be fitted or derived only after these factors survive separate causal tests. Prematurely choosing new weights would convert the experiment back into curve fitting.

---

## 9. Current project verdict

### Supported now

- musical identity is relational and multi-scale rather than reducible to one repetitive stream;
- order and cross-stream relationships matter;
- A5 is a viable structural-coherence detector on its frozen development and Axis S tests;
- coherent surprise + later integration is a falsifiable and independently plausible dynamic hypothesis;
- the existing IPM architecture already exposes most variables required to test it;
- Counterfactual Episode v2 is a legitimate first human mechanism test, but it has no participant result while recruitment remains on HOLD.

### Not supported now

- a universal formula for good music;
- universal numerical weights;
- the claim that higher A5 means better music;
- the claim that current `ipm_score` is a perceptual law;
- unseen-song A5 Axis U validation;
- external listener preference for IPM.

## 10. Working law to carry forward

Until falsified, the project should carry this statement rather than “maximise A”:

> **A musical event becomes valuable when it changes expectation without destroying the learned identity of the piece, and when what follows makes that change useful.**

The next scientific objective is not another hand-tuned score. It is to isolate and measure the causal contributions of **identity continuity** and **future integration**.

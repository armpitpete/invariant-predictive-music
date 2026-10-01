# Composition Framework v0.1

**Status:** ENGINE INTEGRATED / FIRST A/B COMPLETE / LISTENING VALIDATION OPEN
**Project:** Invariant Predictive Music (IPM)
**Relationship to IPM v0.2:** opt-in additive layer; framework mode defaults off and does not replace the prediction/surprise falsification model
**Epistemic boundary:** structural metrics are proxies. Listener tests decide whether intended emotion is actually perceived.

## Purpose

Composition Framework v0.1 converts the current emotional-composition ideas into a deterministic, traceable system.

The framework is intended to make music that can:
- establish something learnable;
- allow prediction to form;
- alter prediction deliberately;
- make deviation consequential;
- protect important moments with space;
- use expressive gesture instead of random humanisation;
- let timbre participate in form;
- repeat material with transformation;
- keep intensity separate from significance;
- target mixed rather than one-dimensional emotional states.

## Governing rules

1. Establish something the listener can learn.
2. Allow prediction to form before relying on deviation.
3. Alter prediction deliberately rather than arbitrarily.
4. Every major deviation must have a consequence or be explicitly recorded unresolved.
5. Protect important events with negative space.
6. Expression must follow phrase or structural function; random jitter is not expression.
7. Timbre may carry musical structure and need not be removable from the composition.
8. Repetition should preserve recognisable identity while allowing transformation.
9. Loudness, density, register height and complexity are not synonyms for emotional significance.
10. Structural proxies must never be reported as proof of listener emotion.


## Functional form

The framework uses six musical functions rather than fixed timestamps:

- **Introduction** — establish identity.
- **Recognition** — reinforce learnable material.
- **Complication** — disturb established behaviour.
- **Suspension** — withhold, thin or destabilise.
- **Arrival** — fulfil or decisively redirect expectation.
- **Aftermath** — allow the event to change what follows.

These are functions, not mandatory sections.

The seeded form planner can:
- repeat functions;
- omit functions;
- reorder selected functions;
- produce a denied-expectation form with no arrival;
- vary duration by allocating different numbers of bars to each function.

No 4–6 minute template is part of the contract.

## Mixed emotional targets

Every framework-enabled experiment declares:
- one primary emotional target;
- one secondary or conflicting target.

Useful target pairs include:
- warmth + uncertainty;
- beauty + loss;
- security + vulnerability;
- hope + distance;
- tenderness + restraint;
- nostalgia + movement;
- calm + unease.

These labels guide hypotheses. They do not certify perception.

## Existing IPM relationship

IPM v0.2 already implements:
- learnable structure;
- predictive probability;
- expected/revealing/exploratory branches;
- controlled violation;
- invariant continuity;
- retrospective coherence and necessity;
- silence competition;
- pattern memory;
- deterministic seeded generation.

Composition Framework v0.1 therefore does **not** create a second prediction engine.


It adds the missing higher-level controls around the existing engine:
- functional form planning;
- density/negative-space shaping;
- intentional expressive directives;
- timbral directives;
- motif recurrence/transformation tracking;
- deviation/consequence tracking;
- mixed emotional targets;
- framework-level evaluation;
- listening-test scaffolding.

The original IPM falsification conditions remain independently selectable.

## Machine-usable concepts

The implementation represents or traces:
- learnable pattern;
- expectation strength;
- prediction strength;
- deviation;
- delay/withholding through suspension;
- fulfilment;
- redirection;
- unresolved consequence;
- arrival;
- aftermath;
- negative space;
- expressive gesture;
- timbral identity;
- repetition with transformation;
- intensity proxy;
- structural-significance proxy.

The term **structural-significance proxy** is deliberately used instead of claiming measured emotional significance.

## Negative space

Negative space is implemented by shaping Bass and Rhythm opportunity probabilities according to structural function.

The permanent v0.2 endpoint law is preserved:
- activity = 0 gives no opportunities;
- activity = 1 gives every opportunity.

Framework shaping changes the curve between those endpoints, not the endpoints themselves.
The `negative_space` control scales the strength of that shaping: zero leaves
the original phase curve intact, while one applies the full structural-function
density shape.

Suspension and aftermath are normally thinned.
Complication can admit more activity.
Arrival does not automatically mean maximum density.

## Expressive gesture

Framework expression is deterministic and structurally directed.

The current note model can directly express:
- velocity contour.

The trace additionally carries future-renderer directives for:
- attack behaviour;
- note-length behaviour;
- vibrato onset;
- portamento;
- timing feel;
- dynamic shape.

These directives are intentional and function-dependent.
Random pitch/timing/velocity jitter is explicitly excluded as a substitute for expression.


## Timbre as composition

Each bar receives a timbral directive tied to structural function while preserving a piece-level sonic identity.

The directive vocabulary includes:
- envelope behaviour;
- spectral breadth;
- filter motion;
- spatial motion;
- texture state.

The MIDI renderer cannot encode all of these dimensions. The Machine Synth
Engine can consume the structural plan directly through the separate
`timbral_strength` control, affecting attack/release, filter brightness,
upper-partial balance, stereo position and vibrato while preserving the lane's
core preset.

For the first structural A/B gate `timbral_strength = 0`, so sound-design change
cannot explain the result. Timbral execution is reserved for a later
post-listening generalisation gate. The full directive set remains in the trace.

## Repetition with transformation

Motif identity is tracked separately from exact rendering.

Current identity features include:
- attack count;
- interval contour direction;
- duration geometry.

A return can therefore be recognised even when exact pitches, velocity or placement differ.

Existing IPM pattern locks remain available for explicit subsidiary repetition.
Tune repetition is not forced because that would bypass the central prediction experiment.

## Lower-level emotional vocabulary

The emotional_vocabulary module contains experimental tendencies for:
- intervals;
- harmony;
- voicing;
- rhythm;
- phrase length/shape;
- articulation;
- register;
- timbre;
- dynamics;
- silence/density.

Every mapping is marked **hypothesis**.

The emotional vocabulary is **not consumed by the first structural A/B
experiment**. It remains a later soft-bias experiment after the structural
mechanism has listener evidence. Interaction rules prevent single-feature
emotional claims and discourage cue stacking.

## Superseded ideas

The following are no longer governing rules:
- a melody must work on piano before it is valid;
- melody must always be the emotional centre;
- random humanisation creates expression;
- every piece should follow one fixed 4–6 minute arc;
- an unusual sound should be added merely for memorability;
- louder/denser/higher automatically means more emotional.

The useful part of the old piano test remains:
a musical gesture should survive simplification conceptually, while timbre may still be structurally essential.


## Anti-formula safeguards

The framework must:
- support multiple seeded form templates;
- allow repeated or omitted functions;
- allow denied expectation;
- avoid mandatory climax placement;
- avoid mandatory rising-melody payoffs;
- avoid mandatory bass removal before payoff;
- avoid mandatory layer addition at arrival;
- avoid identical expressive patterns across all functions;
- preserve exact activity endpoint semantics;
- keep deterministic reproduction for the same seed/configuration.

## Evaluation criteria

Each generated experiment records:
- whether learnable material is present;
- whether expectation forms;
- whether deviation is explicit;
- whether deviations receive consequences;
- whether important moments have usable negative space;
- whether expression changes with structural function;
- whether timbral directives change with structural function;
- whether intensity is separable from structural significance;
- whether a mixed emotional target is declared;
- whether the system has more than one form template.

A failed criterion is evidence for repair, not something to hide.

## Listening-test boundary

Automated tests can establish:
- determinism;
- structural coverage;
- trace completeness;
- endpoint behaviour;
- reproducible transformations;
- formal variation;
- proxy metrics.

Automated tests cannot establish:
- perceived tenderness;
- perceived longing;
- emotional impact;
- memorability in humans;
- preference;
- whether an arrival feels earned.

Those require blinded listener data.

## Integration acceptance

The current **engine-integration gate** passes when:
- this canonical contract exists;
- framework mode defaults off and disabled output matches the accepted IPM base;
- InstrumentConfig carries the opt-in framework configuration;
- structural function changes real subsidiary density when enabled;
- one bounded transformation changes real musical material;
- obligations are explicitly recorded and accounted for;
- framework/control traces remain valid;
- a matched 60–90 second A/B pair passes mechanical controls;
- timbral shaping and emotional-vocabulary execution are held out of that first pair;
- the blind listener protocol exists.

Those conditions are now satisfied for the first A/B evidence pack.

The **listening-evidence gate remains open**. Do not execute the eight-profile
generalisation programme merely because the software gate passes. First record
the blinded judgment, classify demonstrated failures, and repair only those
mechanisms. Full emotional-composition-system freeze is not authorised.

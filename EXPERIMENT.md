# IPM Listening Experiment 1 — matched counterfactual episode pilot

**Status:** pre-listening gate. No human result exists yet.

## Question

Does a surprising Tune event that preserves learned melodic invariants and is better integrated by the music that follows produce greater **retrospective sense** than a similarly surprising, weaker-invariant event in the same musical context?

The causal claim under test is:

> learned structure → prediction → one controlled violation → invariant continuity → later music makes the violation fit in retrospect

This pilot tests that mechanism before returning to the full Tune/Bass/Rhythm texture.

## Experimental unit

The unit is an **8-bar Tune-only episode**.

- Bars 1–4: identical learning prefix.
- Bar 5: the only structural intervention.
- Bars 6–8: identical suffix.

The three versions of one episode therefore have:

> **same past → same target candidate pool → different target bar → same future**

All non-target Tune events must be identical across the three versions.

Bass and Rhythm are absent from Experiment 1. This is an experimental isolation choice, not a new composer mode.

At 58 BPM, an 8-bar episode is about 33 seconds. Twelve trials therefore contain about 6.6 minutes of audio before ratings.

## Conditions

At the shared target candidate pool:

1. **Predictable** — the engine's existing Expected choice.
2. **IPM** — the engine's existing IPM choice, and it must actually replace Expected.
3. **Unstructured Surprise** — a control chosen from the **same candidate pool**.

The control is matched to IPM on target surprise and local base quality, has the same target rhythm pattern as IPM, but must have weaker learned-invariant continuity.

Listeners never see these labels.

## Fixed future

The suffix is generated once from the Predictable reference trajectory and copied verbatim into all three versions.

This is deliberate. If each target event generated its own future, the conditions would immediately become different musical trajectories and the causal comparison would be lost.

The experiment therefore asks how the **same later music** changes the interpretation of different target events.

## Future integration

Experiment 1 adds a researcher-side `future_integration` measure.

It is computed only after the actual suffix exists. It compares the target's melodic interval structure with interval patterns in the suffix and includes the immediate target→suffix pitch connection.

This is distinct from the engine's current prospective `retrospective_coherence` / `retrospective_necessity` selection fields, which are available before later bars exist.

`future_integration` is a stimulus-construction measure, not evidence that a human listener experienced retrospective coherence. The human measure below is the empirical test.

## Pre-listening qualification

A seed is admitted only if all of the following are true before any listener data exists:

- one shared target candidate pool generated from the identical prefix state;
- the current IPM selector chooses a non-Expected target;
- the IPM target is sufficiently surprising;
- a control exists in that same pool;
- IPM and control use the same target rhythm pattern;
- IPM and control are close in modelled target surprise;
- IPM and control are close in local base musical score;
- control has weaker learned-invariant similarity;
- IPM reaches a minimum actual-suffix integration score;
- the identical suffix integrates IPM more strongly than control;
- generated non-target events are verified identical across all three variants.

Seeds are rejected rather than repaired by ear.

Human ratings are never used to decide which stimuli enter the experiment.

## Selection-funnel requirement

Every seed examined must remain in the research record, whether accepted or rejected.

The frozen corpus records:

- starting seed;
- search limit;
- final seed examined;
- every attempted seed;
- every qualification check and metric;
- qualified seed list;
- exact source revision.

This is necessary to show how selective the stimulus filter was.

## Pilot corpus

Default build:

- 12 qualified episode sets;
- 8 bars per stimulus;
- target = bar 5;
- 58 BPM;
- three condition-assignment groups;
- 36 planned complete participants;
- one condition per episode seed per participant;
- across each set of three groups, every seed appears once in every condition;
- each participant receives an independently shuffled trial order;
- participant-facing filenames are opaque hashes.

The 36-person figure is a pilot recruitment target, not a powered confirmatory sample size.

## Human measures

After each episode, collect 0–100 ratings for:

1. **Retrospective sense — primary mechanism outcome**  
   How much did unusual moments come to make sense as the music continued?
2. perceived surprise;
3. coherence;
4. liking;
5. desire to hear again.

Record separately:

- years of music-making experience;
- years of formal musical training.

These variables describe the sample; they are not exclusion criteria.

## Primary test

Primary planned contrast:

> **IPM > Unstructured Surprise on retrospective sense**

This is the most direct human test of the proposed mechanism.

Secondary contrasts include:

- IPM > Unstructured Surprise on coherence;
- IPM > Unstructured Surprise on liking;
- IPM > Predictable on liking;
- IPM > Predictable on retrospective sense.

## Manipulation checks

A valid manipulation requires:

- IPM and Unstructured Surprise to be approximately matched in **listener-rated surprise**;
- both to be more surprising than Predictable to a useful degree.

If listener-rated surprise is not matched, report a failed surprise manipulation.

Do **not** classify absence of an IPM advantage in coherence or retrospective sense as a manipulation failure. Those are predicted outcomes and null or contrary results count against the theory.

## Analysis

Use trial-level mixed-effects models.

Primary model:

- outcome: retrospective sense;
- fixed effect: condition;
- random intercepts: participant and episode seed;
- participant condition slopes if they fit stably;
- include trial position as a nuisance covariate if needed.

Report:

- condition effect estimates;
- confidence intervals;
- model diagnostics;
- all exclusions;
- manipulation-check results.

Do not reduce each participant to one grand mean before analysis.

## Confirmatory study

The pilot is for:

- mechanism failure discovery;
- effect-size estimation;
- variance estimation;
- playback/procedure validation.

A confirmatory sample size and analysis must be frozen from the pilot evidence **before** the confirmatory run begins.

Pilot listeners must not be silently folded into the confirmatory dataset.

## Exclusions fixed before data collection

Exclude only for predeclared procedural reasons:

- duplicate participation;
- failure to complete the main listening block;
- confirmed technical playback failure;
- unusable response record.

Do not exclude participants for flat ratings, negative ratings, unexpected ratings, low musical experience, or disagreement with IPM.

The participant metadata schema contains explicit fields for these decisions.

## Audio-render gate

MIDI remains the deterministic composition object. Human stimuli are frozen audio.

Before recruitment:

- render every admitted MIDI through one fixed synthesizer and soundfont;
- use 44.1 kHz stereo 16-bit PCM WAV;
- apply the same loudness-normalisation procedure;
- record FluidSynth and FFmpeg versions;
- hash the soundfont;
- hash every MIDI and WAV;
- freeze the exact source revision.

No listening result is interpretable if materially different assets are substituted during data collection.

## Blinding and schedules

The researcher corpus contains:

- condition key;
- qualification audit trail;
- participant→counterbalance-group assignments.

Participant-facing schedule files contain only:

- trial number;
- opaque stimulus ID.

Condition assignment is balanced by three groups, but trial order is independently shuffled for every participant so fatigue/order cannot collapse onto three fixed sequences.

## Stop conditions

Do not change composer weights after listening begins.

Do not relax stimulus criteria after seeing listener responses.

If the default matching gate cannot produce enough episodes, inspect which **experimental** criterion fails. Change a threshold only with a written scientific reason before recruitment.

Do not add Tune/Bass/Rhythm composer features merely to make the experiment pass.

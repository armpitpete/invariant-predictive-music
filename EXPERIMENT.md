# IPM Listening Experiment 1 — Counterfactual Episode v2

**Status:** pre-listening corpus gate. No human result exists yet and recruitment has not started.

## Question

Does a surprising Tune event that preserves learned melodic invariants and is better integrated by the music that follows produce greater **retrospective sense** than a similarly surprising, weaker-invariant event in the same musical context?

The causal claim under test is:

> learned structure → prediction → one controlled violation → invariant continuity → later music makes the violation fit in retrospect

This pilot tests that mechanism before returning to the full Tune/Bass/Rhythm texture.

## Experimental unit

The unit is an **8-bar Tune-only episode**.

- Bars 1–4: identical learning prefix.
- Bar 5: the only structural intervention.
- Bars 6–8: one common suffix, generated from the IPM target state and then copied unchanged into every condition.

The three versions therefore have:

> **same past → one target-bar intervention → same IPM-conditioned future**

All non-target Tune events must be identical across the three variants.

Bass and Rhythm are absent from Experiment 1. This is an experimental isolation choice, not a new composer mode.

At 58 BPM, an 8-bar episode is about 33 seconds. Twelve trials therefore contain about 6.6 minutes of audio before ratings.

## Conditions

Predictable and IPM are defined by the production engine at one frozen target candidate pool generated from the identical pre-target state:

1. **Predictable** — the engine's existing Expected choice.
2. **IPM** — the engine's existing IPM choice, and it must actually replace Expected.
3. **Unstructured Surprise / Control** — constructed only after the IPM target is fixed.

The Control is **not required to occur naturally in the production candidate pool**. Counterfactual Episode v2 instead:

- freezes the IPM target's structural rhythm pattern;
- starts from the identical pre-target musical state;
- uses an independent deterministic experiment RNG stream;
- generates 64 alternative pitch realisations on that fixed rhythm;
- scores those alternatives against the frozen original target-pool softmax reference, without renormalising or changing the IPM treatment;
- requires Control to match IPM on target surprise and local base musical score;
- requires Control to have weaker learned-invariant similarity.

This removes the v1 requirement to stumble across an exact rhythmic duplicate among the production target candidates.

Listeners never see the condition labels.

## Audible target-rhythm lock

Structural rhythm identity is not sufficient by itself because the production micro-rhythm realiser can consume pitch-dependent random draws.

The experiment layer therefore freezes the IPM target's realised:

- onset/subdivision pattern;
- note durations;
- velocities;
- note count.

Control replays that articulation template while using its own pitch content. IPM and Control therefore differ at the target in pitch, not audible rhythm or accent pattern.

This lock is experiment-only and does not change `micro_rhythm.py` or production composer behaviour.

## Fixed future

The common suffix is generated **once from the state produced by the IPM target**. That exact suffix is then attached to Predictable, IPM and Control.

This is deliberate. The later music is therefore capable, by construction, of integrating the IPM surprise while remaining acoustically identical across conditions.

If each target generated its own future, the conditions would immediately become different musical trajectories and the causal comparison would be lost.

The experiment asks how the **same later music** changes the interpretation of three different target events.

## Future integration

Experiment 1 uses a researcher-side `future_integration` measure.

It is computed only after the actual common suffix exists. It compares the target's melodic interval structure with interval patterns in the suffix and includes the immediate target→suffix pitch connection.

This is distinct from the production engine's prospective `retrospective_coherence` / `retrospective_necessity` selection fields, which are available before later bars exist.

`future_integration` is a stimulus-construction measure, not evidence that a human listener experienced retrospective coherence. The human measure below is the empirical test.

## Frozen pre-listening qualification

The thresholds are unchanged from Counterfactual Episode v1:

- IPM target surprise >= **1.50 bits**;
- IPM/Control target surprise error <= **0.65 bits**;
- IPM-minus-Control local invariant gap >= **0.10**;
- IPM/Control target base-score delta <= **0.10**;
- IPM future integration >= **0.40**;
- IPM-minus-Control future-integration gap >= **0.10**.

A seed is admitted only if all of the following are true before any listener data exists:

- the production target pool is frozen before Control search;
- Predictable and IPM are scored from the identical pre-target state;
- the current IPM selector chooses a non-Expected target;
- the IPM target reaches the frozen surprise threshold;
- Control pitch alternatives are generated from the same pre-target state;
- IPM and Control have the same structural target rhythm;
- a target-surprise-matched alternative exists;
- a sufficiently weaker-invariant alternative exists;
- a base-quality-matched alternative exists;
- at least one alternative satisfies all three local matching constraints together;
- the suffix is generated from the IPM target state;
- IPM reaches the minimum actual-suffix integration score;
- the common suffix integrates IPM more strongly than Control by the frozen gap;
- generated non-target events are identical across all three variants;
- IPM and Control have identical audible target rhythm/articulation.

Seeds are rejected rather than repaired by ear.

Human ratings are never used to decide which stimuli enter the experiment.

## Frozen 512-seed corpus gate

The frozen corpus window is:

- start seed: `2026081800`;
- seed count: `512`;
- final seed: `2026082311`;
- bars: `8`;
- target: bar `5` (zero-indexed bar `4`).

The final articulated v2 constructor is evaluated over **every seed in that window** with no early stop.

Corpus result:

- **213 / 512 seeds qualify**;
- 12 qualified sets are required for the pilot;
- therefore the construction gate passes without threshold relaxation.

Selection funnel:

- 284 seeds: IPM actually replaces Expected;
- all 284 reach fixed-rhythm pitch generation and produce the full 64 alternatives;
- 268 have at least one fully locally matched Control;
- all 268 meet the minimum IPM future-integration threshold;
- 213 also meet the required IPM-minus-Control future-integration gap;
- all 213 accepted episodes pass non-target identity and audible target-rhythm identity.

First rejection cause among failed seeds:

- IPM does not replace Expected: `228`;
- no target-surprise-matched pitch alternative: `1`;
- no sufficiently weaker-invariant pitch alternative: `1`;
- no alternative satisfies all local matching constraints together: `14`;
- common IPM-conditioned suffix fails the required IPM integration advantage: `55`.

The full-window diagnostic is a corpus gate, not a mechanism result. It shows that Counterfactual Episode v2 can construct the required causal contrast robustly under the frozen criteria.

## Pilot corpus

The first 12 qualified seeds remain the frozen pilot set:

`2026081804, 2026081805, 2026081808, 2026081810, 2026081812, 2026081813, 2026081814, 2026081817, 2026081819, 2026081822, 2026081827, 2026081828`

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

The 36-person figure is a pilot recruitment target, not a powered confirmatory sample size. **Recruitment has not started.**

## Selection-funnel record

Every seed examined must remain in the research record whether accepted or rejected.

The corpus record includes:

- starting seed and final seed;
- all 512 attempted seeds;
- every qualification check and metric;
- qualified seed list;
- frozen threshold values;
- exact diagnostic revision;
- rendered-pilot source revision and asset hashes.

This is necessary to show how selective the stimulus filter was.

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

Do not recruit listeners until the pre-listening construction, artifact and review gates are complete.

If the matching gate cannot produce enough episodes in a future revision, inspect which **experimental** criterion fails. Change a threshold only with a written scientific reason before recruitment.

Do not add Tune/Bass/Rhythm composer features merely to make the experiment pass.

# IPM Listening Experiment 1 — Counterfactual Episode v2

**Status:** pre-listening corpus and protocol gate. No human result exists yet and recruitment has not started.

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

The frozen pilot design is:

- 12 qualified episode sets;
- 8 bars per stimulus;
- target = bar 5;
- 58 BPM;
- three condition-assignment groups;
- **36 total enrolments, not 36 usable-complete records**;
- one condition per episode seed per participant;
- across each set of three groups, every seed appears once in every condition;
- each participant receives an independently shuffled trial order;
- participant-facing filenames are opaque hashes.

The 36-person figure is a pilot design choice, not a powered confirmatory sample size. **Recruitment has not started.**

## Frozen rendered-pilot provenance

The authoritative listener stimulus artifact is the exact-head articulated-v2 render:

- stimulus-generator revision: `184105d341366d91919388e298105e4eeb4c13ac`;
- render workflow run: `32120102219`;
- artifact ID: `9318246875`;
- artifact name: `ipm-listening-pilot-v2`;
- artifact SHA-256: `c6246d50f63e178e7eca280d746307a0c563d34c86947231d941af83220f805e`.

At that revision the public `ipm-experiment` entry point resolves to `ipm.experiment_v2_articulation:main`, so the documented CLI and the render workflow use the same final experiment constructor.

A bytewise comparison against the earlier articulated-v2 artifact `9317664611` found every participant stimulus MIDI and WAV to be identical. Only provenance files (`manifest.json` and `researcher/audio-renderer.txt`) differ because they record a different source revision. Artifact `9318246875` therefore supersedes the earlier provenance freeze **without changing any listener stimulus**.

The full frozen 512-seed diagnostic at the same revision is:

- workflow run: `32120102069`;
- artifact ID: `9318415552`;
- artifact SHA-256: `e0f6bac20c3874ccbaed9b5c5f754111b61891552e69cc6461f5af5c685c0a8d`.

The protocol lock is the exact Git commit containing this document after hostile pre-registration review. Protocol-only commits after the stimulus-generator revision do not authorize stimulus regeneration or substitution.

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

## Recruitment stopping rule

Recruitment is frozen as follows:

- participant IDs `P001` through `P036` are the complete enrolment set already represented by the frozen schedules;
- a person becomes **enrolled** when consent is complete and the first main-block stimulus begins playback;
- recruitment closes permanently when `P036` becomes enrolled;
- an enrolled participant who later withdraws, fails playback, duplicates an earlier participant, fails to complete, or has an unusable record is **not replaced**;
- the analysed usable sample may therefore be smaller than 36;
- recruitment must not be extended because an interim effect is small, large, significant, non-significant, surprising, or otherwise interesting;
- no outcome summaries or condition-stratified results may be inspected before recruitment closes and the blinded exclusion lock is complete.

People who consent but leave **before the first main-block stimulus begins** are not enrolled and do not consume a `P001`–`P036` schedule.

## Listening procedure

The participant procedure is fixed before recruitment:

1. Complete consent and participant metadata.
2. Use headphones in a quiet setting. A participant who cannot confirm headphone use does not begin the main block and is not enrolled.
3. Before trial 1, use a non-experimental platform audio check to set a comfortable volume. The check sound is not one of the 36 experimental stimuli.
4. Once the main block begins, keep the listening level unchanged unless adjustment is necessary for safety or discomfort; any such adjustment is recorded as a procedural note but is not by itself an exclusion.
5. Each experimental stimulus plays automatically **once** from the beginning. Seeking and replay are disabled.
6. The rating screen appears only after successful playback reaches the end of the stimulus.
7. All five ratings are required before the next trial can begin.
8. Participants may pause between trials for as long as needed, but may not replay a completed stimulus.
9. The 12-trial order is exactly the participant's frozen schedule. Trials may not be substituted, reordered, skipped, or repeated.

A browser/device interruption during playback that prevents the stimulus from reaching its end is a technical playback failure under the exclusion rule below. A participant should never be asked to judge a partially heard stimulus.

## Human measures

All ratings use an integer 0–100 slider and appear after each episode in the fixed order below.

1. **Retrospective sense — primary mechanism outcome**  
   Exact prompt: **“Thinking about what you heard around the middle of the excerpt: by the end, how much did that moment come to make sense because of what followed?”**  
   `0 = Not at all — what followed did not make it fit.`  
   `100 = Completely — what followed made it fit strongly in retrospect.`
2. **Perceived surprise**  
   Exact prompt: **“How surprising was what you heard around the middle of the excerpt?”**  
   `0 = Not at all surprising.`  
   `100 = Extremely surprising.`
3. **Coherence**  
   Exact prompt: **“How coherent did the excerpt feel as a whole?”**  
   `0 = Not at all coherent.`  
   `100 = Completely coherent.`
4. **Liking**  
   Exact prompt: **“How much did you like this excerpt?”**  
   `0 = Not at all.`  
   `100 = Extremely.`
5. **Desire to hear again**  
   Exact prompt: **“How much would you like to hear this excerpt again?”**  
   `0 = Not at all.`  
   `100 = Very much.`

Record separately before the main block:

- years of music-making experience;
- years of formal musical training.

These variables describe the sample; they are not exclusion criteria and are not included in the frozen primary model.

## Primary test

Primary planned contrast:

> **IPM minus Unstructured Surprise / Control on retrospective sense**

The directional theoretical prediction is positive. Because this is an estimation pilot rather than a confirmatory efficacy test, the primary report is the estimated contrast and its 95% confidence interval rather than a pass/fail p-value threshold.

Secondary contrasts are descriptive and include:

- IPM minus Control on coherence;
- IPM minus Control on liking;
- IPM minus Predictable on liking;
- IPM minus Predictable on retrospective sense.

No secondary outcome can replace retrospective sense as the primary outcome after data collection.

## Manipulation checks

Listener-rated surprise checks are operationalised before data collection.

Use the same fixed-effects and random-effects structure as the primary model, with perceived surprise as the outcome. Report model-adjusted condition contrasts and 95% confidence intervals.

The **predeclared descriptive targets** are:

- IPM and Control are considered approximately surprise-matched when `abs(IPM - Control) <= 10` points on the 0–100 scale;
- IPM is considered meaningfully more surprising than Predictable when `IPM - Predictable >= 10` points;
- Control is considered meaningfully more surprising than Predictable when `Control - Predictable >= 10` points.

These 10-point targets are descriptive operational thresholds, not inferential stopping rules. If any target is missed, report **“surprise manipulation not demonstrated”** for that component and still run and report the frozen primary analysis unchanged.

Do **not** exclude participants or trials, relax stimulus thresholds, choose a different corpus, change the primary model, or reclassify a null/contrary retrospective-sense result because a manipulation check failed.

Absence of an IPM advantage in coherence or retrospective sense is never a manipulation failure. Those are predicted outcomes and null or contrary results count against the theory.

## Frozen analysis

Analyse trial-level data; do not reduce each participant to one grand mean.

### Primary model

The frozen primary model is a linear mixed-effects model:

`retrospective_sense_0_100 ~ condition + trial_position_c + (1 + condition || participant_id) + (1 | episode_seed)`

where:

- `Control` is the condition reference level;
- `trial_position_c` is trial number 1–12 centred on its sample mean and is **always included** as a linear nuisance covariate;
- participant condition slopes are uncorrelated with the participant intercept (`||` formulation);
- episode seed has a random intercept;
- the primary estimand is the model-adjusted **IPM − Control** contrast in retrospective-sense points.

Fit the model by maximum likelihood. Report the point estimate and a two-sided 95% confidence interval, along with convergence and residual diagnostics. This pilot has **no predeclared alpha/significance threshold** for declaring the theory confirmed.

### Frozen convergence fallback

Attempt the primary model first. If, after one refit with a high-iteration derivative-free optimiser, the model either:

- emits a convergence warning; or
- is singular at tolerance `1e-4`,

then use exactly this fallback model:

`retrospective_sense_0_100 ~ condition + trial_position_c + (1 | participant_id) + (1 | episode_seed)`

No other random-effects search is permitted. The fixed effects, primary estimand, reference level, nuisance covariate and 95% interval remain unchanged. Report which model was used and why the fallback was triggered.

### Secondary analyses

Run secondary outcome models using the final random-effects structure selected by the frozen primary/fallback rule and the same fixed condition and centred trial-position terms. Report secondary contrasts with 95% confidence intervals as descriptive estimates. Do not promote a secondary result to primary status.

## Confirmatory study

The pilot is for:

- mechanism failure discovery;
- effect-size estimation;
- variance estimation;
- playback/procedure validation.

A confirmatory sample size and analysis must be frozen from the pilot evidence **before** the confirmatory run begins.

Pilot listeners must not be silently folded into the confirmatory dataset.

## Exclusions fixed before data collection

Exclusion decisions are procedural and must be locked **before condition labels are joined to the response data and before any outcome summary is calculated**. The exclusion reviewer may inspect participant IDs, schedule completion and technical/procedural flags, but not condition assignments or rating values.

Exclude an enrolled participant only for one of these reasons:

1. **Duplicate participation** — the same study-issued identity/recruitment identity is found to have entered the main block more than once. Retain the first session that began the main block and exclude later duplicate sessions.
2. **Failure to complete the main listening block** — fewer than all 12 scheduled stimuli reached successful playback completion with a recorded primary retrospective-sense rating.
3. **Confirmed technical playback failure** — at least one main-block stimulus failed to start, ended early, was inaudible/corrupted, or was interrupted by a browser/device failure before playback completion. The failure must be logged contemporaneously by the platform or participant; it cannot be inferred from an unusual rating pattern.
4. **Unusable response record** — the participant ID cannot be reliably linked to the frozen schedule, the exported record is corrupted/unparseable, or one or more of the 12 primary retrospective-sense ratings cannot be recovered. Missing secondary ratings alone do not make an otherwise usable primary record unusable; any such missingness is reported and the corresponding secondary observation is omitted only from that secondary analysis.

Do **not** exclude participants or trials for flat ratings, negative ratings, unexpected ratings, low musical experience, slow/fast responding, disagreement with IPM, or because their responses weaken the predicted effect.

The final exclusion table must list every enrolled `P001`–`P036`, usable/excluded status and exactly one predeclared reason where excluded. Excluded participants are not replaced.

## Audio-render gate

MIDI remains the deterministic composition object. Human stimuli are the frozen audio from artifact `9318246875`.

The frozen render uses:

- 44.1 kHz stereo 16-bit PCM WAV;
- one fixed FluidSynth/FluidR3_GM rendering path;
- the same loudness-normalisation procedure for every stimulus;
- recorded FluidSynth and FFmpeg versions;
- a hashed soundfont;
- a SHA-256 for every MIDI and WAV.

No listening result is interpretable if a materially different asset is substituted during data collection. A stimulus hash mismatch is a stop condition, not permission to rerender silently.

## Blinding and schedules

The researcher corpus contains:

- condition key;
- qualification audit trail;
- participant→counterbalance-group assignments.

Participant-facing schedule files contain only:

- trial number;
- opaque stimulus ID.

Condition assignment is balanced by three groups, but trial order is independently shuffled for every participant so fatigue/order cannot collapse onto three fixed sequences.

During recruitment and the exclusion lock, the condition key remains separate from participant response records. Unblinding occurs only after recruitment has closed and the exclusion table is frozen.

## Stop conditions

Do not change composer weights after listening begins.

Do not relax stimulus criteria after seeing listener responses.

Do not regenerate, substitute, reorder or relabel listener stimuli after recruitment begins.

Do not inspect outcome summaries or condition-stratified data before recruitment closes and the blinded exclusion lock is complete.

Do not recruit beyond 36 enrolled participants and do not replace exclusions.

Do not recruit listeners until the pre-listening construction, artifact, protocol and hostile-review gates are complete.

If a future revision cannot produce enough matched episodes, inspect which **experimental** criterion fails. Change a threshold only with a written scientific reason before any recruitment for that future revision.

Do not add Tune/Bass/Rhythm composer features merely to make the experiment pass.

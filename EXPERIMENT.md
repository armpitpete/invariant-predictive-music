# IPM Listening Experiment 1 — mechanism-isolation pilot

**Status:** pre-listening gate. No human result exists yet.

## Question

Does the IPM condition produce better listener responses than both a predictable baseline and a surprise-matched weaker-invariant control?

The central prediction is:

> IPM should be preferred to both Predictable and Unstructured Surprise, while IPM and Unstructured Surprise remain similar in perceived surprise and differ in structural coherence / retrospective sense.

## Why Experiment 1 is Tune-only

Bass and Rhythm are disabled through their existing `activity = 0` density governors for this first human experiment.

That is deliberate. Once Tune differs between conditions, independently generated subsidiary events can also differ. If the first experiment retained the full texture, a listener effect could be caused by accompaniment rather than the prediction / invariant / retrospective-integration mechanism.

A later replication should restore the default Tune/Bass/Rhythm texture if the Tune mechanism survives.

## Conditions

Each seed generates the existing three modes from the same high-level configuration:

1. `predictable`
2. `ipm`
3. `unstructured-surprise`

No listener is shown those labels.

## Stimulus qualification

A seed is admitted only before listening and only from generator-side quantities.

Required checks:

- identical seed, tempo, duration, tonic, candidate-pool size and lane controls;
- all engine validation checks pass;
- Predictable selects Expected throughout;
- Bass and Rhythm are silent in all three conditions;
- IPM contains at least three non-Expected bars;
- IPM and Unstructured Surprise are close in modelled surprise burden;
- Unstructured Surprise is lower in invariant similarity on most IPM-surprise bars and lower on average;
- Tune event counts remain close enough to avoid a crude density confound.

Seeds that miss the matching contract are rejected rather than repaired by ear.

Human ratings are never used to decide which stimuli enter the experiment.

## Pilot set

Default build:

- 12 qualified seed sets;
- 16 bars per stimulus;
- 58 BPM unless the production configuration changes before the experiment is frozen;
- three counterbalancing groups;
- each participant hears exactly one condition for each seed;
- across the three groups, every seed is heard once in every condition;
- trial order is deterministically shuffled inside each group;
- condition filenames are opaque hashes.

At 16 bars and 58 BPM, each stimulus is about 66 seconds, so 12 listening trials are about 13 minutes of audio before ratings.

## Human measures

After each stimulus, collect 0–100 ratings for:

- **Liking** — primary outcome;
- coherence;
- perceived surprise;
- retrospective sense: how much unusual moments came to make sense as the music continued;
- desire to hear again.

Record musical training / music-making experience as participant metadata, but do not use it as an exclusion criterion.

## Primary tests

Planned contrasts on **Liking**:

1. IPM > Unstructured Surprise.
2. IPM > Predictable.

The first contrast is the more diagnostic test of the proposed mechanism.

## Manipulation checks

The experiment is not interpretable as an IPM test unless:

- perceived surprise is approximately matched between IPM and Unstructured Surprise;
- both are more surprising than Predictable to a useful degree;
- IPM scores higher than Unstructured Surprise on coherence and retrospective sense.

If listener-rated surprise is not matched, treat the experiment as a failed manipulation rather than evidence for or against IPM.

## Analysis

Use a mixed-effects model rather than collapsing each participant to one mean:

- fixed effect: condition;
- random intercepts: participant and stimulus seed;
- add participant condition slopes if the data support a stable fit;
- report effect estimates and confidence intervals, not only p-values.

The pilot is for effect-size / variance estimation and failure discovery. A default initial recruitment target is **36 complete participants** (12 per counterbalance group). Do not treat that number as a powered confirmatory sample.

A confirmatory sample size must be set from the pilot effect and variance before the confirmatory run starts.

## Exclusions fixed before data collection

Exclude only for predeclared procedural reasons such as:

- duplicate participation;
- failure to complete the main listening block;
- confirmed technical playback failure;
- unusable response record.

Do not exclude people because their ratings are flat, surprising, negative, or contrary to the theory.

## Audio-render gate

MIDI is the reproducible composition object, not the final human stimulus.

Before recruitment, render every admitted MIDI through one fixed synthesizer / soundfont and one fixed sample rate, then loudness-normalise consistently. The rendered audio files, renderer version, soundfont identity and hashes must be frozen with the experiment manifest.

No listening result should be interpreted if participants heard materially different renderers or playback assets.

## Stop conditions

Do not change composer weights after listening begins.

If the matching contract cannot produce enough qualifying seeds, fix the experimental control or relax only a scientifically unjustified threshold **before** collecting listeners. Do not tune the composer against listener responses from this experiment.

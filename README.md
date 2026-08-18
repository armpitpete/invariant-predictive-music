# Invariant Predictive Music

**Invariant Predictive Music (IPM)** is a falsifiable compositional theory embodied in a deterministic three-part musical instrument.

The current architecture is **v0.2**:

- **TUNE** — the predictive melodic world.
- **BASS** — a configurable slow structural lane.
- **RHYTHM** — a configurable short pitched/arpeggiated lane.

All three parts share an abstract scale-degree world and are projected into separate tonic-relative registers. The instrument can therefore transpose without changing the musical identity of a degree or leaking notes between roles.

The authoritative design is [`SPEC.md`](SPEC.md).

## What IPM is testing

IPM does not claim that surprise is good by itself. It tests a narrower proposition:

> A locally surprising continuation should be more successful when it preserves learned structural invariants and becomes strongly justified by what follows.

The Tune engine therefore records, for each bar:

- an expected/predictable baseline;
- candidate prediction probabilities;
- surprise in bits;
- invariant similarity;
- retrospective coherence;
- retrospective necessity;
- the reason the expected or surprising candidate won.

The same high-level configuration can generate three experimental conditions:

1. `predictable`
2. `ipm`
3. `unstructured-surprise`

That makes the central claim testable rather than merely aesthetic.

## Listening Experiment 1

The active pre-listening gate is **Counterfactual Episode v2**, not more composer features.

[`EXPERIMENT.md`](EXPERIMENT.md) defines an 8-bar Tune-only matched episode. Predictable and IPM are selected from the same frozen production target pool after an identical 4-bar learning prefix. Once IPM has been chosen, the experiment layer holds its target rhythm fixed and generates deterministic alternative pitch realisations from the identical pre-target state. The selected Unstructured-Surprise control must match IPM on modelled surprise and local base quality while weakening the learned melodic invariant.

The common 3-bar suffix is generated once from the **IPM target state** and attached unchanged to Predictable, IPM, and Control. The experiment realiser also replays the IPM target's audible subdivisions, durations, and velocities for Control, so IPM and Control differ in target pitch content rather than target rhythm/articulation.

Build the prequalified pilot set with:

```bash
ipm-experiment --output listening-pilot
```

The builder keeps the complete accepted/rejected seed funnel, creates opaque stimulus IDs, generates participant-specific trial orders inside three balanced condition groups, and freezes exact source provenance. GitHub Actions renders admitted MIDI through one fixed soundfont as 44.1 kHz stereo 16-bit WAV and records renderer, soundfont and stimulus hashes.

A corpus diagnostic also evaluates the unchanged qualification thresholds across the entire frozen 512-seed window rather than stopping when the first 12 qualified sets have been found.

The primary human mechanism outcome remains **retrospective sense**: whether the unusual target comes to make sense as the identical, IPM-conditioned suffix unfolds. Liking remains a secondary outcome. No listener result is claimed by the construction gate.

## Musical controls

Bass and Rhythm are instrument parameters, not hard-coded Study behaviour.

Bass exposes:

- `activity`
- `sustain`
- `movement`
- `pattern_complexity`
- `gate`

Rhythm exposes:

- `activity`
- `complexity`
- `syncopation`
- `gate`

`activity` is a real **density governor**. It controls how often that lane receives an opportunity to propose an event, with openings/endings naturally sparser and development/climax naturally more permissive. The endpoints are exact: `0` gives no opportunities and `1` gives every opportunity.

An opportunity is not permission to sound. Bass candidates still compete with a duration-sensitive silence score. A Rhythm motif is accepted only when **every attack** beats silence, so an attractive average cannot hide one unjustified note. Pattern locks are re-screened the same way when re-anchored.

The default density is deliberately sparse enough for **Tune alone to remain the single most common texture**; three simultaneous parts are exceptional rather than the permanent surface.

Patterns are scale-degree-relative rather than fixed MIDI phrases. Subsidiary patterns can be captured, named, locked over a bar window, harmonically re-anchored, and explicitly unlocked.

## Generate the current instrument

```bash
python -m pip install -e '.[dev]'
ipm --output examples
```

Useful controls:

```bash
ipm \
  --mode ipm \
  --bass-activity 0.46 \
  --bass-sustain 0.62 \
  --bass-movement 0.30 \
  --rhythm-activity 0.40
```

Output:

- `examples/ipm-v0.2.mid`
- `examples/ipm-v0.2.trace.json`

The trace is part of the research object. It records the decision evidence as well as the selected music, including density opportunities, silence decisions and actual texture occupancy.

## Historical studies

Studies #001–#011 are preserved as the experimental path that produced the current instrument. They are **not** the v0.2 production architecture and the current engine does not call through them.

Important listening milestones included:

- #001 — failed control: hymn-like, mechanically aligned, emotionally flat.
- #005 — fixed counter-register spikes.
- #008 — whole-bar sequential composition.
- #009 — first musically viable short-note/arpeggiated direction.
- #010 — explicit scalable Tune/Bass/Rhythm architecture.
- #011 — first pattern-lock experiment and shorter Bass vocabulary.

Historical failures remain useful evidence and should not be rewritten to look successful.

## Development

Python 3.11+:

```bash
python -m pip install -e '.[dev]'
pytest
```

CI runs the suite on Python 3.11 and 3.13.

## Epistemic boundary

Passing tests proves deterministic implementation properties; it does **not** prove the musical theory.

The IPM hypothesis requires listener comparison of predictable, IPM, and surprise-matched weak-invariant controls. Numerical weights, consonance priors, density settings and default musical controls remain experimental parameters.

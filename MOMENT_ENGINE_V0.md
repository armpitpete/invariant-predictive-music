# IPM Moment Engine v0 — Prototype Contract

Status: **experimental product surface; separate from the frozen IPM scientific composer**

## Product question

> Does triggering a stored musical gesture feel like playing an instrument rather than operating a sequencer?

The prototype exists to answer that question before hardware, DNA breeding, scale intelligence, AI generation, or a larger sequencing system is designed.

## Core abstraction

The playable atom is a **Moment**: a captured set of MIDI note events with their relative timing, velocity, duration and channel.

A 16-pad vocabulary stores sixteen Moments. A pad trigger renders one whole Moment. A **moment sentence** stores only the order of pad triggers, so composition is built from whole gestures rather than steps.

This is intentionally different from:

- a 16-step sequencer;
- a note arpeggiator;
- a random MIDI generator;
- the existing IPM Tune/Bass/Rhythm whole-piece composer.

## v0 controls

Exactly three transformation controls define the prototype:

1. **REPEAT** — 1–8 complete cycles of the captured Moment.
2. **EVOLVE** — deterministic structural drift across repeats.
3. **SURPRISE → RECOVERY** — a larger deterministic disturbance near the end followed by a recognisable return. Surprise automatically requires at least three repeats in the UI because disruption and recovery need separate cycles.

At REPEAT=1, EVOLVE=0 and SURPRISE=0, triggering a pad reproduces the captured event ledger exactly.

## Mutation invariants

v0 mutation is deliberately conservative.

- deterministic: the same Moment and controls produce the same result;
- no newly invented pitch classes;
- octave displacement is allowed because pitch identity is preserved;
- velocity, gate and bounded timing may move;
- Surprise is not unstructured randomness;
- the final cycle is pulled back toward the source after a Surprise event.

The engine therefore tests controlled musical memory before any harmonic-intelligence layer is added.

## Interaction contract

- 16 pads, keyboard-addressable as `1 2 3 4 / Q W E R / A S D F / Z X C V`;
- click or shortcut triggers a stored Moment as one object;
- one selected pad can be armed for MIDI recording;
- recording begins on the first MIDI note;
- stopping stores the completed gesture in that pad;
- overwriting or clearing a stored Moment requires an explicit confirmation in the UI;
- Chain Capture records the order of Moment triggers, not note steps;
- Play Chain renders the sentence of whole Moments;
- vocabulary and chain are persisted to `~/.ipm-moment/session.json` by default;
- vocabulary can be exported as JSON.

## Sound boundary

The browser includes a deliberately simple WebAudio audition voice so the interaction can be tested without external hardware. It is **not** an accepted IPM product synthesizer and must not be used to judge the existing Machine synth replacement gate.

For musical evaluation, MIDI output should be routed to a real hardware or software synthesizer.

## Deliberate omissions

v0 does not contain:

- a piano keyboard UI;
- a step grid;
- note-by-note editing;
- scales/chord detection;
- generative AI;
- probabilistic note invention;
- Moment DNA breeding;
- multi-lane phase engines;
- hardware design;
- integration into the scientific IPM Tune scoring formula.

Those are blocked until the playable-atom question has a human answer.

## Acceptance gate

Use the prototype with a real MIDI controller and preferred synth.

Create at least four genuinely different Moments, then play them from the pads and build one short sentence without editing individual notes.

Answer only this question:

> **After a few minutes, do the Moments begin to feel like playable musical objects — something closer to notes or words — rather than saved MIDI clips?**

Allowed result: **PASS / MIXED / FAIL**.

- **PASS** → keep the abstraction and design the next mutation/memory layer.
- **MIXED** → identify the smallest interaction that still feels clip-like; do not add features yet.
- **FAIL** → stop. Do not rescue the idea by turning it into a more complicated sequencer.

# Real Synth Engine v3 — Patch-Range Re-Audition Contract

Status: **FROZEN BEFORE RE-AUDITION**

## Prior human result

The first v3 human engine audition is **FAIL**.

Owner judgment:

> 1st 2 sound the same

This specifically rejects `crystal-motion` vs `warm-poly` as a convincing demonstration of instrument range. It does **not** yet demonstrate that the underlying patch-driven engine is incapable of range; both patches shared a broadly similar subtractive/unison/low-pass character.

Machine PLAY/FINISH remains blocked from v3 promotion.

## Protected interpretation

For this re-audition:

- do not change IPM composition;
- do not change the v3 DSP engine;
- do not select another musical seed;
- do not use effects-heavy production to manufacture apparent distinction;
- change patch data only;
- keep the exact previously frozen 122-event Tune ledger.

If deliberately orthogonal patch data still does not yield perceptually distinct instruments, that is evidence against the sufficiency of the v3 engine itself and the next gate must be engine redesign rather than further preset tuning.

## Frozen source

- root seed: `987762706`
- Activity: `0.50`
- Surprise: `0.50`
- candidate count: `5`
- expected selected seed: `1693196453`
- expected Tune event count: `122`
- expected Tune ledger SHA-256: `1bee94ac3d65ce6a01efd6ec2921f2cae82238ddbeaaab79fcee38dc4726bd31`

## Required patch families

Exactly three Tune patches will be rendered through the unchanged `RealSynthEngine`.

### A — dry subtractive pluck

Purpose: short, percussive, harmonically rich analog-like articulation.

Required character:

- saw/pulse oscillator family;
- low-pass filtering with strong filter-envelope movement;
- fast attack and short decay;
- low sustain;
- one voice or minimal unison;
- effectively dry: no chorus or delay and only negligible room send.

### B — hollow sustained organ/reed

Purpose: sustained, hollow, breath/reed-like tone whose identity comes from steady partial structure rather than a pluck transient.

Required character:

- pulse/triangle or square/triangle family;
- clearly sustained amplitude envelope;
- notch or band-pass filtering rather than the pluck's low-pass contour;
- subtle slow pitch or timbral movement only;
- no unison wash;
- effectively dry.

### C — metallic FM bell

Purpose: inharmonic/metallic struck character from FM rather than subtractive waveform filtering.

Required character:

- sine carrier/modulator architecture;
- strong FM amount;
- immediate attack;
- long decaying tail with zero or near-zero sustain;
- band-pass filtering permitted;
- no chorus; at most modest room send.

## Technical assertions

The audition harness must abort unless:

1. the source selected seed is exactly `1693196453`;
2. the Tune ledger hash is exactly the frozen SHA-256 above;
3. all three renders use the same `RealSynthEngine` implementation;
4. only patch data differs between the three Tune renders;
5. all three WAV hashes differ;
6. the source Tune ledger remains unchanged after every render.

## Human gate

Listen without being told which sound should be preferred.

Question:

> **Do these now sound like three clearly different instruments made by one synthesizer engine, rather than closely related variations of one synth voice?**

Allowed judgment: **PASS** or **FAIL**.

A FAIL blocks Machine promotion and ends patch-only rescue attempts for this engine version. The next work would be v4 engine architecture, not another set of v3 presets.

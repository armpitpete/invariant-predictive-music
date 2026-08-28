# RealSynthEngine v4R1 — Redesign Contract Hostile Review v0.1

Status: **DESIGN REVIEW BEFORE IMPLEMENTATION**

Reviewed contract commit: `a326aeb42deba668d4cfe06425b52cc2aeca2861`

## Verdict

**REVISE BEFORE IMPLEMENTATION.**

The v0.1 redesign is directionally correct, especially the reversal of control/evolution gate order, but it contains four weaknesses that could let v4R1 pass mechanically without fixing the actual ambiguity exposed by failed Gate D.

## Finding 1 — direction without minimum authority repeats the old weakness

v0.1 requires macro diagnostics to move in the intended direction, but a tiny mathematically correct movement can satisfy a direction check while remaining inaudible.

That is exactly the class of ambiguity exposed by Gate D: nonzero automation and different WAV bytes did not imply coherent audible development.

### Required correction

Before any v4R1 implementation output is inspected, freeze a separate **control diagnostics specification** that defines both:

- semantic direction; and
- a minimum effect-size threshold for the low/high control endpoints.

Human R-D remains necessary; mechanical effect size is a prerequisite, not a substitute.

## Finding 2 — the 1/2/3 curve-count rule is arbitrary

Requiring one note, two phrase and three piece curves risks replacing the failed underpowered fixture with an over-specified fixture chosen because v2 happened to be richer.

Gate D proved that its exact one-target-per-scope design failed. It did not prove a universal minimum number of curves per scope.

### Required correction

Require:

- at least one nonzero curve at each scope: note, phrase, piece;
- at least three independent perceptual dimensions across the full evolution design;
- every target to have already passed R-D with full human `PASS`;
- no fixed minimum of two phrase or three piece curves.

This preserves breadth without pretending the failed evidence established a universal curve count.

## Finding 3 — ATTACK has different temporal semantics from continuous macros

The v0.1 wording could be read as requiring every macro to continuously affect already sounding voices.

That is wrong for ATTACK: once a note has passed its attack stage, changing an attack-time control cannot retroactively alter that attack without violating ordinary instrument semantics.

### Required correction

Freeze macro application classes:

- continuous where meaningful: `BRIGHTNESS`, `BODY`, `MOTION`, `CHARACTER`, `DRIVE`, `WIDTH`, `SPACE`;
- event/retrigger boundary: `ATTACK` may determine articulation for newly started/retriggered notes and need not rewrite an already completed attack.

Evolution may still target ATTACK across a phrase/piece by changing articulation of subsequent written notes.

## Finding 4 — partial technical regression is too weak for a new version

v0.1 describes R-B as re-running technical properties “affected by the delta.” A source change can cause regressions outside the obvious delta.

### Required correction

v4R1 must re-run the **complete v4 Gate A and B technical contract** at its exact implementation head, then add v4R1-specific tests on top.

Historical v4 PASS is provenance, not a waiver.

## Finding 5 — root cause must remain plural until diagnostics close it

The failure analysis correctly preserves competing explanations. Implementation must not be described as a confirmed fix for one cause until pre-audition diagnostics support that classification.

The revision should therefore use language such as “architecture corrections designed to eliminate known ambiguity,” not claim that control weakness alone caused the failed human result.

## Acceptance of review

A superseding v0.2 contract should incorporate all five findings before any v4R1 synthesis source is changed.

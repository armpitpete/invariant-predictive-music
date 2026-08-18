# Listening Experiment 1 — Participant Interface Contract

**Status:** participant-facing pre-recruitment implementation gate passed at exact implementation head `94fb37ab37077346d6de585df5ee1d69ae23d009`. This does not authorize recruitment by itself.

This is the participant-facing implementation contract for the frozen Counterfactual Episode v2 pilot in `EXPERIMENT.md`.

## Frozen trust anchor

The interface may use only listener artifact:

- source revision: `25625299d09c8db2c84a5f88de7f4ec3a6198fe6`;
- workflow run: `32123921259`;
- artifact ID: `9319656473`;
- artifact SHA-256: `356e8882a73df91ed178bf2b902c03b90532f855c6c13bde251b637efc48d47d`.

`participant-ui/frozen-participant-contract.json` pins every one of the 36 WAV hashes, every P001–P036 source-schedule hash, participant/counterbalance assignments, both export schemas, consent text and rating prompts. The participant build fails on byte drift.

Participant-interface code may advance beyond the stimulus source revision without reopening the musical construction only while the WAVs, schedules and schemas continue to reproduce this frozen trust anchor exactly.

## Participant-safe bundle

The standalone `participant-web` bundle contains only generic UI assets, the 36 opaque WAVs, participant-safe P001–P036 schedules, schema headers and bundle provenance/hashes. It must not include the researcher condition key, qualification audits, condition names, target metrics or seed-to-condition mapping.

Each participant enters through `?participant=P001` through `?participant=P036`. The browser loads only that participant's frozen schedule. Each scheduled trial contains only trial number, opaque stimulus ID and the expected frozen WAV SHA-256.

## Consent before the main block

Consent version is `music-listening-study-consent-v1`.

Participant information:

> You will listen to 12 short musical excerpts, each about 33 seconds, through headphones and rate each excerpt on five 0–100 scales. The main listening block contains about 7 minutes of audio and usually takes longer once ratings are included.
>
> There are no right or wrong answers. Please answer based on what you hear.
>
> Participation is voluntary. You can stop at any time. If you stop after the main listening block begins, the session will be marked incomplete.
>
> This study interface uses only your study participant ID and asks for years of music-making and formal musical training. It does not ask for your name or email.
>
> The interface does not automatically transmit your responses. At the end it creates a study export file for the researcher. Ask the person who invited you if you have questions about the study or how the export will be handled.

Required affirmations:

1. “I have read the information above and understand what taking part involves.”
2. “I understand that taking part is voluntary and that I can stop at any time.”
3. “I agree to take part in this music listening study.”
4. “I am using headphones in a quiet setting.”

Music-making and formal-training years are required numeric metadata; blank fields are rejected rather than coerced to zero. Consent version, accepted items and timestamp are written to the final export.

This operational consent screen is not a claim of institutional ethics approval and does not invent sponsor, retention or legal-basis information that the project has not established.

## Audio check and enrolment boundary

Before the main block, the interface plays a non-experimental 440 Hz check tone and requires confirmation that playback is audible and comfortable.

Consent and the audio check merely **arm** the main block. Under the frozen preregistration, the participant becomes enrolled only when the correctly scheduled, hash-verified **trial-1 WAV begins playback**. That moment records `main_block_started` and `enrolled_at_utc`. Someone who leaves before trial-1 playback begins is not enrolled.

## Single-play and reload enforcement

For each frozen trial:

1. fetch the scheduled opaque WAV;
2. calculate SHA-256 over the delivered bytes using browser WebCrypto;
3. refuse playback unless it equals the frozen schedule digest;
4. expose one play action only, with no native audio controls;
5. hold playback rate at 1× and treat seeking as a technical playback failure;
6. persist the study state immediately when playback starts;
7. expose ratings only after end-of-playback;
8. require all five ratings to be actively touched before advancing;
9. advance only to the next item in the frozen schedule.

Participant state is persisted in browser storage under a key tied to participant ID, frozen source-schedule SHA and frozen artifact SHA. Reload behavior is conservative:

- reload **during playback** → terminal technical playback failure; the excerpt cannot restart;
- reload **after playback while rating** → restore the rating screen with no replay;
- reload **between trials** → restore the next frozen trial;
- reload **after completion/withdrawal/failure** → restore the terminal state; the study cannot restart.

A participant may stop the study. A stop or technical failure terminates that browser study state rather than restarting or replacing a trial. Cross-device/cleared-storage duplicate participation is a recruitment/exclusion control, not something a static browser bundle can prove; it remains governed by the frozen duplicate-participation rule.

The interface also requires browser persistent storage and WebCrypto. Deployment must therefore use a secure context such as HTTPS.

## Exact rating prompts

The page reads these directly from the frozen participant contract, in this order:

1. **Retrospective sense** — “Thinking about what you heard around the middle of the excerpt: by the end, how much did that moment come to make sense because of what followed?”
   - 0: “Not at all — what followed did not make it fit.”
   - 100: “Completely — what followed made it fit strongly in retrospect.”
2. **Perceived surprise** — “How surprising was what you heard around the middle of the excerpt?”
   - 0: “Not at all surprising.”
   - 100: “Extremely surprising.”
3. **Coherence** — “How coherent did the excerpt feel as a whole?”
   - 0: “Not at all coherent.”
   - 100: “Completely coherent.”
4. **Liking** — “How much did you like this excerpt?”
   - 0: “Not at all.”
   - 100: “Extremely.”
5. **Desire to hear again** — “How much would you like to hear this excerpt again?”
   - 0: “Not at all.”
   - 100: “Very much.”

Every response is an integer 0–100.

## Data export

The interface does not automatically transmit data. At completion, withdrawal or technical failure it can download one JSON study export containing frozen artifact and schedule provenance, consent, participant metadata, procedural state, ordered trial responses, audit events, and exact-schema `participant.csv` / `responses.csv` text.

`duplicate_participation`, `record_usable` and `exclusion_reason` remain blank participant-side. They belong to the later blinded researcher exclusion lock.

## Exact-head pre-recruitment evidence

Participant implementation head:

`94fb37ab37077346d6de585df5ee1d69ae23d009`

Workflow `participant-listening-gate` run `32127364426`: **success**.

Frozen participant bundle:

- artifact: `ipm-participant-web-v1`;
- artifact ID: `9321126844`;
- artifact SHA-256: `ab61b0d89db85dc17458c38df518e238748ea8e0f6a15a5448fca7f0a84ae6aa`.

Gate evidence:

- artifact: `participant-interface-gate`;
- artifact ID: `9321127149`;
- artifact SHA-256: `f86bf24c0dccc3f1bbe842717890e36c5037d81b6abca3973094be933b287e6c`.

The Python artifact dry-run passed **36 / 36 participant schedules and 432 / 432 trial assignments**, verifying all frozen WAV/schedule/schema hashes and counterbalance assignments.

The JavaScript state-machine dry-run passed **36 / 36 and 432 / 432**, including blank-metadata rejection, first-play enrolment, replay rejection, restored playback/rating/between-trial state, completion restart rejection, frozen response order and a representative P001 export.

A pinned Playwright `1.55.0` / Chromium browser acceptance then ran synthetic non-human sessions for P001, P002 and P003 (counterbalance groups 1, 2 and 3). Together those sessions covered all **36 unique frozen stimuli** through the actual browser path. All 36 trials:

- were fetched exactly once in the scheduled order;
- passed browser WebCrypto WAV-digest verification;
- played through the real audio element to natural `ended` before ratings became available;
- took approximately 33.46–33.61 seconds wall-clock per excerpt;
- produced 12 ordered response rows and a completed export per synthetic session.

The browser exports contain no condition labels or frozen episode seeds, leave researcher exclusion fields blank, preserve the exact CSV headers, and record `enrolled_at_utc`, `main_block_started` and first `playback_started` at the same trial-1 boundary.

Independent download inspection reproduced both GitHub artifact ZIP digests and found **0 / 36 WAV hash mismatches, 0 / 36 schedule-provenance mismatches, 0 bundle-manifest mismatches, and 0 condition/seed mapping leaks**. Consent, rating config and both schemas reproduce the frozen participant contract exactly.

At implementation head `94fb37ab…` the ordinary test, render, diagnostic and participant-listening workflows all pass. No actual listener was recruited by any acceptance test.

The current branch may contain documentation-only descendants that record this evidence. They do not supersede the implementation/artifact freeze unless participant code, workflow, trust-anchor files or assets change and the gate is rerun.

## Recruitment boundary

The participant-facing implementation gate is complete, but recruitment is still blocked on a separate deployment/data-collection gate. That gate must establish the actual HTTPS host, participant-ID allocation and cross-device duplicate control, study contact details, export-return/data-handling procedure, and any applicable ethics/privacy governance.

Merge and recruitment remain separate owner decisions.

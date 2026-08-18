# Listening Experiment 1 — Participant Interface Contract

**Status:** pre-recruitment implementation gate. This document does not authorize recruitment by itself.

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

## Automated pre-recruitment dry-run

The participant workflow rebuilds and PCM-renders the exact-head pilot rather than copying the old artifact. It may build the participant bundle only after the fresh assets reproduce the frozen WAV, schedule and schema hashes.

The Python artifact dry-run checks P001–P036, all 36 WAV hashes, all 36 source schedule hashes, 12 trials each / 432 total assignments, 36 opaque stimuli, counterbalance assignments, schemas, absence of researcher condition labels and frozen response order.

The JavaScript dry-run uses the same `StudySession` state machine as the browser for all 36 schedules and checks:

- consent/audio check before the main block;
- blank metadata rejection;
- `enrolled_at_utc` remains empty until trial-1 playback starts;
- one-play state and ratings-after-ended;
- restored in-play state cannot replay;
- restored rating state cannot replay;
- between-trial state resumes at the correct next trial;
- completed state cannot restart;
- exact frozen response order and CSV headers;
- a representative P001 final export.

Both dry-runs must pass 36 participants / 432 trials.

## Recruitment boundary

No actual participant may be recruited until an exact participant-interface head has green ordinary tests and participant-gate CI; the standalone participant bundle and evidence artifacts have been independently inspected; all 36 WAV and P001–P036 schedule hashes reproduce the frozen trust anchor; the P001 dry-run export matches the frozen schemas; and the exact participant-web artifact ID/SHA is frozen in the PR record.

A separate deployment/data-collection gate must still establish the actual HTTPS host, participant-ID allocation/duplicate control, study contact and export-return/data-handling procedure. Merge and recruitment remain separate owner decisions.

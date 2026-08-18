# Listening Experiment 1 — Participant Interface Contract

**Status:** pre-recruitment implementation gate. This document does not authorize recruitment by itself.

This is the participant-facing implementation contract for the frozen Counterfactual Episode v2 pilot described in `EXPERIMENT.md`.

## Frozen trust anchor

The participant interface is built only from listener artifact:

- source revision: `25625299d09c8db2c84a5f88de7f4ec3a6198fe6`;
- workflow run: `32123921259`;
- artifact ID: `9319656473`;
- artifact SHA-256: `356e8882a73df91ed178bf2b902c03b90532f855c6c13bde251b637efc48d47d`.

`participant-ui/frozen-participant-contract.json` records the SHA-256 of all 36 frozen WAV files, all P001–P036 schedule CSVs, and both export schemas. The participant build must fail if any of those bytes change.

A later source revision may change participant-interface code without reopening the stimulus construction only when the current WAVs, schedules and schemas still reproduce those frozen hashes exactly.

## Participant-safe bundle

The build creates a separate standalone `participant-web` bundle. It contains only:

- generic participant UI assets;
- the 36 opaque WAV stimuli;
- P001–P036 participant-safe schedules;
- participant and response schema headers;
- bundle provenance and file hashes.

It must not contain the researcher condition key, qualification audits, condition names, target metrics or seed-to-condition mapping.

Each participant-specific URL uses `?participant=P001` through `?participant=P036`. The page loads only the frozen schedule for that participant ID. Schedules expose trial number, opaque stimulus ID, the frozen source-schedule SHA-256 and the expected WAV SHA-256.

## Consent shown before enrolment

The exact participant information is versioned as `music-listening-study-consent-v1` in the frozen participant contract:

> You will listen to 12 short musical excerpts, each about 33 seconds, through headphones and rate each excerpt on five 0–100 scales. The main listening block contains about 7 minutes of audio and usually takes longer once ratings are included.
>
> There are no right or wrong answers. Please answer based on what you hear.
>
> Participation is voluntary. You can stop at any time. If you stop after the main listening block begins, the session will be marked incomplete.
>
> This study interface uses only your study participant ID and asks for years of music-making and formal musical training. It does not ask for your name or email.
>
> The interface does not automatically transmit your responses. At the end it creates a study export file for the researcher. Ask the person who invited you if you have questions about the study or how the export will be handled.

Before the audio check, the participant must affirm all three statements:

1. “I have read the information above and understand what taking part involves.”
2. “I understand that taking part is voluntary and that I can stop at any time.”
3. “I agree to take part in this music listening study.”

They must also confirm:

> “I am using headphones in a quiet setting.”

Consent acceptance time, consent version and accepted items are written into the final study export.

This operational consent screen is not a claim of institutional ethics approval and does not invent sponsor, retention or legal-basis information that the project has not established.

## Pre-block audio check

Before enrolment, the interface plays a short non-experimental 440 Hz check tone. The participant must confirm that it is audible and comfortable.

Only after consent and the audio check are complete may the participant start the main listening block. The `main_block_started` event is the enrolment boundary defined in `EXPERIMENT.md`.

## Trial enforcement

For each of the 12 frozen trials:

1. The interface fetches the scheduled opaque WAV file.
2. Browser WebCrypto computes SHA-256 over the delivered bytes.
3. Playback is refused unless that digest matches the frozen digest in the participant schedule.
4. The participant receives one play action only.
5. Native audio controls are not exposed.
6. Playback rate is held at 1×.
7. Seeking is treated as a technical playback failure.
8. Rating controls remain inaccessible until the browser reports end-of-playback.
9. The five ratings must all be actively touched before the trial can advance.
10. The next stimulus is exactly the next item in the frozen schedule; substitution, reordering and replay are not supported.

A participant may stop the study. A stop or technical playback failure terminates the session rather than restarting or replacing a trial.

## Exact rating prompts

The participant page reads these directly from the frozen participant contract and shows them in this order after every episode:

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

Every response is an integer from 0 to 100.

## Data export

The interface does not automatically transmit participant data. At completion, withdrawal or technical failure it can create one JSON study export containing:

- frozen listener-artifact provenance;
- frozen schedule SHA-256;
- consent version, accepted items and timestamp;
- participant metadata;
- participant procedural row;
- ordered trial response rows;
- playback/rating audit events;
- `participant.csv` text with the exact frozen participant-schema header;
- `responses.csv` text with the exact frozen response-schema header.

The participant-facing interface leaves `duplicate_participation`, `record_usable` and `exclusion_reason` blank. Those fields belong to the later blinded researcher exclusion lock rather than participant-side judgement.

## Automated pre-recruitment dry-run

The participant gate must run two independent dry-runs against the freshly rendered exact-head pilot while checking every asset against the frozen trust anchor.

### Python artifact dry-run

`ipm.experiment_participant` must verify:

- exactly P001–P036;
- all 36 source schedule SHA-256 values;
- all 36 frozen WAV SHA-256 values;
- exactly 12 trials per participant and 432 total trial assignments;
- exactly 36 opaque stimuli;
- frozen participant/response schemas;
- unchanged counterbalance-group assignments;
- no researcher condition labels in generated participant config/schedules;
- export row order equals each frozen participant schedule.

### JavaScript state-machine dry-run

`participant-ui/dry-run.mjs` uses the exact browser state machine for all 36 schedules and must prove:

- enrolment cannot start before consent and audio check;
- ratings cannot be submitted before playback completion;
- a second play cannot start for the current trial;
- the scheduled stimulus ID and frozen WAV digest are mandatory;
- each participant reaches exactly 12 response rows in frozen order;
- exported CSV headers exactly match the frozen schemas.

The gate passes only when both dry-runs report 36 participants and 432 trials with no failure.

## Recruitment boundary

No actual participant may be recruited until:

- this participant implementation is present at one exact Git head;
- exact-head tests pass;
- the participant gate workflow passes;
- the standalone participant-web artifact is downloaded and independently inspected;
- its 36 WAVs reproduce the frozen listener hashes;
- its P001–P036 schedules reproduce the frozen schedule hashes and expose no condition labels;
- one exported dry-run record is checked against the frozen schemas;
- the exact participant-web artifact ID and SHA-256 are frozen in the PR record.

Merge and recruitment remain separate owner decisions.

# Deployment / data-collection gate status — 18 August 2026

## Current authority

The original participant implementation/deployment is **rejected for participant use** after an owner real-device QA run exposed a WebKit-style user-activation failure before trial-1 audio began.

Current authoritative participant interface evidence revision:

`e6b07579878350c80fb6548107290898b48501ca`

Current authoritative participant bundle:

- artifact `ipm-participant-web-v3` / `9328095073`
- artifact SHA-256 `1e512e85fea0e90f1e03791897803a28d264be9a5c3a8569def9324a1d5364c6`
- participant gate run `32145307925`: **PASS**

Current participant-interface evidence:

- artifact `participant-interface-gate-v3` / `9328095794`
- artifact SHA-256 `54d802b265c29cca853f894d46be3a3ff2c4502e7b2b8f61ba1961f0f810d501`

All 36 WAVs and all 36 P001–P036 schedules remain byte-identical to the previously frozen scientific stimulus/schedule set. The repair changed participant delivery/provenance only.

## Owner real-device QA finding

An owner-only P001 test on the superseded v1 deployment reached trial 1 but the browser rejected `HTMLMediaElement.play()` with a user-agent/platform permission error before audible experimental playback began.

Hostile review found two participant-layer defects in v1:

1. the click handler awaited WAV fetch/hash work before calling `audio.play()`, allowing Safari/WebKit user activation to expire;
2. the app logged `main_block_started`, `playback_started` and `enrolled_at_utc` before confirming that media playback had actually begun.

Therefore the owner QA export is **not a real participant record and not a real enrolment under the frozen protocol**. It is not committed as study data.

The repair now:

- fetches and SHA-verifies the frozen WAV before enabling the trial Play button;
- calls `audio.play()` directly in the subsequent trusted click task with no preceding await;
- records enrolment/playback start only after the browser reports successful actual playback start;
- leaves a rejected pre-start playback attempt unenrolled;
- uses interface-revision-bound browser storage so superseded saved state cannot contaminate a repaired deployment.

The browser acceptance gate removed the prior autoplay-policy bypass and actively rejects any media `play()` call that escapes the trusted click task. P001/P002/P003 then passed all 36 real Chromium playback trials.

## Export provenance repair

The direct-play repair was first frozen as participant v2, but that version was immediately superseded because its returned JSON did not identify the participant-interface revision. Since v1 and v2 intentionally shared the same scientific audio/schedules, intake could not mechanically distinguish a complete old-interface export from a repaired-interface export.

Participant v3 closes that gap:

- `export_version = 2`;
- every export includes `participant_interface_source_revision`;
- saved session snapshots include and enforce the same revision;
- researcher intake rejects export version 1 and any interface revision that does not exactly match the authorised participant bundle.

## Data-control half: PASS on v3

Evidence-bearing CI run: `32147376085`.

Artifact: `data-collection-control-gate-v3` / `9328321516`.

Artifact SHA-256: `5d84067b8a1f756f69c416a63c662674056095214205ff5580b15a96638c1eb9`.

The v3 control gate uses participant artifact `9328095073` and participant-browser evidence `9328095794`. It passes:

- exact P001–P036 initialization;
- atomic one-time reservation;
- P001/P002/P003 synthetic intake;
- exact interface/listener-artifact/schedule/WAV/export validation;
- central-reservation enforcement;
- rejection of superseded export version 1 and wrong interface revision;
- content-addressed raw evidence preservation;
- idempotent re-ingest;
- cross-device duplicate ordering in which earliest actual `enrolled_at_utc` remains canonical while every distinct submission is retained.

Study contact / response-return mailbox: `merrin@merrinworld.uk`.

Gmail study label: `IPM Listening Study/Responses`.

Private researcher storage: Google Drive folder `IPM Listening Study - Private Data`, folder ID `1LJySie2I_gwCaf3UKLQZ--aP8fyO8bfX`; when verified it was unshared with owner `merrin@merrinworld.uk` as the sole permission.

## Hosting half: PASS on v3

Evidence-bearing deployment run: `32147297192`.

Deployment workflow revision: `6ca0b5d8d68da349117872eaee58edaebeeb58a1`.

Authoritative content-addressed HTTPS study URL:

`https://armpitpete.github.io/invariant-predictive-music/freeze-1e512e85fea0e90f1e03791897803a28d264be9a5c3a8569def9324a1d5364c6/`

Deployment evidence:

- exact participant artifact `9328095073` retrieved and verified before deployment;
- **79 / 79** deployed manifest files fetched back over HTTPS and SHA-256 verified, 0 mismatches;
- synthetic P001/P002/P003 covered counterbalance groups 1/2/3 and all 36 unique stimuli;
- **36 / 36** deployed browser trials reached natural audio `ended`;
- browser WebCrypto delivery hashes passed;
- direct-user-gesture playback gate passed with **no autoplay-policy override**;
- deployed returned exports were version 2 and carried exact interface revision `e6b07579878350c80fb6548107290898b48501ca`;
- no condition-mapping leak;
- 0 real participants recruited.

Deployment evidence artifact: `deployed-listening-gate-v3` / `9328666559`.

Artifact SHA-256: `a5ec5b4923958166f5d47bedd352824d98ceb541f8cda6e16e891160b629eae5`.

## Superseded participant artifacts / URLs

Do not use for participants:

- v1 artifact `9321126844`, SHA `ab61b0d89db85dc17458c38df518e238748ea8e0f6a15a5448fca7f0a84ae6aa`: rejected after real-device playback/user-activation defect and false pre-play enrolment audit;
- v2 artifact `9326978102`, SHA `7f17c97d628adb4f4ddc6ef5233b29f6b5fc282d366790593cc6dbb2674b65f2`: direct-play repair passed CI/deployment but superseded because returned exports lacked participant-interface revision provenance.

Only the v3 content-addressed deployment above is authorised for further owner QA.

## Remaining gate: same-context owner retest

Automated participant, collection and deployed-browser v3 gates pass. Because the defect was discovered on an actual user device/context that Chromium CI did not reproduce, the technical gate remains conservatively **open** until the repaired v3 URL is checked again on that same class of real device/browser.

Required owner QA evidence:

- trial-1 Play tap audibly starts the excerpt without `NotAllowedError`;
- if an export is produced, it has `export_version: 2` and participant interface revision `e6b07579878350c80fb6548107290898b48501ca`;
- `enrolled_at_utc`, first `main_block_started` and first `playback_started` appear only if actual playback begins.

This is owner QA, not recruitment.

## Governance / recruitment / merge

The operational privacy/invitation template is `researcher/invitation-template.md`; UK governance scope is recorded in `DATA_COLLECTION.md`.

Even after the same-context owner retest passes, recruitment remains blocked until the owner closes the factual governance checklist: controller/sponsorship context, ICO data-protection-fee assessment, applicable ethics/institutional requirement or independent status, and mailbox MFA/forwarding/delegation state.

No real participant has been recruited. PR #24 remains draft and unmerged.

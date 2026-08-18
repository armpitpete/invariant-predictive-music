# Deployment / data-collection gate status — 18 August 2026

Current authoritative participant interface evidence revision: `e6b07579878350c80fb6548107290898b48501ca`.

Participant v3 artifact: `9328095073`, SHA-256 `1e512e85fea0e90f1e03791897803a28d264be9a5c3a8569def9324a1d5364c6`. Participant evidence: `9328095794`, SHA-256 `54d802b265c29cca853f894d46be3a3ff2c4502e7b2b8f61ba1961f0f810d501`. Participant gate run `32145307925`: PASS.

Data-control v3 run `32147376085`: PASS. Evidence artifact `9328321516`, SHA-256 `5d84067b8a1f756f69c416a63c662674056095214205ff5580b15a96638c1eb9`.

Deployment v3 run `32147297192`: PASS. Evidence artifact `9328666559`, SHA-256 `a5ec5b4923958166f5d47bedd352824d98ceb541f8cda6e16e891160b629eae5`.

Authoritative v3 owner-QA URL:

`https://armpitpete.github.io/invariant-predictive-music/freeze-1e512e85fea0e90f1e03791897803a28d264be9a5c3a8569def9324a1d5364c6/`

The v1 participant artifact/deployment is rejected: an owner real-device test showed a user-agent media-playback rejection before trial-1 audio began, while the old interface incorrectly logged enrolment/playback start before `audio.play()` had succeeded. The v2 direct-play repair is superseded because its export did not include participant-interface revision provenance.

Participant v3 fetches and SHA-verifies each frozen WAV before enabling Play; calls `audio.play()` in the trusted click task; leaves pre-start playback rejection unenrolled; binds saved state to the interface revision; returns export version 2 with the exact interface revision; and researcher intake rejects superseded/wrong-revision exports. All 36 WAVs and all 36 schedules remain byte-identical to the frozen scientific set.

Automated v3 participant, data-control, HTTPS 79/79 byte verification and deployed P001/P002/P003 browser gates all pass, with no autoplay-policy override and 0 real participants recruited.

**Overall technical pre-recruitment gate remains OPEN only for the same-class real-device/browser owner retest of v3.** Required evidence: trial-1 Play audibly starts without `NotAllowedError`; any returned export is version 2 with interface revision `e6b07579878350c80fb6548107290898b48501ca`; enrolment/start events exist only if actual playback begins.

This is owner QA, not recruitment. After it passes, governance owner checks still remain: controller/sponsorship context, ICO fee assessment, applicable ethics/institutional status, and mailbox MFA/forwarding/delegation. PR #24 remains draft and unmerged; no recruitment is authorised.

# Deployment / data-collection gate status — 18 August 2026

See commit history for prior superseded versions. Current authoritative participant interface evidence revision is `e6b07579878350c80fb6548107290898b48501ca`, participant artifact `9328095073` SHA-256 `1e512e85fea0e90f1e03791897803a28d264be9a5c3a8569def9324a1d5364c6`, participant evidence artifact `9328095794` SHA-256 `54d802b265c29cca853f894d46be3a3ff2c4502e7b2b8f61ba1961f0f810d501`, v3 data-control run `32147376085` / artifact `9328321516` SHA-256 `5d84067b8a1f756f69c416a63c662674056095214205ff5580b15a96638c1eb9`, and v3 deployment run `32147297192` / evidence artifact `9328666559` SHA-256 `a5ec5b4923958166f5d47bedd352824d98ceb541f8cda6e16e891160b629eae5`.

Authoritative v3 owner-QA URL:

`https://armpitpete.github.io/invariant-predictive-music/freeze-1e512e85fea0e90f1e03791897803a28d264be9a5c3a8569def9324a1d5364c6/`

The v1 participant artifact/deployment is rejected: an owner real-device test showed a user-agent media-playback rejection before trial-1 audio began, while the old interface incorrectly logged enrolment/playback start before `audio.play()` had succeeded. The v2 direct-play repair is also superseded because its export did not include participant-interface revision provenance.

Participant v3 fixes both classes of defect: frozen audio is fetched/SHA-verified before the Play button unlocks; `audio.play()` is then called in the trusted click task; pre-start rejection remains unenrolled; browser storage is interface-revision-bound; export version 2 includes the exact interface revision; researcher intake rejects v1/wrong-revision exports. All 36 WAVs and all 36 schedules remain byte-identical to the frozen scientific set.

Automated v3 participant, data-control, HTTPS 79/79 byte verification and deployed P001/P002/P003 browser gates all PASS, with no autoplay-policy override and 0 real participants recruited.

**Overall technical pre-recruitment gate remains OPEN only for a same-class real-device/browser owner retest of v3**, because that environment found the original defect outside Chromium CI. Required evidence: trial-1 Play audibly starts without `NotAllowedError`; any returned export is version 2 with interface revision `e6b07579878350c80fb6548107290898b48501ca`; enrolment/start events exist only if playback actually begins.

This is owner QA, not recruitment. After it passes, governance owner checks still remain: controller/sponsorship context, ICO fee assessment, applicable ethics/institutional status, and mailbox MFA/forwarding/delegation. PR #24 remains draft and unmerged; no recruitment is authorised.

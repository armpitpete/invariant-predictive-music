# IPM Listening Experiment 1 — deployment, data collection and governance

**Status:** technical pre-recruitment gate PASS; privacy/international-processing disclosure CLOSED; governance owner gate has one remaining account-security attestation. No real participant may be invited until that final item is recorded. PR #24 remains draft/unmerged unless separately authorised.

## Authoritative frozen study object

The only participant bundle authorised for recruitment is:

- GitHub Actions artifact `9328095073` (`ipm-participant-web-v3`)
- artifact SHA-256 `1e512e85fea0e90f1e03791897803a28d264be9a5c3a8569def9324a1d5364c6`
- participant-interface evidence revision `e6b07579878350c80fb6548107290898b48501ca`
- participant gate run `32145307925`: PASS
- participant evidence artifact `9328095794`, SHA-256 `54d802b265c29cca853f894d46be3a3ff2c4502e7b2b8f61ba1961f0f810d501`
- exactly P001–P036, 12 trials each, with all 36 WAVs and all 36 schedules byte-identical to the frozen scientific set.

The rejected v1 and superseded v2 participant artifacts are not authorised for recruitment or intake. Researcher intake accepts only export version 2 carrying the exact v3 participant-interface revision above.

Authoritative HTTPS deployment:

`https://armpitpete.github.io/invariant-predictive-music/freeze-1e512e85fea0e90f1e03791897803a28d264be9a5c3a8569def9324a1d5364c6/`

Deployment run `32147297192`: PASS. Evidence artifact `9328666559`, SHA-256 `a5ec5b4923958166f5d47bedd352824d98ceb541f8cda6e16e891160b629eae5`.

79/79 deployed files verified over HTTPS; strict synthetic P001/P002/P003 acceptance passed across all 36 stimuli; same-class owner real-device/browser regression passed. Owner-QA ratings are not study data.

## Controller and institutional status — CLOSED

Owner attestation, 18 August 2026:

**Independent.** Merrin Dream is the data controller for this pilot. No university, employer, NHS body, company, charity, funder or other institution governs the study.

Study/controller contact and response mailbox: **`merrin@merrinworld.uk`**.

Because the project is independent, there is no governing institution whose internal ethics approval/exemption must be obtained. The separate HRA/NHS REC scope screening below is closed as not applicable on the frozen study scope.

## Study contact and response return

The connected Gmail mailbox is the response-return channel. Study response mail is isolated under the Gmail label **`IPM Listening Study/Responses`**.

Participant return instruction:

1. Complete the study using only the issued P### URL.
2. Download the JSON study export at the terminal screen.
3. Email it to `merrin@merrinworld.uk` with subject `IPM listening study export P###`.
4. Do not paste ratings into the email body or add extra personal information.
5. Sender address and mail metadata stay in the mailbox transport layer and are not copied into the research response dataset.

## Participant eligibility

Recruit only adults aged 18 or over who can consent for themselves, can complete the study in English, and can listen through headphones in a quiet setting. Do not recruit anyone requiring a consultee/proxy-consent process. No health information or special-category data is requested.

## P001–P036 issuance and duplicate control

The live participant-control store is private researcher material and must never be committed to the public repository.

`python -m ipm.collection_control` provides `init`, `reserve`, `ingest` and `audit` operations. One P### may be reserved once; an invitation reference must be opaque and contain no name/email; no P037 or replacement ID exists; unreserved/superseded/wrong-revision/wrong-schedule/wrong-WAV submissions are rejected; valid distinct returns are preserved content-addressably; and the earliest valid enrolled session remains canonical if duplicate enrolled submissions exist.

Data-control v3 run `32147376085`: PASS. Evidence artifact `9328321516`, SHA-256 `5d84067b8a1f756f69c416a63c662674056095214205ff5580b15a96638c1eb9`.

## Access controls and separation

Private researcher storage is the Google Drive folder **`IPM Listening Study - Private Data`**. At creation/verification it was not shared and had one owner permission only: `merrin@merrinworld.uk`.

Required controls:

- no public/shared-link access;
- MFA / strong authentication on the research mailbox/account;
- no automatic forwarding of study mail to third parties;
- no undeclared mailbox delegation;
- least-privilege access;
- no live invitation mappings, returned participant exports or live SQLite database in the public GitHub repository.

## Privacy and lawful processing

P### exports are pseudonymous personal data while separate invitation/mail linkage exists. No special-category or criminal-offence data is intentionally collected. Email metadata remains in the transport layer and browser storage is used only for protocol-critical session state.

Working UK GDPR Article 6 basis for this independent controller: **legitimate interests**. Participation consent is the ethical agreement to participate, not the Article 6 basis. The LIA records purpose, necessity and balancing; safeguards include minimisation, pseudonymisation, linkage separation, access restriction, bounded retention and no consequential individual decisions.

The participant invitation/privacy template now also discloses that GitHub and Google operate internationally and that personal data handled through GitHub Pages, Gmail or Google Drive may be processed outside the UK. It points participants to the providers' current published transfer-framework and safeguard information. This is downstream governance text only; the frozen participant artifact is unchanged. The supporting source assessment is recorded in `researcher/governance-assessment.md`.

A mandatory DPIA is not indicated on the frozen scope. Re-screen if the study expands into vulnerable participants, sensitive data, data matching, profiling, consequential automation, large-scale collection or new tracking/analytics.

## Retention and withdrawal

- Mailbox copy: delete within 7 days after validated ingestion, unless temporarily needed for delivery/withdrawal resolution.
- Invitation/contact linkage: destroy 30 days after data collection closes.
- Raw pseudonymous exports, audit and exclusion evidence: retain until 24 months after analysis freeze, then delete absent a documented legal/ethical reason.
- De-identified analysis/code/aggregate outputs may be retained once they no longer permit participant identification.
- Withdrawal of submitted research records may be requested by P### until 30 days after data collection closes.

## Ethics / regulatory scope — CLOSED

The frozen project is independent adult non-clinical music-perception research outside NHS services. It does not involve medicines/devices, human tissue, NHS records/sites, patients as patients or adults unable to consent. It falls outside the non-NHS categories for which NHS REC review remains required.

**NHS HRA Approval / NHS REC review is not the applicable route on the present scope.** No governing institution exists to impose an additional institutional ethics route. Retain the proportionate governance/risk assessment with the study record; reassess if scope or controller context changes.

## ICO data-protection fee — CLOSED

Owner reports completion of the ICO data-protection-fee self-assessment for the actual independent controller. Exact reported outcome:

**`You don't need to pay a fee.`**

Recorded as the controller's self-assessment result. Reassess only if the controller's circumstances or processing materially change.

## Pre-recruitment governance checklist

Closed:

- [x] Technical participant v3 gate.
- [x] Immutable HTTPS deployment and 79/79 verification.
- [x] Deployed P001/P002/P003 browser gate.
- [x] Same-class owner real-device regression.
- [x] P001–P036 issuance/duplicate-control gate.
- [x] Adults 18+ / able-to-consent boundary.
- [x] Private researcher storage selected and access checked.
- [x] Participant privacy/invitation information established.
- [x] International-processing / transfer disclosure established in the invitation/privacy layer.
- [x] NHS/HRA REC route assessed as not applicable.
- [x] Controller context: **Independent — Merrin Dream**.
- [x] Institutional ethics: no governing institution; no additional institutional approval route.
- [x] ICO fee self-assessment: **You don't need to pay a fee.**

Still open:

- [ ] **Account security:** owner must confirm that MFA / 2-Step Verification is enabled on `merrin@merrinworld.uk`, automatic forwarding of study mail to third parties is off, and no undeclared mailbox delegate can access study responses.

After that single attestation is recorded, the governance gate reaches PASS and the project reaches the separate owner decision on actual listener recruitment. Merge remains separate.
# IPM Listening Experiment 1 — deployment, data collection and governance

**Status:** technical pre-recruitment gate PASS; governance owner gate still open. No real participant may be invited until the remaining owner facts below are recorded. PR #24 remains draft/unmerged unless separately authorised.

## Authoritative frozen study object

The participant surface is not rebuilt for recruitment. The only participant bundle authorised by this gate is:

- GitHub Actions artifact `9328095073` (`ipm-participant-web-v3`)
- artifact SHA-256 `1e512e85fea0e90f1e03791897803a28d264be9a5c3a8569def9324a1d5364c6`
- participant-interface evidence revision `e6b07579878350c80fb6548107290898b48501ca`
- participant gate run `32145307925`: PASS
- participant evidence artifact `9328095794`, SHA-256 `54d802b265c29cca853f894d46be3a3ff2c4502e7b2b8f61ba1961f0f810d501`
- exactly P001–P036, 12 trials each, with all 36 WAVs and all 36 schedules byte-identical to the frozen scientific set.

The rejected v1 participant artifact and the superseded v2 participant artifact are not authorised for recruitment or intake. Researcher intake accepts only export version 2 carrying the exact v3 participant-interface revision above.

Authoritative content-addressed HTTPS deployment:

`https://armpitpete.github.io/invariant-predictive-music/freeze-1e512e85fea0e90f1e03791897803a28d264be9a5c3a8569def9324a1d5364c6/`

Deployment run `32147297192`: PASS. Deployment evidence artifact `9328666559`, SHA-256 `a5ec5b4923958166f5d47bedd352824d98ceb541f8cda6e16e891160b629eae5`.

The deployment gate fetched the site back over HTTPS and verified 79/79 frozen files, then ran strict synthetic P001/P002/P003 browser acceptance across all 36 stimuli with direct-user-gesture playback and no autoplay-policy override. A same-class owner real-device/browser regression also passed after the v1 playback defect was repaired. The owner-QA ratings are not study data.

## Study contact and response return

Study contact / working controller contact:

**Merrin Dream — `merrin@merrinworld.uk`**

The connected Gmail mailbox is the response-return channel. Study response mail is isolated under the Gmail label **`IPM Listening Study/Responses`**.

Participant return instruction:

1. Complete the study using only the issued P### URL.
2. At the completion screen, download the JSON study export.
3. Email that JSON file to `merrin@merrinworld.uk` with subject `IPM listening study export P###`.
4. Do not paste ratings into the email body and do not add other personal information to the export.
5. The researcher validates and ingests the attachment; sender address and mail metadata remain in the transport layer and are not copied into the research response dataset.

The participant UI does not automatically transmit responses.

## Participant eligibility

Recruit only adults aged 18 or over who can consent for themselves, can complete the study in English, and can listen through headphones in a quiet setting. Do not recruit anyone requiring a consultee/proxy-consent process. No health information or special-category data is requested.

This is a fixed recruitment/ethics boundary and does not alter the stimuli, questions, schedules or preregistered analysis.

## P001–P036 issuance and duplicate control

The live participant-control store is private researcher material and must never be committed to this public repository.

`python -m ipm.collection_control` is the control plane:

```text
init    -> seed exactly P001–P036 and their frozen group/schedule hashes
reserve -> atomically bind one available P### to one opaque invitation reference
ingest  -> validate and preserve a returned terminal export
audit   -> report reservations, submissions, canonicals and duplicates
```

Rules:

- One P### can be reserved once.
- One opaque invitation reference can be bound to only one P###.
- The invitation reference must not contain a name or email address.
- Never issue an unreserved participant URL.
- P001–P036 are the complete pool. There is no P037 and no replacement ID.
- Unreserved, superseded-version, wrong-interface-revision, wrong-schedule or wrong-WAV submissions are rejected/quarantined.
- Every distinct valid returned JSON is preserved content-addressably without overwrite.
- If one P### has multiple enrolled submissions, the canonical session is the one with the earliest valid `enrolled_at_utc`; all distinct submissions remain preserved.
- A first enrolled incomplete session is not replaced by a later complete duplicate merely because the later outcome is more convenient.

Data-control v3 run `32147376085`: PASS. Evidence artifact `9328321516`, SHA-256 `5d84067b8a1f756f69c416a63c662674056095214205ff5580b15a96638c1eb9`.

## Access controls and separation

Private researcher storage is the Google Drive folder **`IPM Listening Study - Private Data`**. At creation/verification it was not shared and had one owner permission only: `merrin@merrinworld.uk`.

Live control data and returned submissions must remain in private researcher-only storage with:

- no public/shared-link access;
- strong account authentication with MFA enabled;
- no automatic forwarding of study mail to third parties;
- no undeclared mailbox delegation;
- least-privilege access: Merrin Dream only unless a named collaborator is documented before access;
- backups, if any, subject to the same access and deletion policy.

The public GitHub repository must not contain live invitation mappings, returned participant exports or the live SQLite control database.

## Privacy and lawful-processing record

Working controller **if the project is genuinely independent/unaffiliated:** Merrin Dream. This must be replaced by the actual organisation if the project is being conducted for or under a university, employer, NHS body, company, charity, funder or other institution.

Data classification:

- P### exports are pseudonymous personal data because participants may be linkable through separately held invitation/mail information.
- No special-category or criminal-offence data is intentionally collected.
- Email sender/recipient/message metadata is personal data in the transport layer and is kept separate from the response dataset.
- Browser storage is used only for protocol-critical session state; no advertising or behavioural analytics is authorised.

Working UK GDPR Article 6 basis for an independent/private-sector pilot: **legitimate interests**. The ICO's current research guidance states that legitimate interests is the most likely lawful basis for private or third-sector research; ethical agreement to participate is distinct from the Article 6 lawful basis.

Legitimate-interests assessment:

- **Purpose:** test a defined music-perception hypothesis and produce research knowledge; no individual profiling, eligibility decision, service decision or commercial targeting is made from ratings.
- **Necessity:** trial-level pseudonymous responses and stable P### identifiers are needed for the preregistered repeated-measures analysis and integrity audit; name, postal address, date of birth, health data and IP address are not needed in the research dataset.
- **Balancing:** the data are low-sensitivity subjective music ratings; participation is voluntary; identifiers are separated; access is restricted; retention and withdrawal are disclosed; there is no unexpected reuse or individual decision-making.

Research safeguards include data minimisation, pseudonymisation, separation of linkage, least-privilege access and no use of research processing for measures or decisions about particular people. These are consistent with the Article 89 / DPA 2018 safeguards described by the ICO. The ICO notes that its research-provisions guidance is under review following the Data (Use and Access) Act 2026; this record must be revisited if the regulator materially changes the applicable guidance before recruitment.

## Retention and withdrawal

- **Mailbox transport copy:** delete within 7 days after successful validation and ingestion, unless temporarily needed to resolve a delivery or withdrawal issue.
- **Invitation identity/contact linkage:** retain until 30 days after data collection closes, then destroy the P### ↔ direct-contact link.
- **Raw pseudonymous exports, audit ledger and exclusion evidence:** retain until 24 months after analysis is frozen, then delete unless a documented legal/ethical requirement requires otherwise.
- **De-identified analysis tables, code, aggregate statistics and research outputs:** may be retained once they no longer permit participant identification.

A participant may request withdrawal of their submitted research record by quoting their P### until 30 days after data collection closes. After linkage destruction and de-identification/freeze, removal may no longer be practically possible. This is stated in the invitation/privacy template.

## Ethics / regulatory scope

On the frozen scope, this is adult, non-clinical music-perception research conducted outside NHS services. It does not involve medicines, medical devices, human tissue, health/social-care records, NHS sites, patients as patients, or adults unable to consent for themselves.

The Health Research Authority states that research taking place entirely outside the NHS can still require NHS REC review in specific categories such as Phase 1 studies in healthy volunteers, studies involving adults unable to consent, and certain human-tissue studies. This pilot is not in those categories. **NHS HRA Approval / NHS REC review is therefore not the applicable ethics route on the present scope.** If the scope changes, stop and reassess.

If a university, employer, funder, learned society or other institution governs the project, its own ethics/governance rules may still apply and must be satisfied before recruitment. If no institution governs it, record the project as independent and retain this proportionate ethics/risk assessment with the study record.

## ICO data-protection fee

The ICO states that controllers processing personal information generally need to pay the data-protection fee unless an exemption applies. Scientific research is not itself one of the listed fee exemptions. The personal/household exemption applies only where processing is genuinely personal/family/household and has no commercial or professional connection; the not-for-profit exemption is narrow and is primarily tied to membership/support administration rather than general research activity.

Therefore the fee outcome cannot be inferred simply from the study being small or unpaid. Complete the ICO self-assessment for the actual controller before recruitment and record the result. If the controller is a micro organisation/sole trader that needs to pay, the current tier-one fee is £52 (£5 less by direct debit), but the self-assessment result is authoritative for this gate.

## Official sources checked — 18 August 2026

- ICO — *Data protection fee self assessment* and fee exemptions
- ICO — *Principles and grounds for processing* (research provisions)
- ICO — *What are the appropriate safeguards?*
- ICO — *The research provisions* / current Data (Use and Access) Act 2026 notice
- Health Research Authority — *Non-NHS research projects* and REC review guidance

## Pre-recruitment governance checks

Closed:

- [x] Technical participant v3 gate passed.
- [x] Immutable HTTPS deployment v3 and 79/79 post-deployment verification passed.
- [x] Deployed synthetic P001/P002/P003 browser gate passed.
- [x] Same-class owner real-device regression passed.
- [x] P001–P036 central issuance/duplicate-control gate passed.
- [x] Adults 18+ / able-to-consent recruitment restriction fixed.
- [x] Private researcher-only storage selected and access checked.
- [x] Invitation/privacy template contains return instructions, browser-storage disclosure, retention, withdrawal and data-rights information.
- [x] NHS/HRA REC route assessed as not applicable on the frozen scope.

Still requires owner fact/attestation:

- [ ] **Controller context:** explicitly confirm that this is Merrin Dream's independent/unaffiliated project, or name the actual university/employer/NHS body/company/charity/funder/institution governing it.
- [ ] **ICO fee:** complete the ICO data-protection-fee self-assessment for that actual controller and record the exact result.
- [ ] **Institutional ethics:** if an institution governs the project, record its ethics approval/exemption/reference. If none governs it, explicitly record independent status; no NHS REC application is required on the current scope.
- [ ] **Account security:** confirm MFA is enabled on `merrin@merrinworld.uk`, automatic forwarding to third parties is off, and no undeclared delegate has access to study responses.

Only after those facts are recorded does the project reach the separate owner decision on actual listener recruitment. Merge remains a separate owner decision.
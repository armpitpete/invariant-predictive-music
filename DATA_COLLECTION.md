# IPM Listening Experiment 1 — deployment and data-collection control

**Status:** pre-recruitment operational gate. No real participant may be invited until this document's owner checks are complete and the deployment/data-collection gates pass. PR #24 remains draft/unmerged unless separately authorised.

## Frozen study object

The participant surface is not rebuilt for recruitment. The only listener bundle authorised by this gate is:

- GitHub Actions artifact `9321126844` (`ipm-participant-web-v1`)
- artifact SHA-256 `ab61b0d89db85dc17458c38df518e238748ea8e0f6a15a5448fca7f0a84ae6aa`
- participant implementation revision `94fb37ab37077346d6de585df5ee1d69ae23d009`
- exactly P001–P036, 12 trials each, with the frozen schedule and WAV SHA-256 values already embedded in that bundle.

The Pages deployment workflow publishes the bundle beneath a content-addressed path containing the artifact SHA. Before upload it verifies the artifact ZIP and every manifest entry. After deployment it fetches every manifest file back over HTTPS and checks SHA-256 again, then runs synthetic P001/P002/P003 in Chromium against the deployed URL. A deployment is not accepted merely because the page loads.

## Study contact and response return

Study contact and data controller contact for this independent pilot:

**Merrin Dream — `merrin@merrinworld.uk`**

The connected Gmail mailbox is the response-return channel. Study response mail is isolated under the Gmail label **`IPM Listening Study/Responses`**.

Participant return instruction, to be included with every invitation before the participant follows the study URL:

1. Complete the study using only the issued P### URL.
2. At the completion screen, download the JSON study export.
3. Email that JSON file to `merrin@merrinworld.uk` with subject `IPM listening study export P###`.
4. Do not paste ratings into the email body and do not add other personal information to the export.
5. The researcher validates and ingests the attachment; the sender address is mailbox metadata and is not copied into the research response dataset.

The frozen participant UI does not automatically transmit responses. Email is therefore a transport layer outside the scientific artifact, not a modification of it.

## Participant eligibility and invitation scope

Recruit only adults aged 18 or over who can consent for themselves, can use headphones in a quiet setting, and can complete the study in English. Do not recruit people who require a consultee/proxy consent process. No health information or special-category data is requested.

This is a recruitment/ethics boundary added before recruitment; it does not alter the frozen stimuli, questions, analysis or P001–P036 schedules.

## P001–P036 issuance and reservation

The live participant-control store is private researcher material and must never be committed to this public repository.

`python -m ipm.collection_control` provides the control plane. Initialise it from the exact frozen participant bundle, then reserve one ID before sending any invitation:

```text
init    -> seed exactly P001–P036 and their frozen group/schedule hashes
reserve -> atomically bind one available P### to one opaque invitation reference
ingest  -> validate and preserve a returned terminal export
audit   -> report reservations, submissions, canonicals and duplicates
```

Rules:

- One P### can be reserved once.
- One opaque `invitation_reference` can be bound to only one P###.
- The invitation reference must not be a name or email address; the identity/contact mapping stays in the invitation/mail system.
- Never issue an unreserved participant URL.
- P001–P036 are the complete pool. There is no P037 and no replacement ID.
- A returned export for an unreserved ID is rejected/quarantined rather than silently accepted.

## Cross-device duplicate control

Browser local storage prevents ordinary same-device replay, but cannot prove uniqueness across devices or cleared browser storage. The researcher-side store therefore treats duplicate control as a central evidence problem.

For every valid return:

- compute SHA-256 over the exact JSON bytes;
- retain the raw file under `submissions/P###/<sha256>.json` without overwrite;
- validate participant ID, frozen listener artifact identity, source-schedule hash, counterbalance group, response order, playback audit and browser-verified WAV hashes;
- keep participant-side `duplicate_participation`, `record_usable` and `exclusion_reason` blank on intake;
- record every distinct submission in the central database.

If the same P### has multiple enrolled submissions, **the canonical session is the one with the earliest `enrolled_at_utc`**, where that timestamp must equal the first `main_block_started` and first `playback_started` event. Later-arriving evidence may therefore change the canonical pointer if it proves an earlier enrolment. No submitted file is deleted or overwritten. This implements the preregistered rule to retain the first main-block session.

A first enrolled session that is incomplete remains the first session; a later complete duplicate does not replace it merely because its outcome is more convenient. Final inclusion/exclusion remains the blinded researcher-side protocol decision.

## Access controls and separation

Before recruitment, the live control database and content-addressed submission directory must be placed in one private researcher-only storage location with:

- no public/shared-link access;
- encryption in transit and at rest provided by the storage/device platform;
- strong authentication on the researcher account, with multi-factor authentication enabled where available;
- no automatic forwarding of study mail to third parties;
- least-privilege access: Merrin Dream only for this pilot unless a named collaborator is added and documented before access;
- backups, if used, subject to the same access and deletion policy.

The public GitHub repository contains only code, frozen schedules/stimuli and synthetic gate evidence. It must not contain live invitation mappings, returned participant exports, mailbox addresses other than the public study contact, or the live SQLite database.

## Privacy and lawful-processing record

Working controller: **Merrin Dream**, operating this independent research pilot. This must be revisited if the study is actually conducted on behalf of a university, employer, NHS body, company or other organisation.

Data classification:

- P### exports are **pseudonymous personal data**, because a participant may still be linkable through separately held invitation/mail information.
- No special-category or criminal-offence data is intentionally collected.
- Email sender/recipient/message metadata is personal data in the transport layer and is kept separate from the response dataset.
- The study site uses browser storage only to enforce the requested study session's protocol state (single play, resume/terminal state); no advertising or behavioural analytics is authorised.

Working UK GDPR Article 6 basis for the independent pilot: **legitimate interests**, subject to the balancing assessment below. Participation consent is the ethical agreement to take part and is distinct from UK GDPR consent as a processing lawful basis.

Legitimate-interests assessment:

- **Purpose:** test a defined music-perception hypothesis and produce research knowledge; no individual profiling, eligibility decision, service decision or commercial targeting is made from a participant's ratings.
- **Necessity:** trial-level pseudonymous responses and a stable P### are needed for the preregistered repeated-measures analysis and duplicate/exclusion audit; name, postal address, date of birth, IP address and health data are not needed in the research dataset.
- **Balancing:** the data are low-sensitivity subjective music ratings; participation is voluntary; the study is brief; identifiers are separated; raw returns are access-restricted; participants are told the purpose, data flow, retention and withdrawal route; no unexpected reuse or individual decision is permitted.

Research safeguards: minimise data, pseudonymise at source, keep linkage separately, restrict access, preserve raw evidence rather than rewriting it, and use study data only for research/verification of this project.

### Browser storage / PECR

The session's local browser storage is used only for protocol-critical state requested as part of the online study: it prevents replay and safely resumes or terminates a study session. No non-essential tracking storage is authorised. The invitation/privacy information must disclose this storage even where the strictly-necessary exception is relied upon.

## Retention and withdrawal

- **Mailbox transport copy:** after a returned attachment has been validated, safely ingested and backed up where applicable, delete the study email and attachment from the mailbox within **7 days**, unless it is temporarily required to resolve a delivery/withdrawal dispute.
- **Invitation identity/contact linkage:** retain only until **30 days after data collection closes**, then destroy the link between the opaque invitation reference/P### and direct contact identity.
- **Raw pseudonymous exports, audit ledger and exclusion evidence:** retain until **24 months after the analysis is frozen**, then delete unless a documented legal/ethical requirement requires a different period.
- **De-identified analysis tables, code, aggregate statistics and published/research outputs:** may be retained with the project record once they no longer permit participant identification.

A participant may request withdrawal of their submitted research record by quoting their P### to `merrin@merrinworld.uk` until **30 days after data collection closes**. After the identity/contact linkage is destroyed and the analysis dataset is de-identified/frozen, withdrawal may no longer be practically possible. This must be stated before participation.

## Ethics / regulatory scope

This pilot is designed as independent, non-clinical music-perception research entirely outside NHS services. It does not involve medicines/devices, human tissue, health/social-care records or adults unable to consent for themselves. On that scope, NHS HRA Approval / NHS REC review is not ordinarily the applicable route. If any of those facts changes, stop and reassess before recruitment.

If the researcher is conducting the project under a university, employer, funder, learned society or other institution, that organisation's ethics/governance rules may require review even where NHS REC review does not. Record the institution and approval/exemption reference before recruitment, or explicitly record that the study is independent.

Before recruitment, complete the ICO data-protection-fee self-assessment for the actual controller and record the outcome. Do not assume either liability or exemption merely from the small size of the pilot.

Official sources checked for this gate (18 August 2026):

- ICO, *Principles and grounds for processing* (research provisions)
- ICO, *What are the appropriate safeguards?* (research provisions)
- ICO, *Guidance on the use of storage and access technologies* / strictly-necessary exception
- GOV.UK, *Pay the data protection fee*
- Health Research Authority, *Non-NHS research projects* and REC guidance

## Pre-recruitment owner checks

The technical mechanism can pass without making these factual assertions on the owner's behalf. **Recruitment remains blocked** until the owner records all of the following:

- [ ] Controller context confirmed: independent Merrin Dream, or the actual sponsoring institution named.
- [ ] ICO data-protection-fee checker completed and outcome recorded.
- [ ] Institutional ethics requirement checked; approval/exemption/reference recorded, or independent status confirmed.
- [ ] Adults 18+ / able-to-consent recruitment restriction accepted.
- [ ] `merrin@merrinworld.uk` account strong authentication/MFA and forwarding/delegation state checked.
- [ ] A private researcher-only live storage location for the SQLite control DB + `submissions/` directory selected and access checked.
- [ ] Invitation template includes the return instructions, privacy summary, browser-storage disclosure, retention periods and withdrawal deadline above.

Only after these checks, successful HTTPS/deployed-browser evidence, and successful data-control dry-run does the project reach the separate owner decision on actual listener recruitment.

# IPM Listening Study — invitation and privacy template

**Researcher / data controller for this independent pilot:** Merrin Dream  
**Contact / response return:** `merrin@merrinworld.uk`

> Replace `{PARTICIPANT_ID}` and `{PARTICIPANT_URL}` from the private reservation ledger before sending. Never send an unreserved URL. Do not add condition labels, episode seeds, or researcher mappings.

## Invitation

You are invited to take part in an independent music-listening research pilot.

You can take part only if you are **18 or over**, can consent for yourself, can complete the study in English, and can listen through **headphones in a quiet setting**.

The study contains 12 short musical excerpts, each about 33 seconds. Each excerpt can be played once. After each excerpt you will answer five 0–100 rating questions. The main block contains about seven minutes of audio and takes longer once ratings are included.

Your study ID is **{PARTICIPANT_ID}**. Please use only this link and do not share it:

**{PARTICIPANT_URL}**

Do not open the same study ID on another device. If playback fails or you are interrupted during playback, do not restart the study to obtain another listen; contact the researcher instead.

Participation is voluntary. You may stop at any time.

## What information is collected

The research export contains your P### study ID, years of music-making and formal musical training, the scheduled stimulus IDs, your five ratings per trial, and technical/audit timestamps needed to prove playback and schedule integrity. The study does not ask for your name, postal address, date of birth, health information or other special-category information.

The study page does not automatically send your ratings to the researcher. When you finish, download the JSON study export and email the file to `merrin@merrinworld.uk` with subject:

`IPM listening study export {PARTICIPANT_ID}`

Please do not paste ratings into the email body and do not add extra personal information to the export. Your email address and mail metadata exist in the mailbox transport layer but are not copied into the research response dataset.

## Website and browser storage

The study is hosted on GitHub Pages. GitHub states that visitors' IP addresses are logged and stored for security purposes when a GitHub Pages site is visited. The research export does not contain your IP address and the study code does not add advertising or behavioural analytics.

The study uses your browser's local storage only to maintain protocol-critical session state: it prevents replay, resumes the correct point after an ordinary reload, and preserves a terminal completed/failed/withdrawn state. This state is not automatically transmitted to the researcher. It remains in that browser until the site's stored data are cleared. After you have safely returned your completed export, you may clear the site's browser data if you wish.

## Why the information is used

The purpose is to test a defined music-perception hypothesis and evaluate the study protocol. The working UK GDPR lawful basis for the independent pilot is **legitimate interests**: the minimum pseudonymous trial-level data are needed for the planned repeated-measures analysis and integrity checks, the information is low sensitivity, participation is voluntary, direct identifiers are separated from the response dataset, and no decisions about you are made from your ratings.

Your agreement on the study consent screen is your ethical agreement to participate. It is not being treated as the UK GDPR lawful basis for the research processing.

There is **no automated decision-making or profiling about you**. Your ratings are used for research analysis only.

## Service platforms and recipients

The research response dataset is accessible only to Merrin Dream for this pilot unless another named researcher is documented before being granted access.

The study necessarily uses third-party technical services:

- **GitHub Pages** hosts the public study files and, as GitHub documents, logs visitor IP addresses for security purposes.
- **Google Gmail** carries the response email and attachment you send to `merrin@merrinworld.uk`.
- **Google Drive** is the private researcher storage location used after a returned export has been validated and ingested.

These services may process technical or account information under their own service/privacy terms. The research response dataset does not intentionally add their account, device or network identifiers to your P### ratings record.

## International processing and transfers

GitHub and Google operate services internationally, so personal data handled through GitHub Pages, Gmail or Google Drive may be processed outside the UK, including in the United States and other countries.

GitHub's published privacy statement says that it stores and processes personal data in multiple locations and describes the transfer mechanisms it uses for international processing, including standard contractual clauses where applicable. Current details are available at:

`https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement`

Google states that information may be processed on servers outside the country where a person lives. Its published transfer-framework information describes reliance, as applicable, on UK adequacy regulations, the UK Extension to the EU-US Data Privacy Framework, and standard contractual clauses. Current details, including how to obtain information about the safeguards, are available at:

`https://policies.google.com/privacy/frameworks?hl=en_GB`

The researcher does not intentionally transfer the P### research response dataset to any additional third-party service. If the study's service providers or data flows materially change, this notice and the transfer assessment must be reviewed before further recruitment.

## Storage, access and retention

Returned study files are validated and stored in the researcher's private, access-restricted study storage. Only Merrin Dream is authorised to access the live pilot data unless an additional researcher is documented before access is granted.

- The response email/attachment is deleted from the mailbox within **7 days after successful validation and ingestion**, unless temporarily needed to resolve a delivery or withdrawal issue.
- The direct invitation/contact link to your P### is kept until **30 days after data collection closes**, then destroyed.
- Raw pseudonymous exports, the integrity audit and exclusion evidence are kept until **24 months after the analysis is frozen**, then deleted unless a specific legal or ethical requirement requires otherwise.
- De-identified analysis tables, code, aggregate statistics and research outputs may be retained after they no longer permit participant identification.

## Your data-protection rights

You can contact `merrin@merrinworld.uk` to ask about the personal data used for this study or to exercise a data-protection right that applies to the processing, including access, correction, erasure or restriction. Some rights can be limited in particular circumstances, including where UK data-protection research provisions apply.

### Your right to object

Because the working lawful basis is **legitimate interests**, you may object to the processing of your personal data. The right to object is not absolute in every circumstance, and research/statistical processing can have specific limitations, but any objection will be considered under the applicable UK data-protection rules. Email `merrin@merrinworld.uk` and quote your P### where possible.

If you are dissatisfied with how your personal data or a rights request is handled, first contact `merrin@merrinworld.uk`. You also have the right to make a complaint to the **Information Commissioner's Office (ICO)**, the UK data-protection regulator.

## Withdrawal and questions

You may stop participation at any time. If you have already returned an export and want your submitted research record removed, email `merrin@merrinworld.uk` and quote your P### **no later than 30 days after data collection closes**. After the identity/contact link has been destroyed and the analysis data have been de-identified/frozen, removal may no longer be practically possible.

A request to withdraw from the study and a UK data-protection rights request are related but not identical processes; contact the researcher if you are unsure which applies.

You may also contact `merrin@merrinworld.uk` with questions about the study, your data, or the use of browser storage.

## Researcher send checklist

Before sending this invitation:

- [ ] the P### is atomically reserved in the private collection ledger;
- [ ] `{PARTICIPANT_URL}` points to the exact content-addressed frozen HTTPS deployment and includes only the reserved P### query parameter;
- [ ] the deployment gate is PASS at the recorded frozen artifact hash;
- [ ] the participant is not known to be under 18 or unable to consent for themselves;
- [ ] no condition/seed/mapping information is included;
- [ ] the current pre-recruitment owner/ethics/data-protection gates are all closed.

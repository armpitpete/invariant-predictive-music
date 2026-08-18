# Deployment / data-collection gate status — 18 August 2026

## Data-control half: PASS

Evidence-bearing CI run: `32138030700`

Artifact: `data-collection-control-gate` / `9324748181`

Artifact digest: `sha256:a3facb08f4b228f22f46a8c4809f8ad709c615e271e3a7c5ca141e405b2bae1e`

The gate used frozen participant artifact `9321126844` and frozen participant-browser evidence artifact `9321127149`. It passed central P001–P036 initialization, atomic one-time reservation, P001/P002/P003 intake, exact export/schedule/WAV validation, rejection of a valid-but-unreserved P004 return, content-addressed raw evidence preservation, idempotent re-ingest, and cross-device duplicate ordering in which the earliest real `enrolled_at_utc` remains canonical while all distinct submissions are retained.

Study contact / return mailbox: `merrin@merrinworld.uk`.

Gmail study label: `IPM Listening Study/Responses`.

Private researcher storage location: Google Drive folder `IPM Listening Study - Private Data`, folder ID `1LJySie2I_gwCaf3UKLQZ--aP8fyO8bfX`. At creation/verification it was `shared: false` with one permission only: owner `merrin@merrinworld.uk`.

## Hosting half: PASS

Evidence-bearing deployment run: `32136418241`, attempt `2`.

Deployment workflow revision: `35298fa1d2d6500f0a3819d989736ca65061c163`.

Frozen participant artifact: `9321126844`.

Frozen artifact SHA-256: `ab61b0d89db85dc17458c38df518e238748ea8e0f6a15a5448fca7f0a84ae6aa`.

Immutable content-addressed HTTPS study URL:

`https://armpitpete.github.io/invariant-predictive-music/freeze-ab61b0d89db85dc17458c38df518e238748ea8e0f6a15a5448fca7f0a84ae6aa/`

Post-deployment verification fetched the deployed site back over HTTPS and verified **79 / 79 frozen manifest files**, with **0 mismatches**.

Pinned Playwright/Chromium acceptance then ran synthetic non-human P001/P002/P003 against that deployed URL:

- groups 1/2/3 covered;
- 36 / 36 trials completed through actual browser audio playback to natural `ended`;
- all 36 unique frozen stimuli covered;
- browser WebCrypto delivery hash checks passed;
- three completed exports verified;
- no condition-mapping leak detected;
- 0 real participants recruited.

Deployment evidence artifact: `deployed-listening-gate` / `9325230824`.

Artifact digest: `sha256:277872eadbe8cbb498ca861e277359db1e34b20154543a1b94d707b93bc4b360`.

The workflow's overall Actions conclusion is `failure` only because its final non-scientific PR-comment POST returned HTTP 403 after the evidence artifact had uploaded. All deployment, HTTPS byte-verification, deployed-browser, evidence-recording and artifact-upload steps passed. The equivalent PR evidence comment was recorded separately through the connected GitHub surface as comment `5328478538`.

## Governance state

The operational privacy/invitation template is `researcher/invitation-template.md`. It discloses the pseudonymous export, email return, GitHub Pages IP logging, browser local-storage behavior, legitimate-interests basis, retention and withdrawal route before participation.

Current UK regulatory/ethics scope is recorded in `DATA_COLLECTION.md`. The remaining pre-recruitment owner facts are not technical build work: actual controller/sponsorship context, ICO data-protection-fee assessment, applicable independent/institutional ethics review or exemption, and account-security confirmation.

## Recruitment / merge

No real participant has been recruited. PR #24 remains draft and unmerged.

**Technical deployment + data-control gate: PASS. Recruitment remains blocked until the remaining owner/legal/ethics checks are closed, after which the project reaches the separate owner decision on actual listener recruitment.**

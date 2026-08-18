# Deployment / data-collection gate status — 18 August 2026

## Data-control half: PASS

Evidence-bearing CI run: `32138030700`

Artifact: `data-collection-control-gate` / `9324748181`

Artifact digest: `sha256:a3facb08f4b228f22f46a8c4809f8ad709c615e271e3a7c5ca141e405b2bae1e`

The gate used frozen participant artifact `9321126844` and frozen participant-browser evidence artifact `9321127149`. It passed central P001–P036 initialization, atomic one-time reservation, P001/P002/P003 intake, exact export/schedule/WAV validation, rejection of a valid-but-unreserved P004 return, content-addressed raw evidence preservation, idempotent re-ingest, and cross-device duplicate ordering in which the earliest real `enrolled_at_utc` remains canonical while all distinct submissions are retained.

Study contact / return mailbox: `merrin@merrinworld.uk`.

Gmail study label created: `IPM Listening Study/Responses`.

## Hosting half: BLOCKED on GitHub environment policy

Push-triggered deployment run `32136418241` at workflow head `35298fa1d2d6500f0a3819d989736ca65061c163` failed before any runner step.

Read-only environment inspection proved `github-pages` has one custom deployment branch policy only: `main`.

Therefore `agent/matched-listening-pilot` cannot currently enter the `github-pages` environment. This is an environment-policy block, not an artifact/hash/browser failure.

Required pre-recruitment hosting action: permit `agent/matched-listening-pilot` in the `github-pages` environment (or otherwise explicitly authorize a branch-specific Pages deployment environment) and rerun the frozen deployment workflow. Do not merge solely to satisfy this gate.

## Recruitment / merge

No real participant has been recruited. PR #24 remains draft and unmerged. Recruitment remains blocked until HTTPS deployment, deployed-byte verification, deployed P001/P002/P003 browser acceptance, and the owner checklist are complete.

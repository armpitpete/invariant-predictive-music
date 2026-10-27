#!/usr/bin/env python3
"""Read-only pre-upload retention gate for one IPM listening-pilot workflow.

The ordinary PR path records reproducible checksums in the Actions log and
does NOT retain a large artifact. A manual, explicit second run can retain
an exact reviewed payload if its content digest matches prior evidence.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

MAX_UNCOMPRESSED_BYTES = 512 * 1024 * 1024

def inventory(root: Path):
    if not root.is_dir():
        raise ValueError("pilot directory missing")
    files = sorted(p for p in root.rglob("*") if p.is_file() and not p.is_symlink())
    if not files:
        raise ValueError("empty pilot directory")
    digest = hashlib.sha256()
    total = 0
    for path in files:
        name = path.relative_to(root).as_posix()
        size = path.stat().st_size
        total += size
        if total > MAX_UNCOMPRESSED_BYTES:
            raise ValueError("pilot exceeds the 512 MiB per-artifact limit")
        file_hash = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                file_hash.update(chunk)
        digest.update(f"{name}\0{size}\0{file_hash.hexdigest()}\n".encode())
    return {"sha256": digest.hexdigest(), "files": len(files), "uncompressed_bytes": total}

def decide(report, event, requested, expected_digest, evidence_ref):
    if event != "workflow_dispatch" or not requested:
        return "SKIP", "routine-run-no-large-artifact"
    if not evidence_ref or len(evidence_ref.strip()) < 12:
        return "BLOCK", "missing-reviewed-evidence-reference"
    if len(expected_digest) != 64 or any(c not in "0123456789abcdef" for c in expected_digest):
        return "BLOCK", "invalid-expected-content-sha256"
    if expected_digest != report["sha256"]:
        return "BLOCK", "content-differs-from-reviewed-digest"
    return "PRESERVE", "manual-reviewed-exact-content"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", default="listening-pilot")
    parser.add_argument("--event", required=True)
    parser.add_argument("--request-full", default="false")
    parser.add_argument("--expected-sha256", default="")
    parser.add_argument("--evidence-ref", default="")
    args = parser.parse_args()
    report = inventory(Path(args.dir))
    decision, reason = decide(
        report, args.event, args.request_full.lower() == "true",
        args.expected_sha256.lower().strip(), args.evidence_ref.strip()
    )
    result = {"decision": decision, "reason": reason, **report}
    print(json.dumps(result, sort_keys=True))
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as f:
            f.write(f"decision={decision}\n")
            f.write(f"content_sha256={report['sha256']}\n")
    if decision == "BLOCK":
        raise SystemExit(2)

if __name__ == "__main__":
    main()

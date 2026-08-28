"""Verify that a v4R1 human-audition render still uses the frozen source package.

The freeze declaration itself is committed *after* the source package has been
machine-accepted.  It records ``package_freeze_head`` as the exact source head.
Later gate-result JSON files may be added, but any change to protected DSP,
fixture, contract, diagnostic, renderer or workflow paths invalidates the
package and blocks further audition materialisation.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

FREEZE_PATH = Path("REAL_SYNTH_ENGINE_V4R1_PRE_AUDITION_FREEZE_v0_1.json")

# Git pathspecs deliberately exclude the freeze declaration and later judgment
# JSON files.  Those are evidence layered on top of the frozen source package.
PROTECTED_PATHS = (
    "src/ipm/real_synth_v4*.py",
    "scripts/*real_synth_v4r1*.py",
    ".github/workflows/real-synth-v4r1-*.yml",
    "tests/test_real_synth_v4*.py",
    "fixtures/real_synth_v4_gate_c/REAL_SYNTH_ENGINE_V4_GATE_C_TUNE_LEDGER_v0_1.json",
    "REAL_SYNTH_ENGINE_V4R1_*CONTRACT*.md",
)


def _git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        capture_output=True,
        check=check,
    )


def _ensure_commit_available(root: Path, head: str) -> None:
    probe = _git(root, "cat-file", "-e", f"{head}^{{commit}}", check=False)
    if probe.returncode == 0:
        return
    # Actions normally uses a shallow checkout. Fetch only the frozen object;
    # checkout credentials are persisted by actions/checkout.
    fetch = _git(root, "fetch", "--no-tags", "--depth=1", "origin", head, check=False)
    if fetch.returncode != 0:
        raise RuntimeError(f"cannot obtain frozen package head {head}: {fetch.stderr.strip()}")
    probe = _git(root, "cat-file", "-e", f"{head}^{{commit}}", check=False)
    if probe.returncode != 0:
        raise RuntimeError(f"frozen package head is unavailable after fetch: {head}")


def require_frozen_package(root: Path) -> dict[str, Any]:
    path = root / FREEZE_PATH
    if not path.exists():
        raise RuntimeError("v4R1 pre-audition freeze declaration is missing")
    freeze = json.loads(path.read_text())
    if freeze.get("status") != "FROZEN_PRE_AUDITION_PACKAGE":
        raise RuntimeError("v4R1 pre-audition package is not frozen")
    if freeze.get("human_audition_performed") is not False:
        raise RuntimeError("freeze declaration must precede all v4R1 human audition")
    head = str(freeze.get("package_freeze_head", ""))
    if not re.fullmatch(r"[0-9a-f]{40}", head):
        raise RuntimeError("freeze declaration has no exact 40-hex package_freeze_head")

    _ensure_commit_available(root, head)
    diff = _git(root, "diff", "--name-only", head, "HEAD", "--", *PROTECTED_PATHS)
    changed = [line for line in diff.stdout.splitlines() if line.strip()]
    if changed:
        raise RuntimeError(
            "frozen v4R1 source package drifted after package_freeze_head: "
            + ", ".join(changed)
        )
    return freeze

"""Agent bundle drift verification tests."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SYNC_SCRIPT = REPO_ROOT / "devtools" / "sync_agent_bundle.py"


def test_agent_bundle_verify_matches_committed_tree() -> None:
    result = subprocess.run(
        [sys.executable, str(SYNC_SCRIPT), "--verify"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout

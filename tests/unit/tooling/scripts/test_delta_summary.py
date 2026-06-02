"""Unit tests for devtools/sync/delta_summary."""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
_DEVTOOLS = _REPO_ROOT / "devtools"
if str(_DEVTOOLS) not in sys.path:
    sys.path.insert(0, str(_DEVTOOLS))

from sync.delta_summary import provenance_meaningful_delta  # noqa: E402


def test_provenance_meaningful_delta_detects_spec_change() -> None:
    old = {"spec_sha256": "a", "endorctl_version": "1"}
    new = {"spec_sha256": "b", "endorctl_version": "1"}
    assert provenance_meaningful_delta(old, new) is True


def test_provenance_meaningful_delta_ignores_timestamp_only() -> None:
    old = {"spec_sha256": "x", "endorctl_version": "1", "generated_at_utc": "t1"}
    new = {"spec_sha256": "x", "endorctl_version": "1", "generated_at_utc": "t2"}
    assert provenance_meaningful_delta(old, new) is False

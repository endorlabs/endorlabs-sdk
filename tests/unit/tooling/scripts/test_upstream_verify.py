"""Tests for devtools.sync.upstream_verify (committed provenance vs upstream)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
_DEVTOOLS = str(_REPO_ROOT / "devtools")
if _DEVTOOLS not in sys.path:
    sys.path.insert(0, _DEVTOOLS)

from sync.upstream_verify import (
    extract_semver_from_banner,
    parse_committed_provenance,
    semver_less,
)


def test_parse_committed_provenance_reads_json_line() -> None:
    sample = '''"""Module."""

# model_sync_provenance: {"endorctl_version":"endorctl version v1.7.946","spec_sha256":"abc"}

RUNTIME_REGISTRY_CONTRACT = {}
'''
    got = parse_committed_provenance(sample)
    assert got["spec_sha256"] == "abc"
    assert got["endorctl_version"] == "endorctl version v1.7.946"


def test_parse_committed_provenance_missing_raises() -> None:
    with pytest.raises(ValueError, match="Could not find model_sync_provenance"):
        parse_committed_provenance("# nothing here\n")


@pytest.mark.parametrize(
    ("banner", "expected"),
    [
        ("endorctl version v1.7.946", "1.7.946"),
        ("v2.0.1", "2.0.1"),
        ("unknown", None),
        ("", None),
    ],
)
def test_extract_semver_from_banner(banner: str, expected: str | None) -> None:
    assert extract_semver_from_banner(banner) == expected


@pytest.mark.parametrize(
    ("left", "right", "less"),
    [
        ("1.7.945", "1.7.946", True),
        ("1.7.946", "1.7.946", False),
        ("1.8.0", "1.7.999", False),
        ("1.0", "1.0.1", True),
    ],
)
def test_semver_less(left: str, right: str, less: bool) -> None:
    assert semver_less(left, right) is less


def test_parse_committed_provenance_normalizes_missing_endorctl() -> None:
    payload = json.dumps({"spec_sha256": "deadbeef", "endorctl_version": None})
    sample = f"# model_sync_provenance: {payload}\n"
    got = parse_committed_provenance(sample)
    assert got["endorctl_version"] == "unknown"

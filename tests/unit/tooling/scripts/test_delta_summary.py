"""Unit tests for scripts/sync/delta_summary."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SCRIPTS = _REPO_ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from sync.delta_summary import (  # noqa: E402
    provenance_meaningful_delta,
    render_compact_delta_summary_lines,
)


def test_provenance_meaningful_delta_detects_spec_change() -> None:
    old = {"spec_sha256": "a", "endorctl_version": "1"}
    new = {"spec_sha256": "b", "endorctl_version": "1"}
    assert provenance_meaningful_delta(old, new) is True


def test_provenance_meaningful_delta_ignores_timestamp_only() -> None:
    old = {"spec_sha256": "x", "endorctl_version": "1", "generated_at_utc": "t1"}
    new = {"spec_sha256": "x", "endorctl_version": "1", "generated_at_utc": "t2"}
    assert provenance_meaningful_delta(old, new) is False


def test_render_compact_delta_summary_lines_smoke(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    base = repo / "workspace" / "model-sync" / "custom_mapping"
    mapping = base / "mapping"
    mapping.mkdir(parents=True)
    meta = {
        "operation_count": 1,
        "operations": [
            {
                "method": "get",
                "path": "/v1/x",
                "tags": ["T"],
                "operation_id": "X",
                "request_refs": [],
                "response_refs": [],
            }
        ],
    }
    (mapping / "operation_path_metadata.json").write_text(
        json.dumps(meta), encoding="utf-8"
    )
    facade = {"resources": [{"attr_name": "Project", "model_class": "Project"}]}
    (base / "facade_contract.json").write_text(json.dumps(facade), encoding="utf-8")
    payload = {"resources": []}
    (mapping / "payload_schemas.json").write_text(json.dumps(payload), encoding="utf-8")
    prov = {"spec_sha256": "abc", "endorctl_version": "1.0"}
    (base / "provenance.json").write_text(json.dumps(prov), encoding="utf-8")

    subprocess.run(
        ["git", "init", "-b", "main"],
        cwd=repo,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "t@t.t"],
        cwd=repo,
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "t"],
        cwd=repo,
        capture_output=True,
        check=True,
    )
    subprocess.run(["git", "add", "."], cwd=repo, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=repo,
        capture_output=True,
        check=True,
    )

    lines = render_compact_delta_summary_lines(git_ref="HEAD", repo_root=repo)
    text = "\n".join(lines)
    assert "Delta summary" in text
    assert "HEAD" in text
    assert "Upstream" in text or "upstream" in text.lower()

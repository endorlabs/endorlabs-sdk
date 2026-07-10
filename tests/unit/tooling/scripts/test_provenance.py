"""Tests for devtools.sync.provenance (published endorctl watermark)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[4]
_DEVTOOLS = str(_REPO_ROOT / "devtools" / "codegen")
if _DEVTOOLS not in sys.path:
    sys.path.insert(0, _DEVTOOLS)

from sync import provenance as provenance_mod


def test_get_endorctl_version_uses_meta_version_api(monkeypatch: Any) -> None:
    calls: list[str] = []

    def _fake_fetch(
        *, meta_version_url: str, timeout_seconds: float = 15.0
    ) -> str | None:
        _ = timeout_seconds
        calls.append(meta_version_url)
        return "1.7.976"

    monkeypatch.setattr(
        provenance_mod,
        "fetch_latest_endorctl_semver",
        _fake_fetch,
    )
    got = provenance_mod.get_endorctl_version(
        meta_version_url="https://api.test/meta/version",
    )
    assert got == "endorctl version v1.7.976"
    assert calls == ["https://api.test/meta/version"]


def test_get_endorctl_version_unknown_when_api_unavailable(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        provenance_mod,
        "fetch_latest_endorctl_semver",
        lambda **_: None,
    )
    assert provenance_mod.get_endorctl_version() == "unknown"


def test_build_provenance_stamps_meta_version_banner(
    monkeypatch: Any,
    tmp_path: Path,
) -> None:
    spec = tmp_path / "spec.json"
    spec.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        provenance_mod,
        "get_endorctl_version",
        lambda **_: "endorctl version v1.7.976",
    )
    payload = provenance_mod.build_provenance(
        spec,
        {"datamodel-codegen": {"available": True}},
        meta_version_url="https://api.test/meta/version",
    )
    assert payload["endorctl_version"] == "endorctl version v1.7.976"
    assert payload["spec_sha256"] == provenance_mod.file_sha256(spec)
    assert json.loads(spec.read_text(encoding="utf-8")) == {}

"""Tests for reconciling legacy flat .endorlabs-context downloads."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock

from endorlabs.context._sync import _reconcile_legacy_platform_downloads, sync_openapi
from endorlabs.context.paths import (
    OPENAPI_FILENAME,
    platform_openapi_path,
    platform_user_docs_path,
)


def test_reconcile_moves_legacy_openapi_to_platform_path(tmp_path: Path) -> None:
    root = tmp_path / ".endorlabs-context"
    root.mkdir()
    legacy = root / OPENAPI_FILENAME
    legacy.write_text('{"legacy": true}', encoding="utf-8")
    canonical = platform_openapi_path(root)

    _reconcile_legacy_platform_downloads(root)

    assert not legacy.exists()
    assert canonical.is_file()
    assert json.loads(canonical.read_text(encoding="utf-8")) == {"legacy": True}


def test_reconcile_removes_legacy_openapi_when_canonical_exists(tmp_path: Path) -> None:
    root = tmp_path / ".endorlabs-context"
    root.mkdir()
    legacy = root / OPENAPI_FILENAME
    legacy.write_text('{"legacy": true}', encoding="utf-8")
    canonical = platform_openapi_path(root)
    canonical.parent.mkdir(parents=True, exist_ok=True)
    canonical.write_text('{"canonical": true}', encoding="utf-8")

    _reconcile_legacy_platform_downloads(root)

    assert not legacy.exists()
    assert json.loads(canonical.read_text(encoding="utf-8")) == {"canonical": True}


def test_sync_openapi_default_uses_platform_layout(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    context_root = tmp_path / ".endorlabs-context"
    legacy = context_root / OPENAPI_FILENAME
    context_root.mkdir()
    legacy.write_text('{"legacy": true}', encoding="utf-8")

    mock_response = Mock()
    mock_response.json.return_value = {"openapi": "3.0.0"}
    mock_client = Mock()
    mock_client.get.return_value = mock_response

    result = sync_openapi(force=True, client=mock_client)

    expected = platform_openapi_path(context_root)
    assert result.resolve() == expected.resolve()
    assert expected.is_file()
    assert not legacy.exists()
    assert json.loads(expected.read_text(encoding="utf-8")) == {"openapi": "3.0.0"}


def test_reconcile_moves_legacy_user_docs(tmp_path: Path) -> None:
    root = tmp_path / ".endorlabs-context"
    root.mkdir()
    legacy_docs = root / "user-docs"
    legacy_docs.mkdir()
    (legacy_docs / "index.md").write_text("# legacy", encoding="utf-8")
    canonical = platform_user_docs_path(root)

    _reconcile_legacy_platform_downloads(root)

    assert not legacy_docs.exists()
    assert (canonical / "index.md").read_text(encoding="utf-8") == "# legacy"

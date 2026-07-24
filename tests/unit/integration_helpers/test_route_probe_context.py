"""Unit tests for scan-plane probe helpers used by route integration tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from endorlabs.facade.context_partition import context_partition_filter
from tests.integration.client.conftest import (
    _context_usable,
    _project_scans_for_context,
    _scan_has_context,
)


def test_context_usable_accepts_context_object() -> None:
    ctx = SimpleNamespace(type="CONTEXT_TYPE_MAIN", id="default")
    assert _context_usable(ctx)
    assert not _context_usable(None)
    assert not _context_usable(SimpleNamespace(type=None))
    assert not _context_usable(SimpleNamespace(type=""))


def test_scan_has_context_requires_nested_context() -> None:
    ctx = SimpleNamespace(type="CONTEXT_TYPE_MAIN", id="default")
    assert _scan_has_context(SimpleNamespace(context=ctx))
    # Passing a Context itself must not be treated as a scan.
    assert not _scan_has_context(ctx)
    assert not _scan_has_context(SimpleNamespace(context=None))


def test_project_scans_for_context_passes_partition_filter() -> None:
    """Row probes must filter scans by context, not newest-first alone."""
    ctx = SimpleNamespace(type="CONTEXT_TYPE_REF", id="feature/branch")
    project = SimpleNamespace(uuid="proj-1")
    client = MagicMock()
    client.ScanResult.list_by_project.return_value = []
    assert _project_scans_for_context(client, project, ctx) == []
    client.ScanResult.list_by_project.assert_called_once_with(
        project,
        filter=context_partition_filter(ctx),
        limit=10,
        max_pages=1,
    )

"""Unit tests for scan-plane probe helpers used by route integration tests."""

from __future__ import annotations

from types import SimpleNamespace

from tests.integration.client.conftest import (
    _context_usable,
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

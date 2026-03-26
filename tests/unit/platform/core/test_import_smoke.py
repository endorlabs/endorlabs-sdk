"""Import smoke tests for public SDK boundaries."""

from __future__ import annotations


def test_public_imports_smoke() -> None:
    """Top-level SDK import should expose core public symbols."""
    import endorlabs
    from endorlabs import Client, F

    assert endorlabs is not None
    assert Client is not None
    assert F is not None


def test_internal_namespace_imports_smoke() -> None:
    """Internal core namespace should be importable."""
    import endorlabs.core as core

    assert core is not None

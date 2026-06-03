"""Tests for client stub generation."""

from __future__ import annotations

from pathlib import Path


def test_vector_store_query_create_includes_metadata_filter() -> None:
    """Generated stub exposes metadata_filter on VectorStoreQuery.create."""
    repo_root = Path(__file__).resolve().parents[3]
    pyi_path = repo_root / "src" / "endorlabs" / "client_surface.pyi"
    content = pyi_path.read_text(encoding="utf-8")
    assert "class _VectorStoreQueryFacade" in content
    section_start = content.index("class _VectorStoreQueryFacade")
    section_end = content.find("\nclass _", section_start + 1)
    section = (
        content[section_start:section_end]
        if section_end != -1
        else content[section_start:]
    )
    assert "def create(" in section
    assert "metadata_filter" in section
    assert "vector_store_uuid" in section
    assert "query" in section

"""Tests for per-resource reference page generation."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEVTOOLS = _REPO_ROOT / "devtools" / "codegen"
if str(_DEVTOOLS) not in sys.path:
    sys.path.insert(0, str(_DEVTOOLS))

from generate_resource_reference_pages import (  # noqa: E402
    _render_resource_page,
    generate_resource_reference_pages,
)


@pytest.fixture
def vector_store_query_contract() -> dict:
    return {
        "resource_name": "queries/vector-stores",
        "scope": "tenant",
        "parent_kind": None,
        "supported_ops": ["create", "list", "get"],
        "create_mode": "both",
        "create_convenience_spec_fields": [
            "vector_store_uuid",
            "query",
            "metadata_filter",
        ],
        "create_convenience_spec_required": ["vector_store_uuid", "query"],
        "create_convenience_meta_fields": ["name"],
        "create_convenience_payload_top_level_fields": ["meta", "spec"],
        "create_convenience_read_only_spec_fields": ["matches"],
        "convenience_skip_reason": None,
        "model_class": "VectorStoreQuery",
        "model_class_import_path": (
            "endorlabs.resources.vector_store_query:VectorStoreQuery"
        ),
    }


def test_render_vector_store_query_page(vector_store_query_contract: dict) -> None:
    page = _render_resource_page(
        "VectorStoreQuery",
        vector_store_query_contract,
        "Natural-language vector store queries.",
        {"VectorStoreQuery": ["VectorStore"]},
    )
    assert "## Create convenience kwargs" in page or "Create convenience kwargs" in page
    assert "`metadata_filter`" in page
    assert "`matches`" in page
    assert "VectorStore.md" in page


def test_render_project_page_includes_search_by_name() -> None:
    from generate_resource_reference_pages import _load_contract_resources

    contract = _load_contract_resources()["Project"]
    page = _render_resource_page(
        "Project",
        contract,
        "Logical root for a repository and its scan results.",
        {"Project": ["Finding", "ScanResult"]},
    )
    assert "## Facade helpers" in page
    assert "search_by_name" in page


def test_generate_prunes_stale_resource_pages() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    stale = repo_root / "docs" / "generated-reference" / "resources" / "StaleResource.md"
    stale.write_text("# Stale\n", encoding="utf-8")
    try:
        generate_resource_reference_pages()
        assert not stale.is_file()
    finally:
        if stale.is_file():
            stale.unlink()


def test_generate_writes_vector_store_query_page() -> None:
    generate_resource_reference_pages()
    repo_root = Path(__file__).resolve().parents[3]
    path = repo_root / "docs" / "generated-reference" / "resources" / "VectorStoreQuery.md"
    assert path.is_file()
    content = path.read_text(encoding="utf-8")
    assert "metadata_filter" in content
    assert "matches" in content

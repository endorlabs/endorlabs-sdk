"""Tests for relationship list masks."""

from __future__ import annotations

from endorlabs.workflows.estate.filters.masks import (
    DEP_METADATA_LIST_MASK,
    PROJECT_LIST_MASK,
    PV_PUBLISHER_LIST_MASK,
)


def test_masks_include_corpus_fields() -> None:
    assert "project_paths" in DEP_METADATA_LIST_MASK
    assert "meta.tags" in PROJECT_LIST_MASK
    assert "spec.ecosystem" in PV_PUBLISHER_LIST_MASK

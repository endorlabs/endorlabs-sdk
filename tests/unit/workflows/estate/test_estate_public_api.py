"""Tests for estate package library entrypoints advertised in agent knowledge."""

from __future__ import annotations

import endorlabs.workflows.estate as estate


def test_library_entrypoints_are_exported_from_package() -> None:
    assert callable(estate.collect_workspace)
    assert callable(estate.analyze_workspace)
    assert callable(estate.export_version_cardinality_for_package_match)
    assert callable(estate.export_risk_ranked_version_cardinality)

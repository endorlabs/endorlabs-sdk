"""Tests for route contract code generation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from endorlabs.generated.route_contract import ROUTE_CONTRACT, ROUTE_TABLE_BY_ATTR


def test_generated_contract_has_core_edges() -> None:
    ids = {edge.id for edge in ROUTE_CONTRACT.edges}
    assert "project.findings" in ids
    assert "scan.findings" in ids
    assert "finding.dependency_metadata.get" in ids


def test_partition_edges_match_golden_fixture() -> None:
    repo = Path(__file__).resolve().parents[3]
    golden = json.loads(
        (repo / "tests" / "fixtures" / "routes" / "golden_edges.json").read_text(
            encoding="utf-8"
        )
    )
    golden_ids = {edge["id"] for edge in golden["edges"]}
    assert "scan.findings" in golden_ids
    assert "scan.dependency_metadata" in golden_ids
    scan_finding = next(e for e in golden["edges"] if e["id"] == "scan.findings")
    assert scan_finding["edge"] == "list_by_context_partition"
    assert scan_finding["also_filter"] == 'spec.project_uuid=="{source.meta.parent_uuid}"'
    dm = next(e for e in golden["edges"] if e["id"] == "scan.dependency_metadata")
    assert (
        dm["also_filter"]
        == 'spec.importer_data.project_uuid=="{source.meta.parent_uuid}"'
    )
    contract_ids = {edge.id for edge in ROUTE_CONTRACT.edges}
    assert contract_ids == golden_ids


def test_route_table_by_attr() -> None:
    assert "Finding" in ROUTE_TABLE_BY_ATTR
    assert "project.findings" in ROUTE_TABLE_BY_ATTR["Finding"]
    assert "scan.findings" in ROUTE_TABLE_BY_ATTR["Finding"]


def test_relationship_map_generated() -> None:
    from endorlabs.generated.route_contract import ROUTE_RELATIONSHIP_MAP

    assert any(row[2] == "Finding.list_by_project" for row in ROUTE_RELATIONSHIP_MAP)
    assert any(row[2] == "Finding.list_for_context" for row in ROUTE_RELATIONSHIP_MAP)


def test_generate_route_contract_script_is_stable() -> None:
    repo = Path(__file__).resolve().parents[3]
    out = repo / "src" / "endorlabs" / "generated" / "route_contract.py"
    golden = repo / "tests" / "fixtures" / "routes" / "golden_edges.json"
    before_py = out.read_text(encoding="utf-8")
    before_golden = golden.read_text(encoding="utf-8")
    subprocess.run(
        [sys.executable, str(repo / "devtools" / "codegen" / "generate_route_contract.py")],
        check=True,
        cwd=repo,
    )
    assert before_py == out.read_text(encoding="utf-8")
    assert before_golden == golden.read_text(encoding="utf-8")

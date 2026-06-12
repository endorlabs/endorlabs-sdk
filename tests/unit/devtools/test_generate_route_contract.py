"""Tests for route contract code generation."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from endorlabs.generated.route_contract import ROUTE_CONTRACT, ROUTE_TABLE_BY_ATTR


def test_generated_contract_has_core_edges() -> None:
    ids = {edge.id for edge in ROUTE_CONTRACT.edges}
    assert "project.findings" in ids
    assert "finding.dependency_metadata.get" in ids


def test_route_table_by_attr() -> None:
    assert "Finding" in ROUTE_TABLE_BY_ATTR
    assert "project.findings" in ROUTE_TABLE_BY_ATTR["Finding"]


def test_relationship_map_generated() -> None:
    from endorlabs.generated.route_contract import ROUTE_RELATIONSHIP_MAP

    assert any(row[2] == "Finding.list_by_project" for row in ROUTE_RELATIONSHIP_MAP)


def test_generate_route_contract_script_is_stable() -> None:
    repo = Path(__file__).resolve().parents[3]
    out = repo / "src" / "endorlabs" / "generated" / "route_contract.py"
    before = out.read_text(encoding="utf-8")
    subprocess.run(
        [sys.executable, str(repo / "devtools" / "generate_route_contract.py")],
        check=True,
        cwd=repo,
    )
    after = out.read_text(encoding="utf-8")
    assert before == after

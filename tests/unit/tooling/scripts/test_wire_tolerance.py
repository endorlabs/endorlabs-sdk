"""SDK-005 model-sync wire tolerance rewrite."""

from __future__ import annotations

from devtools.codegen.sync.wire_tolerance import apply_wire_tolerances


def test_apply_wire_tolerances_widens_bom_adjacency() -> None:
    src = "dependency_graph: dict[str, list[dict[str, Any]]] | None = Field(\n"
    out = apply_wire_tolerances({"package_version_service.py": src})
    assert "list[dict[str, Any] | str]" in out["package_version_service.py"]

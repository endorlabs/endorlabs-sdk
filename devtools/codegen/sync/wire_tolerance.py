"""Post-codegen wire tolerances that OpenAPI still under-declares.

SDK-005: BOM ``dependency_graph`` adjacency values are package-coordinate
strings or objects on the wire. Keep this rewrite until upstream OpenAPI
declares the union and Foundry can drop ``bom-adjacency-strings-v1``.
"""

from __future__ import annotations

_BOM_ADJACENCY_OBJECT = "dependency_graph: dict[str, list[dict[str, Any]]] | None"
_BOM_ADJACENCY_UNION = (
    "dependency_graph: dict[str, list[dict[str, Any] | str]] | None"
)


def apply_wire_tolerances(generated_modules: dict[str, str]) -> dict[str, str]:
    """Return a copy of generated sources with durable wire-tolerance rewrites."""
    out: dict[str, str] = {}
    for path, source in generated_modules.items():
        if _BOM_ADJACENCY_OBJECT in source:
            source = source.replace(_BOM_ADJACENCY_OBJECT, _BOM_ADJACENCY_UNION)
        out[path] = source
    return out

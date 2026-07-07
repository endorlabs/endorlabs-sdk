# ruff: noqa: D101, D102, TRY004
"""Route contract types and validation for generated accessor edges."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, cast

from endorlabs.workflows.wire_access import as_dict, dict_str

RouteEdgeKind = Literal[
    "get_by_uuid",
    "list_by_parent",
    "list_by_uuid_field",
    "list_by_index_field",
    "list_by_attribute",
    "list_by_context_partition",
    "via_intermediate",
]

VALID_EDGE_KINDS: frozenset[str] = frozenset(
    {
        "get_by_uuid",
        "list_by_parent",
        "list_by_uuid_field",
        "list_by_index_field",
        "list_by_attribute",
        "list_by_context_partition",
        "via_intermediate",
    }
)


@dataclass(frozen=True)
class RouteWhen:
    """Optional gate on source row fields."""

    categories: tuple[str, ...] = ()
    methods: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> RouteWhen | None:
        if not raw:
            return None
        raw_dict = as_dict(raw)
        categories_raw = raw_dict.get("categories")
        methods_raw = raw_dict.get("methods")
        categories: tuple[str, ...] = ()
        if isinstance(categories_raw, list):
            categories = tuple(
                str(item)
                for item in cast("list[Any]", categories_raw)
                if item is not None
            )
        methods: tuple[str, ...] = ()
        if isinstance(methods_raw, list):
            methods = tuple(
                str(item) for item in cast("list[Any]", methods_raw) if item is not None
            )
        return cls(categories=categories, methods=methods)


@dataclass(frozen=True)
class RouteChainStep:
    kind: RouteEdgeKind
    through_kind: str | None = None
    filter_field: str | None = None
    uuid_from: str | None = None
    source_attr: str | None = None
    target_filter_field: str | None = None
    match: Literal["exact", "substring", "regex"] | None = None
    optional: bool = False


@dataclass(frozen=True)
class RouteEdge:
    """One stitched path between resource kinds."""

    id: str
    from_kind: str
    to_kind: str
    edge: RouteEdgeKind
    tier: str = "B"
    public_method: str | None = None
    filter_field: str | None = None
    uuid_from: str | None = None
    namespace_from: str = "source"
    list_only: bool = False
    parent_kind: str | None = None
    source_attr: str | None = None
    target_filter_field: str | None = None
    match: Literal["exact", "substring", "regex"] | None = None
    also_filter: str | None = None
    context_from: str = "context"
    when: RouteWhen | None = None
    steps: tuple[RouteChainStep, ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> RouteEdge:
        edge = raw.get("edge")
        if not isinstance(edge, str) or edge not in VALID_EDGE_KINDS:
            raise ValueError(f"Invalid or missing edge kind: {edge!r}")
        steps_raw = raw.get("steps")
        steps: tuple[RouteChainStep, ...] = ()
        if isinstance(steps_raw, list):
            parsed: list[RouteChainStep] = []
            for raw_item in cast("list[Any]", steps_raw):
                if not isinstance(raw_item, dict):
                    continue
                item = cast("dict[str, Any]", raw_item)
                kind = item.get("kind")
                if not isinstance(kind, str) or kind not in VALID_EDGE_KINDS:
                    raise ValueError(f"Invalid chain step kind: {kind!r}")
                match_raw = item.get("match")
                match: Literal["exact", "substring", "regex"] | None = None
                if match_raw in ("exact", "substring", "regex"):
                    match = match_raw
                optional_raw = item.get("optional")
                parsed.append(
                    RouteChainStep(
                        kind=kind,  # type: ignore[arg-type]
                        through_kind=dict_str(item, "through_kind") or None,
                        filter_field=dict_str(item, "filter_field") or None,
                        uuid_from=dict_str(item, "uuid_from") or None,
                        source_attr=dict_str(item, "source_attr") or None,
                        target_filter_field=dict_str(item, "target_filter_field")
                        or None,
                        match=match,
                        optional=bool(optional_raw),
                    )
                )
            steps = tuple(parsed)
        match_top = raw.get("match")
        top_match: Literal["exact", "substring", "regex"] | None = None
        if match_top in ("exact", "substring", "regex"):
            top_match = match_top
        return cls(
            id=str(raw["id"]),
            from_kind=str(raw["from_kind"]),
            to_kind=str(raw["to_kind"]),
            edge=edge,  # type: ignore[arg-type]
            tier=dict_str(raw, "tier") or "B",
            public_method=dict_str(raw, "public_method") or None,
            filter_field=dict_str(raw, "filter_field") or None,
            uuid_from=dict_str(raw, "uuid_from") or None,
            namespace_from=dict_str(raw, "namespace_from") or "source",
            list_only=bool(raw.get("list_only")),
            parent_kind=dict_str(raw, "parent_kind") or None,
            source_attr=dict_str(raw, "source_attr") or None,
            target_filter_field=dict_str(raw, "target_filter_field") or None,
            match=top_match,
            also_filter=dict_str(raw, "also_filter") or None,
            context_from=dict_str(raw, "context_from") or "context",
            when=RouteWhen.from_dict(
                cast("dict[str, Any]", when_raw)
                if isinstance((when_raw := raw.get("when")), dict)
                else None
            ),
            steps=steps,
        )


@dataclass(frozen=True)
class RouteContract:
    edges: tuple[RouteEdge, ...]

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> RouteContract:
        edges_raw = raw.get("edges")
        if not isinstance(edges_raw, list):
            raise ValueError("Route contract must contain an 'edges' list")
        edges = tuple(
            RouteEdge.from_dict(cast("dict[str, Any]", item))
            for item in cast("list[Any]", edges_raw)
            if isinstance(item, dict)
        )
        validate_contract(edges)
        return cls(edges=edges)

    @classmethod
    def load_json(cls, path: Path) -> RouteContract:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"Expected JSON object in {path}")
        return cls.from_dict(cast("dict[str, Any]", payload))

    def edge_by_id(self, edge_id: str) -> RouteEdge | None:
        for edge in self.edges:
            if edge.id == edge_id:
                return edge
        return None

    def edges_for_attr(self, attr_name: str) -> tuple[RouteEdge, ...]:
        """Edges whose public_method starts with ``{attr_name}.``."""
        prefix = f"{attr_name}."
        return tuple(
            e
            for e in self.edges
            if e.public_method and e.public_method.startswith(prefix)
        )


def validate_contract(edges: tuple[RouteEdge, ...]) -> None:
    """Reject unknown kinds and duplicate edge ids."""
    seen: set[str] = set()
    for edge in edges:
        if edge.id in seen:
            raise ValueError(f"Duplicate route edge id: {edge.id!r}")
        seen.add(edge.id)
        if edge.edge not in VALID_EDGE_KINDS:
            raise ValueError(f"Unknown edge kind: {edge.edge!r}")


def load_golden_contract(repo_root: Path | None = None) -> RouteContract:
    """Load committed golden fixture (tests and bootstrap)."""
    root = repo_root or Path(__file__).resolve().parents[3]
    return RouteContract.load_json(
        root / "tests" / "fixtures" / "routes" / "golden_edges.json"
    )

# ruff: noqa: D101, D102, TRY004
"""Route contract types and validation for CRUD+ stitched paths."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

RouteEdgeKind = Literal[
    "get_by_uuid",
    "list_by_parent",
    "list_by_uuid_field",
    "list_by_index_field",
    "list_by_attribute",
    "via_intermediate",
]

VALID_EDGE_KINDS: frozenset[str] = frozenset(
    {
        "get_by_uuid",
        "list_by_parent",
        "list_by_uuid_field",
        "list_by_index_field",
        "list_by_attribute",
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
        categories = raw.get("categories")
        methods = raw.get("methods")
        return cls(
            categories=tuple(categories) if isinstance(categories, list) else (),
            methods=tuple(methods) if isinstance(methods, list) else (),
        )


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
            for item in steps_raw:
                if not isinstance(item, dict):
                    continue
                kind = item.get("kind")
                if not isinstance(kind, str) or kind not in VALID_EDGE_KINDS:
                    raise ValueError(f"Invalid chain step kind: {kind!r}")
                match_raw = item.get("match")
                match: Literal["exact", "substring", "regex"] | None = None
                if match_raw in ("exact", "substring", "regex"):
                    match = match_raw
                parsed.append(
                    RouteChainStep(
                        kind=kind,  # type: ignore[arg-type]
                        through_kind=item.get("through_kind")
                        if isinstance(item.get("through_kind"), str)
                        else None,
                        filter_field=item.get("filter_field")
                        if isinstance(item.get("filter_field"), str)
                        else None,
                        uuid_from=item.get("uuid_from")
                        if isinstance(item.get("uuid_from"), str)
                        else None,
                        source_attr=item.get("source_attr")
                        if isinstance(item.get("source_attr"), str)
                        else None,
                        target_filter_field=item.get("target_filter_field")
                        if isinstance(item.get("target_filter_field"), str)
                        else None,
                        match=match,
                        optional=bool(item.get("optional")),
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
            tier=str(raw.get("tier", "B")),
            public_method=raw.get("public_method")
            if isinstance(raw.get("public_method"), str)
            else None,
            filter_field=raw.get("filter_field")
            if isinstance(raw.get("filter_field"), str)
            else None,
            uuid_from=raw.get("uuid_from")
            if isinstance(raw.get("uuid_from"), str)
            else None,
            namespace_from=str(raw.get("namespace_from", "source")),
            list_only=bool(raw.get("list_only")),
            parent_kind=raw.get("parent_kind")
            if isinstance(raw.get("parent_kind"), str)
            else None,
            source_attr=raw.get("source_attr")
            if isinstance(raw.get("source_attr"), str)
            else None,
            target_filter_field=raw.get("target_filter_field")
            if isinstance(raw.get("target_filter_field"), str)
            else None,
            match=top_match,
            also_filter=raw.get("also_filter")
            if isinstance(raw.get("also_filter"), str)
            else None,
            when=RouteWhen.from_dict(
                raw.get("when") if isinstance(raw.get("when"), dict) else None
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
            RouteEdge.from_dict(item) for item in edges_raw if isinstance(item, dict)
        )
        validate_contract(edges)
        return cls(edges=edges)

    @classmethod
    def load_json(cls, path: Path) -> RouteContract:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"Expected JSON object in {path}")
        return cls.from_dict(payload)

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

"""Query AI-SAST function_summary seeds for Call Graph join."""

from __future__ import annotations

from typing import Any, cast

ENTRY_POINT_QUERY = "HTTP REST entry point handler rest_path"


def _match_as_dict(match: Any) -> dict[str, Any]:
    if isinstance(match, dict):
        return cast("dict[str, Any]", dict(match))
    if hasattr(match, "model_dump"):
        return cast("dict[str, Any]", dict(match.model_dump(exclude_none=False)))
    data = getattr(match, "data", None)
    metadata = getattr(match, "metadata", None)
    out: dict[str, Any] = {}
    if data is not None:
        out["data"] = data
    if metadata is not None:
        if isinstance(metadata, dict):
            out["metadata"] = cast("dict[str, Any]", dict(metadata))
        elif hasattr(metadata, "model_dump"):
            out["metadata"] = cast(
                "dict[str, Any]", dict(metadata.model_dump(exclude_none=False))
            )
        elif hasattr(metadata, "__dict__"):
            out["metadata"] = cast("dict[str, Any]", dict(vars(metadata)))
        else:
            out["metadata"] = {}
    return out


def _nested_get(meta: dict[str, Any], *keys: str) -> Any:
    cur: Any = meta
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cast("dict[str, Any]", cur).get(key)
    return cur


def parse_vector_match(match: Any) -> dict[str, Any]:
    """Normalize one VectorStoreQuery match into a seed row."""
    raw = _match_as_dict(match)
    meta_raw = raw.get("metadata")
    meta: dict[str, Any] = (
        cast("dict[str, Any]", dict(meta_raw)) if isinstance(meta_raw, dict) else {}
    )
    func_info_raw = meta.get("function_info")
    func_info: dict[str, Any] = (
        cast("dict[str, Any]", dict(func_info_raw))
        if isinstance(func_info_raw, dict)
        else {}
    )
    data = raw.get("data")
    data_str = str(data) if data is not None else ""
    return {
        "fqn": meta.get("fqn") or _nested_get(meta, "function_info", "fqn"),
        "file_path": meta.get("file_path"),
        "line_start": meta.get("line_start"),
        "line_end": meta.get("line_end"),
        "rest_path": func_info.get("rest_path") or meta.get("rest_path"),
        "is_entry_point": bool(
            func_info.get("is_entry_point")
            if "is_entry_point" in func_info
            else meta.get("is_entry_point")
        ),
        "is_source": bool(func_info.get("is_source", False)),
        "is_sink": bool(func_info.get("is_sink", False)),
        "score": raw.get("score"),
        "data_snippet": data_str[:500] if data_str else "",
        "metadata": meta,
    }


def extract_matches_from_query_result(result: Any) -> list[Any]:
    """Return match list from VectorStoreQuery response."""
    hits_raw: Any = None
    spec = getattr(result, "spec", None)
    if spec is not None:
        hits_raw = getattr(spec, "matches", None)
        if hits_raw is None:
            hits_raw = getattr(spec, "documents", None)
    if isinstance(result, dict):
        result_d = cast("dict[str, Any]", result)
        spec_raw = result_d.get("spec")
        if isinstance(spec_raw, dict):
            spec_d = cast("dict[str, Any]", spec_raw)
            hits_raw = spec_d.get("matches") or spec_d.get("documents")
    return cast("list[Any]", hits_raw) if isinstance(hits_raw, list) else []


def fetch_entry_point_seeds(
    client: Any,
    store: Any,
    *,
    repo_name: str,
    query: str = ENTRY_POINT_QUERY,
    max_seeds: int = 40,
) -> list[dict[str, Any]]:
    """Query function_summary for entry-point-biased seeds scoped to *repo_name*."""
    from endorlabs.workflows.vector_search.query import query_vector_store

    result = query_vector_store(
        client,
        store,
        query,
        metadata_filter={"repo": repo_name},
    )
    seeds = [parse_vector_match(m) for m in extract_matches_from_query_result(result)]
    # Prefer explicit entry points when present; keep others as fallback.
    entry = [s for s in seeds if s.get("is_entry_point") or s.get("rest_path")]
    ordered = entry + [s for s in seeds if s not in entry]
    return ordered[: max(0, max_seeds)]

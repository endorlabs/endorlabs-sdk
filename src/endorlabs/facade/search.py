"""Shared search helpers for resource facades (identity lane)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast


def _row_field_text(row: Any, field_path: str) -> str:
    parts = field_path.split(".")
    if isinstance(row, dict):
        cur: Any = cast("dict[str, Any]", row)
        for part in parts:
            if not isinstance(cur, dict):
                return ""
            cur = cast("dict[str, Any]", cur).get(part)
        return str(cur or "").lower()
    cur_obj: Any = row
    for part in parts:
        cur_obj = getattr(cur_obj, part, None)
        if cur_obj is None:
            return ""
    return str(cur_obj).lower()


def _row_matches_needle(
    row: Any,
    needle: str,
    *,
    field_paths: tuple[str, ...],
    uuid_also: bool,
) -> bool:
    if uuid_also:
        uid: Any = getattr(row, "uuid", None)
        if uid is None and isinstance(row, dict):
            uid = cast("dict[str, Any]", row).get("uuid")
        if uid and needle in str(uid).lower():
            return True
    return any(needle in _row_field_text(row, path) for path in field_paths)


def _truncation_warning(
    row_count: int,
    *,
    max_pages: int | None,
    page_size: int | None,
) -> str | None:
    if max_pages is None or max_pages <= 0:
        return None
    effective_page_size = page_size if page_size and page_size > 0 else 100
    cap = max_pages * effective_page_size
    if row_count >= cap:
        return (
            f"Search list may be truncated at {row_count} rows; "
            "matches beyond the cap are invisible — "
            "increase max_pages or narrow filter."
        )
    return None


def search_substring_on_fields(
    facade: Any,
    *,
    query: str,
    field_paths: tuple[str, ...],
    namespace: str | None = None,
    traverse: bool = False,
    warnings_out: list[str] | None = None,
    uuid_also: bool = False,
    row_predicate: Callable[[Any, str], bool] | None = None,
    **list_kwargs: Any,
) -> list[Any]:
    """List via ``facade.list`` then client-side substring match on field paths.

    Forwards ``list_kwargs`` (``mask``, ``filter``, ``sort_by``, ``list_params``,
    etc.) to ``list()``. Raises ``ValueError`` when ``count=True``.
    """
    if list_kwargs.get("count") is True:
        raise ValueError("search methods do not support count=True; use list().count()")
    needle = query.strip().lower()
    if not needle:
        return []

    ns = namespace
    if ns is None:
        ns_fn = getattr(facade, "_ns", None)
        if callable(ns_fn):
            ns = ns_fn(None)

    max_pages = list_kwargs.get("max_pages")
    page_size = list_kwargs.get("page_size")

    rows = facade.list(
        namespace=ns,
        traverse=traverse,
        **list_kwargs,
    )
    msg = _truncation_warning(len(rows), max_pages=max_pages, page_size=page_size)
    if msg and warnings_out is not None:
        warnings_out.append(msg)

    out: list[Any] = []
    for row in rows:
        if row_predicate is not None and row_predicate(row, needle):
            out.append(row)
            continue
        if _row_matches_needle(
            row, needle, field_paths=field_paths, uuid_also=uuid_also
        ):
            out.append(row)
    return out


def _authorization_policy_row_matches(row: Any, n: str) -> bool:
    if isinstance(row, dict):
        row_dict = cast("dict[str, Any]", row)
        meta_raw = cast("dict[str, Any]", row_dict.get("meta") or {})
        pname = meta_raw.get("name")
        if pname and n in str(pname).lower():
            return True
        spec_raw = cast("dict[str, Any]", row_dict.get("spec") or {})
        raw_clauses = cast("list[Any]", spec_raw.get("clause") or [])
        if raw_clauses:
            blob = " ".join(str(c) for c in raw_clauses).lower()
            if n in blob:
                return True
        target_ns = cast("list[Any]", spec_raw.get("target_namespaces") or [])
        if target_ns:
            blob = " ".join(str(x) for x in target_ns).lower()
            if n in blob:
                return True
        return False

    meta = getattr(row, "meta", None)
    name = getattr(meta, "name", None) if meta else None
    if name and n in str(name).lower():
        return True
    spec = getattr(row, "spec", None)
    clauses = getattr(spec, "clause", None) if spec else None
    if clauses:
        blob = " ".join(str(c) for c in clauses).lower()
        if n in blob:
            return True
    target_ns = getattr(spec, "target_namespaces", None) if spec else None
    if target_ns:
        blob = " ".join(str(x) for x in target_ns).lower()
        if n in blob:
            return True
    return False


def search_policy_by_claims(
    facade: Any,
    *,
    query: str,
    namespace: str | None = None,
    traverse: bool = True,
    warnings_out: list[str] | None = None,
    **list_kwargs: Any,
) -> list[Any]:
    """Search authorization policies by name and claim clause text."""
    needle = query.strip().lower()
    if not needle:
        return []

    return search_substring_on_fields(
        facade,
        query=query,
        field_paths=("meta.name",),
        namespace=namespace,
        traverse=traverse,
        warnings_out=warnings_out,
        row_predicate=_authorization_policy_row_matches,
        **list_kwargs,
    )

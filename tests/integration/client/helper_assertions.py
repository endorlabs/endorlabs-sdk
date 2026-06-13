"""Semantic assertions for facade helper integration tests."""

from __future__ import annotations

from typing import Any


def nested_attr(obj: Any, path: str) -> Any:
    """Read dotted path from a model or dict row."""
    cur: Any = obj
    for part in path.split("."):
        if cur is None:
            return None
        cur = cur.get(part) if isinstance(cur, dict) else getattr(cur, part, None)
    return cur


def assert_search_hit(
    row: Any,
    query: str,
    field_paths: tuple[str, ...],
    *,
    uuid_also: bool = False,
) -> None:
    """Row matches client-side search semantics (substring on fields or UUID)."""
    needle = query.strip().lower()
    assert needle, "query must be non-empty"
    if uuid_also:
        uid = nested_attr(row, "uuid")
        if uid and needle in str(uid).lower():
            return
    for path in field_paths:
        text = nested_attr(row, path)
        if text is not None and needle in str(text).lower():
            return
    raise AssertionError(
        f"Row {nested_attr(row, 'uuid')!r} does not match search query {query!r} "
        f"on fields {field_paths}"
    )


def assert_rows_have_field_value(
    rows: list[Any],
    field_path: str,
    expected: str,
    *,
    max_rows: int = 5,
) -> None:
    """Each sampled row has ``field_path == expected`` when the field is present."""
    sample = rows[:max_rows]
    assert sample, "expected at least one row to validate"
    for row in sample:
        actual = nested_attr(row, field_path)
        if actual is not None:
            assert str(actual) == str(expected), (
                f"{field_path}={actual!r} expected {expected!r} "
                f"(row uuid={nested_attr(row, 'uuid')!r})"
            )


def assert_scan_context_partition(
    rows: list[Any], scan: Any, *, max_rows: int = 5
) -> None:
    """Rows belong to the same scan context partition as *scan*."""
    ctx = getattr(scan, "context", None)
    assert ctx is not None, "scan must expose context for partition checks"
    ctx_type = getattr(ctx, "type", None)
    ctx_id = getattr(ctx, "id", None)
    sample = rows[:max_rows]
    assert sample, "expected at least one row to validate partition"
    for row in sample:
        row_ctx = getattr(row, "context", None)
        assert row_ctx is not None, f"row {nested_attr(row, 'uuid')} missing context"
        assert getattr(row_ctx, "type", None) == ctx_type
        if ctx_id:
            assert getattr(row_ctx, "id", None) == ctx_id


# list_for_context edges from golden_edges.json → semantic anchor per target kind
CONTEXT_PARTITION_ANCHORS: dict[str, tuple[str, str]] = {
    "Finding": ("spec.project_uuid", "scan.meta.parent_uuid"),
    "PackageVersion": ("spec.project_uuid", "scan.meta.parent_uuid"),
    "DependencyMetadata": ("spec.importer_data.project_uuid", "scan.meta.parent_uuid"),
    "LinterResult": ("spec.project_uuid", "scan.meta.parent_uuid"),
    "PackageLicense": ("spec.project_uuid", "scan.meta.parent_uuid"),
    "VersionUpgrade": ("spec.project_uuid", "scan.meta.parent_uuid"),
    "RepositoryVersion": ("meta.parent_uuid", "scan.meta.parent_uuid"),
    "ScanWorkflowResult": ("meta.parent_uuid", "scan.meta.parent_uuid"),
}

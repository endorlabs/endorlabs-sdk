"""Tests for context path helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from endorlabs.context.paths import (
    DEFAULT_CONTEXT_DIR,
    cache_dir,
    context_json_path,
    default_reports_subdir,
    flat_task_dir,
    namespace_path_slug,
    platform_openapi_path,
    project_workspace_dir,
    report_packet_dir,
    task_activity_dir,
    tenant_day_slug,
    tenant_day_suffix,
)


def test_default_context_dir() -> None:
    assert DEFAULT_CONTEXT_DIR == ".endorlabs"


def test_cache_and_openapi_paths(tmp_path: Path) -> None:
    root = tmp_path / ".endorlabs"
    assert cache_dir(root).name == "_cache"
    assert platform_openapi_path(root).name == "openapi.json"
    assert context_json_path(root).name == "context.json"
    assert context_json_path(root).parent == cache_dir(root)


def test_tenant_day_suffix_utc() -> None:
    when = datetime(2026, 8, 28, 15, 30, tzinfo=UTC)
    assert tenant_day_suffix(when=when) == "2026-08-28"


def test_tenant_day_slug() -> None:
    assert tenant_day_slug("tenant.example", date_suffix="2026-08-28") == (
        "tenant_example-2026-08-28"
    )


def test_report_packet_dir() -> None:
    path = report_packet_dir("tenant.example", date_suffix="2026-08-28")
    assert path.as_posix().endswith("reports/tenant_example-2026-08-28")


def test_task_activity_dir() -> None:
    path = task_activity_dir("tenant.example", "estate", date_suffix="2026-08-28")
    assert path.as_posix().endswith("tasks/tenant_example-2026-08-28/estate")


def test_flat_task_dir() -> None:
    assert flat_task_dir("parity").as_posix().endswith("tasks/parity")


def test_project_workspace_dir_with_namespace() -> None:
    path = project_workspace_dir(
        "abc-uuid",
        namespace="tenant.example",
        date_suffix="2026-08-28",
    )
    assert path.name == "abc-uuid"
    assert path.parent.name == "projects"


def test_namespace_path_slug() -> None:
    assert namespace_path_slug("tenant.example.child") == "tenant_example_child"


def test_default_reports_subdir() -> None:
    path = default_reports_subdir("duplicates")
    assert path.as_posix().endswith("reports/duplicates")


def test_task_activity_rejects_slashes() -> None:
    from endorlabs.core.exceptions import WorkspaceLayoutError

    with pytest.raises(WorkspaceLayoutError, match="activity"):
        task_activity_dir("tenant", "estate/nested")

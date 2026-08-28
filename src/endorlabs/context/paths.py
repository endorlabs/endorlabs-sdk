"""Path helpers for the unified ``.endorlabs`` local layout."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_CONTEXT_DIR = ".endorlabs"
GITIGNORE_ENTRY = f"{DEFAULT_CONTEXT_DIR}/"
CACHE_DIRNAME = "_cache"
CONTEXT_JSON_FILENAME = "context.json"
SDK_DIRNAME = "sdk"
REPORTS_DIRNAME = "reports"
TASKS_DIRNAME = "tasks"
OPENAPI_FILENAME = "openapi.json"


def default_context_dir() -> Path:
    """Return the default project-local context root directory."""
    return Path(DEFAULT_CONTEXT_DIR)


def namespace_path_slug(namespace: str) -> str:
    """Filesystem slug for a namespace path (``tenant.child`` → ``tenant_child``)."""
    cleaned = namespace.strip().rstrip(".")
    if not cleaned:
        return "unknown"
    return cleaned.replace(".", "_")


def tenant_day_suffix(*, when: datetime | None = None) -> str:
    """UTC calendar day (``YYYY-MM-DD``) for tenant-day directory names."""
    dt = when or datetime.now(UTC)
    return dt.strftime("%Y-%m-%d")


def tenant_day_slug(
    namespace: str,
    *,
    date_suffix: str | None = None,
) -> str:
    """Return ``<namespace-slug>-<YYYY-MM-DD>``."""
    suffix = date_suffix if date_suffix is not None else tenant_day_suffix()
    return f"{namespace_path_slug(namespace)}-{suffix}"


def _context_root(context_dir: str | Path | None) -> Path:
    return Path(context_dir) if context_dir is not None else default_context_dir()


def cache_dir(context_dir: str | Path | None = None) -> Path:
    """Return ``<context>/_cache``."""
    return _context_root(context_dir) / CACHE_DIRNAME


def sdk_dir(context_dir: str | Path | None = None) -> Path:
    """Return materialized SDK agent bundle path under ``_cache/sdk``."""
    return cache_dir(context_dir) / SDK_DIRNAME


def platform_openapi_path(context_dir: str | Path | None = None) -> Path:
    """Canonical OpenAPI spec path after init."""
    return cache_dir(context_dir) / OPENAPI_FILENAME


def context_json_path(context_dir: str | Path | None = None) -> Path:
    """Return path to init manifest JSON."""
    return cache_dir(context_dir) / CONTEXT_JSON_FILENAME


def reports_dir(context_dir: str | Path | None = None) -> Path:
    """Return ``<context>/reports``."""
    return _context_root(context_dir) / REPORTS_DIRNAME


def tasks_dir(context_dir: str | Path | None = None) -> Path:
    """Return ``<context>/tasks``."""
    return _context_root(context_dir) / TASKS_DIRNAME


def report_packet_dir(
    namespace: str,
    *,
    context_dir: str | Path | None = None,
    date_suffix: str | None = None,
) -> Path:
    """Default executive HTML packet directory."""
    return reports_dir(context_dir) / tenant_day_slug(
        namespace, date_suffix=date_suffix
    )


def task_session_dir(
    namespace: str,
    *,
    context_dir: str | Path | None = None,
    date_suffix: str | None = None,
) -> Path:
    """Return ``tasks/<slug>-<YYYY-MM-DD>/``."""
    return tasks_dir(context_dir) / tenant_day_slug(namespace, date_suffix=date_suffix)


def task_activity_dir(
    namespace: str,
    activity: str,
    *,
    context_dir: str | Path | None = None,
    date_suffix: str | None = None,
) -> Path:
    """Return ``tasks/<slug>-<YYYY-MM-DD>/<activity>/``."""
    from endorlabs.core.exceptions import WorkspaceLayoutError

    segment = activity.strip()
    if not segment or "/" in segment or "\\" in segment:
        raise WorkspaceLayoutError(
            f"activity={activity!r} must be a single path segment "
            "(endor-workspace-layout)."
        )
    return (
        task_session_dir(namespace, context_dir=context_dir, date_suffix=date_suffix)
        / segment
    )


def flat_task_dir(
    activity: str,
    *,
    context_dir: str | Path | None = None,
) -> Path:
    """Return ``tasks/<activity>/`` when no tenant-day bucket applies."""
    from endorlabs.core.exceptions import WorkspaceLayoutError

    segment = activity.strip()
    if not segment or "/" in segment or "\\" in segment:
        raise WorkspaceLayoutError(
            f"activity={activity!r} must be a single path segment "
            "(endor-workspace-layout)."
        )
    return tasks_dir(context_dir) / segment


def default_reports_subdir(
    subcommand: str,
    *,
    context_dir: str | Path | None = None,
) -> Path:
    """Return ``reports/<subcommand>/`` for tabular or canvas report outputs."""
    from endorlabs.core.exceptions import WorkspaceLayoutError

    segment = subcommand.strip()
    if not segment or "/" in segment or "\\" in segment:
        raise WorkspaceLayoutError(
            f"subcommand={subcommand!r} must be a single path segment "
            "(endor-workspace-layout)."
        )
    return reports_dir(context_dir) / segment


def project_workspace_dir(
    project_uuid: str,
    *,
    namespace: str | None = None,
    context_dir: str | Path | None = None,
    date_suffix: str | None = None,
) -> Path:
    """Return project-scoped path under ``tasks/<slug>-<date>/projects/<uuid>``."""
    if namespace:
        base = task_activity_dir(
            namespace,
            "projects",
            context_dir=context_dir,
            date_suffix=date_suffix,
        )
    else:
        base = flat_task_dir("projects", context_dir=context_dir)
    return base / project_uuid


def load_context_json(context_dir: str | Path | None = None) -> dict[str, Any] | None:
    """Load context.json when present."""
    path = context_json_path(context_dir)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_openapi_spec_path(context_dir: str | Path | None = None) -> Path | None:
    """Resolve OpenAPI spec path under ``_cache``."""
    path = platform_openapi_path(context_dir)
    return path if path.is_file() else None


def require_openapi_spec(context_dir: str | Path | None = None) -> Path:
    """Return the OpenAPI path or raise :class:`LocalContextError` if absent."""
    from endorlabs.core.exceptions import LocalContextError

    path = resolve_openapi_spec_path(context_dir)
    if path is not None:
        return path
    expected = platform_openapi_path(context_dir)
    raise LocalContextError(
        f"Expected OpenAPI at {expected}. Run "
        "endorlabs.init(include_openapi=True) or configure Docs MCP "
        "(https://docs.endorlabs.com/introduction/docs-mcp-server); unsupported "
        "harnesses can use https://docs.endorlabs.com/llms.txt "
        "(endor-local-context)."
    )


def sanitize_path_segment(value: str) -> str:
    """Normalize a namespace or tenant segment for use in filesystem paths."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    return cleaned.strip("-._") or "unknown"


def resolve_session_user_slug(client: Any) -> str:
    """Derive a short session slug from ``Client().whoami()`` for metadata only."""
    try:
        whoami = client.whoami()
    except Exception:
        return "agent"
    email = str(getattr(whoami, "email", "") or "")
    if email and "@" in email:
        local = email.split("@", 1)[0]
        return "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in local)
    return "agent"


__all__ = [
    "CACHE_DIRNAME",
    "CONTEXT_JSON_FILENAME",
    "DEFAULT_CONTEXT_DIR",
    "GITIGNORE_ENTRY",
    "OPENAPI_FILENAME",
    "REPORTS_DIRNAME",
    "SDK_DIRNAME",
    "TASKS_DIRNAME",
    "cache_dir",
    "context_json_path",
    "default_context_dir",
    "default_reports_subdir",
    "flat_task_dir",
    "load_context_json",
    "namespace_path_slug",
    "platform_openapi_path",
    "project_workspace_dir",
    "report_packet_dir",
    "reports_dir",
    "require_openapi_spec",
    "resolve_openapi_spec_path",
    "resolve_session_user_slug",
    "sanitize_path_segment",
    "sdk_dir",
    "task_activity_dir",
    "task_session_dir",
    "tasks_dir",
    "tenant_day_slug",
    "tenant_day_suffix",
]

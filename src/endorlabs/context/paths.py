"""Path helpers for the unified .endorlabs-context layout."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_CONTEXT_DIR = ".endorlabs-context"
CONTEXT_JSON_FILENAME = "context.json"
SDK_DIRNAME = "sdk"
PLATFORM_DIRNAME = "platform"
WORKSPACE_DIRNAME = "workspace"
PLATFORM_OPENAPI_DIRNAME = "openapi"
PLATFORM_USER_DOCS_DIRNAME = "user-docs"
OPENAPI_FILENAME = "openapiv2.swagger.json"


def default_context_dir() -> Path:
    """Return the default project-local context root directory."""
    return Path(DEFAULT_CONTEXT_DIR)


def sdk_dir(context_dir: str | Path) -> Path:
    """Return materialized SDK agent bundle path under context."""
    return Path(context_dir) / SDK_DIRNAME


def platform_dir(context_dir: str | Path) -> Path:
    """Return platform downloads root under context."""
    return Path(context_dir) / PLATFORM_DIRNAME


def platform_openapi_path(context_dir: str | Path) -> Path:
    """Canonical OpenAPI spec path after init."""
    return platform_dir(context_dir) / PLATFORM_OPENAPI_DIRNAME / OPENAPI_FILENAME


def platform_user_docs_path(context_dir: str | Path) -> Path:
    """Canonical user docs directory after init."""
    return platform_dir(context_dir) / PLATFORM_USER_DOCS_DIRNAME


def workspace_dir(context_dir: str | Path) -> Path:
    """Return workspace root for generated run artifacts."""
    return Path(context_dir) / WORKSPACE_DIRNAME


def project_workspace_dir(context_dir: str | Path, project_uuid: str) -> Path:
    """Return workspace directory for a project UUID."""
    return workspace_dir(context_dir) / "projects" / project_uuid


def session_workspace_dir(context_dir: str | Path, user: str) -> Path:
    """Legacy path under ``workspace/sessions/<user>/``.

    Prefer :func:`default_runs_dir` for new workflow output.
    """
    return workspace_dir(context_dir) / "sessions" / user


def context_json_path(context_dir: str | Path) -> Path:
    """Return path to init manifest JSON."""
    return Path(context_dir) / CONTEXT_JSON_FILENAME


def load_context_json(context_dir: str | Path) -> dict[str, Any] | None:
    """Load context.json when present."""
    path = context_json_path(context_dir)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_openapi_spec_path(context_dir: str | Path) -> Path | None:
    """Resolve OpenAPI spec path under platform layout."""
    path = platform_openapi_path(context_dir)
    return path if path.is_file() else None


def resolve_user_docs_path(context_dir: str | Path) -> Path | None:
    """Resolve user docs directory under platform layout."""
    path = platform_user_docs_path(context_dir)
    return path if path.is_dir() else None


def workflow_projects_root(context_dir: str | Path | None = None) -> Path:
    """Default base directory for project-scoped workflow artifacts."""
    root = Path(context_dir or DEFAULT_CONTEXT_DIR)
    return workspace_dir(root) / "projects"


def workflow_sessions_root(
    context_dir: str | Path | None = None,
    *,
    user: str | None = None,
    subdir: str | None = None,
) -> Path:
    """Legacy session layout under ``workspace/sessions/``.

    Prefer :func:`default_runs_dir` for new workflow output. This helper remains for
    callers not yet migrated to the ``workspace/runs/<run-bucket>/`` layout.
    """
    root = Path(context_dir or DEFAULT_CONTEXT_DIR)
    base = workspace_dir(root) / "sessions"
    if user:
        base = base / user
    if subdir:
        base = base / subdir
    return base


def default_runs_dir(
    run_bucket: str,
    context_dir: str | Path | None = None,
) -> Path:
    """Return ``workspace/runs/<run-bucket>/`` for ephemeral workflow artifacts.

    ``run_bucket`` is a fixed, authored string (catalog ``workflow_id`` or skill id
    minus ``endor-``). It is not generated at runtime and must not be a timestamp.
    """
    root = Path(context_dir or DEFAULT_CONTEXT_DIR)
    return workspace_dir(root) / "runs" / run_bucket


def workflow_inventory_root(context_dir: str | Path | None = None) -> Path:
    """Return ``workspace/inventory/`` for namespace-scoped inventory artifacts."""
    root = Path(context_dir or DEFAULT_CONTEXT_DIR)
    return workspace_dir(root) / "inventory"


def workflow_artifacts_root(context_dir: str | Path | None = None) -> Path:
    """Alias for :func:`workflow_inventory_root` (legacy name ``artifacts/``)."""
    return workflow_inventory_root(context_dir)


def sanitize_path_segment(value: str) -> str:
    """Normalize a namespace or tenant segment for use in filesystem paths."""
    import re

    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    return cleaned.strip("-._") or "unknown"


def resolve_session_user_slug(client: Any) -> str:
    """Derive a short session slug from ``Client().whoami()`` for metadata only.

    Default run paths do not include this slug; use for JSON summaries when needed.
    Fallback is ``agent``.
    """
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
    "CONTEXT_JSON_FILENAME",
    "DEFAULT_CONTEXT_DIR",
    "OPENAPI_FILENAME",
    "PLATFORM_DIRNAME",
    "PLATFORM_OPENAPI_DIRNAME",
    "PLATFORM_USER_DOCS_DIRNAME",
    "SDK_DIRNAME",
    "WORKSPACE_DIRNAME",
    "context_json_path",
    "default_context_dir",
    "default_runs_dir",
    "load_context_json",
    "platform_dir",
    "platform_openapi_path",
    "platform_user_docs_path",
    "project_workspace_dir",
    "resolve_openapi_spec_path",
    "resolve_session_user_slug",
    "resolve_user_docs_path",
    "sanitize_path_segment",
    "sdk_dir",
    "session_workspace_dir",
    "workflow_artifacts_root",
    "workflow_inventory_root",
    "workflow_projects_root",
    "workflow_sessions_root",
    "workspace_dir",
]

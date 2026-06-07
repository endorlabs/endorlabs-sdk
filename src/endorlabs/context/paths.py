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
    """Return workspace directory for an interactive session user."""
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
    """Default base directory for session-scoped workflow artifacts."""
    root = Path(context_dir or DEFAULT_CONTEXT_DIR)
    base = workspace_dir(root) / "sessions"
    if user:
        base = base / user
    if subdir:
        base = base / subdir
    return base


def workflow_artifacts_root(context_dir: str | Path | None = None) -> Path:
    """Default directory for namespace-scoped workflow artifacts (non-project)."""
    root = Path(context_dir or DEFAULT_CONTEXT_DIR)
    return workspace_dir(root) / "artifacts"


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
    "load_context_json",
    "platform_dir",
    "platform_openapi_path",
    "platform_user_docs_path",
    "project_workspace_dir",
    "resolve_openapi_spec_path",
    "resolve_user_docs_path",
    "sdk_dir",
    "session_workspace_dir",
    "workflow_artifacts_root",
    "workflow_projects_root",
    "workflow_sessions_root",
    "workspace_dir",
]

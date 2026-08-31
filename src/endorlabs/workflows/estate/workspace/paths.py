"""Estate workspace directory layout."""

from __future__ import annotations

from pathlib import Path

from endorlabs.context.paths import (
    default_context_dir,
    namespace_path_slug,
    task_activity_dir,
    tenant_day_suffix,
)
from endorlabs.workflows.estate.contracts.resources import (
    ANALYZE_LOG_FILENAME,
    COLLECT_MANIFEST_FILENAME,
    DATA_DIR,
    IR_DIR,
    LOGS_DIR,
    PULL_LOG_FILENAME,
    VIZ_DIR,
    collect_manifest_relpath,
    ir_relpath,
    logs_relpath,
    resource_data_relpath,
    viz_relpath,
)

# Re-export shared layout helpers (estate historically owned these names).
namespace_slug = namespace_path_slug


def workspace_dir_for(
    context_dir: str | Path,
    namespace: str,
    *,
    date_suffix: str | None = None,
) -> Path:
    """Return estate workspace under ``tasks/<slug>-<YYYY-MM-DD>/estate/``."""
    return task_activity_dir(
        namespace,
        "estate",
        context_dir=context_dir,
        date_suffix=date_suffix,
    )


def resolve_workspace_root(path_or_manifest: Path) -> Path:
    """Return workspace root for a manifest file or workspace directory path."""
    path = path_or_manifest.resolve()
    if path.is_file():
        if path.name == COLLECT_MANIFEST_FILENAME:
            return path.parent.parent
        return path.parent
    return path


def data_dir(workspace_root: Path) -> Path:
    return workspace_root / DATA_DIR


def ir_dir(workspace_root: Path) -> Path:
    return workspace_root / IR_DIR


def viz_dir(workspace_root: Path) -> Path:
    return workspace_root / VIZ_DIR


def collect_manifest_path(workspace_root: Path) -> Path:
    return workspace_root / collect_manifest_relpath()


def resource_path(workspace_root: Path, resource_id: str) -> Path:
    return workspace_root / resource_data_relpath(resource_id)


def ir_path(workspace_root: Path, filename: str) -> Path:
    return workspace_root / ir_relpath(filename)


def viz_path(workspace_root: Path, filename: str) -> Path:
    return workspace_root / viz_relpath(filename)


def logs_dir(workspace_root: Path) -> Path:
    return workspace_root / LOGS_DIR


def pull_log_path(workspace_root: Path) -> Path:
    return workspace_root / logs_relpath(PULL_LOG_FILENAME)


def analyze_log_path(workspace_root: Path) -> Path:
    return workspace_root / logs_relpath(ANALYZE_LOG_FILENAME)


def ensure_workspace_layout(workspace_root: Path) -> None:
    workspace_root.mkdir(parents=True, exist_ok=True)
    data_dir(workspace_root).mkdir(parents=True, exist_ok=True)
    ir_dir(workspace_root).mkdir(parents=True, exist_ok=True)
    viz_dir(workspace_root).mkdir(parents=True, exist_ok=True)
    logs_dir(workspace_root).mkdir(parents=True, exist_ok=True)


__all__ = [
    "analyze_log_path",
    "collect_manifest_path",
    "data_dir",
    "default_context_dir",
    "ensure_workspace_layout",
    "ir_dir",
    "ir_path",
    "logs_dir",
    "namespace_slug",
    "pull_log_path",
    "resolve_workspace_root",
    "resource_path",
    "tenant_day_suffix",
    "viz_dir",
    "viz_path",
    "workspace_dir_for",
]

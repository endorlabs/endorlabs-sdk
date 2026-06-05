"""Tests for context path helpers."""

from __future__ import annotations

from pathlib import Path

from endorlabs.context.paths import (
    context_json_path,
    platform_openapi_path,
    platform_user_docs_path,
    project_workspace_dir,
    session_workspace_dir,
    workflow_projects_root,
    workflow_sessions_root,
    workspace_dir,
)


def test_platform_paths_under_context(tmp_path: Path) -> None:
    root = tmp_path / ".endorlabs-context"
    assert platform_openapi_path(root).name == "openapiv2.swagger.json"
    assert platform_openapi_path(root).parent.name == "openapi"
    assert platform_user_docs_path(root).name == "user-docs"


def test_workspace_layout(tmp_path: Path) -> None:
    root = tmp_path / ".endorlabs-context"
    assert workspace_dir(root).name == "workspace"
    assert project_workspace_dir(root, "abc").parts[-2:] == ("projects", "abc")
    assert session_workspace_dir(root, "tim").parts[-2:] == ("sessions", "tim")


def test_context_json_path(tmp_path: Path) -> None:
    root = tmp_path / ".endorlabs-context"
    assert context_json_path(root).name == "context.json"


def test_workflow_defaults_use_workspace() -> None:
    assert workflow_projects_root().as_posix().endswith("workspace/projects")
    assert (
        workflow_sessions_root(subdir="troubleshooting")
        .as_posix()
        .endswith("sessions/troubleshooting")
    )
    assert workflow_sessions_root(user="alice").as_posix().endswith("sessions/alice")

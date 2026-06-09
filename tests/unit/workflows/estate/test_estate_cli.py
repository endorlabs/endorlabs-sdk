"""Tests for endor-estate CLI wiring."""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock, patch

from endorlabs.workflows.estate.cli.main import (
    _resolve_workspace,
    build_parser,
    cmd_analyze,
    cmd_pull,
    cmd_summarize,
    main,
)
from endorlabs.workflows.estate.workspace.paths import ensure_workspace_layout, ir_path


def test_build_parser_registers_subcommands() -> None:
    parser = build_parser()
    args = parser.parse_args(["pull", "-n", "tenant.example"])
    assert args.command == "pull"
    assert args.namespace == "tenant.example"


def test_resolve_workspace_from_explicit_path(tmp_path: Path) -> None:
    args = Namespace(workspace=str(tmp_path), namespace=None, date=None)
    assert _resolve_workspace(args) == tmp_path.resolve()


def test_resolve_workspace_from_namespace_slug() -> None:
    args = Namespace(workspace=None, namespace="tenant.example", date="20260101")
    path = _resolve_workspace(args)
    assert path.name == "tenant_example-20260101"


def test_cmd_summarize_prints_text(tmp_path: Path, capsys) -> None:
    ensure_workspace_layout(tmp_path)
    ir_path(tmp_path, "compile_dependency_graph.json").write_text(
        json.dumps(
            {"node_count": 1, "edge_count": 0, "isolated_count": 0, "nodes": []}
        ),
        encoding="utf-8",
    )
    args = Namespace(workspace=str(tmp_path), namespace="tenant", json=False, date=None)
    assert cmd_summarize(args) == 0
    out = capsys.readouterr().out
    assert "nodes=1" in out


def test_cmd_pull_delegates_to_collect_workspace(tmp_path: Path) -> None:
    fake_client = MagicMock()
    fake_result = MagicMock(
        workspace_root=tmp_path,
        resources={"project": "complete"},
    )
    with (
        patch(
            "endorlabs.workflows.estate.cli.main.endorlabs.Client",
            return_value=fake_client,
        ),
        patch(
            "endorlabs.workflows.estate.cli.main.collect_workspace",
            return_value=fake_result,
        ) as mock_collect,
    ):
        args = Namespace(
            namespace="tenant.example",
            workspace=str(tmp_path),
            date=None,
            max_workers=4,
            max_pages=0,
            page_size=500,
            resume=False,
            overwrite=False,
            preflight=False,
            validate_counts=False,
        )
        assert cmd_pull(args) == 0
    mock_collect.assert_called_once()
    fake_client.close.assert_called_once()


def test_cmd_pull_requires_namespace() -> None:
    args = Namespace(
        namespace=None,
        workspace=None,
        date=None,
        max_workers=8,
        max_pages=0,
        page_size=500,
        resume=False,
        overwrite=False,
        preflight=False,
        validate_counts=False,
    )
    assert cmd_pull(args) == 2


def test_cmd_analyze_returns_error_on_failure(tmp_path: Path) -> None:
    ensure_workspace_layout(tmp_path)
    with patch(
        "endorlabs.workflows.estate.cli.main.analyze_workspace",
        side_effect=RuntimeError("analyze failed"),
    ):
        args = Namespace(
            namespace="tenant.example",
            workspace=str(tmp_path),
            date=None,
            only=None,
            top_n=5,
            scorer="critical_high_count",
            skip_metrics=False,
            skip_validate=True,
        )
        assert cmd_analyze(args) == 1


def test_cmd_analyze_delegates_to_workspace(tmp_path: Path) -> None:
    ensure_workspace_layout(tmp_path)
    fake_result = MagicMock(steps={"graph": "ok"})
    with patch(
        "endorlabs.workflows.estate.cli.main.analyze_workspace",
        return_value=fake_result,
    ) as mock_analyze:
        args = Namespace(
            namespace="tenant.example",
            workspace=str(tmp_path),
            date=None,
            only="graph,viz",
            top_n=5,
            scorer="critical_high_count",
            skip_metrics=True,
            skip_validate=True,
        )
        assert cmd_analyze(args) == 0
    mock_analyze.assert_called_once()


def test_main_invokes_subcommand() -> None:
    with patch(
        "endorlabs.workflows.estate.cli.main.cmd_pull", return_value=0
    ) as mock_pull:
        assert main(["pull", "-n", "tenant.example"]) == 0
    mock_pull.assert_called_once()

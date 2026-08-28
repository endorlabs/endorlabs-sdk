"""Tests for endor-reports CLI Option B (default build with -n)."""

from __future__ import annotations

import os
from unittest.mock import patch

from endorlabs.context.paths import default_reports_subdir
from endorlabs.workflows.reports.cli import build_parser, catalog_for_list, main


def test_build_parser_default_build_without_subcommand() -> None:
    parser = build_parser()
    args = parser.parse_args(["-n", "example-tenant", "--skip-version-sprawl"])
    assert args.command is None
    assert args.namespace == "example-tenant"
    assert args.skip_version_sprawl is True


def test_build_parser_patches_subcommand() -> None:
    parser = build_parser()
    args = parser.parse_args(["patches", "-n", "example-tenant"])
    assert args.command == "patches"
    assert args.patches_only is True


def test_namespace_before_subcommand_duplicates() -> None:
    with patch(
        "endorlabs.workflows.reports.analyze.duplicate_projects.main",
        return_value=0,
    ) as mock_run:
        assert main(["-n", "example-tenant", "duplicates"]) == 0
    assert mock_run.call_args[0][0] == ["--tenant", "example-tenant"]


def test_namespace_after_subcommand_duplicates() -> None:
    with patch(
        "endorlabs.workflows.reports.analyze.duplicate_projects.main",
        return_value=0,
    ) as mock_run:
        assert main(["duplicates", "-n", "example-tenant"]) == 0
    assert mock_run.call_args[0][0] == ["--tenant", "example-tenant"]


def test_namespace_env_fallback_for_tabular() -> None:
    with (
        patch.dict(os.environ, {"ENDOR_NAMESPACE": "env-tenant"}),
        patch(
            "endorlabs.workflows.reports.analyze.duplicate_projects.main",
            return_value=0,
        ) as mock_run,
    ):
        assert main(["duplicates"]) == 0
    assert mock_run.call_args[0][0] == ["--tenant", "env-tenant"]


def test_main_default_build_requires_namespace() -> None:
    with patch(
        "endorlabs.workflows.reports.cli._run_packet", return_value=0
    ) as mock_run:
        assert main(["-n", "example-tenant"]) == 0
    mock_run.assert_called_once()


def test_main_list_subcommand() -> None:
    assert main(["list"]) == 0


def test_catalog_for_list_includes_login_count() -> None:
    rows = catalog_for_list()
    login = next(r for r in rows if r["subcommand"] == "login-count")
    assert (
        login["default_output"]
        == f"{default_reports_subdir('auth-login-count').as_posix()}/"
    )


def test_main_refresh_code_subcommand() -> None:
    with patch(
        "endorlabs.workflows.reports.cli._run_refresh_code", return_value=0
    ) as mock:
        assert main(["refresh-code", "--packet-dir", "/tmp/packet"]) == 0
    mock.assert_called_once()

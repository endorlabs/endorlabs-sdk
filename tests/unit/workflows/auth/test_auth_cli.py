"""Unit tests for endor-auth CLI."""

from __future__ import annotations

from argparse import Namespace
from unittest.mock import patch

from endorlabs.workflows.auth.cli import _run_check, _run_refresh


def test_run_check_ready_json(capsys) -> None:
    from endorlabs.workflows.auth.session import (
        AuthEnvironmentScan,
        AuthVerification,
        EndorctlProbe,
    )

    verification = AuthVerification(
        status="ready",
        environment=AuthEnvironmentScan(
            has_bearer_token=True,
            has_api_key=False,
            has_api_secret=False,
            has_namespace_env=True,
            dual_mode_conflict=False,
            endor_namespace_set=True,
            endorctl_config_present=False,
            endorctl_namespace_configured=False,
        ),
        endorctl=EndorctlProbe(
            on_path=False,
            executable=None,
            version=None,
            config_path="/home/user/.endorctl/config.yaml",
            config_exists=False,
        ),
    )
    with patch(
        "endorlabs.workflows.auth.cli.verify_auth",
        return_value=verification,
    ):
        code = _run_check(Namespace(tenant=None, json=True))
    assert code == 0
    out = capsys.readouterr().out
    assert '"status": "ready"' in out


def test_run_refresh_failure(capsys) -> None:
    with patch(
        "endorlabs.workflows.auth.cli.refresh_token_to_dotenv",
        side_effect=RuntimeError("timed out"),
    ):
        code = _run_refresh(
            Namespace(
                env_file=".env",
                method="sso",
                namespace="tenant",
                email=None,
                environment=None,
                timeout=120,
            )
        )
    assert code == 1
    assert "timed out" in capsys.readouterr().err

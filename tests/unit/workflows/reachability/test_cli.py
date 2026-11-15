"""Tests for reachability CLI argument parsing and main flow."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from endorlabs.workflows.reachability import cli
from endorlabs.workflows.reachability.context import ReachabilityContextResult


def test_parse_args_defaults_and_flags() -> None:
    args = cli.parse_args(
        [
            "-n",
            "tenant.ns",
            "--finding-uuid",
            "f-1",
            "--output-dir",
            ".tmp/out",
            "--no-decode-zstd",
            "--no-include-oss-callgraph",
        ]
    )
    assert args.tenant == "tenant.ns"
    assert args.namespace == ""
    assert args.finding_uuid == "f-1"
    assert args.decode_zstd is False
    assert args.include_oss_callgraph is False
    assert args.include_customer_callgraph is True


def test_main_defaults_namespace_to_tenant(
    capsys: pytest.CaptureFixture[str],
) -> None:
    acquired = ReachabilityContextResult(
        status="success",
        message="ok",
        payload={"warnings": []},
    )
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)

    with (
        patch(
            "endorlabs.workflows.reachability.cli.endorlabs.Client",
            return_value=mock_client,
        ),
        patch(
            "endorlabs.workflows.reachability.cli.acquire_reachability_context",
            return_value=acquired,
        ) as mock_acquire,
        patch(
            "endorlabs.workflows.reachability.cli.write_reachability_context",
            return_value=Path("out/context.json"),
        ),
    ):
        code = cli.main(
            [
                "-n",
                "tenant.ns",
                "--finding-uuid",
                "finding-123",
                "--output-dir",
                ".tmp",
            ]
        )

    assert code == 0
    req = mock_acquire.call_args.args[1]
    assert req.tenant == "tenant.ns"
    assert req.namespace == "tenant.ns"


@pytest.mark.parametrize(
    "argv",
    [
        ["--tenant", "t", "--namespace", "n", "--output-dir", "o"],
        [
            "--tenant",
            "t",
            "--namespace",
            "n",
            "--finding-uuid",
            "f",
            "--pv-uuid",
            "p",
            "--output-dir",
            "o",
        ],
    ],
)
def test_main_requires_exactly_one_identifier(argv: list[str]) -> None:
    with pytest.raises(SystemExit, match="exactly one"):
        cli.main(argv)


def test_main_builds_request_and_prints_output(
    capsys: pytest.CaptureFixture[str],
) -> None:
    acquired = ReachabilityContextResult(
        status="success",
        message="ok",
        payload={"warnings": []},
    )
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)

    with (
        patch(
            "endorlabs.workflows.reachability.cli.endorlabs.Client",
            return_value=mock_client,
        ),
        patch(
            "endorlabs.workflows.reachability.cli.acquire_reachability_context",
            return_value=acquired,
        ) as mock_acquire,
        patch(
            "endorlabs.workflows.reachability.cli.write_reachability_context",
            return_value=Path("out/context.json"),
        ),
    ):
        code = cli.main(
            [
                "--tenant",
                "tenant.ns",
                "--namespace",
                "tenant.ns",
                "--finding-uuid",
                "finding-123",
                "--output-dir",
                ".tmp",
            ]
        )

    assert code == 0
    req = mock_acquire.call_args.args[1]
    assert req.finding_uuid == "finding-123"
    assert req.pv_uuid is None
    assert capsys.readouterr().out.strip().endswith("context.json")

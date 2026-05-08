"""Tests for reachability CLI argument parsing and main flow."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from endorlabs.workflows.reachability import cli


def test_parse_args_defaults_and_flags() -> None:
    args = cli.parse_args(
        [
            "--tenant",
            "tenant.ns",
            "--namespace",
            "tenant.ns",
            "--finding-uuid",
            "f-1",
            "--output-dir",
            ".tmp/out",
            "--no-decode-zstd",
            "--no-include-oss-callgraph",
        ]
    )
    assert args.finding_uuid == "f-1"
    assert args.decode_zstd is False
    assert args.include_oss_callgraph is False
    assert args.include_customer_callgraph is True


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
    with patch(
        "endorlabs.workflows.reachability.cli.build_reachability_context",
        return_value=Path("out/context.json"),
    ) as mock_build:
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
    req = mock_build.call_args.args[0]
    assert req.finding_uuid == "finding-123"
    assert req.pv_uuid is None
    assert capsys.readouterr().out.strip().endswith("context.json")

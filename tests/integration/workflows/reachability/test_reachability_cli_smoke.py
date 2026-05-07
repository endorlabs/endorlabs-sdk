"""Integration smoke tests for reachability workflow CLI plumbing."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from endorlabs.workflows.reachability import cli as reachability_cli


@pytest.mark.integration
def test_reachability_cli_finding_mode_smoke(tmp_path: Path) -> None:
    with patch(
        "endorlabs.workflows.reachability.cli.build_reachability_context",
        return_value=tmp_path / "reachability_context.json",
    ) as mocked:
        rc = reachability_cli.main(
            [
                "--tenant",
                "acme",
                "--namespace",
                "acme",
                "--finding-uuid",
                "finding-1",
                "--output-dir",
                str(tmp_path),
            ]
        )
    assert rc == 0
    assert mocked.called


@pytest.mark.integration
def test_reachability_cli_requires_exactly_one_subject(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        reachability_cli.main(
            [
                "--tenant",
                "acme",
                "--namespace",
                "acme",
                "--finding-uuid",
                "f-1",
                "--pv-uuid",
                "pv-1",
                "--output-dir",
                str(tmp_path),
            ]
        )

"""Unit tests for agent_context CLI dispatch wrapper."""

from __future__ import annotations

from unittest.mock import patch

from endorlabs.workflows.agent_context.cli import cli_main


def test_cli_main_delegates_to_export_main() -> None:
    with patch("endorlabs.workflows.agent_context.cli.main", return_value=7) as mocked:
        assert cli_main() == 7
        mocked.assert_called_once_with()

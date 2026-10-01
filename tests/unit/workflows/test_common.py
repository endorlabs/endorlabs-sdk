"""Unit tests for endorlabs.workflows.common."""

import argparse

from endorlabs.workflows.common import WorkflowResult
from endorlabs.workflows.common.cli_client import (
    add_client_auth_arguments,
    client_kwargs_from_args,
)


class TestWorkflowResult:
    """Tests for WorkflowResult base dataclass."""

    def test_defaults(self) -> None:
        r = WorkflowResult()
        assert r.status == "success"
        assert r.message == ""
        assert r.errors == []
        assert r.ok is True

    def test_error_status(self) -> None:
        r = WorkflowResult(status="error", message="boom", errors=["e1"])
        assert r.ok is False
        assert r.errors == ["e1"]

    def test_partial_status(self) -> None:
        r = WorkflowResult(status="partial")
        assert r.ok is False


class TestCliClientAuth:
    """Shared workflow CLI auth flag mapping."""

    def test_empty_args(self) -> None:
        parser = argparse.ArgumentParser()
        add_client_auth_arguments(parser)
        args = parser.parse_args([])
        assert client_kwargs_from_args(args) == {}

    def test_token_and_api(self) -> None:
        parser = argparse.ArgumentParser()
        add_client_auth_arguments(parser)
        args = parser.parse_args(["--token", "t", "--api", "https://api.endorlabs.com"])
        assert client_kwargs_from_args(args) == {
            "token": "t",
            "base_url": "https://api.endorlabs.com",
        }

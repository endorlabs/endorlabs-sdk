"""Unit tests for endorlabs.workflows.common."""

from endorlabs.workflows.common import WorkflowResult


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

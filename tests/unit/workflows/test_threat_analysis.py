"""Unit tests for the threat_analysis workflow."""

from __future__ import annotations

from unittest.mock import MagicMock

from endorlabs.workflows.threat_analysis import (
    ThreatModelResult,
    _count_metrics,
    analyze_project_threat_model,
)

# ---------------------------------------------------------------------------
# _count_metrics tests
# ---------------------------------------------------------------------------


class TestCountMetrics:
    """Tests for the metric extraction helper."""

    def test_extracts_finding_count(self) -> None:
        md = "**Total findings**: 354\n"
        m = _count_metrics(md)
        assert m["finding_count"] == 354

    def test_extracts_policy_count(self) -> None:
        md = "**Total policies**: 77\n"
        m = _count_metrics(md)
        assert m["policy_count"] == 77

    def test_counts_category_rows(self) -> None:
        md = (
            "| Category | Critical | High |\n"
            "|----------|----------|------|\n"
            "| VULNERABILITY | 5 | 10 |\n"
            "| SAST | 0 | 0 |\n"
            "| SECRETS | 1 | 2 |\n"
            "\n"
        )
        m = _count_metrics(md)
        assert m["category_count"] == 3

    def test_defaults_on_empty_input(self) -> None:
        m = _count_metrics("")
        assert m["finding_count"] == 0
        assert m["category_count"] == 1  # max(0, 1)
        assert m["policy_count"] == 0


# ---------------------------------------------------------------------------
# analyze_project_threat_model tests
# ---------------------------------------------------------------------------


SAMPLE_REPORT = """\
## Component Architecture
The application is a Node.js web app.

## Attack Surface
REST API and WebSocket endpoints.

## Risk Assessment
1. CVE-2024-1234 — SQL injection in login form (CRITICAL)
2. GHSA-abcd — XSS in search bar (HIGH)
3. Outdated express dependency (MEDIUM)

## Dependency Risk
form-data uses unsafe random.

## Policy Coverage
No SAST policy configured.

## Recommendations
1. Upgrade express to latest.
2. Add SAST scanning.
3. Rotate leaked secrets.
"""


class TestAnalyzeProjectThreatModel:
    """Tests for the main analysis function."""

    def test_success_path(self) -> None:
        llm = MagicMock()
        llm.invoke.return_value = MagicMock(content=SAMPLE_REPORT)

        result = analyze_project_threat_model(
            llm, "juice-shop", "**Total findings**: 10\n"
        )
        assert isinstance(result, ThreatModelResult)
        assert result.status == "success"
        assert result.project_name == "juice-shop"
        assert result.risk_count == 3
        assert "SQL injection" in result.report

    def test_llm_failure_returns_error(self) -> None:
        llm = MagicMock()
        llm.invoke.side_effect = RuntimeError("LLM timeout")

        result = analyze_project_threat_model(llm, "juice-shop", "context")
        assert result.status == "error"
        assert "LLM timeout" in result.message
        assert result.report == ""

    def test_prompt_includes_project_name(self) -> None:
        llm = MagicMock()
        llm.invoke.return_value = MagicMock(content="report")

        analyze_project_threat_model(llm, "my-project", "**Total findings**: 5\n")
        prompt_text = llm.invoke.call_args[0][0]
        assert "my-project" in prompt_text

    def test_prompt_includes_finding_count(self) -> None:
        llm = MagicMock()
        llm.invoke.return_value = MagicMock(content="report")

        analyze_project_threat_model(llm, "p", "**Total findings**: 42\n")
        prompt_text = llm.invoke.call_args[0][0]
        assert "42 security findings" in prompt_text


class TestThreatModelResult:
    """Tests for the result dataclass."""

    def test_ok_property(self) -> None:
        r = ThreatModelResult(status="success")
        assert r.ok is True

    def test_not_ok_on_error(self) -> None:
        r = ThreatModelResult(status="error")
        assert r.ok is False

    def test_defaults(self) -> None:
        r = ThreatModelResult()
        assert r.project_name == ""
        assert r.report == ""
        assert r.risk_count == 0

"""Tests for the session_context workflow.

Verifies context pulling, summary rendering, and artifact writing
with mocked client facades.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock

from endorlabs.workflows.session_context import (
    FindingsContext,
    PoliciesContext,
    SessionResult,
    VersionsContext,
    build_project_session_key,
    create_session,
    pull_findings_context,
    pull_policies_context,
    pull_repository_versions_context,
    render_findings_summary,
    render_policies_summary,
    render_versions_summary,
    write_session_artifacts,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_mock_project(
    uuid: str = "proj-uuid-123",
    name: str = "https://github.com/org/test-repo.git",
    namespace: str = "test-tenant",
) -> Mock:
    """Create a mock project resource."""
    project = Mock()
    project.uuid = uuid
    project.meta.name = name
    project.tenant_meta.namespace = namespace
    return project


def _make_mock_finding(
    uuid: str = "find-1",
    level: str = "FINDING_LEVEL_HIGH",
    categories: list[str] | None = None,
    description: str = "Test finding",
) -> Mock:
    """Create a mock finding resource."""
    if categories is None:
        categories = ["FINDING_CATEGORY_VULNERABILITY"]
    finding = Mock()
    finding.uuid = uuid
    finding.meta.description = description
    finding.spec.level = level
    finding.spec.finding_categories = categories
    finding.spec.target_dependency_package_name = "lodash"
    finding.spec.summary = description
    return finding


def _make_mock_policy(
    uuid: str = "pol-1",
    name: str = "test-policy",
    disabled: bool = False,
    policy_type: str = "POLICY_TYPE_FINDING",
    action: str = "POLICY_ACTION_WARN",
) -> Mock:
    """Create a mock policy resource."""
    policy = Mock()
    policy.uuid = uuid
    policy.meta.name = name
    policy.meta.description = "Test policy description"
    policy.spec.disabled = disabled
    policy.spec.policy_type = policy_type
    policy.spec.action = action
    return policy


def _make_mock_version(
    uuid: str = "ver-1",
    name: str = "main",
    ref: str = "refs/heads/main",
    sha: str = "abc123def456",
) -> Mock:
    """Create a mock repository version resource."""
    version = Mock()
    version.uuid = uuid
    version.meta.name = name
    version.spec.version.ref = ref
    version.spec.version.sha = sha
    version.spec.last_commit_date = "2025-01-15T10:00:00Z"
    return version


# ---------------------------------------------------------------------------
# Pull context tests
# ---------------------------------------------------------------------------


class TestPullFindingsContext:
    """Tests for pull_findings_context."""

    def test_returns_empty_on_no_findings(self) -> None:
        """Returns FindingsContext with total=0 when no findings exist."""
        client = Mock()
        client.Finding.list.return_value = []
        project = _make_mock_project()

        ctx = pull_findings_context(client, project)

        assert ctx.total == 0
        assert ctx.raw_findings == []

    def test_aggregates_by_category_and_severity(self) -> None:
        """Correctly aggregates findings into the by-category matrix."""
        findings = [
            _make_mock_finding(
                "f1", "FINDING_LEVEL_CRITICAL", ["FINDING_CATEGORY_VULNERABILITY"]
            ),
            _make_mock_finding(
                "f2", "FINDING_LEVEL_HIGH", ["FINDING_CATEGORY_VULNERABILITY"]
            ),
            _make_mock_finding("f3", "FINDING_LEVEL_MEDIUM", ["FINDING_CATEGORY_SAST"]),
        ]
        client = Mock()
        client.Finding.list.return_value = findings
        project = _make_mock_project()

        ctx = pull_findings_context(client, project)

        assert ctx.total == 3
        assert ctx.by_category["VULNERABILITY"]["Critical"] == 1
        assert ctx.by_category["VULNERABILITY"]["High"] == 1
        assert ctx.by_category["SAST"]["Medium"] == 1

    def test_top_findings_limited_to_critical_high(self) -> None:
        """top_findings only includes CRITICAL and HIGH severity."""
        findings = [
            _make_mock_finding("f1", "FINDING_LEVEL_CRITICAL"),
            _make_mock_finding("f2", "FINDING_LEVEL_LOW"),
        ]
        client = Mock()
        client.Finding.list.return_value = findings
        project = _make_mock_project()

        ctx = pull_findings_context(client, project)

        assert len(ctx.top_findings) == 1
        assert ctx.top_findings[0]["uuid"] == "f1"

    def test_handles_api_error_gracefully(self) -> None:
        """Returns empty context on API failure."""
        client = Mock()
        client.Finding.list.side_effect = Exception("API error")
        project = _make_mock_project()

        ctx = pull_findings_context(client, project)

        assert ctx.total == 0
        assert ctx.fetch_error == "API error"


class TestPullPoliciesContext:
    """Tests for pull_policies_context."""

    def test_returns_policies_list(self) -> None:
        """Extracts policy data correctly."""
        policies = [
            _make_mock_policy("p1", "critical-vuln-policy"),
            _make_mock_policy("p2", "sast-policy", disabled=True),
        ]
        client = Mock()
        client.Policy.list.return_value = policies
        project = _make_mock_project()

        ctx = pull_policies_context(client, project)

        assert ctx.total == 2
        assert ctx.policies[0]["name"] == "critical-vuln-policy"
        assert ctx.policies[1]["disabled"] is True


class TestPullVersionsContext:
    """Tests for pull_repository_versions_context."""

    def test_returns_versions_list(self) -> None:
        """Extracts version data correctly."""
        versions = [_make_mock_version()]
        client = Mock()
        client.RepositoryVersion.list.return_value = versions
        project = _make_mock_project()

        ctx = pull_repository_versions_context(client, project)

        assert ctx.total == 1
        assert ctx.versions[0]["ref"] == "refs/heads/main"
        client.RepositoryVersion.list.assert_called_once()
        kwargs = client.RepositoryVersion.list.call_args.kwargs
        assert kwargs["parent"] == project
        assert kwargs["max_pages"] == 2


# ---------------------------------------------------------------------------
# Render tests
# ---------------------------------------------------------------------------


class TestRenderFindingsSummary:
    """Tests for render_findings_summary."""

    def test_empty_findings(self) -> None:
        """Renders 'no findings' message when total is 0."""
        ctx = FindingsContext(project_name="test-repo", total=0)
        md = render_findings_summary(ctx)
        assert "No findings found" in md

    def test_renders_fetch_error_warning(self) -> None:
        """Includes warning when findings query failed."""
        ctx = FindingsContext(
            project_name="test-repo",
            total=0,
            fetch_error="backend timeout",
        )
        md = render_findings_summary(ctx)
        assert "could not be retrieved" in md
        assert "backend timeout" in md

    def test_renders_table(self) -> None:
        """Renders a table with category rows."""
        ctx = FindingsContext(
            project_name="test-repo",
            total=5,
            by_category={
                "VULNERABILITY": {
                    "Critical": 1,
                    "High": 2,
                    "Medium": 1,
                    "Low": 1,
                    "Total": 5,
                },
            },
        )
        md = render_findings_summary(ctx)
        assert "VULNERABILITY" in md
        assert "| 1 |" in md  # Critical count


class TestRenderPoliciesSummary:
    """Tests for render_policies_summary."""

    def test_renders_policy_table(self) -> None:
        """Renders policy names in a table."""
        ctx = PoliciesContext(
            namespace="test-ns",
            total=1,
            policies=[
                {
                    "name": "my-policy",
                    "policy_type": "FINDING",
                    "disabled": False,
                    "action": "WARN",
                }
            ],
        )
        md = render_policies_summary(ctx)
        assert "my-policy" in md


class TestRenderVersionsSummary:
    """Tests for render_versions_summary."""

    def test_renders_version_table(self) -> None:
        """Renders version refs and SHAs in a table."""
        ctx = VersionsContext(
            project_uuid="proj-1",
            total=1,
            versions=[
                {
                    "name": "main",
                    "ref": "refs/heads/main",
                    "sha": "abc123",
                    "last_commit_date": "2025-01-15",
                }
            ],
        )
        md = render_versions_summary(ctx)
        assert "refs/heads/main" in md


# ---------------------------------------------------------------------------
# Artifact writer tests
# ---------------------------------------------------------------------------


class TestWriteSessionArtifacts:
    """Tests for write_session_artifacts."""

    def test_creates_directory_structure(self, tmp_path: Path) -> None:
        """Creates the full progressive-disclosure directory tree."""
        project = _make_mock_project(name="https://github.com/org/test-repo.git")
        findings = FindingsContext(
            project_name="test-repo",
            total=0,
            raw_findings=[],
        )
        policies = PoliciesContext(namespace="test-ns", total=0, policies=[])
        versions = VersionsContext(project_uuid="proj-1", total=0, versions=[])

        write_session_artifacts(tmp_path, project, findings, policies, versions)

        # Check directory structure
        slug_dir = tmp_path / build_project_session_key(project)
        assert (slug_dir / "project-summary.md").exists()
        assert (slug_dir / "findings" / "findings-summary.md").exists()
        assert (slug_dir / "findings" / "findings.json").exists()
        assert (slug_dir / "policies" / "policies-summary.md").exists()
        assert (slug_dir / "policies" / "policies.json").exists()
        assert (slug_dir / "repository-versions" / "versions-summary.md").exists()
        assert (slug_dir / "repository-versions" / "versions.json").exists()

    def test_findings_json_contains_raw_data(self, tmp_path: Path) -> None:
        """findings.json contains the raw finding dictionaries."""
        project = _make_mock_project(name="https://github.com/org/repo.git")
        findings = FindingsContext(
            project_name="repo",
            total=1,
            raw_findings=[{"uuid": "f1", "description": "test"}],
        )
        policies = PoliciesContext(total=0, policies=[])
        versions = VersionsContext(total=0, versions=[])

        write_session_artifacts(tmp_path, project, findings, policies, versions)

        slug_dir = tmp_path / build_project_session_key(project)
        data = json.loads((slug_dir / "findings" / "findings.json").read_text())
        assert len(data) == 1
        assert data[0]["uuid"] == "f1"

    def test_deterministic_mode_uses_stable_timestamp(self, tmp_path: Path) -> None:
        project = _make_mock_project(name="https://github.com/org/repo.git")
        findings = FindingsContext(project_name="repo", total=0, raw_findings=[])
        policies = PoliciesContext(total=0, policies=[])
        versions = VersionsContext(total=0, versions=[])

        write_session_artifacts(
            tmp_path,
            project,
            findings,
            policies,
            versions,
            deterministic=True,
        )
        slug_dir = tmp_path / build_project_session_key(project)
        summary = (slug_dir / "project-summary.md").read_text()
        assert "Generated at 1970-01-01T00:00:00Z" in summary

    def test_same_repo_name_different_uuid_creates_distinct_dirs(
        self, tmp_path: Path
    ) -> None:
        project_one = _make_mock_project(
            uuid="proj-1", name="https://github.com/org/repo.git"
        )
        project_two = _make_mock_project(
            uuid="proj-2", name="https://github.com/org/repo.git"
        )
        findings = FindingsContext(project_name="repo", total=0, raw_findings=[])
        policies = PoliciesContext(total=0, policies=[])
        versions = VersionsContext(total=0, versions=[])

        write_session_artifacts(tmp_path, project_one, findings, policies, versions)
        write_session_artifacts(tmp_path, project_two, findings, policies, versions)

        assert (tmp_path / build_project_session_key(project_one)).exists()
        assert (tmp_path / build_project_session_key(project_two)).exists()


# ---------------------------------------------------------------------------
# Orchestrator tests
# ---------------------------------------------------------------------------


class TestCreateSession:
    """Tests for create_session orchestrator."""

    def test_returns_session_result(self, tmp_path: Path) -> None:
        """create_session returns a SessionResult with status."""
        client = Mock()
        client.Finding.list.return_value = []
        client.Policy.list.return_value = []
        client.RepositoryVersion.list.return_value = []

        project = _make_mock_project()
        result = create_session(client, project, tmp_path)

        assert isinstance(result, SessionResult)
        assert result.status == "success"
        assert result.findings.total == 0

    def test_sets_error_status_when_findings_fetch_fails(self, tmp_path: Path) -> None:
        """Session result surfaces data retrieval errors."""
        client = Mock()
        client.Finding.list.side_effect = Exception("boom")
        client.Policy.list.return_value = []
        client.RepositoryVersion.list.return_value = []
        project = _make_mock_project()

        result = create_session(client, project, tmp_path)

        assert result.status == "error"
        assert result.errors
        assert "Unable to fetch findings: boom" in result.errors[0]
        assert "retrieval/write errors" in result.message

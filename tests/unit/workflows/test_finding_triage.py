"""Unit tests for endorlabs.workflows.finding_triage."""

from unittest.mock import Mock

from endorlabs.workflows.finding_triage import (
    ExceptionPolicyResult,
    TaggingResult,
    build_exception_rego_rule,
    create_exception_policy,
    resolve_rego_package,
    tag_findings_by_criteria,
)

# ---------------------------------------------------------------------------
# resolve_rego_package
# ---------------------------------------------------------------------------


class TestResolveRegoPackage:
    """Tests for Rego package name resolution."""

    def test_sast_category(self) -> None:
        assert resolve_rego_package("FINDING_CATEGORY_SAST") == "sast"

    def test_secrets_category(self) -> None:
        assert resolve_rego_package("FINDING_CATEGORY_SECRETS") == "secrets"

    def test_other_category(self) -> None:
        assert resolve_rego_package("FINDING_CATEGORY_VULNERABILITY") == "exceptions"

    def test_none_category(self) -> None:
        assert resolve_rego_package(None) == "exceptions"


# ---------------------------------------------------------------------------
# build_exception_rego_rule (pure function — most important to test)
# ---------------------------------------------------------------------------


class TestBuildExceptionRegoRule:
    """Tests for Rego rule generation."""

    def test_minimal_rule_has_package_and_match(self) -> None:
        rule = build_exception_rego_rule()
        assert rule.startswith("package exceptions")
        assert "match_finding[result]" in rule
        assert "data.resources.Finding[i]" in rule

    def test_sast_category_sets_package(self) -> None:
        rule = build_exception_rego_rule(finding_category="FINDING_CATEGORY_SAST")
        assert rule.startswith("package sast")
        assert "FINDING_CATEGORY_SAST" in rule

    def test_secrets_category_sets_package(self) -> None:
        rule = build_exception_rego_rule(finding_category="FINDING_CATEGORY_SECRETS")
        assert rule.startswith("package secrets")

    def test_tag_condition(self) -> None:
        rule = build_exception_rego_rule(tag="false-positive")
        assert 'finding.meta.tags[_] == "false-positive"' in rule

    def test_finding_tag_condition(self) -> None:
        rule = build_exception_rego_rule(
            finding_tag="FINDING_TAGS_UNREACHABLE_DEPENDENCY"
        )
        assert "FINDING_TAGS_UNREACHABLE_DEPENDENCY" in rule

    def test_cwe_list_generates_helpers(self) -> None:
        rule = build_exception_rego_rule(cwe_list=["CWE-22", "CWE-78"])
        assert "cwe_match(finding)" in rule
        assert "CWE-22:" in rule
        assert "CWE-78:" in rule

    def test_file_path_generates_helpers(self) -> None:
        rule = build_exception_rego_rule(file_path="scripts/")
        assert "file_path_match(finding" in rule
        assert 'file_path_match(finding, "scripts/")' in rule

    def test_project_uuid_scoping(self) -> None:
        rule = build_exception_rego_rule(project_uuid="proj-123")
        assert 'finding.spec.project_uuid == "proj-123"' in rule

    def test_global_scope_omits_project_uuid(self) -> None:
        rule = build_exception_rego_rule(project_uuid="proj-123", global_scope=True)
        assert "project_uuid" not in rule

    def test_combined_criteria(self) -> None:
        rule = build_exception_rego_rule(
            finding_category="FINDING_CATEGORY_SAST",
            cwe_list=["CWE-22"],
            file_path="tests/",
            tag="test-data",
            project_uuid="proj-1",
        )
        assert rule.startswith("package sast")
        assert "FINDING_CATEGORY_SAST" in rule
        assert "CWE-22:" in rule
        assert 'file_path_match(finding, "tests/")' in rule
        assert 'finding.meta.tags[_] == "test-data"' in rule
        assert 'finding.spec.project_uuid == "proj-1"' in rule


# ---------------------------------------------------------------------------
# tag_findings_by_criteria
# ---------------------------------------------------------------------------


def _make_finding(
    uuid: str = "f-1",
    tags: list[str] | None = None,
) -> Mock:
    """Create a mock Finding resource."""
    f = Mock()
    f.uuid = uuid
    f.meta.tags = tags or []
    f.spec.level = "FINDING_LEVEL_HIGH"
    f.spec.finding_categories = ["FINDING_CATEGORY_SECRETS"]
    return f


def _make_mock_client(findings: list[Mock] | None = None) -> Mock:
    """Build a mock Client for tagging tests."""
    client = Mock()
    client.Finding.list.return_value = findings or []
    client.Finding.update.return_value = Mock()
    return client


class TestTagFindingsByCriteria:
    """Tests for tag_findings_by_criteria."""

    def test_no_findings_returns_zero_counts(self) -> None:
        client = _make_mock_client([])
        result = tag_findings_by_criteria(
            client, "ns", "proj-1", ["FINDING_CATEGORY_SECRETS"], "fp"
        )
        assert isinstance(result, TaggingResult)
        assert result.total == 0
        assert result.tagged == 0
        assert result.ok is True

    def test_dry_run_does_not_call_update(self) -> None:
        findings = [_make_finding("f-1"), _make_finding("f-2")]
        client = _make_mock_client(findings)
        result = tag_findings_by_criteria(
            client,
            "ns",
            "proj-1",
            ["FINDING_CATEGORY_SECRETS"],
            "fp",
            dry_run=True,
        )
        assert result.tagged == 2
        assert result.total == 2
        client.Finding.update.assert_not_called()

    def test_tags_findings_via_facade_update(self) -> None:
        findings = [_make_finding("f-1"), _make_finding("f-2")]
        client = _make_mock_client(findings)
        result = tag_findings_by_criteria(
            client, "ns", "proj-1", ["FINDING_CATEGORY_SECRETS"], "fp"
        )
        assert result.tagged == 2
        assert result.total == 2
        assert result.ok is True
        assert client.Finding.update.call_count == 2

    def test_skips_already_tagged_findings(self) -> None:
        findings = [_make_finding("f-1", tags=["fp"])]
        client = _make_mock_client(findings)
        result = tag_findings_by_criteria(
            client, "ns", "proj-1", ["FINDING_CATEGORY_SECRETS"], "fp"
        )
        assert result.skipped == 1
        assert result.tagged == 0
        client.Finding.update.assert_not_called()

    def test_partial_failure(self) -> None:
        f1 = _make_finding("f-1")
        f2 = _make_finding("f-2")
        client = _make_mock_client([f1, f2])
        client.Finding.update.side_effect = [Mock(), RuntimeError("API error")]
        result = tag_findings_by_criteria(
            client, "ns", "proj-1", ["FINDING_CATEGORY_SECRETS"], "fp"
        )
        assert result.tagged == 1
        assert result.failed == 1
        assert result.status == "partial"
        assert len(result.errors) == 1

    def test_filter_includes_categories(self) -> None:
        client = _make_mock_client([])
        tag_findings_by_criteria(
            client,
            "ns",
            "proj-1",
            ["FINDING_CATEGORY_SECRETS", "FINDING_CATEGORY_SAST"],
            "fp",
        )
        call_kwargs = client.Finding.list.call_args.kwargs
        assert "FINDING_CATEGORY_SECRETS" in call_kwargs["filter"]
        assert "FINDING_CATEGORY_SAST" in call_kwargs["filter"]

    def test_filter_includes_file_path(self) -> None:
        client = _make_mock_client([])
        tag_findings_by_criteria(
            client,
            "ns",
            "proj-1",
            ["FINDING_CATEGORY_SECRETS"],
            "fp",
            file_path="src/utils/",
        )
        call_kwargs = client.Finding.list.call_args.kwargs
        assert "src/utils/" in call_kwargs["filter"]


# ---------------------------------------------------------------------------
# create_exception_policy
# ---------------------------------------------------------------------------


class TestCreateExceptionPolicy:
    """Tests for create_exception_policy."""

    def test_dry_run_does_not_create(self) -> None:
        client = Mock()
        result = create_exception_policy(
            client,
            "ns",
            "Test Policy",
            tag="false-positive",
            dry_run=True,
        )
        assert isinstance(result, ExceptionPolicyResult)
        assert result.ok is True
        assert "DRY RUN" in result.message
        assert result.rego_rule  # non-empty
        client.Policy.create.assert_not_called()

    def test_creates_policy_via_facade(self) -> None:
        client = Mock()
        mock_policy = Mock()
        mock_policy.uuid = "policy-uuid-1"
        client.Policy.create.return_value = mock_policy

        result = create_exception_policy(
            client,
            "ns",
            "FP Policy",
            tag="false-positive",
            project_uuid="proj-1",
        )
        assert result.uuid == "policy-uuid-1"
        assert result.ok is True
        client.Policy.create.assert_called_once()

    def test_auto_generates_description(self) -> None:
        client = Mock()
        client.Policy.create.return_value = Mock(uuid="p1")

        create_exception_policy(
            client,
            "ns",
            "Policy",
            tag="fp",
            finding_category="FINDING_CATEGORY_SAST",
            cwe_list=["CWE-22"],
            global_scope=True,
        )
        call_kwargs = client.Policy.create.call_args.kwargs
        assert "fp" in call_kwargs["description"]
        assert "FINDING_CATEGORY_SAST" in call_kwargs["description"]
        assert "CWE-22" in call_kwargs["description"]
        assert "globally" in call_kwargs["description"]

    def test_handles_creation_error(self) -> None:
        client = Mock()
        client.Policy.create.side_effect = RuntimeError("API 500")

        result = create_exception_policy(client, "ns", "Policy", tag="fp")
        assert result.status == "error"
        assert "API 500" in result.message
        assert len(result.errors) == 1

    def test_propagate_kwarg_forwarded(self) -> None:
        client = Mock()
        client.Policy.create.return_value = Mock(uuid="p1")

        create_exception_policy(
            client,
            "ns",
            "Policy",
            tag="fp",
            propagate=True,
        )
        assert client.Policy.create.call_args.kwargs["propagate"] is True

    def test_project_selector_from_uuid(self) -> None:
        client = Mock()
        client.Policy.create.return_value = Mock(uuid="p1")

        create_exception_policy(
            client,
            "ns",
            "Policy",
            tag="fp",
            project_uuid="proj-1",
        )
        selector = client.Policy.create.call_args.kwargs["project_selector"]
        assert selector == ["$uuid=proj-1"]

    def test_project_selector_from_tags(self) -> None:
        client = Mock()
        client.Policy.create.return_value = Mock(uuid="p1")

        create_exception_policy(
            client,
            "ns",
            "Policy",
            tag="fp",
            project_tags=["sdk", "python"],
            global_scope=True,
        )
        selector = client.Policy.create.call_args.kwargs["project_selector"]
        assert selector == ["$sdk", "$python"]

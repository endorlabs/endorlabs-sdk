"""Unit tests for experimental.workflows.notification_setup."""

from unittest.mock import Mock

import pytest

from endorlabs.experimental.workflows.notification_setup import (
    NotificationPolicyResult,
    NotificationTargetResult,
    _build_action_spec,
    create_notification_policy,
    create_notification_target,
)

# ---------------------------------------------------------------------------
# _build_action_spec (pure function)
# ---------------------------------------------------------------------------


class TestBuildActionSpec:
    """Tests for action specification building."""

    def test_jira_action(self) -> None:
        spec = _build_action_spec(
            "jira",
            jira_url="https://example.atlassian.net/",
            jira_username="user@example.com",
            jira_pat="secret-pat",
            jira_project_key="PROJ",
        )
        assert spec["action_type"] == "ACTION_TYPE_JIRA"
        assert spec["jira_config"]["url"] == "https://example.atlassian.net/"
        assert spec["jira_config"]["project_key"] == "PROJ"
        assert spec["jira_config"]["issue_type"] == "VULN"

    def test_jira_missing_required_fields(self) -> None:
        with pytest.raises(ValueError, match="jira_url"):
            _build_action_spec("jira", jira_url="https://example.com")

    def test_github_pr_action(self) -> None:
        spec = _build_action_spec("github-pr", github_pr_enabled=True)
        assert spec["action_type"] == "ACTION_TYPE_GITHUB_PR"
        assert spec["github_pr_config"]["enabled"] is True

    def test_email_action(self) -> None:
        spec = _build_action_spec("email", email_addresses=["a@b.com", "c@d.com"])
        assert spec["action_type"] == "ACTION_TYPE_EMAIL"
        assert "a@b.com" in spec["email_config"]["receivers_addresses"]

    def test_email_missing_addresses(self) -> None:
        with pytest.raises(ValueError, match="email_addresses"):
            _build_action_spec("email")

    def test_slack_action(self) -> None:
        spec = _build_action_spec(
            "slack", slack_webhook_url="https://hooks.slack.com/xxx"
        )
        assert spec["action_type"] == "ACTION_TYPE_SLACK"

    def test_slack_missing_url(self) -> None:
        with pytest.raises(ValueError, match="slack_webhook_url"):
            _build_action_spec("slack")

    def test_webhook_action(self) -> None:
        spec = _build_action_spec("webhook", webhook_url="https://example.com/hook")
        assert spec["action_type"] == "ACTION_TYPE_WEBHOOK"

    def test_webhook_missing_url(self) -> None:
        with pytest.raises(ValueError, match="webhook_url"):
            _build_action_spec("webhook")

    def test_unknown_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown action type"):
            _build_action_spec("carrier-pigeon")

    def test_jira_custom_issue_type(self) -> None:
        spec = _build_action_spec(
            "jira",
            jira_url="https://x.atlassian.net/",
            jira_username="u",
            jira_pat="p",
            jira_project_key="K",
            jira_issue_type="Bug",
            jira_resolved_status="Closed",
        )
        assert spec["jira_config"]["issue_type"] == "Bug"
        assert spec["jira_config"]["resolved_status"] == "Closed"


# ---------------------------------------------------------------------------
# create_notification_target
# ---------------------------------------------------------------------------


class TestCreateNotificationTarget:
    """Tests for create_notification_target."""

    def test_dry_run_does_not_create(self) -> None:
        client = Mock()
        result = create_notification_target(
            client,
            "ns",
            "My JIRA",
            "jira",
            jira_url="https://x.atlassian.net/",
            jira_username="u",
            jira_pat="p",
            jira_project_key="K",
            dry_run=True,
        )
        assert isinstance(result, NotificationTargetResult)
        assert result.ok is True
        assert "DRY RUN" in result.message
        client.notification_target.create.assert_not_called()

    def test_creates_target_via_facade(self) -> None:
        client = Mock()
        client.notification_target.create.return_value = Mock(uuid="target-1")

        result = create_notification_target(
            client,
            "ns",
            "My JIRA",
            "jira",
            jira_url="https://x.atlassian.net/",
            jira_username="u",
            jira_pat="p",
            jira_project_key="K",
        )
        assert result.uuid == "target-1"
        assert result.ok is True
        client.notification_target.create.assert_called_once()

    def test_invalid_action_type_returns_error(self) -> None:
        client = Mock()
        result = create_notification_target(client, "ns", "Bad", "carrier-pigeon")
        assert result.status == "error"
        assert "Unknown action type" in result.message

    def test_missing_jira_fields_returns_error(self) -> None:
        client = Mock()
        result = create_notification_target(client, "ns", "Bad JIRA", "jira")
        assert result.status == "error"
        assert len(result.errors) == 1

    def test_api_failure_returns_error(self) -> None:
        client = Mock()
        client.notification_target.create.side_effect = RuntimeError("500")

        result = create_notification_target(
            client,
            "ns",
            "My Target",
            "github-pr",
            github_pr_enabled=True,
        )
        assert result.status == "error"
        assert "500" in result.message


# ---------------------------------------------------------------------------
# create_notification_policy
# ---------------------------------------------------------------------------


class TestCreateNotificationPolicy:
    """Tests for create_notification_policy."""

    def test_dry_run_does_not_create(self) -> None:
        client = Mock()
        result = create_notification_policy(
            client,
            "ns",
            "My Policy",
            ["target-1"],
            dry_run=True,
        )
        assert isinstance(result, NotificationPolicyResult)
        assert result.ok is True
        assert "DRY RUN" in result.message
        client.policy.create.assert_not_called()

    def test_creates_policy_via_facade(self) -> None:
        client = Mock()
        client.policy.create.return_value = Mock(uuid="policy-1")

        result = create_notification_policy(
            client, "ns", "My Policy", ["target-1", "target-2"]
        )
        assert result.uuid == "policy-1"
        assert result.ok is True
        assert result.target_uuids == ["target-1", "target-2"]

    def test_passes_notification_config(self) -> None:
        client = Mock()
        client.policy.create.return_value = Mock(uuid="p1")

        create_notification_policy(
            client,
            "ns",
            "Pol",
            ["t1"],
            finding_level="FINDING_LEVEL_CRITICAL",
            project_selector=["$sdk"],
        )
        kw = client.policy.create.call_args.kwargs
        assert kw["notification"]["notification_target_uuids"] == ["t1"]
        assert kw["finding_level"] == "FINDING_LEVEL_CRITICAL"
        assert kw["project_selector"] == ["$sdk"]

    def test_api_failure_returns_error(self) -> None:
        client = Mock()
        client.policy.create.side_effect = RuntimeError("conflict")

        result = create_notification_policy(client, "ns", "Pol", ["t1"])
        assert result.status == "error"
        assert "conflict" in result.message

    def test_propagate_forwarded(self) -> None:
        client = Mock()
        client.policy.create.return_value = Mock(uuid="p1")

        create_notification_policy(client, "ns", "Pol", ["t1"], propagate=False)
        assert client.policy.create.call_args.kwargs["propagate"] is False

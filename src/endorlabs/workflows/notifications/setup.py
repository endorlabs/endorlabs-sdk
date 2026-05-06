"""Notification setup workflows: create targets and policies.

Provides composable functions for setting up notification integrations
(JIRA, GitHub PR, Slack, email) using the Client facade and SDK models.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ..common import WorkflowResult

if TYPE_CHECKING:
    from endorlabs import Client

from endorlabs.utils.logging_config import get_resource_logger

logger = get_resource_logger(__name__)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class NotificationTargetResult(WorkflowResult):
    """Result of a notification target creation.

    Attributes:
        uuid: UUID of the created target (empty on dry-run or failure).
        name: Name of the notification target.
        action_type: Type of action (e.g. ``"ACTION_TYPE_JIRA"``).
    """

    uuid: str = ""
    name: str = ""
    action_type: str = ""


@dataclass
class NotificationPolicyResult(WorkflowResult):
    """Result of a notification policy creation.

    Attributes:
        uuid: UUID of the created policy (empty on dry-run or failure).
        name: Name of the notification policy.
        target_uuids: UUIDs of linked notification targets.
    """

    uuid: str = ""
    name: str = ""
    target_uuids: list[str] | None = None


# ---------------------------------------------------------------------------
# Notification target creation
# ---------------------------------------------------------------------------


def _build_action_spec(
    action_type: str,
    *,
    jira_url: str | None = None,
    jira_username: str | None = None,
    jira_pat: str | None = None,
    jira_project_key: str | None = None,
    jira_issue_type: str | None = None,
    jira_resolved_status: str | None = None,
    github_pr_enabled: bool = False,
    email_addresses: list[str] | None = None,
    slack_webhook_url: str | None = None,
    webhook_url: str | None = None,
) -> dict[str, Any]:
    """Build an action specification dict for a notification target.

    This is a **pure function** — returns the action dict without making
    any API calls.

    Args:
        action_type: One of ``"jira"``, ``"github-pr"``, ``"email"``,
            ``"slack"``, ``"webhook"``.
        jira_url: JIRA instance URL (required for ``jira`` type).
        jira_username: Atlassian username (required for ``jira`` type).
        jira_pat: Atlassian personal access token (required for ``jira`` type).
        jira_project_key: JIRA project key (required for ``jira`` type).
        jira_issue_type: JIRA issue type (default varies by integration).
        jira_resolved_status: JIRA status for resolved issues.
        github_pr_enabled: Enable GitHub PR comments (for ``github-pr`` type).
        email_addresses: Recipient email addresses (for ``email`` type).
        slack_webhook_url: Slack webhook URL (for ``slack`` type).
        webhook_url: Generic webhook URL (for ``webhook`` type).

    Returns:
        Action specification dict suitable for ``NotificationTargetSpec``.

    Raises:
        ValueError: When required fields for the action type are missing.
    """
    action_type_lower = action_type.lower().replace("_", "-")

    if action_type_lower == "jira":
        if not all([jira_url, jira_username, jira_pat, jira_project_key]):
            raise ValueError(
                "JIRA notification target requires jira_url, jira_username, "
                "jira_pat, and jira_project_key."
            )
        return {
            "action_type": "ACTION_TYPE_JIRA",
            "jira_config": {
                "url": jira_url,
                "username": jira_username,
                "secret": jira_pat,
                "project_key": jira_project_key,
                "issue_type": jira_issue_type or "VULN",
                "resolved_status": jira_resolved_status or "Done",
            },
        }

    if action_type_lower == "github-pr":
        return {
            "action_type": "ACTION_TYPE_GITHUB_PR",
            "github_pr_config": {
                "enabled": github_pr_enabled,
            },
        }

    if action_type_lower == "email":
        if not email_addresses:
            raise ValueError("Email notification target requires email_addresses.")
        return {
            "action_type": "ACTION_TYPE_EMAIL",
            "email_config": {
                "receivers_addresses": email_addresses,
            },
        }

    if action_type_lower == "slack":
        if not slack_webhook_url:
            raise ValueError("Slack notification target requires slack_webhook_url.")
        return {
            "action_type": "ACTION_TYPE_SLACK",
            "slack_config": {
                "webhook_url": slack_webhook_url,
            },
        }

    if action_type_lower == "webhook":
        if not webhook_url:
            raise ValueError("Webhook notification target requires webhook_url.")
        return {
            "action_type": "ACTION_TYPE_WEBHOOK",
            "webhook_config": {
                "url": webhook_url,
            },
        }

    raise ValueError(f"Unknown action type: {action_type}")


def create_notification_target(
    client: Client,
    namespace: str,
    name: str,
    action_type: str,
    *,
    description: str = "",
    propagate: bool = False,
    dry_run: bool = False,
    **action_kwargs: Any,
) -> NotificationTargetResult:
    """Create a notification target (JIRA, GitHub PR, email, etc.).

    Uses the Client facade and SDK models from
    ``endorlabs.resources.notification_target``.

    Args:
        client: Authenticated ``endorlabs.Client`` instance.
        namespace: Namespace where the target will be created.
        name: Human-readable name for the notification target.
        action_type: One of ``"jira"``, ``"github-pr"``, ``"email"``,
            ``"slack"``, ``"webhook"``.
        description: Optional description.
        propagate: Propagate to child namespaces.
        dry_run: When True, build the payload but skip creation.
        **action_kwargs: Type-specific arguments passed to
            ``_build_action_spec`` (e.g. ``jira_url``, ``jira_pat``).

    Returns:
        NotificationTargetResult with the created target details.
    """
    try:
        action_spec = _build_action_spec(action_type, **action_kwargs)
    except ValueError as exc:
        return NotificationTargetResult(
            status="error",
            message=str(exc),
            errors=[str(exc)],
            action_type=action_type,
        )

    result = NotificationTargetResult(
        name=name,
        action_type=action_spec["action_type"],
    )

    if dry_run:
        result.message = (
            f"[DRY RUN] Would create notification target '{name}' "
            f"(type={action_spec['action_type']})."
        )
        return result

    from endorlabs.resources.notification_target import (
        CreateNotificationTargetPayload,
        NotificationAction,
        NotificationTargetMeta,
        NotificationTargetSpec,
    )

    payload = CreateNotificationTargetPayload(
        meta=NotificationTargetMeta(
            name=name,
            kind="NotificationTarget",
            description=description,
        ),
        spec=NotificationTargetSpec(
            action=NotificationAction(**action_spec),
        ),
        propagate=propagate,
    )

    try:
        target = client.NotificationTarget.create(payload=payload, namespace=namespace)
        result.uuid = target.uuid
        result.message = f"Created notification target '{name}' (uuid={target.uuid})."
        logger.info(result.message)
    except Exception as exc:
        result.status = "error"
        result.message = f"Unable to create notification target: {exc}"
        result.errors.append(str(exc))
        logger.error(result.message)

    return result


# ---------------------------------------------------------------------------
# Notification policy creation
# ---------------------------------------------------------------------------


def create_notification_policy(
    client: Client,
    namespace: str,
    name: str,
    target_uuids: list[str],
    *,
    description: str = "",
    finding_categories: list[str] | None = None,
    finding_level: str | None = None,
    project_selector: list[str] | None = None,
    propagate: bool = True,
    dry_run: bool = False,
) -> NotificationPolicyResult:
    """Create a notification policy linked to notification targets.

    Uses the Client facade's ``policy.create()`` to create a
    ``POLICY_TYPE_NOTIFICATION`` policy.

    Args:
        client: Authenticated ``endorlabs.Client`` instance.
        namespace: Namespace where the policy will be created.
        name: Human-readable name for the policy.
        target_uuids: UUIDs of notification targets to link.
        description: Optional description.
        finding_categories: Finding categories to trigger on.
        finding_level: Minimum finding level to trigger on.
        project_selector: Project tags for selector.
        propagate: Propagate to child namespaces.
        dry_run: When True, build but skip creation.

    Returns:
        NotificationPolicyResult with the created policy details.
    """
    result = NotificationPolicyResult(name=name, target_uuids=target_uuids)

    if dry_run:
        result.message = (
            f"[DRY RUN] Would create notification policy '{name}' "
            f"with {len(target_uuids)} target(s)."
        )
        return result

    # Build notification config
    notification_config: dict[str, Any] = {
        "notification_target_uuids": target_uuids,
    }

    # Build kwargs for facade create
    create_kwargs: dict[str, Any] = {
        "name": name,
        "namespace": namespace,
        "description": description or f"Notification policy: {name}",
        "tags": ["notification", "endorlabs-sdk"],
        "policy_type": "POLICY_TYPE_NOTIFICATION",
        "notification": notification_config,
        "resource_kinds": ["Finding"],
        "disable": False,
        "propagate": propagate,
    }

    if finding_categories:
        create_kwargs["finding_categories"] = finding_categories
    if finding_level:
        create_kwargs["finding_level"] = finding_level
    if project_selector:
        create_kwargs["project_selector"] = project_selector

    try:
        policy = client.Policy.create(**create_kwargs)
        result.uuid = policy.uuid
        result.message = f"Created notification policy '{name}' (uuid={policy.uuid})."
        logger.info(result.message)
    except Exception as exc:
        result.status = "error"
        result.message = f"Unable to create notification policy: {exc}"
        result.errors.append(str(exc))
        logger.error(result.message)

    return result

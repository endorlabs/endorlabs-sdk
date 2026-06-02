"""NotificationTarget resource module for Endor Labs API.

This module provides notification target management: list, get, create,
update, and delete. Notification targets define actions (email, JIRA,
Slack, GitHub PR, etc.) when notifications are raised.

API OPERATIONS SUPPORTED:
- GET: List notification targets, Get by UUID
- POST: Create notification target
- PATCH: Update notification target
- DELETE: Delete notification target
"""

from __future__ import annotations

from typing import Any, ClassVar, override

from pydantic import BaseModel, Field, field_validator

from ..models.base import (
    BaseMeta,
    BaseResource,
    BaseSpec,
    FlexibleEnum,
)
from ..utils.logging_config import get_resource_logger

logger = get_resource_logger(__name__)


class NotificationTargetActionType(FlexibleEnum):
    """Notification target action type."""

    UNSPECIFIED = "ACTION_TYPE_UNSPECIFIED"
    WEBHOOK = "ACTION_TYPE_WEBHOOK"
    JIRA = "ACTION_TYPE_JIRA"
    EMAIL = "ACTION_TYPE_EMAIL"
    VANTA = "ACTION_TYPE_VANTA"
    SLACK = "ACTION_TYPE_SLACK"
    GITHUB_PR = "ACTION_TYPE_GITHUB_PR"


class NotificationAction(BaseModel):
    """Action configuration (action_type and type-specific config)."""

    action_type: NotificationTargetActionType | str | None = Field(
        None,
        description="Type of action (email, slack, jira, webhook, etc.).",
    )
    email_config: dict[str, Any] | None = Field(
        None, description="Email action config (e.g. receivers_addresses)."
    )
    slack_config: dict[str, Any] | None = Field(
        None, description="Slack action config (e.g. webhook_url)."
    )
    jira_config: dict[str, Any] | None = Field(None, description="JIRA action config.")
    webhook_config: dict[str, Any] | None = Field(
        None, description="Webhook action config (url, auth_method, etc.)."
    )
    github_pr_config: dict[str, Any] | None = Field(
        None, description="GitHub PR action config."
    )
    vanta_config: dict[str, Any] | None = Field(
        None, description="Vanta action config."
    )

    model_config: ClassVar[dict[str, str]] = {"extra": "allow"}  # type: ignore[assignment]


class CustomTemplate(BaseModel):
    """Custom template for the notification."""

    template_type: str | None = Field(None, description="Type of template.")
    email_template: dict[str, Any] | None = Field(
        None, description="Email template (open_action, resolve_action, etc.)."
    )
    slack_template: dict[str, Any] | None = Field(None, description="Slack template.")
    webhook_template: dict[str, Any] | None = Field(
        None, description="Webhook template."
    )
    prcomments_template: dict[str, Any] | None = Field(
        None, description="PR comments template."
    )

    model_config: ClassVar[dict[str, str]] = {"extra": "allow"}  # type: ignore[assignment]


class NotificationTargetSpec(BaseSpec):
    """Notification target specification extending BaseSpec."""

    action: NotificationAction | dict[str, Any] | None = Field(
        None,
        description=(
            "Action configuration: action_type and type-specific config "
            "(jira_config, email_config, slack_config, github_pr_config, etc.)"
        ),
    )
    custom_template: CustomTemplate | dict[str, Any] | None = Field(
        None,
        description="Custom template for the notification; default used if not set.",
    )


class NotificationTargetMeta(BaseMeta):
    """Notification target metadata extending BaseMeta."""

    pass


class NotificationTarget(BaseResource):
    """Notification Target resource model.

    OPERATION SUPPORT:
    - List, Get, Create, Update, Delete
    """

    spec: NotificationTargetSpec | None = Field(  # pyright: ignore[reportIncompatibleVariableOverride]
        None, description="Notification target specification"
    )
    propagate: bool | None = Field(
        None,
        description="Whether the object is visible in child namespaces.",
    )

    model_config: ClassVar[dict[str, str]] = {"extra": "ignore"}

    @override
    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v: Any, info: Any) -> Any:
        """Detect and log schema drift in notification target responses."""
        if info.field_name == "spec" and isinstance(v, dict):
            known = {"action", "custom_template"}
            unknown = set(v.keys()) - known
            if unknown:
                logger.warning(
                    "Schema drift in NotificationTarget.spec: unknown fields %s",
                    unknown,
                )
        return v


class CreateNotificationTargetPayload(BaseModel):
    """Payload for creating a notification target."""

    meta: NotificationTargetMeta = Field(
        ..., description="Notification target metadata"
    )
    spec: NotificationTargetSpec = Field(
        ..., description="Notification target specification"
    )
    propagate: bool | None = Field(False, description="Propagate to child namespaces")


def build_create_payload(**kwargs: Any) -> CreateNotificationTargetPayload:
    """Build CreateNotificationTargetPayload from kwargs (decoupled create)."""
    from ..utils.create_payload import pass_through_create_payload

    return pass_through_create_payload(
        CreateNotificationTargetPayload, kwargs, attr_name="NotificationTarget"
    )

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

import logging
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, ClassVar

from pydantic import BaseModel, Field, field_validator

from ..models.base import (
    BaseMeta,
    BaseResource,
    BaseResourceOperations,
    BaseSpec,
    FlexibleEnum,
)

if TYPE_CHECKING:
    from ..api_client import APIClient
    from ..types import ListParameters

logger = logging.getLogger(__name__)


def _get_notification_target_ops(
    client: APIClient,
) -> BaseResourceOperations[NotificationTarget]:
    """Get BaseResourceOperations instance for notification targets."""
    return BaseResourceOperations(client, "notification-targets", NotificationTarget)


class NotificationTargetActionType(FlexibleEnum):
    """Notification target action type."""

    UNSPECIFIED = "ACTION_TYPE_UNSPECIFIED"
    WEBHOOK = "ACTION_TYPE_WEBHOOK"
    JIRA = "ACTION_TYPE_JIRA"
    EMAIL = "ACTION_TYPE_EMAIL"
    VANTA = "ACTION_TYPE_VANTA"
    SLACK = "ACTION_TYPE_SLACK"
    GITHUB_PR = "ACTION_TYPE_GITHUB_PR"


class NotificationTargetSpec(BaseSpec):
    """Notification target specification extending BaseSpec."""

    action: dict[str, Any] | None = Field(
        None,
        description=(
            "Action configuration: action_type and type-specific config "
            "(jira_config, email_config, slack_config, github_pr_config, etc.)"
        ),
    )
    custom_template: dict[str, Any] | None = Field(
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


def list_notification_targets(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: ListParameters | None = None,
    max_pages: int | None = None,
    **kwargs: Any,
) -> list[NotificationTarget]:
    """List notification targets in the namespace."""
    ops = _get_notification_target_ops(client)
    return ops.list(tenant_meta_namespace, list_params, max_pages, **kwargs)


def list_notification_targets_iter(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: ListParameters | None = None,
    max_pages: int | None = None,
    **kwargs: Any,
) -> Iterator[NotificationTarget]:
    """Iterate over notification targets without materializing the full list."""
    ops = _get_notification_target_ops(client)
    return ops.list_iter(tenant_meta_namespace, list_params, max_pages, **kwargs)


def get_notification_target(
    client: APIClient,
    tenant_meta_namespace: str,
    notification_target_uuid: str,
) -> NotificationTarget:
    """Get a notification target by UUID."""
    ops = _get_notification_target_ops(client)
    return ops.get(tenant_meta_namespace, notification_target_uuid)


def create_notification_target(
    client: APIClient,
    tenant_meta_namespace: str,
    payload: CreateNotificationTargetPayload,
) -> NotificationTarget:
    """Create a notification target."""
    ops = _get_notification_target_ops(client)
    return ops.create(tenant_meta_namespace, payload)


def update_notification_target(
    client: APIClient,
    tenant_meta_namespace: str,
    notification_target_uuid: str,
    payload: NotificationTarget | dict[str, Any],
    update_mask: str | list[str] | None = None,
) -> NotificationTarget:
    """Update a notification target."""
    ops = _get_notification_target_ops(client)
    if isinstance(payload, dict):
        payload = NotificationTarget(**payload)
    mask_list: list[str] = (
        [p.strip() for p in update_mask.split(",") if p.strip()]
        if isinstance(update_mask, str)
        else (update_mask or [])
    )
    return ops.update(
        tenant_meta_namespace,
        notification_target_uuid,
        payload,
        mask_list,
    )


def delete_notification_target(
    client: APIClient,
    tenant_meta_namespace: str,
    notification_target_uuid: str,
) -> bool:
    """Delete a notification target by UUID."""
    ops = _get_notification_target_ops(client)
    return ops.delete(tenant_meta_namespace, notification_target_uuid)

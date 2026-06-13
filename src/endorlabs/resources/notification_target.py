"""NotificationTarget — thin consumer wrapper over generated V1NotificationTarget."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field

from endorlabs.generated.models.notification_target_service import V1NotificationTarget

from ..utils.logging_config import get_resource_logger
from .base import BaseMeta, BaseSpec, FlexibleEnum
from .consumer.mixin import ConsumerResourceMixin
from .consumer.registry_fields import immutable_fields_for, mutable_fields_for
from .consumer.wire_compat import ConsumerResourceWireMixin

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

    model_config = ConfigDict(extra="allow")

    action_type: NotificationTargetActionType | str | None = None
    email_config: dict[str, Any] | None = None
    slack_config: dict[str, Any] | None = None
    jira_config: dict[str, Any] | None = None
    webhook_config: dict[str, Any] | None = None
    github_pr_config: dict[str, Any] | None = None
    vanta_config: dict[str, Any] | None = None


class NotificationTargetSpec(BaseSpec):
    """Notification target specification."""

    action: NotificationAction | dict[str, Any] | None = None
    custom_template: dict[str, Any] | None = None


class NotificationTargetMeta(BaseMeta):
    """Notification target metadata."""

    pass


class NotificationTarget(
    V1NotificationTarget, ConsumerResourceWireMixin, ConsumerResourceMixin
):
    """Consumer facade model for NotificationTarget (generated wire shape)."""

    _MUTABLE_FIELDS: ClassVar[list[str]] = mutable_fields_for("NotificationTarget")
    _IMMUTABLE_FIELDS: ClassVar[list[str]] = immutable_fields_for("NotificationTarget")

    spec: NotificationTargetSpec | None = None  # pyright: ignore[reportIncompatibleVariableOverride]
    propagate: bool | None = None


class CreateNotificationTargetPayload(BaseModel):
    """Create payload for NotificationTarget."""

    meta: NotificationTargetMeta | dict[str, Any] = Field(...)
    spec: NotificationTargetSpec | dict[str, Any] = Field(...)
    propagate: bool | None = None


def build_create_payload(**kwargs: Any) -> CreateNotificationTargetPayload:
    """Build create payload for NotificationTarget."""
    from ..utils.create_payload import pass_through_create_payload

    return pass_through_create_payload(
        CreateNotificationTargetPayload, kwargs, attr_name="NotificationTarget"
    )

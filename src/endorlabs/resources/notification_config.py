"""Notification configuration models for policy and resource specifications.

These models define the structure of notification configurations while
maintaining flexibility for API evolution.
"""

from pydantic import BaseModel, ConfigDict, Field


class NotificationConfig(BaseModel):
    """Notification configuration with known fields.

    This model documents the known structure of notification configurations
    while allowing additional fields via extra="allow" for API evolution.
    """

    model_config = ConfigDict(
        extra="allow"  # Allow unknown fields for forward compatibility
    )

    notification_target_uuids: list[str] | None = Field(
        None, description="List of notification target UUIDs"
    )
    aggregation_type: str | None = Field(
        None,
        description="How to aggregate notifications (e.g., 'AGGREGATION_TYPE_PROJECT')",
    )
    bypass_exceptions: bool | None = Field(
        None,
        description="Whether to bypass exception policies when sending notifications",
    )

"""Invitation resource module for Endor Labs API.

Invitation represents an invitation for a new user in the system.
List, get, create, update, delete.
"""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, Field

from ..utils.logging_config import get_resource_logger
from .base import (
    BaseMeta,
    BaseResource,
    BaseSpec,
    FlexibleEnum,
)

logger = get_resource_logger(__name__)


class InvitationState(FlexibleEnum):
    """Invitation state."""

    UNSPECIFIED = "INVITATION_STATE_UNSPECIFIED"
    PENDING = "INVITATION_STATE_PENDING"
    ACCEPTED = "INVITATION_STATE_ACCEPTED"
    EXPIRED = "INVITATION_STATE_EXPIRED"
    CANCELLED = "INVITATION_STATE_CANCELLED"


class InvitationSpec(BaseSpec):
    """Invitation specification extending BaseSpec."""

    user_email: str | None = Field(
        None,
        description="Email of the user to invite to the tenant.",
    )
    invitation_state: InvitationState | str | None = Field(
        None,
        description="State of the invitation (read-only from API).",
    )


class InvitationMeta(BaseMeta):
    """Invitation metadata extending BaseMeta."""

    pass


class Invitation(BaseResource):
    """Invitation resource model. List, get, create, update, delete."""

    spec: InvitationSpec | None = Field(  # pyright: ignore[reportIncompatibleVariableOverride]
        None, description="Invitation specification"
    )

    model_config: ClassVar[dict[str, str]] = {"extra": "ignore"}


class CreateInvitationPayload(BaseModel):
    """Payload for creating an invitation."""

    meta: InvitationMeta = Field(..., description="Invitation metadata")
    spec: InvitationSpec = Field(..., description="Invitation specification")


def build_create_payload(**kwargs: Any) -> CreateInvitationPayload:
    """Build CreateInvitationPayload from kwargs (decoupled facade create)."""
    from ..utils.create_payload import pass_through_create_payload

    return pass_through_create_payload(
        CreateInvitationPayload, kwargs, attr_name="Invitation"
    )

"""Invitation resource module for Endor Labs API.

Invitation represents an invitation for a new user in the system.
List, get, create, update, delete.
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


def _get_invitation_ops(
    client: APIClient,
) -> BaseResourceOperations[Invitation]:
    """Get BaseResourceOperations instance for invitations."""
    return BaseResourceOperations(client, "invitations", Invitation)


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

    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v: Any, info: Any) -> Any:
        """Detect and log schema drift in invitation responses."""
        if info.field_name == "spec" and isinstance(v, dict):
            known = {"user_email", "invitation_state"}
            unknown = set(v.keys()) - known
            if unknown:
                logger.warning(
                    "Schema drift in Invitation.spec: unknown fields %s",
                    unknown,
                )
        return v


class CreateInvitationPayload(BaseModel):
    """Payload for creating an invitation."""

    meta: InvitationMeta = Field(..., description="Invitation metadata")
    spec: InvitationSpec = Field(..., description="Invitation specification")


def list_invitations(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: ListParameters | None = None,
    max_pages: int | None = None,
    **kwargs: Any,
) -> list[Invitation]:
    """List invitations in the namespace."""
    ops = _get_invitation_ops(client)
    return ops.list(tenant_meta_namespace, list_params, max_pages, **kwargs)


def list_invitations_iter(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: ListParameters | None = None,
    max_pages: int | None = None,
    **kwargs: Any,
) -> Iterator[Invitation]:
    """Iterate over invitations without materializing the full list."""
    ops = _get_invitation_ops(client)
    return ops.list_iter(tenant_meta_namespace, list_params, max_pages, **kwargs)


def get_invitation(
    client: APIClient,
    tenant_meta_namespace: str,
    invitation_uuid: str,
) -> Invitation:
    """Get an invitation by UUID."""
    ops = _get_invitation_ops(client)
    return ops.get(tenant_meta_namespace, invitation_uuid)


def create_invitation(
    client: APIClient,
    tenant_meta_namespace: str,
    payload: CreateInvitationPayload,
) -> Invitation:
    """Create an invitation."""
    ops = _get_invitation_ops(client)
    return ops.create(tenant_meta_namespace, payload)


def update_invitation(
    client: APIClient,
    tenant_meta_namespace: str,
    invitation_uuid: str,
    payload: Invitation | dict[str, Any],
    update_mask: str | list[str] | None = None,
) -> Invitation:
    """Update an invitation."""
    ops = _get_invitation_ops(client)
    if isinstance(payload, dict):
        payload = Invitation(**payload)
    mask_list: list[str] = (
        [p.strip() for p in update_mask.split(",") if p.strip()]
        if isinstance(update_mask, str)
        else (update_mask or [])
    )
    return ops.update(
        tenant_meta_namespace,
        invitation_uuid,
        payload,
        mask_list,
    )


def delete_invitation(
    client: APIClient,
    tenant_meta_namespace: str,
    invitation_uuid: str,
) -> bool:
    """Delete an invitation by UUID."""
    ops = _get_invitation_ops(client)
    return ops.delete(tenant_meta_namespace, invitation_uuid)

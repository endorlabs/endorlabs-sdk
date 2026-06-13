"""APIKey — thin consumer wrapper over generated V1APIKey."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, Field, field_validator

from endorlabs.generated.models.a_p_i_key_service import V1APIKey

from .base import BaseMeta, BaseSpec
from .consumer.mixin import ConsumerResourceMixin
from .consumer.registry_fields import immutable_fields_for, mutable_fields_for
from .consumer.wire_compat import ConsumerResourceWireMixin


class APIKey(V1APIKey, ConsumerResourceWireMixin, ConsumerResourceMixin):
    """Consumer facade model for APIKey (generated wire shape)."""

    _MUTABLE_FIELDS: ClassVar[list[str]] = mutable_fields_for("APIKey")
    _IMMUTABLE_FIELDS: ClassVar[list[str]] = immutable_fields_for("APIKey")


# --- integration / create-update compat (pre-cutover helpers) ---


class PermissionsMethods(BaseModel):
    """Methods configuration for resource permissions."""

    methods: list[str] = Field(
        ...,
        description=(
            "Array of allowed methods (e.g., ['METHOD_READ', 'METHOD_CREATE'])"
        ),
    )


class APIKeyPermissions(BaseModel):
    """Permissions configuration for API key."""

    roles: list[str] | None = Field(
        None,
        description=(
            "System roles - predefined role-based permissions "
            "(e.g., SYSTEM_ROLE_READ_ONLY, SYSTEM_ROLE_ADMIN)"
        ),
    )
    rules: dict[str, dict[str, list[str]]] | None = Field(
        None,
        description=(
            "Resource-specific permissions - maps resource types to "
            "allowed methods (e.g., {'scan_profile': "
            "{'methods': ['METHOD_READ', 'METHOD_CREATE']}})"
        ),
    )
    except_resources: list[str] | None = Field(
        None,
        description=(
            "Excluded resources - list of resources to exclude from "
            "wildcard permissions"
        ),
    )

    @field_validator("roles")
    @classmethod
    def validate_roles(cls, v: list[str] | None) -> list[str] | None:
        """Validate roles are not empty strings."""
        if v:
            return [role.strip() for role in v if role.strip()]
        return v

    @field_validator("except_resources")
    @classmethod
    def validate_except_resources(cls, v: list[str] | None) -> list[str] | None:
        """Validate except_resources are not empty strings."""
        if v:
            return [resource.strip() for resource in v if resource.strip()]
        return v


class APIKeySpec(BaseSpec):
    """API key specification extending BaseSpec."""

    key: str | None = Field(
        None,
        description="The identifier of an API key (read-only, returned by API)",
    )
    secret: str | None = Field(
        None,
        description=(
            "The secret for the specified API key (read-only, returned by API)"
        ),
    )
    permissions: APIKeyPermissions = Field(
        ...,
        description="The access permissions associated with the API key",
    )
    expiration_time: str = Field(
        ...,
        description="The expiration time of the API key (ISO 8601 datetime)",
    )
    issuing_user: dict[str, Any] | None = Field(
        None,
        description=("The user that created this API key (read-only, returned by API)"),
    )


class APIKeyMeta(BaseMeta):
    """API key metadata extending BaseMeta."""

    # API key-specific fields only (universal fields inherited from BaseMeta)
    pass

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate API key name is not empty or whitespace."""
        if not v.strip():
            raise ValueError("name cannot be empty or whitespace")
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str | None) -> str | None:
        """Validate API key description."""
        if v is not None and not v.strip():
            raise ValueError("description cannot be empty or whitespace")
        return v.strip() if v else v


class CreateAPIKeyPayload(BaseModel):
    """Payload for creating a new API key."""

    meta: APIKeyMeta = Field(..., description="API key metadata")
    spec: APIKeySpec = Field(..., description="API key specification")
    propagate: bool | None = Field(False, description="Propagate to child namespaces")


def build_create_payload(**kwargs: Any) -> CreateAPIKeyPayload:
    """Build CreateAPIKeyPayload from kwargs (decoupled facade create)."""
    from ..utils.create_payload import pass_through_create_payload

    return pass_through_create_payload(CreateAPIKeyPayload, kwargs, attr_name="APIKey")

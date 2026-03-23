"""AuthenticationLog resource module for Endor Labs API.

Represents authentication events (login, API key, etc.). This resource is
system-owned: LIST is supported; GET, UPDATE, and DELETE return 403 (only
system can perform them). The Client exposes list() only; use
client.AuthenticationLog.list().
"""

from __future__ import annotations

from typing import Any, ClassVar, override

from pydantic import Field, field_validator

from ..models.base import (
    BaseMeta,
    BaseResource,
    BaseSpec,
)
from ..utils.logging_config import get_resource_logger

logger = get_resource_logger(__name__)


class AuthenticationLogSpec(BaseSpec):
    """Authentication log specification extending BaseSpec."""

    success: bool | None = Field(
        None,
        description="True if authentication was successful.",
    )
    authorized_tenants: list[str] | None = Field(
        None,
        description="Tenants accessible by the user at authentication time.",
    )
    error_message: str | None = Field(
        None,
        description="Error message if authentication failed.",
    )
    claims: list[str] | None = Field(
        None,
        description="Authentication claims.",
    )
    remote_address: str | None = Field(
        None,
        description="Source IP address.",
    )
    status: int | None = Field(
        None,
        description="Return code of the authentication.",
    )
    uri: str | None = Field(
        None,
        description="Request URI (e.g. /v1/auth/api-key).",
    )


class AuthenticationLogMeta(BaseMeta):
    """Authentication log metadata extending BaseMeta."""

    pass


class AuthenticationLog(BaseResource):
    """Authentication Log resource model. List and get only."""

    spec: AuthenticationLogSpec | None = Field(  # pyright: ignore[reportIncompatibleVariableOverride]
        None, description="Authentication log specification"
    )

    model_config: ClassVar[dict[str, str]] = {"extra": "ignore"}

    @override
    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v: Any, info: Any) -> Any:
        """Detect and log schema drift in authentication log responses."""
        if info.field_name == "spec" and isinstance(v, dict):
            known = {
                "success",
                "authorized_tenants",
                "error_message",
                "claims",
                "remote_address",
                "status",
                "uri",
            }
            unknown = set(v.keys()) - known
            if unknown:
                logger.warning(
                    "Schema drift in AuthenticationLog.spec: unknown fields %s",
                    unknown,
                )
        return v

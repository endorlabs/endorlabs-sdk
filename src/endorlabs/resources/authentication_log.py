"""AuthenticationLog resource module for Endor Labs API.

Represents authentication events (login, API key, etc.). This resource is
system-owned: LIST is supported; GET, UPDATE, and DELETE return 403 (only
system can perform them). The Client exposes list() only; use
client.authentication_log.list(). Module-level get_authentication_log() remains
for advanced use but will raise PermissionDeniedError (403) for non-system
callers.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, ClassVar, override

from pydantic import Field, field_validator

from ..models.base import (
    BaseMeta,
    BaseResource,
    BaseResourceOperations,
    BaseSpec,
)

if TYPE_CHECKING:
    from ..api_client import APIClient
    from ..types import ListParameters

logger = logging.getLogger(__name__)


def _get_authentication_log_ops(
    client: APIClient,
) -> BaseResourceOperations[AuthenticationLog]:
    """Get BaseResourceOperations instance for authentication logs."""
    return BaseResourceOperations(client, "authentication-logs", AuthenticationLog)


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


def list_authentication_logs(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: ListParameters | None = None,
    max_pages: int | None = None,
    **kwargs: Any,
) -> list[AuthenticationLog]:
    """List authentication logs in the namespace."""
    ops = _get_authentication_log_ops(client)
    return ops.list(tenant_meta_namespace, list_params, max_pages, **kwargs)


def list_authentication_logs_iter(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: ListParameters | None = None,
    max_pages: int | None = None,
    **kwargs: Any,
) -> Iterator[AuthenticationLog]:
    """Iterate over authentication logs without materializing the full list."""
    ops = _get_authentication_log_ops(client)
    return ops.list_iter(tenant_meta_namespace, list_params, max_pages, **kwargs)


def get_authentication_log(
    client: APIClient,
    tenant_meta_namespace: str,
    authentication_log_uuid: str,
) -> AuthenticationLog:
    """Get an authentication log by UUID."""
    ops = _get_authentication_log_ops(client)
    return ops.get(tenant_meta_namespace, authentication_log_uuid)

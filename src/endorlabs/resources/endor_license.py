"""EndorLicense resource module for Endor Labs API.

EndorLicense represents a specific Endor license assigned to a tenant. This
resource is system-owned: LIST is supported; GET, UPDATE, and DELETE return
403 (only system can perform them). The Client exposes list() only; use
client.endor_license.list(). Module-level get_endor_license() remains for
advanced use but will raise PermissionDeniedError (403) for non-system
callers.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, ClassVar, override

from pydantic import BaseModel, Field, field_validator

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


def _get_endor_license_ops(
    client: APIClient,
) -> BaseResourceOperations[EndorLicense]:
    """Get BaseResourceOperations instance for Endor licenses."""
    return BaseResourceOperations(client, "endor-licenses", EndorLicense)


class AiLimit(BaseModel):
    """AI limit quota (days, max_tokens)."""

    days: int | None = Field(None, description="Days.")
    max_tokens: int | None = Field(None, description="Max tokens.")

    model_config: ClassVar[dict[str, str]] = {"extra": "allow"}  # type: ignore[assignment]


class Quota(BaseModel):
    """License quota (e.g. max_daily_cloud_scans, ai_limit)."""

    max_daily_cloud_scans: int | None = Field(
        None, description="Max daily cloud scans."
    )
    max_daily_pr_scans: int | None = Field(None, description="Max daily PR scans.")
    ai_limit: AiLimit | dict[str, Any] | None = Field(
        None, description="AI limit (days, max_tokens)."
    )

    model_config: ClassVar[dict[str, str]] = {"extra": "allow"}  # type: ignore[assignment]


class SecurityReviewConfiguration(BaseModel):
    """Security review license configuration."""

    max_pr_reviews_per_month: int | None = Field(
        None, description="Max PR reviews per month."
    )

    model_config: ClassVar[dict[str, str]] = {"extra": "allow"}  # type: ignore[assignment]


class LicenseConfigurations(BaseModel):
    """License configurations (e.g. security_review_configuration)."""

    security_review_configuration: SecurityReviewConfiguration | None = Field(
        None, description="Security review configuration."
    )

    model_config: ClassVar[dict[str, str]] = {"extra": "allow"}  # type: ignore[assignment]


class EndorLicenseSpec(BaseSpec):
    """Endor license specification extending BaseSpec."""

    license_info: list[dict[str, Any]] | None = Field(
        None,
        description="Feature license types and limits (read-only).",
    )
    bundle_info: list[dict[str, Any]] | None = Field(
        None,
        description="License bundle information.",
    )
    target_namespace: str | None = Field(
        None,
        description="Target namespace for the license.",
    )
    excluded_feature_types: list[str] | None = Field(
        None,
        description="Excluded feature types.",
    )
    is_customer: bool | None = Field(
        None,
        description="Whether the tenant is a customer.",
    )
    license_configurations: LicenseConfigurations | dict[str, Any] | None = Field(
        None,
        description="License configurations (e.g. security_review_configuration).",
    )
    quota: Quota | dict[str, Any] | None = Field(
        None,
        description="Quota (e.g. ai_limit, max_daily_cloud_scans).",
    )


class EndorLicenseMeta(BaseMeta):
    """Endor license metadata extending BaseMeta."""

    pass


class EndorLicense(BaseResource):
    """Endor License resource model. List and get only."""

    spec: EndorLicenseSpec | None = Field(  # pyright: ignore[reportIncompatibleVariableOverride]
        None, description="Endor license specification"
    )

    model_config: ClassVar[dict[str, str]] = {"extra": "ignore"}

    @override
    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v: Any, info: Any) -> Any:
        """Detect and log schema drift in Endor license responses."""
        if info.field_name == "spec" and isinstance(v, dict):
            known = {
                "license_info",
                "bundle_info",
                "target_namespace",
                "excluded_feature_types",
                "is_customer",
                "license_configurations",
                "quota",
            }
            unknown = set(v.keys()) - known
            if unknown:
                logger.warning(
                    "Schema drift in EndorLicense.spec: unknown fields %s",
                    unknown,
                )
        return v


def list_endor_licenses(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: ListParameters | None = None,
    max_pages: int | None = None,
    **kwargs: Any,
) -> list[EndorLicense]:
    """List Endor licenses in the namespace."""
    ops = _get_endor_license_ops(client)
    return ops.list(tenant_meta_namespace, list_params, max_pages, **kwargs)


def list_endor_licenses_iter(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: ListParameters | None = None,
    max_pages: int | None = None,
    **kwargs: Any,
) -> Iterator[EndorLicense]:
    """Iterate over Endor licenses without materializing the full list."""
    ops = _get_endor_license_ops(client)
    return ops.list_iter(tenant_meta_namespace, list_params, max_pages, **kwargs)


def get_endor_license(
    client: APIClient,
    tenant_meta_namespace: str,
    endor_license_uuid: str,
) -> EndorLicense:
    """Get an Endor license by UUID."""
    ops = _get_endor_license_ops(client)
    return ops.get(tenant_meta_namespace, endor_license_uuid)

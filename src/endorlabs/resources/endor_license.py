"""EndorLicense resource module for Endor Labs API.

EndorLicense represents a specific Endor license assigned to a tenant. This
resource is system-owned: LIST is supported; GET, UPDATE, and DELETE return
403 (only system can perform them). The Client exposes list() only; use
client.EndorLicense.list().
"""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, Field

from ..utils.logging_config import get_resource_logger
from .base import (
    BaseMeta,
    BaseResource,
    BaseSpec,
)

logger = get_resource_logger(__name__)


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

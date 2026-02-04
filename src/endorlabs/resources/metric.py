"""Metric resource module for Endor Labs API.

This module provides CRUD operations for Metric resources following the
established patterns from the base class implementation.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, override

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..api_client import APIClient, RedactingFilter, redaction_pattern
from ..models.base import BaseMeta, BaseResource, BaseResourceOperations, BaseSpec
from ..utils.model_validation import parse_update_mask

if TYPE_CHECKING:
    from ..types import ListParameters

# Set up logger with redaction filter
logger = logging.getLogger(__name__)
logger.addFilter(RedactingFilter([redaction_pattern]))


class ScoreCard(BaseModel):
    """Score card for metric value."""

    score: float = Field(..., description="Score value")
    max_score: float = Field(..., description="Maximum possible score")
    factors: list[str] = Field(..., description="Score factors")


class MetricValue(BaseModel):
    """Metric value for metrics.

    Note: MetricValue can contain many optional complex fields per OpenAPI spec
    (e.g., ci_cd_tools, github_workflows, score_factor_list, time_tracker, etc.).
    We model the core fields here and use extra="ignore" to handle unknown
    complex nested structures gracefully.
    """

    model_config = ConfigDict(extra="ignore")

    category: str | None = Field(None, description="Metric value categories")
    description: str = Field(
        ..., description="Description of the metric value"
    )  # REQUIRED per OpenAPI spec
    int32_value: int | None = Field(None, description="32-bit integer value")
    int64_value: str | None = Field(None, description="64-bit integer value as string")
    string_value: str | None = Field(None, description="String value")
    float_value: float | None = Field(None, description="Float value")
    score_card: ScoreCard | None = Field(None, description="Score card")


class MetricMeta(BaseMeta):
    """Metric metadata extending BaseMeta."""

    # Metric-specific fields only (universal fields inherited from BaseMeta)
    pass


class MetricSpec(BaseSpec):
    """Metric specification extending BaseSpec.

    Field Mutability Guide:
    ======================

    IMMUTABLE FIELDS (cannot be updated after creation):
    - analytic: Analytic name (set at creation)
    - project_uuid: Project assignment (set at creation)
    - metric_values: Metric values (set at creation)
    - raw: Raw data (set at creation)

    MUTABLE FIELDS (can be updated via API):
    - None (Metric is typically immutable after creation)
    """

    analytic: str = Field(
        ...,
        description="The name of the analytic used to generate this specific metric",
    )  # IMMUTABLE: Set at creation
    project_uuid: str = Field(
        ..., description="The UUID of the project to which this metric relates"
    )  # IMMUTABLE: Set at creation
    metric_values: dict[str, MetricValue] = Field(
        ...,
        description="Map of metric values including scores and score factors",
    )  # IMMUTABLE: Set at creation
    raw: dict[str, Any] | None = Field(
        None,
        description="Superset of information included in the specification",
    )  # IMMUTABLE: Set at creation

    @field_validator("metric_values", mode="before")
    @classmethod
    def validate_metric_values(cls, v: Any) -> Any:
        """Handle metric values validation."""
        if isinstance(v, dict):
            validated_values = {}
            for key, value in v.items():
                if isinstance(value, dict):
                    validated_values[key] = MetricValue(**value)
                else:
                    validated_values[key] = value
            return validated_values
        return v


class Metric(BaseResource):
    """Metric resource model extending BaseResource."""

    # Metric-specific fields (universal fields inherited from BaseResource)
    spec: MetricSpec = Field(..., description="Metric specification")  # type: ignore

    model_config = ConfigDict(extra="ignore")

    def __init__(self, **data: Any) -> None:
        # Convert spec to MetricSpec if it's a dict
        if "spec" in data and isinstance(data["spec"], dict):
            data["spec"] = MetricSpec(**data["spec"])
        super().__init__(**data)

    @override
    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v: Any, info: Any) -> Any:
        """Detect and log schema drift for unknown fields."""
        if info.field_name == "spec" and isinstance(v, dict):
            # Log unknown fields for schema drift detection in spec
            known_fields = {"analytic", "project_uuid", "metric_values", "raw"}
            unknown_fields = set(v.keys()) - known_fields
            if unknown_fields:
                logger.warning(
                    f"Schema drift detected in {info.field_name}: "
                    f"unknown fields {unknown_fields}"
                )
        return v

    @override
    @classmethod
    def get_mutable_fields_cls(cls) -> list[str]:
        """Get list of mutable fields for Metric."""
        return ["meta.name", "meta.description", "meta.tags", "spec"]


def _get_metric_ops(client: APIClient) -> BaseResourceOperations[Metric]:
    """Get BaseResourceOperations instance for Metric."""
    return BaseResourceOperations(client, "metrics", Metric)


def list_metrics(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: ListParameters | None = None,
    max_pages: int | None = None,
    **kwargs: Any,
) -> list[Metric]:
    """List metrics with advanced filtering and pagination."""
    ops = _get_metric_ops(client)
    return ops.list(tenant_meta_namespace, list_params, max_pages, **kwargs)


def list_metrics_iter(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: ListParameters | None = None,
    max_pages: int | None = None,
    **kwargs: Any,
) -> Iterator[Metric]:
    """Iterate over metrics without materializing the full list."""
    ops = _get_metric_ops(client)
    return ops.list_iter(tenant_meta_namespace, list_params, max_pages, **kwargs)


def get_metric(
    client: APIClient, tenant_meta_namespace: str, metric_uuid: str
) -> Metric:
    """Get specific metric by UUID.

    Raises:
        NotFoundError: If metric doesn't exist
        PermissionDeniedError: If user lacks permission
        ServerError: If server error occurs

    """
    ops = _get_metric_ops(client)
    return ops.get(tenant_meta_namespace, metric_uuid)


def create_metric(
    client: APIClient,
    tenant_meta_namespace: str,
    payload: CreateMetricPayload,
) -> Metric:
    """Create a new metric with pre-validation and typed errors.

    Raises:
        ValidationError: If payload is invalid
        NotFoundError: If namespace doesn't exist
        PermissionDeniedError: If user lacks permission
        ConflictError: If metric already exists
        ServerError: If server error occurs

    """
    ops = _get_metric_ops(client)
    return ops.create(tenant_meta_namespace, payload)


def update_metric(
    client: APIClient,
    tenant_meta_namespace: str,
    metric_uuid: str,
    payload: UpdateMetricPayload,
    update_mask: str,
) -> Metric:
    """Update an existing metric with partial updates.

    Args:
        client: APIClient instance
        tenant_meta_namespace: Canonical namespace name
        metric_uuid: UUID of the metric to update
        payload: Metric update payload
        update_mask: Comma-separated list of fields to update (required), e.g.
            "meta.tags,meta.description". Missing or empty raises ValidationError.

    Returns:
        Updated Metric object

    Raises:
        ValidationError: If payload is invalid or update_mask is missing/empty
        NotFoundError: If metric doesn't exist
        PermissionDeniedError: If user lacks permission
        ServerError: If server error occurs

    """
    from ..exceptions import ValidationError as EndorValidationError

    if not (update_mask and update_mask.strip()):
        raise EndorValidationError(
            message=(
                "Metric update requires an update_mask "
                "(e.g. 'meta.description', 'meta.tags')."
            ),
            operation="update",
            namespace=tenant_meta_namespace,
            resource_uuid=metric_uuid,
        )
    # Convert update_mask from string to List[str] for base class
    update_mask_list = parse_update_mask(update_mask)
    ops = _get_metric_ops(client)
    return ops.update(tenant_meta_namespace, metric_uuid, payload, update_mask_list)


def delete_metric(
    client: APIClient, tenant_meta_namespace: str, metric_uuid: str
) -> bool:
    """Delete a metric by UUID."""
    ops = _get_metric_ops(client)
    return ops.delete(tenant_meta_namespace, metric_uuid)


# Payload models for create and update operations
class CreateMetricPayload(BaseModel):
    """Payload for creating a metric."""

    meta: MetricMetaCreate = Field(..., description="Metric metadata for creation")
    spec: MetricSpec = Field(..., description="Metric specification")


class UpdateMetricPayload(BaseModel):
    """Payload for updating a metric."""

    meta: MetricMetaUpdate | None = Field(
        None, description="Metric metadata for update"
    )
    spec: MetricSpec | None = Field(None, description="Metric specification for update")


class MetricMetaCreate(BaseModel):
    """Metric metadata for creation."""

    name: str = Field(..., description="Metric name")
    description: str | None = Field(None, description="Metric description")


def build_create_payload(
    *,
    name: str,
    analytic: str,
    project_uuid: str,
    metric_values: dict[str, Any],
    description: str | None = None,
    raw: dict[str, Any] | None = None,
) -> CreateMetricPayload:
    """Build CreateMetricPayload from kwargs (decoupled facade create)."""
    meta = MetricMetaCreate(name=name, description=description)
    spec = MetricSpec(
        analytic=analytic,
        project_uuid=project_uuid,
        metric_values=metric_values,
        raw=raw,
        notification=None,
        finding=None,
        exception=None,
    )
    return CreateMetricPayload(meta=meta, spec=spec)


class MetricMetaUpdate(BaseModel):
    """Metric metadata for update."""

    description: str | None = Field(None, description="Metric description")

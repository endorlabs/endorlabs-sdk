"""
Metric resource module for Endor Labs API.

This module provides CRUD operations for Metric resources following the
established patterns from the base class implementation.
"""

import logging
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..api_client import APIClient, RedactingFilter, redaction_pattern
from ..models.base import BaseMeta, BaseResource, BaseResourceOperations, BaseSpec
from ..types import ListParameters

# Set up logger with redaction filter
logger = logging.getLogger(__name__)
logger.addFilter(RedactingFilter([redaction_pattern]))


class ScoreCard(BaseModel):
    """Score card for metric value."""

    score: float = Field(..., description="Score value")
    max_score: float = Field(..., description="Maximum possible score")
    factors: List[str] = Field(..., description="Score factors")


class MetricValue(BaseModel):
    """Metric value for metrics."""

    category: str = Field(..., description="Metric value categories")
    description: Optional[str] = Field(
        None, description="Description of the metric value"
    )
    int32_value: Optional[int] = Field(None, description="32-bit integer value")
    int64_value: Optional[str] = Field(
        None, description="64-bit integer value as string"
    )
    string_value: Optional[str] = Field(None, description="String value")
    float_value: Optional[float] = Field(None, description="Float value")
    score_card: Optional[ScoreCard] = Field(None, description="Score card")


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
    metric_values: Dict[str, MetricValue] = Field(
        ...,
        description="A map of metric values. These values include scores and score factors",
    )  # IMMUTABLE: Set at creation
    raw: Optional[dict] = Field(
        None,
        description="This is a superset of the information included in the specification",
    )  # IMMUTABLE: Set at creation

    @field_validator("metric_values", mode="before")
    @classmethod
    def validate_metric_values(cls, v):
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

    def __init__(self, **data):
        # Convert spec to MetricSpec if it's a dict
        if "spec" in data and isinstance(data["spec"], dict):
            data["spec"] = MetricSpec(**data["spec"])
        super().__init__(**data)

    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v, info):
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


def _get_metric_ops(client: APIClient) -> BaseResourceOperations:
    """Get BaseResourceOperations instance for Metric."""
    return BaseResourceOperations(client, "metrics", Metric)


def list_metrics(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: Optional[ListParameters] = None,
    **kwargs,
) -> List[Metric]:
    """List metrics with advanced filtering and pagination."""
    ops = _get_metric_ops(client)
    return ops.list(tenant_meta_namespace, list_params, **kwargs)  # type: ignore


def get_metric(
    client: APIClient, tenant_meta_namespace: str, metric_uuid: str
) -> Optional[Metric]:
    """Get specific metric by UUID."""
    ops = _get_metric_ops(client)
    return ops.get(tenant_meta_namespace, metric_uuid)  # type: ignore


def create_metric(
    client: APIClient,
    tenant_meta_namespace: str,
    payload: "CreateMetricPayload",
) -> Optional[Metric]:
    """Create a new metric."""
    ops = _get_metric_ops(client)
    return ops.create(tenant_meta_namespace, payload)  # type: ignore


def update_metric(
    client: APIClient,
    tenant_meta_namespace: str,
    metric_uuid: str,
    payload: "UpdateMetricPayload",
    update_mask: Optional[List[str]] = None,
) -> Optional[Metric]:
    """Update an existing metric with partial updates."""
    ops = _get_metric_ops(client)
    return ops.update(tenant_meta_namespace, metric_uuid, payload, update_mask)  # type: ignore


def delete_metric(
    client: APIClient, tenant_meta_namespace: str, metric_uuid: str
) -> bool:
    """Delete a metric by UUID."""
    ops = _get_metric_ops(client)
    return ops.delete(tenant_meta_namespace, metric_uuid)  # type: ignore


# Payload models for create and update operations
class CreateMetricPayload(BaseModel):
    """Payload for creating a metric."""

    meta: "MetricMetaCreate" = Field(..., description="Metric metadata for creation")
    spec: MetricSpec = Field(..., description="Metric specification")


class UpdateMetricPayload(BaseModel):
    """Payload for updating a metric."""

    meta: Optional["MetricMetaUpdate"] = Field(
        None, description="Metric metadata for update"
    )
    spec: Optional[MetricSpec] = Field(
        None, description="Metric specification for update"
    )


class MetricMetaCreate(BaseModel):
    """Metric metadata for creation."""

    name: str = Field(..., description="Metric name")
    description: Optional[str] = Field(None, description="Metric description")


class MetricMetaUpdate(BaseModel):
    """Metric metadata for update."""

    description: Optional[str] = Field(None, description="Metric description")

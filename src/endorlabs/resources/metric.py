"""Metric resource module for Endor Labs API.

This module provides CRUD operations for Metric resources following the
established patterns from the base class implementation.
"""

from __future__ import annotations

from typing import Any, override

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..models.base import BaseMeta, BaseResource, BaseSpec
from ..utils.logging_config import get_resource_logger

logger = get_resource_logger(__name__)


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

"""ScanWorkflow resource module for Endor Labs API.

Scan workflows represent a workflow of scan steps. List and get only;
API may omit list.objects when empty (treat as []).
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


class ScanWorkflowSpec(BaseSpec):
    """Scan workflow specification extending BaseSpec."""

    steps: list[dict[str, Any]] | None = Field(
        None,
        description="Workflow steps.",
    )
    remediation_parameters: dict[str, Any] | None = Field(
        None,
        description="Parameters for remediation actions of the analytic scan.",
    )
    automated_scan_parameters: dict[str, Any] | None = Field(
        None,
        description="Parameters applied across cloud workflow scans.",
    )


class ScanWorkflowMeta(BaseMeta):
    """Scan workflow metadata extending BaseMeta."""

    pass


class ScanWorkflow(BaseResource):
    """Scan Workflow resource model. List and get only."""

    spec: ScanWorkflowSpec | None = Field(  # pyright: ignore[reportIncompatibleVariableOverride]
        None, description="Scan workflow specification"
    )

    model_config: ClassVar[dict[str, str]] = {"extra": "ignore"}

    @override
    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v: Any, info: Any) -> Any:
        """Detect and log schema drift in scan workflow responses."""
        if info.field_name == "spec" and isinstance(v, dict):
            known = {"steps", "remediation_parameters", "automated_scan_parameters"}
            unknown = set(v.keys()) - known
            if unknown:
                logger.warning(
                    "Schema drift in ScanWorkflow.spec: unknown fields %s",
                    unknown,
                )
        return v

"""ScanWorkflow resource module for Endor Labs API.

Scan workflows represent a workflow of scan steps. List and get only;
API may omit list.objects when empty (treat as []).
"""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import Field

from ..utils.logging_config import get_resource_logger
from .base import (
    BaseMeta,
    BaseResource,
    BaseSpec,
)

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

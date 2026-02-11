"""ScanWorkflowResult resource module for Endor Labs API.

Scan workflow results correspond to workflow scan results. List and get only;
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


class ScanWorkflowResultSpec(BaseSpec):
    """Scan workflow result specification extending BaseSpec."""

    # Spec may have many fields; use dict for flexibility
    steps: list[dict[str, Any]] | None = Field(
        None,
        description="Workflow result steps.",
    )


class ScanWorkflowResultMeta(BaseMeta):
    """Scan workflow result metadata extending BaseMeta."""

    pass


class ScanWorkflowResult(BaseResource):
    """Scan Workflow Result resource model. List and get only."""

    spec: ScanWorkflowResultSpec | None = Field(  # pyright: ignore[reportIncompatibleVariableOverride]
        None, description="Scan workflow result specification"
    )

    model_config: ClassVar[dict[str, str]] = {"extra": "ignore"}

    @override
    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v: Any, info: Any) -> Any:
        """Detect and log schema drift in scan workflow result responses."""
        if info.field_name == "spec" and isinstance(v, dict):
            known = {"steps"}
            unknown = set(v.keys()) - known
            if unknown:
                logger.warning(
                    "Schema drift in ScanWorkflowResult.spec: unknown fields %s",
                    unknown,
                )
        return v

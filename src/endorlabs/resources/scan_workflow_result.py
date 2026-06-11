"""ScanWorkflowResult resource module for Endor Labs API.

Scan workflow results correspond to workflow scan results. List and get only;
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

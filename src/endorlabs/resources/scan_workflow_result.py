"""ScanWorkflowResult resource module for Endor Labs API.

Scan workflow results correspond to workflow scan results. List and get only;
API may omit list.objects when empty (treat as []).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, ClassVar, override

from pydantic import Field, field_validator

from ..models.base import (
    BaseMeta,
    BaseResource,
    BaseResourceOperations,
    BaseSpec,
)
from ..utils.logging_config import get_resource_logger

if TYPE_CHECKING:
    from ..api_client import APIClient
    from ..types import ListParameters

logger = get_resource_logger(__name__)


def _get_scan_workflow_result_ops(
    client: APIClient,
) -> BaseResourceOperations[ScanWorkflowResult]:
    """Get BaseResourceOperations instance for scan workflow results."""
    return BaseResourceOperations(client, "scan-workflow-results", ScanWorkflowResult)


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


def list_scan_workflow_results(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: ListParameters | None = None,
    max_pages: int | None = None,
    **kwargs: Any,
) -> list[ScanWorkflowResult]:
    """List scan workflow results. Missing list.objects treated as []."""
    ops = _get_scan_workflow_result_ops(client)
    return ops.list(tenant_meta_namespace, list_params, max_pages, **kwargs)


def list_scan_workflow_results_iter(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: ListParameters | None = None,
    max_pages: int | None = None,
    **kwargs: Any,
) -> Iterator[ScanWorkflowResult]:
    """Iterate over scan workflow results without materializing the full list."""
    ops = _get_scan_workflow_result_ops(client)
    return ops.list_iter(tenant_meta_namespace, list_params, max_pages, **kwargs)


def get_scan_workflow_result(
    client: APIClient,
    tenant_meta_namespace: str,
    scan_workflow_result_uuid: str,
) -> ScanWorkflowResult:
    """Get a scan workflow result by UUID."""
    ops = _get_scan_workflow_result_ops(client)
    return ops.get(tenant_meta_namespace, scan_workflow_result_uuid)

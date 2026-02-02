"""ScanWorkflow resource module for Endor Labs API.

Scan workflows represent a workflow of scan steps. List and get only;
API may omit list.objects when empty (treat as []).
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, ClassVar

from pydantic import Field, field_validator

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


def _get_scan_workflow_ops(
    client: APIClient,
) -> BaseResourceOperations[ScanWorkflow]:
    """Get BaseResourceOperations instance for scan workflows."""
    return BaseResourceOperations(client, "scan-workflows", ScanWorkflow)


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


def list_scan_workflows(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: ListParameters | None = None,
    max_pages: int | None = None,
    **kwargs: Any,
) -> list[ScanWorkflow]:
    """List scan workflows in the namespace. Missing list.objects treated as []."""
    ops = _get_scan_workflow_ops(client)
    return ops.list(tenant_meta_namespace, list_params, max_pages, **kwargs)


def list_scan_workflows_iter(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: ListParameters | None = None,
    max_pages: int | None = None,
    **kwargs: Any,
) -> Iterator[ScanWorkflow]:
    """Iterate over scan workflows without materializing the full list."""
    ops = _get_scan_workflow_ops(client)
    return ops.list_iter(tenant_meta_namespace, list_params, max_pages, **kwargs)


def get_scan_workflow(
    client: APIClient,
    tenant_meta_namespace: str,
    scan_workflow_uuid: str,
) -> ScanWorkflow:
    """Get a scan workflow by UUID."""
    ops = _get_scan_workflow_ops(client)
    return ops.get(tenant_meta_namespace, scan_workflow_uuid)

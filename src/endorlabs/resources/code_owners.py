"""CodeOwners resource module for Endor Labs API.

Code owner information for a project. List, get, create, update, delete.
endorctl uses resource name CodeOwners (capital O).
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, ClassVar, override

from pydantic import BaseModel, Field, field_validator

from ..models.base import (
    BaseMeta,
    BaseResource,
    BaseResourceOperations,
    BaseSpec,
)
from ..utils.logging_config import get_resource_logger
from ..utils.model_validation import parse_update_mask

if TYPE_CHECKING:
    from ..api_client import APIClient
    from ..types import ListParameters

logger = get_resource_logger(__name__)


def _get_code_owners_ops(
    client: APIClient,
) -> BaseResourceOperations[CodeOwners]:
    """Get BaseResourceOperations instance for code owners."""
    return BaseResourceOperations(client, "codeowners", CodeOwners)


class CodeOwnerData(BaseModel):
    """Code owner data per path/pattern (v1CodeOwnerData)."""

    owners: list[str] = Field(..., description="List of code owners")
    paths: list[str] | None = Field(None, description="List of owned paths")
    labels: list[str] | None = Field(None, description="List of labels")

    model_config: ClassVar[dict[str, str]] = {"extra": "allow"}  # type: ignore[assignment]


class CodeOwnersVersion(BaseModel):
    """Version of the CODEOWNERS file (ref, sha, metadata)."""

    ref: str | None = Field(None, description="Resolved ref (e.g. branch or tag).")
    sha: str | None = Field(None, description="Commit SHA.")
    metadata: dict[str, Any] | None = Field(None, description="Version metadata.")

    model_config: ClassVar[dict[str, str]] = {"extra": "allow"}  # type: ignore[assignment]


class CodeOwnersSpec(BaseSpec):
    """Code owners specification extending BaseSpec."""

    patterns: dict[str, CodeOwnerData | dict[str, Any]] | None = Field(
        None,
        description=(
            "Map of path/pattern to code owner data. "
            "Refreshed from CODEOWNERS file or populated manually."
        ),
    )
    version: CodeOwnersVersion | None = Field(
        None,
        description="Version of the CODEOWNERS file (ref, sha, metadata).",
    )


class CodeOwnersMeta(BaseMeta):
    """Code owners metadata extending BaseMeta."""

    pass


class CodeOwners(BaseResource):
    """Code Owners resource model. List, get, create, update, delete."""

    spec: CodeOwnersSpec | None = Field(  # pyright: ignore[reportIncompatibleVariableOverride]
        None, description="Code owners specification"
    )

    model_config: ClassVar[dict[str, str]] = {"extra": "ignore"}

    @override
    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v: Any, info: Any) -> Any:
        """Detect and log schema drift in code owners responses."""
        if info.field_name == "spec" and isinstance(v, dict):
            known = {"patterns", "version"}
            unknown = set(v.keys()) - known
            if unknown:
                logger.warning(
                    "Schema drift in CodeOwners.spec: unknown fields %s",
                    unknown,
                )
        return v


class CreateCodeOwnersPayload(BaseModel):
    """Payload for creating code owners."""

    meta: CodeOwnersMeta = Field(..., description="Code owners metadata")
    spec: CodeOwnersSpec = Field(..., description="Code owners specification")


def build_create_payload(**kwargs: Any) -> CreateCodeOwnersPayload:
    """Build CreateCodeOwnersPayload from kwargs (decoupled facade create)."""
    return CreateCodeOwnersPayload(**kwargs)


def list_code_owners(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: ListParameters | None = None,
    max_pages: int | None = None,
    **kwargs: Any,
) -> list[CodeOwners]:
    """List code owners in the namespace."""
    ops = _get_code_owners_ops(client)
    return ops.list(tenant_meta_namespace, list_params, max_pages, **kwargs)


def list_code_owners_iter(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: ListParameters | None = None,
    max_pages: int | None = None,
    **kwargs: Any,
) -> Iterator[CodeOwners]:
    """Iterate over code owners without materializing the full list."""
    ops = _get_code_owners_ops(client)
    return ops.list_iter(tenant_meta_namespace, list_params, max_pages, **kwargs)


def get_code_owners(
    client: APIClient,
    tenant_meta_namespace: str,
    code_owners_uuid: str,
) -> CodeOwners:
    """Get code owners by UUID."""
    ops = _get_code_owners_ops(client)
    return ops.get(tenant_meta_namespace, code_owners_uuid)


def create_code_owners(
    client: APIClient,
    tenant_meta_namespace: str,
    payload: CreateCodeOwnersPayload,
) -> CodeOwners:
    """Create code owners."""
    ops = _get_code_owners_ops(client)
    return ops.create(tenant_meta_namespace, payload)


def update_code_owners(
    client: APIClient,
    tenant_meta_namespace: str,
    code_owners_uuid: str,
    payload: CodeOwners | dict[str, Any],
    update_mask: str | list[str] | None = None,
) -> CodeOwners:
    """Update code owners."""
    ops = _get_code_owners_ops(client)
    if isinstance(payload, dict):
        payload = CodeOwners(**payload)
    mask_list: list[str] = (
        parse_update_mask(update_mask)
        if isinstance(update_mask, str)
        else (update_mask or [])
    )
    return ops.update(
        tenant_meta_namespace,
        code_owners_uuid,
        payload,
        mask_list,
    )


def delete_code_owners(
    client: APIClient,
    tenant_meta_namespace: str,
    code_owners_uuid: str,
) -> bool:
    """Delete code owners by UUID."""
    ops = _get_code_owners_ops(client)
    return ops.delete(tenant_meta_namespace, code_owners_uuid)

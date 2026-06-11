"""CodeOwners resource module for Endor Labs API.

Code owner information for a project. List, get, create, update, delete.
endorctl uses resource name CodeOwners (capital O).
"""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, Field

from ..utils.logging_config import get_resource_logger
from .base import (
    BaseMeta,
    BaseResource,
    BaseSpec,
)

logger = get_resource_logger(__name__)


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


class CreateCodeOwnersPayload(BaseModel):
    """Payload for creating code owners."""

    meta: CodeOwnersMeta = Field(..., description="Code owners metadata")
    spec: CodeOwnersSpec = Field(..., description="Code owners specification")


def build_create_payload(**kwargs: Any) -> CreateCodeOwnersPayload:
    """Build CreateCodeOwnersPayload from kwargs (decoupled facade create)."""
    from ..utils.create_payload import pass_through_create_payload

    return pass_through_create_payload(
        CreateCodeOwnersPayload, kwargs, attr_name="CodeOwners"
    )

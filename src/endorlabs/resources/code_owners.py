"""CodeOwners — thin consumer wrapper over generated V1CodeOwners."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field

from endorlabs.generated.models.code_owners_service import V1CodeOwners

from .base import BaseMeta, BaseSpec
from .consumer.mixin import ConsumerResourceMixin
from .consumer.registry_fields import immutable_fields_for, mutable_fields_for
from .consumer.wire_compat import ConsumerResourceWireMixin


class CodeOwnerData(BaseModel):
    """Code owner data per path/pattern."""

    model_config = ConfigDict(extra="allow")

    owners: list[str] = Field(..., description="List of code owners")
    paths: list[str] | None = None
    labels: list[str] | None = None


class CodeOwnersVersion(BaseModel):
    """Version of the CODEOWNERS file."""

    model_config = ConfigDict(extra="allow")

    ref: str | None = None
    sha: str | None = None
    metadata: dict[str, Any] | None = None


class CodeOwnersSpec(BaseSpec):
    """Code owners specification."""

    patterns: dict[str, CodeOwnerData | dict[str, Any]] | None = None
    version: CodeOwnersVersion | None = None


class CodeOwnersMeta(BaseMeta):
    """Code owners metadata."""

    pass


class CodeOwners(V1CodeOwners, ConsumerResourceWireMixin, ConsumerResourceMixin):
    """Consumer facade model for CodeOwners (generated wire shape)."""

    _MUTABLE_FIELDS: ClassVar[list[str]] = mutable_fields_for("CodeOwners")
    _IMMUTABLE_FIELDS: ClassVar[list[str]] = immutable_fields_for("CodeOwners")

    spec: CodeOwnersSpec | None = None  # pyright: ignore[reportIncompatibleVariableOverride]


class CreateCodeOwnersPayload(BaseModel):
    """Payload for creating code owners."""

    meta: CodeOwnersMeta = Field(...)
    spec: CodeOwnersSpec = Field(...)


def build_create_payload(**kwargs: Any) -> CreateCodeOwnersPayload:
    """Build CreateCodeOwnersPayload from kwargs (decoupled facade create)."""
    from ..utils.create_payload import pass_through_create_payload

    return pass_through_create_payload(
        CreateCodeOwnersPayload, kwargs, attr_name="CodeOwners"
    )

"""PRCommentConfig resource module for Endor Labs API.

PR comment template configuration used by SCM integrations.
List, get, create, update, delete.
"""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, Field

from ..utils.logging_config import get_resource_logger
from .base import (
    BaseMeta,
    BaseResource,
    BaseSpec,
    FlexibleEnum,
)

logger = get_resource_logger(__name__)


class PlatformSource(FlexibleEnum):
    """Platform source/type for PR comment configuration."""

    UNSPECIFIED = "PLATFORM_SOURCE_UNSPECIFIED"
    GITHUB = "PLATFORM_SOURCE_GITHUB"
    GITLAB = "PLATFORM_SOURCE_GITLAB"
    GITSERVER = "PLATFORM_SOURCE_GITSERVER"
    BITBUCKET = "PLATFORM_SOURCE_BITBUCKET"
    BINARY = "PLATFORM_SOURCE_BINARY"
    HUGGING_FACE = "PLATFORM_SOURCE_HUGGING_FACE"
    AZURE = "PLATFORM_SOURCE_AZURE"
    ARCHIVE = "PLATFORM_SOURCE_ARCHIVE"
    EXTERNAL_AI_SERVICE = "PLATFORM_SOURCE_EXTERNAL_AI_SERVICE"
    GITHUB_ENTERPRISE = "PLATFORM_SOURCE_GITHUB_ENTERPRISE"


class PRCommentsTemplate(BaseModel):
    """Go template content used for findings summary PR comments."""

    findings_summary_template: str = Field(
        ...,
        description="Template for PR comment summary of findings.",
    )

    model_config: ClassVar[dict[str, str]] = {"extra": "allow"}  # type: ignore[assignment]


class PRCommentConfigSpec(BaseSpec):
    """PR comment configuration specification extending BaseSpec."""

    platform_type: PlatformSource | str | None = Field(
        PlatformSource.UNSPECIFIED,
        description="SCM platform type for this PR comment template.",
    )
    template: PRCommentsTemplate = Field(
        ...,
        description="Go template used to render PR comments.",
    )


class PRCommentConfigMeta(BaseMeta):
    """PR comment configuration metadata extending BaseMeta."""

    pass


class PRCommentConfig(BaseResource):
    """PR comment configuration resource model."""

    spec: PRCommentConfigSpec | None = Field(  # pyright: ignore[reportIncompatibleVariableOverride]
        None, description="PR comment configuration spec"
    )
    propagate: bool | None = Field(
        None,
        description="Whether this config should propagate to child namespaces.",
    )

    model_config: ClassVar[dict[str, str]] = {"extra": "ignore"}


class CreatePRCommentConfigPayload(BaseModel):
    """Payload for creating a PR comment configuration."""

    meta: PRCommentConfigMeta = Field(..., description="PR comment config metadata")
    spec: PRCommentConfigSpec = Field(..., description="PR comment config spec")
    propagate: bool | None = Field(
        None,
        description="Whether config is visible in child namespaces.",
    )


def build_create_payload(**kwargs: Any) -> CreatePRCommentConfigPayload:
    """Build CreatePRCommentConfigPayload from kwargs (decoupled facade create)."""
    from ..utils.create_payload import pass_through_create_payload

    return pass_through_create_payload(
        CreatePRCommentConfigPayload, kwargs, attr_name="PRCommentConfig"
    )

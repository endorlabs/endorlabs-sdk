"""PRCommentConfig — thin consumer wrapper over generated V1PRCommentConfig."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, Field

from endorlabs.generated.models.p_r_comment_config_service import V1PRCommentConfig

from .base import BaseMeta, BaseSpec, FlexibleEnum
from .consumer.mixin import ConsumerResourceMixin
from .consumer.registry_fields import immutable_fields_for, mutable_fields_for
from .consumer.wire_compat import ConsumerResourceWireMixin


class PRCommentConfig(
    V1PRCommentConfig, ConsumerResourceWireMixin, ConsumerResourceMixin
):
    """Consumer facade model for PRCommentConfig (generated wire shape)."""

    _MUTABLE_FIELDS: ClassVar[list[str]] = mutable_fields_for("PRCommentConfig")
    _IMMUTABLE_FIELDS: ClassVar[list[str]] = immutable_fields_for("PRCommentConfig")


# --- integration / create-update compat (pre-cutover helpers) ---


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

"""Finding — thin consumer wrapper over generated V1Finding."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, Field

from endorlabs.generated.models.finding_service import V1Finding
from endorlabs.generated.models.finding_service import (
    V1FindingSpec as _V1FindingSpec,
)

from .base import FlexibleEnum
from .consumer.mixin import ConsumerResourceMixin
from .consumer.registry_fields import immutable_fields_for, mutable_fields_for
from .consumer.wire_compat import (
    ConsumerContext,
    ConsumerResourceWireMixin,
    partial_spec_model,
)

FindingSpec = partial_spec_model(_V1FindingSpec, name="FindingSpec")


class FindingTags(FlexibleEnum):
    """Finding tags enumeration (consumer alias names for generated wire values)."""

    UNSPECIFIED = "FINDING_TAGS_UNSPECIFIED"
    AI = "FINDING_TAGS_AI"
    CI_BLOCKER = "FINDING_TAGS_CI_BLOCKER"
    CI_WARNING = "FINDING_TAGS_CI_WARNING"
    DIRECT = "FINDING_TAGS_DIRECT"
    DISPUTED = "FINDING_TAGS_DISPUTED"
    EXCEPTION = "FINDING_TAGS_EXCEPTION"
    EXPLOITED = "FINDING_TAGS_EXPLOITED"
    FALSE_POSITIVE = "FINDING_TAGS_FALSE_POSITIVE"
    FIXABLE = "FINDING_TAGS_FIXABLE"
    FIX_AVAILABLE = "FINDING_TAGS_FIX_AVAILABLE"
    IGNORED = "FINDING_TAGS_IGNORED"
    INVALID_SECRET = "FINDING_TAGS_INVALID_SECRET"
    MALWARE = "FINDING_TAGS_MALWARE"
    NAMESPACE_INTERNAL = "FINDING_TAGS_NAMESPACE_INTERNAL"
    NORMAL = "FINDING_TAGS_NORMAL"
    NOTIFICATION = "FINDING_TAGS_NOTIFICATION"
    PATH_EXTERNAL = "FINDING_TAGS_PATH_EXTERNAL"
    PHANTOM = "FINDING_TAGS_PHANTOM"
    POLICY = "FINDING_TAGS_POLICY"
    POTENTIALLY_REACHABLE_DEPENDENCY = "FINDING_TAGS_POTENTIALLY_REACHABLE_DEPENDENCY"
    POTENTIALLY_REACHABLE_FUNCTION = "FINDING_TAGS_POTENTIALLY_REACHABLE_FUNCTION"
    PRODUCTION = "FINDING_TAGS_PRODUCTION"
    PROJECT_INTERNAL = "FINDING_TAGS_PROJECT_INTERNAL"
    REACHABLE_DEPENDENCY = "FINDING_TAGS_REACHABLE_DEPENDENCY"
    REACHABLE_FUNCTION = "FINDING_TAGS_REACHABLE_FUNCTION"
    SELF = "FINDING_TAGS_SELF"
    SNOOZED = "FINDING_TAGS_SNOOZED"
    TEST = "FINDING_TAGS_TEST"
    TRANSITIVE = "FINDING_TAGS_TRANSITIVE"
    TRUE_POSITIVE = "FINDING_TAGS_TRUE_POSITIVE"
    UNDER_REVIEW = "FINDING_TAGS_UNDER_REVIEW"
    UNFIXABLE = "FINDING_TAGS_UNFIXABLE"
    UNREACHABLE_DEPENDENCY = "FINDING_TAGS_UNREACHABLE_DEPENDENCY"
    UNREACHABLE_FUNCTION = "FINDING_TAGS_UNREACHABLE_FUNCTION"
    VALID_SECRET = "FINDING_TAGS_VALID_SECRET"
    WITHDRAWN = "FINDING_TAGS_WITHDRAWN"


class Finding(V1Finding, ConsumerResourceWireMixin, ConsumerResourceMixin):
    """Consumer facade model for Finding (generated wire shape)."""

    _MUTABLE_FIELDS: ClassVar[list[str]] = mutable_fields_for("Finding")
    _IMMUTABLE_FIELDS: ClassVar[list[str]] = immutable_fields_for("Finding")

    spec: FindingSpec | None = None  # pyright: ignore[reportIncompatibleVariableOverride]
    context: ConsumerContext | None = None  # pyright: ignore[reportIncompatibleVariableOverride]


class CreateFindingPayload(BaseModel):
    """Payload for creating a finding."""

    meta: dict[str, Any] | BaseModel = Field(...)
    spec: dict[str, Any] | BaseModel = Field(...)
    context: dict[str, Any] | BaseModel = Field(...)


class UpdateFindingPayload(BaseModel):
    """Payload for updating a finding."""

    meta: dict[str, Any] | BaseModel | None = None
    spec: dict[str, Any] | BaseModel | None = None
    context: dict[str, Any] | BaseModel | None = None


class FindingMetaUpdate(BaseModel):
    """Partial meta for finding updates."""

    tags: list[str] | None = None


def build_create_payload(**kwargs: Any) -> CreateFindingPayload:
    """Build CreateFindingPayload from kwargs (decoupled facade create)."""
    from ..utils.create_payload import pass_through_create_payload

    return pass_through_create_payload(
        CreateFindingPayload, kwargs, attr_name="Finding"
    )

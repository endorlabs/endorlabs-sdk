"""PolicyTemplate resource module for Endor Labs API.

Policy templates can be used to create policies from templates. This resource
is system-owned: LIST is supported; GET, UPDATE, and DELETE return 403 (only
system can perform them). The Client exposes list() only; use
client.policy_template.list().
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


class PolicyTemplateSpec(BaseSpec):
    """Policy template specification extending BaseSpec."""

    rule: str | None = Field(
        None,
        description="Policy template rule in text format (e.g. Rego).",
    )
    template_parameters: list[dict[str, Any]] | None = Field(
        None,
        description="Template parameters.",
    )
    finding_categories: list[str] | None = Field(
        None,
        description="Finding categories.",
    )
    policy_type: str | None = Field(
        None,
        description="Policy type.",
    )
    query_statements: list[str] | None = Field(
        None,
        description="Query statements.",
    )
    resource_kinds: list[str] | None = Field(
        None,
        description="Resource kinds.",
    )


class PolicyTemplateMeta(BaseMeta):
    """Policy template metadata extending BaseMeta."""

    pass


class PolicyTemplate(BaseResource):
    """Policy Template resource model. List and get only."""

    spec: PolicyTemplateSpec | None = Field(  # pyright: ignore[reportIncompatibleVariableOverride]
        None, description="Policy template specification"
    )

    model_config: ClassVar[dict[str, str]] = {"extra": "ignore"}

    @override
    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v: Any, info: Any) -> Any:
        """Detect and log schema drift in policy template responses."""
        if info.field_name == "spec" and isinstance(v, dict):
            known = {
                "rule",
                "template_parameters",
                "finding_categories",
                "policy_type",
                "query_statements",
                "resource_kinds",
            }
            unknown = set(v.keys()) - known
            if unknown:
                logger.warning(
                    "Schema drift in PolicyTemplate.spec: unknown fields %s",
                    unknown,
                )
        return v

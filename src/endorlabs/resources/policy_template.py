"""PolicyTemplate resource module for Endor Labs API.

Policy templates can be used to create policies from templates.
List and get only.
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


def _get_policy_template_ops(
    client: APIClient,
) -> BaseResourceOperations[PolicyTemplate]:
    """Get BaseResourceOperations instance for policy templates."""
    return BaseResourceOperations(client, "policy-templates", PolicyTemplate)


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


def list_policy_templates(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: ListParameters | None = None,
    max_pages: int | None = None,
    **kwargs: Any,
) -> list[PolicyTemplate]:
    """List policy templates in the namespace."""
    ops = _get_policy_template_ops(client)
    return ops.list(tenant_meta_namespace, list_params, max_pages, **kwargs)


def list_policy_templates_iter(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: ListParameters | None = None,
    max_pages: int | None = None,
    **kwargs: Any,
) -> Iterator[PolicyTemplate]:
    """Iterate over policy templates without materializing the full list."""
    ops = _get_policy_template_ops(client)
    return ops.list_iter(tenant_meta_namespace, list_params, max_pages, **kwargs)


def get_policy_template(
    client: APIClient,
    tenant_meta_namespace: str,
    policy_template_uuid: str,
) -> PolicyTemplate:
    """Get a policy template by UUID."""
    ops = _get_policy_template_ops(client)
    return ops.get(tenant_meta_namespace, policy_template_uuid)

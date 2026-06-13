"""Policy — thin consumer wrapper over generated V1Policy."""

# ruff: noqa: TC001  # Pydantic field types must resolve at model build time.

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, cast

from pydantic import BaseModel, Field, field_validator

from endorlabs.core.types import ListParameters
from endorlabs.generated.models.policy_service import PolicyPolicyType, V1Policy
from endorlabs.operations import BaseResourceOperations

from ..utils.logging_config import get_resource_logger
from .base import BaseMeta, BaseSpec, FlexibleEnum
from .consumer.mixin import ConsumerResourceMixin
from .consumer.registry_fields import immutable_fields_for, mutable_fields_for
from .consumer.wire_compat import ConsumerPolicySpec, ConsumerResourceWireMixin
from .finding_config import FindingConfig
from .notification_config import NotificationConfig

if TYPE_CHECKING:
    from ..api_client import APIClient

logger = get_resource_logger(__name__)


class PolicyType(FlexibleEnum):
    """Policy type enumeration."""

    UNSPECIFIED = "POLICY_TYPE_UNSPECIFIED"
    ADMISSION = "POLICY_TYPE_ADMISSION"
    EXCEPTION = "POLICY_TYPE_EXCEPTION"
    FINDING = "POLICY_TYPE_FINDING"
    FINDING_CFG = "POLICY_TYPE_FINDING_CFG"
    ML_FINDING = "POLICY_TYPE_ML_FINDING"
    NOTIFICATION = "POLICY_TYPE_NOTIFICATION"
    REMEDIATION = "POLICY_TYPE_REMEDIATION"
    SYSTEM_FINDING = "POLICY_TYPE_SYSTEM_FINDING"
    USER_FINDING = "POLICY_TYPE_USER_FINDING"


class Policy(V1Policy, ConsumerResourceWireMixin, ConsumerResourceMixin):
    """Consumer facade model for Policy (generated wire shape)."""

    _MUTABLE_FIELDS: ClassVar[list[str]] = mutable_fields_for("Policy")
    _IMMUTABLE_FIELDS: ClassVar[list[str]] = immutable_fields_for("Policy")

    spec: ConsumerPolicySpec | None = None  # pyright: ignore[reportIncompatibleVariableOverride]


def list_policies_by_type(
    client: APIClient,
    tenant_meta_namespace: str,
    policy_type: PolicyType | PolicyPolicyType,
) -> list[Policy]:
    """List policies filtered by type."""
    ptype = policy_type.value if hasattr(policy_type, "value") else str(policy_type)
    list_params = ListParameters(
        filter=f'spec.policy_type=="{ptype}"',
    )
    ops = BaseResourceOperations(client, "policies", Policy)
    return cast("list[Policy]", ops.list(tenant_meta_namespace, list_params))


def list_policies_by_namespace(
    client: APIClient, tenant_meta_namespace: str, target_namespace: str
) -> list[Policy]:
    """List policies filtered by namespace."""
    list_params = ListParameters(
        filter=f'tenant_meta.namespace=="{target_namespace}"',
    )
    ops = BaseResourceOperations(client, "policies", Policy)
    return cast("list[Policy]", ops.list(tenant_meta_namespace, list_params))


def list_policies_paginated(
    client: APIClient,
    tenant_meta_namespace: str,
    page_size: int = 10,
    page_token: str | None = None,
) -> list[Policy]:
    """List policies with pagination."""
    list_params = ListParameters(
        page_size=page_size,
        page_token=page_token,
    )
    ops = BaseResourceOperations(client, "policies", Policy)
    return cast("list[Policy]", ops.list(tenant_meta_namespace, list_params))


def list_policies_sorted(
    client: APIClient,
    tenant_meta_namespace: str,
    sort_by: str = "meta.create_time",
    desc: bool = True,
) -> list[Policy]:
    """List policies with sorting."""
    list_params = ListParameters(
        sort_by=sort_by,
        desc=desc,
    )
    ops = BaseResourceOperations(client, "policies", Policy)
    return cast("list[Policy]", ops.list(tenant_meta_namespace, list_params))


# --- integration / create-update compat (pre-cutover helpers) ---


class ExceptionReason(FlexibleEnum):
    """Exception reason enumeration."""

    UNSPECIFIED = "EXCEPTION_REASON_UNSPECIFIED"
    FALSE_POSITIVE = "EXCEPTION_REASON_FALSE_POSITIVE"
    IN_TRIAGE = "EXCEPTION_REASON_IN_TRIAGE"
    OTHER = "EXCEPTION_REASON_OTHER"
    RESOLVED = "EXCEPTION_REASON_RESOLVED"
    RISK_ACCEPTED = "EXCEPTION_REASON_RISK_ACCEPTED"


class PolicyRule(BaseModel):
    """Policy rule configuration."""

    action: str = Field(..., description="Rule action (ALLOW, DENY, WARN)")
    condition: str = Field(..., description="Rule condition")
    effect: str = Field(..., description="Rule effect")
    priority: int = Field(..., description="Rule priority")
    description: str = Field(..., description="Rule description")


class PolicySpec(BaseSpec):
    """Policy specification extending BaseSpec."""

    policy_type: PolicyType | None = Field(None, description="Policy type")
    rule: str | None = Field(None, description="Policy rule in text format")
    project_selector: list[str] | None = Field(
        None, description="Project selector tags"
    )
    project_exceptions: list[str] | None = Field(
        None, description="Project exception tags"
    )
    resource_kinds: list[str] | None = Field(None, description="Resource kinds")
    disable: bool | None = Field(False, description="Whether policy is disabled")
    finding: FindingConfig | None = Field(None, description="Finding configuration")
    finding_level: str | None = Field(None, description="Finding level")
    query_statements: list[str] | None = Field(None, description="Query statements")
    template_uuid: str | None = Field(None, description="Template UUID")
    template_version: str | None = Field(None, description="Template version")
    template_parameters: list[dict[str, Any]] | None = Field(
        None, description="Template parameters"
    )
    template_values: dict[str, Any] | None = Field(None, description="Template values")
    admission: dict[str, Any] | None = Field(
        None, description="Admission configuration"
    )
    group_by_fields: list[str] | None = Field(None, description="Group by fields")
    notification: NotificationConfig | None = Field(
        None, description="Notification configuration"
    )
    # exception is now defined in BaseSpec as ExceptionConfig
    # Keeping this for backward compatibility but it will use BaseSpec.exception
    finding_categories: list[str] | None = Field(
        None, description="Finding categories for policy filtering"
    )

    @field_validator("rule")
    @classmethod
    def validate_rule(cls, v: str | None) -> str | None:
        """Validate Rego rule syntax (basic checks)."""
        if v and not v.strip():
            raise ValueError("rule cannot be empty or whitespace")
        if v and not v.strip().startswith("package "):
            logger.warning("Rego rule should start with 'package' declaration")
        return v.strip() if v else v

    @field_validator("project_selector")
    @classmethod
    def validate_project_selector(cls, v: list[str] | None) -> list[str] | None:
        """Validate project selector tags are not empty strings."""
        if v:
            return [tag.strip() for tag in v if tag.strip()]
        return v

    @field_validator("project_exceptions")
    @classmethod
    def validate_project_exceptions(cls, v: list[str] | None) -> list[str] | None:
        """Validate project exception tags are not empty strings."""
        if v:
            return [tag.strip() for tag in v if tag.strip()]
        return v


class PolicyMeta(BaseMeta):
    """Policy metadata extending BaseMeta."""

    # Policy-specific fields only (universal fields inherited from BaseMeta)
    pass

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str] | None) -> list[str] | None:
        """Validate policy tags are not empty strings."""
        if v:
            return [tag.strip() for tag in v if tag.strip()]
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate policy name is not empty or whitespace."""
        if not v.strip():
            raise ValueError("name cannot be empty or whitespace")
        return v.strip()

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Validate policy description is not empty or whitespace."""
        if not v.strip():
            raise ValueError("description cannot be empty or whitespace")
        return v.strip()


class PolicyMetaUpdate(BaseModel):
    """Metadata for updating a Policy (only mutable fields)."""

    name: str | None = Field(None, description="Updated policy name")
    description: str | None = Field(None, description="Updated description")
    tags: list[str] | None = Field(None, description="Updated tags")
    annotations: dict[str, Any] | None = Field(None, description="Updated annotations")

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str] | None) -> list[str] | None:
        """Validate policy tags are not empty strings."""
        if v:
            return [tag.strip() for tag in v if tag.strip()]
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        """Validate policy name is not empty or whitespace if provided."""
        if v is not None and not v.strip():
            raise ValueError("name cannot be empty or whitespace")
        return v.strip() if v else v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str | None) -> str | None:
        """Validate policy description is not empty or whitespace if provided."""
        if v is not None and not v.strip():
            raise ValueError("description cannot be empty or whitespace")
        return v.strip() if v else v


class CreatePolicyPayload(BaseModel):
    """Payload for creating a new policy."""

    meta: PolicyMeta = Field(..., description="Policy metadata")
    spec: PolicySpec = Field(..., description="Policy specification")
    propagate: bool | None = Field(True, description="Propagate to child namespaces")


class UpdatePolicyPayload(BaseModel):
    r"""Payload for updating an Endor Labs policy.

    MUTABLE FIELDS (can be updated via PATCH):
    - meta.name: Policy name
    - meta.description: Policy description
    - meta.tags: Policy tags
    - spec.rule: OPA/Rego rule definition
    - spec.disable: Enable/disable flag
    - spec.project_selector: Projects to apply policy to
    - spec.project_exceptions: Projects to exclude from policy
    - spec.template_values: Template configuration values
    - propagate: Whether to propagate to child namespaces

    IMMUTABLE FIELDS (read-only, managed by API):
    - uuid: Unique identifier
    - meta.create_time, meta.created_by: Creation metadata
    - meta.update_time, meta.updated_by: Auto-managed timestamps
    - spec.policy_type: Policy type (set at creation)
    - spec.template_uuid: Template reference (set at creation)
    - tenant_meta.namespace: Namespace assignment

    Example:
        >>> payload = UpdatePolicyPayload(
        ...     meta=PolicyMetaUpdate(
        ...         name="Updated Policy Name",
        ...         description="Updated description",
        ...         tags=["security", "updated"]
        ...     ),
        ...     spec=PolicySpec(
        ...         policy_type=PolicyType.ML_FINDING,
        ...         rule="package updated\n...",
        ...         resource_kinds=[],
        ...         disable=False
        ...     )
        ... )
        >>> policy = update_policy(
        ...     client, namespace, uuid, payload, "meta.name,meta.description,spec.rule"
        ... )

    """

    meta: PolicyMetaUpdate | None = Field(None, description="Updated policy metadata")
    spec: PolicySpec | None = Field(None, description="Updated policy specification")
    propagate: bool | None = Field(None, description="Propagate to child namespaces")


def build_create_payload(**kwargs: Any) -> CreatePolicyPayload:
    """Build CreatePolicyPayload from kwargs (decoupled facade create)."""
    from ..utils.create_payload import pass_through_create_payload

    return pass_through_create_payload(CreatePolicyPayload, kwargs, attr_name="Policy")

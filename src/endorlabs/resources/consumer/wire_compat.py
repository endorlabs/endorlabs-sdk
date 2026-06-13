"""Consumer wire tolerance helpers for V1-backed resource models.

Generated ``V1*`` types match full OpenAPI shapes; list rows and legacy
callers often send partial specs, legacy ``TenantMeta``, or unknown enum
values.  Thin consumer wrappers use these helpers to stay wire-tolerant
without duplicating entire generated trees.
"""

# ruff: noqa: TC001  # Pydantic field types must resolve at model build time.

from __future__ import annotations

from enum import Enum
from typing import Any, Union, get_args, get_origin

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    create_model,
    model_validator,
)

from ..finding_config import FindingConfig
from ..notification_config import NotificationConfig


def _relax_annotation(annotation: Any) -> Any:
    """Make enum and required nested types tolerant for list-row deserialization."""
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return str | None
    origin = get_origin(annotation)
    if origin is Union:
        args = [a for a in get_args(annotation) if a is not type(None)]
        if len(args) == 1 and isinstance(args[0], type) and issubclass(args[0], Enum):
            return str | None
    if origin is list:
        inner = get_args(annotation)
        if inner and isinstance(inner[0], type) and issubclass(inner[0], Enum):
            return list[str] | None
    if (
        annotation is not None
        and get_origin(annotation) is None
        and isinstance(annotation, type)
        and issubclass(annotation, BaseModel)
    ):
        return dict[str, Any] | annotation | None
    return (
        annotation | None
        if get_origin(annotation) is not Union or type(None) not in get_args(annotation)
        else annotation
    )


def partial_spec_model(
    base: type[BaseModel], *, name: str | None = None
) -> type[BaseModel]:
    """Build a spec subclass with every field optional and ``extra='allow'``."""
    model_name = name or base.__name__
    field_defs: dict[str, Any] = {}
    for field_name, field_info in base.model_fields.items():
        annotation = _relax_annotation(field_info.annotation)
        field_defs[field_name] = (annotation, Field(default=None))
    return create_model(
        model_name,
        __config__=ConfigDict(extra="allow"),
        **field_defs,
    )


def coerce_legacy_wire_data(data: Any) -> Any:
    """Accept legacy ``TenantMeta`` / ``BaseMeta`` instances in constructor dicts."""
    if not isinstance(data, dict):
        return data
    out = dict(data)
    tenant_meta = out.get("tenant_meta")
    if type(tenant_meta).__name__ == "TenantMeta" and hasattr(
        tenant_meta, "model_dump"
    ):
        out["tenant_meta"] = tenant_meta.model_dump(mode="json")
    meta = out.get("meta")
    if type(meta).__name__ == "BaseMeta" and hasattr(meta, "model_dump"):
        out["meta"] = meta.model_dump(mode="json")
    return out


def coerce_legacy_tenant_meta(data: Any) -> Any:
    """Backward-compatible alias for tenant_meta coercion only."""
    return coerce_legacy_wire_data(data)


def _unwrap_model_type(annotation: Any) -> type[BaseModel] | None:
    """Return the nested BaseModel type from an optional/union annotation."""
    origin = get_origin(annotation)
    if origin is Union:
        for arg in get_args(annotation):
            if arg is type(None):
                continue
            unwrapped = _unwrap_model_type(arg)
            if unwrapped is not None:
                return unwrapped
        return None
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation
    return None


def _coerce_constructed_nested_models(
    model_cls: type[BaseModel], obj: BaseModel
) -> BaseModel:
    """Promote nested dicts to typed sub-models after ``model_construct``."""
    for field_name, field_info in model_cls.model_fields.items():
        val = getattr(obj, field_name, None)
        if not isinstance(val, dict):
            continue
        nested_cls = _unwrap_model_type(field_info.annotation)
        if nested_cls is None:
            continue
        try:
            coerced = nested_cls(**val)
        except ValidationError:
            coerced = nested_cls.model_construct(**val)
        object.__setattr__(obj, field_name, coerced)
    return obj


def deserialize_list_row(
    model_cls: type[BaseModel], payload: dict[str, Any]
) -> BaseModel:
    """Construct a resource from a list-row dict; fall back to ``model_construct``."""
    try:
        return model_cls(**payload)
    except ValidationError:
        obj = model_cls.model_construct(**payload)
        return _coerce_constructed_nested_models(model_cls, obj)


class ConsumerResourceWireMixin(BaseModel):
    """Shared before-validator for legacy wire shapes on V1 consumer models."""

    model_config = ConfigDict(extra="ignore")

    @model_validator(mode="before")
    @classmethod
    def _coerce_legacy_wire(cls, data: Any) -> Any:
        return coerce_legacy_wire_data(data)


class ConsumerPolicySpec(BaseModel):
    """Policy spec with tolerant nested finding/notification configs."""

    model_config = ConfigDict(extra="allow")

    policy_type: str | None = None
    rule: str | None = None
    query_statements: list[str] | None = None
    resource_kinds: list[str] | None = None
    template_uuid: str | None = None
    template_values: dict[str, Any] | None = None
    project_selector: list[str] | None = None
    project_exceptions: list[str] | None = None
    finding: FindingConfig | None = None
    notification: NotificationConfig | None = None
    exception: dict[str, Any] | None = None
    enabled: bool | None = None
    name: str | None = None
    description: str | None = None


class BitBucketConfig(BaseModel):
    """Bitbucket installation config (legacy + canonical fields)."""

    model_config = ConfigDict(extra="allow")

    workspace: str | None = None
    access_token: str | None = None
    host_url: str | None = None
    enable_full_scan: bool | None = None
    enable_pr_scans: bool | None = None
    enable_pr_comments: bool | None = None


class InstallationSpec(BaseModel):
    """Installation spec accepting partial and forward-compatible payloads."""

    model_config = ConfigDict(extra="allow")

    bitbucket_config: BitBucketConfig | dict[str, Any] | None = None


class LinterCorrectnessAnalysis(BaseModel):
    """Tolerant nested linter correctness analysis row."""

    model_config = ConfigDict(extra="allow")

    version: str | None = None
    analyzer: str | None = None
    correctness: str | None = None
    confidence_level: str | None = None
    analysis_summary: str | None = None


class LinterResultSpec(BaseModel):
    """LinterResult spec with partial list-row tolerance."""

    model_config = ConfigDict(extra="allow")

    project_uuid: str | None = None
    origin: str | None = None
    extra_key: str | None = None
    linter_correctness_analyses: list[LinterCorrectnessAnalysis] | None = None


class ProjectProcessingStatus(BaseModel):
    """Project processing status with string scan_state tolerance."""

    model_config = ConfigDict(extra="allow")

    disable_automated_scan: bool = False
    scan_state: str | None = None
    scan_time: str | None = None
    analytic_time: str | None = None


class ProjectSpec(BaseModel):
    """Project spec with optional platform_source for masked list rows."""

    model_config = ConfigDict(extra="allow")

    platform_source: str | None = None
    git: dict[str, Any] | None = None
    internal_reference_key: str | None = None
    scan_profile_uuid: str | None = None
    toolchain_profile_uuid: str | None = None


class ConsumerContext(BaseModel):
    """Scan/finding context with unknown type/id tolerance."""

    model_config = ConfigDict(extra="allow")

    id: str | None = None
    type: str | None = None


class ScanLogRequestSpec(BaseModel):
    """Scan log request spec ignoring unknown keys from API drift."""

    model_config = ConfigDict(extra="ignore")

    max_entries: int | None = None
    start_time: str | None = None
    end_time: str | None = None
    newest_first: bool | None = None
    log_levels: list[str] | None = None
    scan_result_uuid: str | None = None
    execution_id: str | None = None
    project_uuid: str | None = None
    installation_uuid: str | None = None
    scan_request_uuid: str | None = None
    onprem_scheduler_uuid: str | None = None
    admin_filter: str | None = None
    applied_filter: str | None = None
    log_messages: list[Any] | None = None

    @model_validator(mode="before")
    @classmethod
    def _coerce_log_messages(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        messages = data.get("log_messages")
        if not isinstance(messages, list):
            return data
        from endorlabs.generated.models.scan_log_request_service import (
            V1ScanLogRequestLogMessage,
        )

        coerced = [
            V1ScanLogRequestLogMessage(**row) if isinstance(row, dict) else row
            for row in messages
        ]
        return {**data, "log_messages": coerced}


class VectorStoreSpec(BaseModel):
    """Vector store spec with optional embedding fields for tests and list rows."""

    model_config = ConfigDict(extra="allow")

    embedding_model: str | None = None
    embedding_provider: str | None = None

"""AsyncJob — thin consumer wrapper over generated V1AsyncJob."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, Field

from endorlabs.generated.models.async_job_service import V1AsyncJob

from .consumer.mixin import ConsumerResourceMixin
from .consumer.registry_fields import immutable_fields_for, mutable_fields_for
from .consumer.wire_compat import ConsumerResourceWireMixin


class AsyncJob(V1AsyncJob, ConsumerResourceWireMixin, ConsumerResourceMixin):
    """Consumer facade model for AsyncJob (SBOM/VEX export jobs)."""

    _MUTABLE_FIELDS: ClassVar[list[str]] = mutable_fields_for("AsyncJob")
    _IMMUTABLE_FIELDS: ClassVar[list[str]] = immutable_fields_for("AsyncJob")


class CreateAsyncJobPayload(BaseModel):
    """Create payload for AsyncJob."""

    meta: dict[str, Any] | BaseModel = Field(...)
    spec: dict[str, Any] | BaseModel = Field(...)
    tenant_meta: dict[str, Any] | BaseModel | None = None


def build_create_payload(**kwargs: Any) -> CreateAsyncJobPayload:
    """Build create payload for AsyncJob."""
    from ..utils.create_payload import pass_through_create_payload

    return pass_through_create_payload(
        CreateAsyncJobPayload, kwargs, attr_name="AsyncJob"
    )

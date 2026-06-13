"""ScanWorkflow — thin consumer wrapper over generated V1ScanWorkflow."""

from __future__ import annotations

from typing import ClassVar

from endorlabs.generated.models.scan_workflow_service import V1ScanWorkflow

from .consumer.mixin import ConsumerResourceMixin
from .consumer.registry_fields import immutable_fields_for, mutable_fields_for
from .consumer.wire_compat import ConsumerResourceWireMixin


class ScanWorkflow(V1ScanWorkflow, ConsumerResourceWireMixin, ConsumerResourceMixin):
    """Consumer facade model for ScanWorkflow (generated wire shape)."""

    _MUTABLE_FIELDS: ClassVar[list[str]] = mutable_fields_for("ScanWorkflow")
    _IMMUTABLE_FIELDS: ClassVar[list[str]] = immutable_fields_for("ScanWorkflow")

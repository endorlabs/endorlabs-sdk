"""ScanWorkflowResult — thin consumer wrapper over generated V1ScanWorkflowResult."""

from __future__ import annotations

from typing import ClassVar

from endorlabs.generated.models.scan_workflow_result_service import V1ScanWorkflowResult

from .consumer.mixin import ConsumerResourceMixin
from .consumer.registry_fields import immutable_fields_for, mutable_fields_for
from .consumer.wire_compat import ConsumerResourceWireMixin


class ScanWorkflowResult(
    V1ScanWorkflowResult, ConsumerResourceWireMixin, ConsumerResourceMixin
):
    """Consumer facade model for ScanWorkflowResult (generated wire shape)."""

    _MUTABLE_FIELDS: ClassVar[list[str]] = mutable_fields_for("ScanWorkflowResult")
    _IMMUTABLE_FIELDS: ClassVar[list[str]] = immutable_fields_for("ScanWorkflowResult")

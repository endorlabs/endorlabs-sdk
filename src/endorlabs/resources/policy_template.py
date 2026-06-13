"""PolicyTemplate — thin consumer wrapper over generated V1PolicyTemplate."""

from __future__ import annotations

from typing import ClassVar

from endorlabs.generated.models.policy_template_service import V1PolicyTemplate

from .consumer.mixin import ConsumerResourceMixin
from .consumer.registry_fields import immutable_fields_for, mutable_fields_for
from .consumer.wire_compat import ConsumerResourceWireMixin


class PolicyTemplate(
    V1PolicyTemplate, ConsumerResourceWireMixin, ConsumerResourceMixin
):
    """Consumer facade model for PolicyTemplate (generated wire shape)."""

    _MUTABLE_FIELDS: ClassVar[list[str]] = mutable_fields_for("PolicyTemplate")
    _IMMUTABLE_FIELDS: ClassVar[list[str]] = immutable_fields_for("PolicyTemplate")

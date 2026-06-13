"""EndorLicense — thin consumer wrapper over generated V1EndorLicense."""

from __future__ import annotations

from typing import ClassVar

from endorlabs.generated.models.endor import V1EndorLicense

from .consumer.mixin import ConsumerResourceMixin
from .consumer.registry_fields import immutable_fields_for, mutable_fields_for
from .consumer.wire_compat import ConsumerResourceWireMixin


class EndorLicense(V1EndorLicense, ConsumerResourceWireMixin, ConsumerResourceMixin):
    """Consumer facade model for EndorLicense (generated wire shape)."""

    _MUTABLE_FIELDS: ClassVar[list[str]] = mutable_fields_for("EndorLicense")
    _IMMUTABLE_FIELDS: ClassVar[list[str]] = immutable_fields_for("EndorLicense")

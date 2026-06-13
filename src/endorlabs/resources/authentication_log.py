"""AuthenticationLog — thin consumer wrapper over generated V1AuthenticationLog."""

from __future__ import annotations

from typing import ClassVar

from endorlabs.generated.models.authentication_log_service import V1AuthenticationLog

from .consumer.mixin import ConsumerResourceMixin
from .consumer.registry_fields import immutable_fields_for, mutable_fields_for
from .consumer.wire_compat import ConsumerResourceWireMixin


class AuthenticationLog(
    V1AuthenticationLog, ConsumerResourceWireMixin, ConsumerResourceMixin
):
    """Consumer facade model for AuthenticationLog (generated wire shape)."""

    _MUTABLE_FIELDS: ClassVar[list[str]] = mutable_fields_for("AuthenticationLog")
    _IMMUTABLE_FIELDS: ClassVar[list[str]] = immutable_fields_for("AuthenticationLog")

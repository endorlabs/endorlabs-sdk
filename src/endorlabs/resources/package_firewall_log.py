"""PackageFirewallLog — thin consumer wrapper over generated V1PackageFirewallLog."""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, Field

from endorlabs.generated.models.package_firewall_log_service import V1PackageFirewallLog

from .consumer.mixin import ConsumerResourceMixin
from .consumer.registry_fields import immutable_fields_for, mutable_fields_for
from .consumer.wire_compat import ConsumerResourceWireMixin


class PackageFirewallLog(
    V1PackageFirewallLog, ConsumerResourceWireMixin, ConsumerResourceMixin
):
    """Consumer facade model for PackageFirewallLog (generated wire shape)."""

    _MUTABLE_FIELDS: ClassVar[list[str]] = mutable_fields_for("PackageFirewallLog")
    _IMMUTABLE_FIELDS: ClassVar[list[str]] = immutable_fields_for("PackageFirewallLog")


class CreatePackageFirewallLogPayload(BaseModel):
    """Create payload for PackageFirewallLog."""

    meta: dict[str, Any] | BaseModel = Field(...)
    spec: dict[str, Any] | BaseModel = Field(...)


def build_create_payload(**kwargs: Any) -> CreatePackageFirewallLogPayload:
    """Build create payload for PackageFirewallLog."""
    from ..utils.create_payload import pass_through_create_payload

    return pass_through_create_payload(
        CreatePackageFirewallLogPayload, kwargs, attr_name="PackageFirewallLog"
    )

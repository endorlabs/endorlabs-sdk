"""VersionUpgrade — thin consumer wrapper over generated V1VersionUpgrade."""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, ClassVar

from endorlabs.generated.models.version_upgrade_service import V1VersionUpgrade
from endorlabs.operations import BaseResourceOperations

from .consumer.mixin import ConsumerResourceMixin
from .consumer.registry_fields import immutable_fields_for, mutable_fields_for
from .consumer.wire_compat import ConsumerResourceWireMixin

if TYPE_CHECKING:
    from ..api_client import APIClient
    from ..core.types import ListParameters


class VersionUpgrade(
    V1VersionUpgrade, ConsumerResourceWireMixin, ConsumerResourceMixin
):
    """Consumer facade model for VersionUpgrade (generated wire shape)."""

    _MUTABLE_FIELDS: ClassVar[list[str]] = mutable_fields_for("VersionUpgrade")
    _IMMUTABLE_FIELDS: ClassVar[list[str]] = immutable_fields_for("VersionUpgrade")


def _get_version_upgrade_ops(
    client: APIClient,
) -> BaseResourceOperations[VersionUpgrade]:
    """Get BaseResourceOperations instance for version upgrades."""
    return BaseResourceOperations(client, "version-upgrades", VersionUpgrade)


def list_version_upgrades(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: ListParameters | None = None,
    max_pages: int | None = None,
    **kwargs: Any,
) -> list[VersionUpgrade] | list[dict[str, Any]]:
    """List version upgrades in the namespace."""
    ops = _get_version_upgrade_ops(client)
    return ops.list(tenant_meta_namespace, list_params, max_pages, **kwargs)


def list_version_upgrades_iter(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: ListParameters | None = None,
    max_pages: int | None = None,
    **kwargs: Any,
) -> Iterator[VersionUpgrade | dict[str, Any]]:
    """Iterate over version upgrades without materializing the full list."""
    ops = _get_version_upgrade_ops(client)
    return ops.list_iter(tenant_meta_namespace, list_params, max_pages, **kwargs)


def get_version_upgrade(
    client: APIClient,
    tenant_meta_namespace: str,
    version_upgrade_uuid: str,
) -> VersionUpgrade:
    """Get a version upgrade by UUID."""
    ops = _get_version_upgrade_ops(client)
    return ops.get(tenant_meta_namespace, version_upgrade_uuid)

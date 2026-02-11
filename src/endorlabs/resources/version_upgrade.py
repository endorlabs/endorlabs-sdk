"""VersionUpgrade resource module for Endor Labs API.

Version upgrade contains information about a possible version upgrade of a
dependency package. List and get only.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, ClassVar, override

from pydantic import Field, field_validator

from ..models.base import (
    BaseMeta,
    BaseResource,
    BaseSpec,
)
from ..operations import BaseResourceOperations
from ..utils.logging_config import get_resource_logger

if TYPE_CHECKING:
    from ..api_client import APIClient
    from ..types import ListParameters

logger = get_resource_logger(__name__)


def _get_version_upgrade_ops(
    client: APIClient,
) -> BaseResourceOperations[VersionUpgrade]:
    """Get BaseResourceOperations instance for version upgrades."""
    return BaseResourceOperations(client, "version-upgrades", VersionUpgrade)


class VersionUpgradeSpec(BaseSpec):
    """Version upgrade specification extending BaseSpec."""

    project_uuid: str | None = Field(
        None,
        description="UUID of the project this version upgrade relates to.",
    )
    name: str | None = Field(
        None,
        description="Name of the project or package version for this record.",
    )
    configuration: dict[str, Any] | None = Field(
        None,
        description="Configuration used in the computation.",
    )
    stats: dict[str, Any] | None = Field(
        None,
        description="Statistics from the computation.",
    )
    upgrade_info: dict[str, Any] | None = Field(
        None,
        description="Information for a single version upgrade.",
    )
    prioritized_upgrades: list[Any] | None = Field(
        None,
        description="Deprecated.",
    )
    all_upgrades: list[Any] | None = Field(
        None,
        description="Deprecated.",
    )
    finding_fixing_upgrades: dict[str, Any] | None = Field(
        None,
        description="Upgrades that fix findings.",
    )


class VersionUpgradeMeta(BaseMeta):
    """Version upgrade metadata extending BaseMeta."""

    pass


class VersionUpgrade(BaseResource):
    """Version Upgrade resource model. List and get only."""

    spec: VersionUpgradeSpec | None = Field(  # pyright: ignore[reportIncompatibleVariableOverride]
        None, description="Version upgrade specification"
    )

    model_config: ClassVar[dict[str, str]] = {"extra": "ignore"}

    @override
    @field_validator("*", mode="before")
    @classmethod
    def detect_schema_drift(cls, v: Any, info: Any) -> Any:
        """Detect and log schema drift in version upgrade responses."""
        if info.field_name == "spec" and isinstance(v, dict):
            known = {
                "project_uuid",
                "name",
                "configuration",
                "stats",
                "upgrade_info",
                "prioritized_upgrades",
                "all_upgrades",
                "finding_fixing_upgrades",
            }
            unknown = set(v.keys()) - known
            if unknown:
                logger.warning(
                    "Schema drift in VersionUpgrade.spec: unknown fields %s",
                    unknown,
                )
        return v


def list_version_upgrades(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: ListParameters | None = None,
    max_pages: int | None = None,
    **kwargs: Any,
) -> list[VersionUpgrade]:
    """List version upgrades in the namespace."""
    ops = _get_version_upgrade_ops(client)
    return ops.list(tenant_meta_namespace, list_params, max_pages, **kwargs)


def list_version_upgrades_iter(
    client: APIClient,
    tenant_meta_namespace: str,
    list_params: ListParameters | None = None,
    max_pages: int | None = None,
    **kwargs: Any,
) -> Iterator[VersionUpgrade]:
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

"""List field masks for compile-dependency-graph pipeline phases."""

from __future__ import annotations

PROJECT_LIST_MASK = "uuid,meta.name,meta.tags,tenant_meta.namespace"

PV_PUBLISHER_LIST_MASK = (
    "uuid,meta.name,spec.project_uuid,spec.ecosystem,tenant_meta.namespace"
)

DEP_METADATA_LIST_MASK = (
    "uuid,"
    "spec.importer_data.project_uuid,"
    "spec.importer_data.package_version_uuid,"
    "spec.dependency_data.package_name,"
    "spec.dependency_data.resolved_version,"
    "spec.dependency_data.unresolved_version,"
    "spec.dependency_data.public,"
    "spec.dependency_data.direct,"
    "spec.dependency_data.scope,"
    "spec.dependency_data.namespace,"
    "spec.dependency_data.project_paths,"
    "spec.dependency_data.declared_licenses,"
    "spec.dependency_data.discovered_licenses,"
    "spec.dependency_data.reachable"
)

"""Field masks for dependency+license export (distinct from estate IR masks)."""

from __future__ import annotations

# MAIN-context DM rows for OSO / compliance inventory.
# Includes dependency_data.package_version_uuid (license join key) plus
# fields the joined CSV/JSONL schema requires — not the thinner estate mask.
DM_LICENSE_EXPORT_MASK = (
    "uuid,"
    "spec.importer_data.project_uuid,"
    "spec.dependency_data.package_version_uuid,"
    "spec.dependency_data.package_name,"
    "spec.dependency_data.resolved_version,"
    "spec.dependency_data.unresolved_version,"
    "spec.dependency_data.public,"
    "spec.dependency_data.direct,"
    "spec.dependency_data.scope,"
    "spec.dependency_data.purl,"
    "spec.dependency_data.ecosystem,"
    "spec.dependency_data.pinned,"
    "spec.dependency_data.internal,"
    "spec.dependency_data.vendored,"
    "spec.dependency_data.last_commit,"
    "spec.dependency_data.reachable"
)

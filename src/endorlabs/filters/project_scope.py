"""Project-scoped MQL filter fragments for counts and lists."""

from __future__ import annotations

from endorlabs.filters.main_context import MAIN_CONTEXT_CLAUSE

PROJECT_UUID_FILTER_FIELD = "spec.project_uuid"


def project_uuid_in_filter(uuids: list[str]) -> str:
    """MQL filter restricting a Project query to known UUIDs."""
    if not uuids:
        return ""
    inner = ", ".join(f'"{u}"' for u in uuids)
    return f"uuid in [{inner}]"


def pv_count_filter(project_uuid: str) -> str:
    """Facade-equivalent filter for one project's main-context PackageVersions."""
    return f'{MAIN_CONTEXT_CLAUSE} and spec.project_uuid=="{project_uuid}"'


def project_scoped_filter(base_filter: str, project_uuid: str) -> str:
    """Append a project UUID clause for per-project list shards."""
    clause = f'{PROJECT_UUID_FILTER_FIELD}=="{project_uuid}"'
    return f"{base_filter} and {clause}" if base_filter else clause


def dm_importer_project_filter(project_uuid: str) -> str:
    """Main-context DependencyMetadata filter scoped to one importer project."""
    from endorlabs.filters.main_context import main_context_filter

    return main_context_filter(f'spec.importer_data.project_uuid=="{project_uuid}"')

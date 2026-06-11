"""Server-side grouped DependencyMetadata list parameter builders."""

from __future__ import annotations

from endorlabs.core.types import ListParameters

from .columns import PACKAGE_NAME_PATH, PACKAGE_VERSION_PATH


def grouped_count_list_parameters(*, page_size: int) -> ListParameters:
    """Grouped DependencyMetadata list for one namespace (never traverse)."""
    return ListParameters(
        traverse=False,
        page_size=page_size,
        group_aggregation_paths=[PACKAGE_NAME_PATH, PACKAGE_VERSION_PATH],
    )


def grouped_count_list_parameters_for_project(
    *,
    page_size: int,
    project_uuid: str,
) -> ListParameters:
    """Grouped list scoped to one project importer (tenant namespace path)."""
    return grouped_count_list_parameters(page_size=page_size).model_copy(
        update={"filter": f'spec.importer_data.project_uuid=="{project_uuid}"'}
    )


def grouped_count_list_parameters_for_importer_package_version(
    *,
    page_size: int,
    package_version_uuid: str,
) -> ListParameters:
    """Grouped list scoped to one importer PackageVersion (tenant namespace path)."""
    return grouped_count_list_parameters(page_size=page_size).model_copy(
        update={
            "filter": (
                f'spec.importer_data.package_version_uuid=="{package_version_uuid}"'
            )
        }
    )


def grouped_count_list_parameters_for_package_name(
    *,
    page_size: int,
    package_name: str,
    main_context: bool = False,
) -> ListParameters:
    """Grouped list for one exact ``package_name``, optionally main-context only."""
    pkg_filter = f'spec.dependency_data.package_name=="{package_name}"'
    if main_context:
        from endorlabs.workflows.estate.filters.main_context import main_context_filter

        filt = main_context_filter(pkg_filter)
    else:
        filt = pkg_filter
    return grouped_count_list_parameters(page_size=page_size).model_copy(
        update={"filter": filt}
    )

"""Query graph join composition for multi-resource fetches.

The platform Query service returns a root Resource Kind plus nested references
in one HTTP call. ``list_parameters`` on each node support filter, mask,
count, group, group_by_time, and pagination — same as facade list.

Project-scoped recipes execute via ``client.Query.Project.*``. For masked
lists, grouped rollups, or deeper nests, use ``QuerySpec`` with
``client.Query.execute`` / ``at_namespace`` or ``create(payload=...)``.

POST URL namespace must match each project's wire namespace
(``tenant_meta.namespace``); ``QueryScope`` carries namespace + optional UUID keys.
"""

from endorlabs.filters import (
    CATEGORY_QUERY_REFS,
    FINDING_CATEGORIES,
    category_filter,
    project_uuid_in_filter,
    pv_count_filter,
    pv_main_context_filter,
)
from endorlabs.filters.query_wire import to_query_filter

from .execute import (
    UUID_BATCH_SIZE,
    QueryExecutor,
    group_projects_by_namespace,
    project_namespace,
    project_uuid,
    query_create,
    query_create_pages,
)
from .normalize import normalize_reference_rows
from .parse import (
    extract_group_response,
    extract_query_objects,
    extract_query_response,
    iter_group_buckets,
    next_page_token,
    parse_group_bucket_counts,
    parse_normalized_query_objects,
    parse_project_multi_reference_counts,
    parse_project_reference_counts,
    parse_project_reference_list_totals,
    reference_count,
    reference_list_total,
    reference_total,
)
from .preflight import preflight_count, query_preflight_count
from .recipes import (
    dm_count_spec,
    estate_findings_list_spec,
    finding_category_count_spec,
    finding_severity_count_spec,
    prf_ecosystem_count_spec,
    prf_findings_list_spec,
    pv_count_spec,
)
from .routing import OutputShape, QueryPlan, recommend
from .scope import QueryScope, query_scopes_from_topology, scopes_from_projects
from .spec import QuerySpec, Reference
from .topology import (
    DiscoveredProject,
    NamespaceGeometry,
    TopologySnapshot,
    discover_topology,
    infer_archetype,
)
from .validate import ValidationResult, validate_sample
from .wire import group_by_time_query_wire, group_query_wire

__all__ = [
    "CATEGORY_QUERY_REFS",
    "FINDING_CATEGORIES",
    "UUID_BATCH_SIZE",
    "DiscoveredProject",
    "NamespaceGeometry",
    "OutputShape",
    "QueryExecutor",
    "QueryPlan",
    "QueryScope",
    "QuerySpec",
    "Reference",
    "TopologySnapshot",
    "ValidationResult",
    "category_filter",
    "discover_topology",
    "dm_count_spec",
    "estate_findings_list_spec",
    "extract_group_response",
    "extract_query_objects",
    "extract_query_response",
    "finding_category_count_spec",
    "finding_severity_count_spec",
    "group_by_time_query_wire",
    "group_projects_by_namespace",
    "group_query_wire",
    "infer_archetype",
    "iter_group_buckets",
    "next_page_token",
    "normalize_reference_rows",
    "parse_group_bucket_counts",
    "parse_normalized_query_objects",
    "parse_project_multi_reference_counts",
    "parse_project_reference_counts",
    "parse_project_reference_list_totals",
    "preflight_count",
    "prf_ecosystem_count_spec",
    "prf_findings_list_spec",
    "project_namespace",
    "project_uuid",
    "project_uuid_in_filter",
    "pv_count_filter",
    "pv_count_spec",
    "pv_main_context_filter",
    "query_create",
    "query_create_pages",
    "query_preflight_count",
    "query_scopes_from_topology",
    "recommend",
    "reference_count",
    "reference_list_total",
    "reference_total",
    "scopes_from_projects",
    "to_query_filter",
    "validate_sample",
]

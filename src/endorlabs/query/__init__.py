"""Query graph join composition for multi-resource fetches.

Released in endorlabs 0.5.0; see docs/changelog.md for 0.5.3+ notes.

The platform Query service is **kind-agnostic**: any root Resource Kind plus
nested references in one HTTP call. Supported ``list_parameters`` per node:
``filter``, ``mask``, ``count``, root ``group`` (limited), pagination, and
``traverse``. Time-bucket aggregation is **not** on Query — use facade
``list_groups`` (e.g. ``FindingLog.list_groups``).

**Default:** ``QuerySpec`` + ``client.Query.execute`` / ``at_namespace`` for
validated join shapes at a wire namespace.

**Estate recipes:** ``client.Query.Project.*`` — validated project-sharded
dashboard patterns (counts, masked finding joins, topology discovery).

POST URL namespace must match the target wire namespace
(``tenant_meta.namespace``); ``QueryScope`` carries namespace + optional keys.
UUID batching via ``keys`` applies when ``QuerySpec.root_has_uuid_keys()`` —
Project only today.
"""

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
    parse_query_root_count,
    reference_count,
    reference_list_total,
    reference_next_page_cursor,
    reference_next_page_token,
    reference_total,
    wire_spec_with_reference_page_cursor,
    wire_spec_with_reference_page_token,
)
from .preflight import preflight_count
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
from .scope import QueryScope, scopes_from_projects
from .spec import QuerySpec, Reference
from .topology import (
    DiscoveredProject,
    NamespaceGeometry,
    TopologySnapshot,
    discover_topology,
    infer_archetype,
    query_scopes_from_topology,
)
from .validate import ValidationResult, validate_sample
from .wire import group_query_wire

__all__ = [
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
    "discover_topology",
    "dm_count_spec",
    "estate_findings_list_spec",
    "extract_group_response",
    "extract_query_objects",
    "extract_query_response",
    "finding_category_count_spec",
    "finding_severity_count_spec",
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
    "parse_query_root_count",
    "preflight_count",
    "prf_ecosystem_count_spec",
    "prf_findings_list_spec",
    "project_namespace",
    "project_uuid",
    "pv_count_spec",
    "query_create",
    "query_create_pages",
    "query_scopes_from_topology",
    "recommend",
    "reference_count",
    "reference_list_total",
    "reference_next_page_cursor",
    "reference_next_page_token",
    "reference_total",
    "scopes_from_projects",
    "validate_sample",
    "wire_spec_with_reference_page_cursor",
    "wire_spec_with_reference_page_token",
]

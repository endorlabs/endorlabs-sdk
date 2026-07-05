"""Query graph join composition for dashboard-style counts.

Prefer recipes such as ``count_pv_by_project`` over hand-built ``query_spec``
dicts. POST URL namespace must match each project's wire namespace
(``tenant_meta.namespace``); the executor groups projects automatically.

For full finding rows or FindingLog trends, use facade list helpers instead.
"""

from .execute import (
    UUID_BATCH_SIZE,
    QueryExecutor,
    group_projects_by_namespace,
    project_namespace,
    project_uuid,
    query_create,
)
from .filters import (
    CATEGORY_QUERY_REFS,
    FINDING_CATEGORIES,
    MAIN_CONTEXT_FILTER,
    category_filter,
    project_uuid_in_filter,
    pv_count_filter,
)
from .parse import (
    parse_project_multi_reference_counts,
    parse_project_reference_counts,
)
from .recipes import (
    count_findings_by_category,
    count_pv_by_project,
    finding_category_count_spec,
    pv_count_spec,
)
from .routing import OutputShape, QueryPlan, recommend
from .spec import QuerySpec, Reference
from .topology import (
    DiscoveredProject,
    NamespaceShard,
    TopologySnapshot,
    discover_topology,
    infer_archetype,
)
from .validate import ValidationResult, validate_sample

__all__ = [
    "CATEGORY_QUERY_REFS",
    "FINDING_CATEGORIES",
    "MAIN_CONTEXT_FILTER",
    "UUID_BATCH_SIZE",
    "DiscoveredProject",
    "NamespaceShard",
    "OutputShape",
    "QueryExecutor",
    "QueryPlan",
    "QuerySpec",
    "Reference",
    "TopologySnapshot",
    "ValidationResult",
    "category_filter",
    "count_findings_by_category",
    "count_pv_by_project",
    "discover_topology",
    "finding_category_count_spec",
    "group_projects_by_namespace",
    "infer_archetype",
    "parse_project_multi_reference_counts",
    "parse_project_reference_counts",
    "project_namespace",
    "project_uuid",
    "project_uuid_in_filter",
    "pv_count_filter",
    "pv_count_spec",
    "query_create",
    "recommend",
    "validate_sample",
]

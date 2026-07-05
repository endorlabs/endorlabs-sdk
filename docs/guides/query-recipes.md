# Query graph join recipes

Dashboard-style **project → child count** joins via `Query.create`. For single-project RCA or full finding rows, use facade `list_by_project` / `count()` instead.

See also [facade-helpers.md](facade-helpers.md) (list/count primitives) and [list-query-performance.md](../contributing/list-query-performance.md).

## When to use

| Goal | Use |
|------|-----|
| PV count per project (many projects) | `endorlabs.query.count_pv_by_project` |
| Finding counts by category (VULN/SECRETS/MALWARE) | `endorlabs.query.count_findings_by_category` |
| One project, full finding rows | `client.Finding.list_by_project` |
| FindingLog trends over time | `FindingLog.list_groups` + `group_by_time` |
| Custom graph join | `QuerySpec` + `QueryExecutor` |

## Namespace rule

`Query.create` must POST to each project's **wire namespace** (`tenant_meta.namespace`), not only the tenant root. The executor groups projects automatically; posting at tenant root when projects live in child namespaces can return **zero counts with no error**.

Resolve `Project` rows first (same as list scoping):

```python
import endorlabs
from endorlabs.query import count_pv_by_project, count_findings_by_category

with endorlabs.Client(tenant="<tenant>") as client:
    projects = client.Project.list(
        traverse=True,
        mask="uuid,meta.name,tenant_meta.namespace",
        max_pages=1,
    )
    pv_counts = count_pv_by_project(client, projects)
    finding_counts = count_findings_by_category(client, projects)
```

## Custom joins

```python
from endorlabs import F
from endorlabs.query import QueryExecutor, QuerySpec, Reference

spec = (
    QuerySpec.root("Project")
    .mask("uuid,meta.name")
    .reference(
        Reference("PackageVersion")
        .connect("uuid", "spec.project_uuid")
        .count(filter=F("context.type") == "CONTEXT_TYPE_MAIN")
    )
)
result = QueryExecutor(client).run(
    spec,
    projects=projects,
    parse_result=lambda r: ...,  # see parse_project_reference_counts
)
```

Low-level escape hatch: `client.Query.create(payload=CreateQueryPayload(...), namespace=leaf_ns)` from [`resources/query.py`](../../src/endorlabs/resources/query.py).

## Facade recipes

`client.Query` exposes the same recipes as `endorlabs.query`:

```python
pv = client.Query.count_pv_by_project(projects)
findings = client.Query.count_findings_by_category(projects)
```

## Topology and routing

```python
from endorlabs.query import (
    OutputShape,
    discover_topology,
    recommend,
    validate_sample,
)

topo = discover_topology(client, "<tenant>", traverse=True, max_pages=5)
plan = recommend(OutputShape.COUNT_BY_PROJECT, topology=topo)
result = validate_sample(client, topo.projects, recipe="pv", sample_size=5)
```

See skill **endor-route-estate-queries** and contract **query-vs-list-semantics**.

## Validation before scale

Compare Query output to facade `count()` on a small sample before running across an entire tenant. Benchmark harness: `.tmp/query_benchmark/run_smoke.py` (imports `endorlabs.query` when available).

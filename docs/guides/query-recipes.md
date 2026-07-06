# Query graph join recipes

**Graph joins** via `Query.create`: one POST returns a root kind plus nested related resources. Project-scoped recipes execute via **`client.Query.Project.*`**; generic joins use **`client.Query.execute`** / **`at_namespace`**. Builders live in **`endorlabs.query`** (`QuerySpec`, `QueryScope`, spec helpers).

For single-project RCA, prefer facade `list_by_project` / `count()` until a join is validated at scale.

See also [facade-helpers.md](facade-helpers.md) and [list-query-performance.md](../contributing/list-query-performance.md).

## When to use

| Goal | Use |
|------|-----|
| PV count per project (many projects) | `client.Query.Project.count_pv` |
| DM count per project (many projects) | `client.Query.Project.count_dm` |
| Finding counts by category (VULN/SECRETS/MALWARE) | `client.Query.Project.count_findings_by_category` |
| Vuln finding counts by severity (CRITICAL/HIGH) | `client.Query.Project.count_findings_by_severity` |
| PRF ecosystem totals | `client.Query.Project.count_prf_by_ecosystem` |
| Masked finding rows (estate / PRF) | `client.Query.Project.collect_estate_findings` / `collect_prf_findings` |
| One project, full finding rows | `client.Finding.list_by_project` |
| Custom graph join (counts, masked lists, nested refs) | `QuerySpec` + `client.Query.execute(scopes=…)` or `create(payload=…)` |
| FindingLog trends over time | `FindingLog.list_groups` today; probe Query `group_by_time` before migrating |
| OSS coordinate lookup | `QueryVulnerability` / `QueryMalware` (oss scope) |

## Namespace rule

`Query.create` must POST to each project's **wire namespace** (`tenant_meta.namespace`), not only the tenant root. `QueryScope` and `Query.Project.discover()` derive leaf namespaces; posting at tenant root when projects live in child namespaces can return **zero counts with no error**.

Resolve `Project` rows first (same as list scoping):

```python
import endorlabs

with endorlabs.Client(tenant="<tenant>") as client:
    topo = client.Query.Project.discover("<tenant>", traverse=True, max_pages=1)
    projects = topo.projects
    pv_counts = client.Query.Project.count_pv(projects)
    finding_counts = client.Query.Project.count_findings_by_category(projects)
    shards = topo.project_shards()  # list-plane parallel grain
    scopes = topo.query_scopes()    # query-plane POST units
```

## Custom joins

Count join with explicit scopes:

```python
from endorlabs import F
from endorlabs.query import QuerySpec, Reference, scopes_from_projects

spec = (
    QuerySpec.root("Project")
    .mask("uuid,meta.name")
    .leaf_scope()
    .reference(
        Reference("PackageVersion")
        .connect("uuid", "spec.project_uuid")
        .count(filter=F("context.type") == "CONTEXT_TYPE_MAIN")
    )
)
counts = client.Query.execute(
    spec,
    scopes_from_projects(projects),
    parse=lambda page: parse_project_reference_counts(page, "PackageVersion"),
)
```

## Topology discovery

Single discovery call returns geometry plus derived views:

- `topology.namespace_geometry` — per-leaf-namespace stats
- `topology.project_shards()` — `ProjectShard` list for facade parallel lists
- `topology.query_scopes()` — `QueryScope` list for Query POST batching

## Validation

Compare Query recipe output to facade `count()` on a sample before estate-scale dashboard use:

```python
client.Query.Project.validate_sample(projects[:5], recipe="pv")
client.Query.Project.validate_sample(projects[:5], recipe="dm")
client.Query.Project.validate_sample(projects[:5], recipe="findings")
```

### Live verification (maintainers)

With a refreshed `.env` token:

```bash
uv run --env-file .env python .tmp/query_workflow_probes/validate_query_facade.py -n <tenant>
uv run --env-file .env python .tmp/query_workflow_probes/probe_workflows.py recipe-parity -n <tenant>
```

Reports land in `.tmp/query_workflow_probes/results/`. See [.tmp/query_workflow_probes/README.md](../../.tmp/query_workflow_probes/README.md).

Integration tests: `tests/integration/client/test_query_recipes.py`.

## Workflow entry points

| Workflow | Module | Query API |
| -------- | ------ | --------- |
| Online dashboard counts | `endorlabs.workflows.estate.online.dashboard` | `fetch_online_dashboard_counts` → `Query.Project.*` |
| Agent dashboard tiles | `endorlabs.workflows.agent_context.dashboard_counts` | `count_pv`, `count_findings_by_category` |
| Estate finding collect | `endorlabs.workflows.estate.collect.findings` | `collect_estate_findings` via `query_collect` |
| Compile graph PV preflight | `endorlabs.workflows.estate.analyze.compile_graph.pipeline` | `preflight_count(plane="query")` |
| Topology bootstrap | `endorlabs.workflows.estate.session` | `Query.Project.discover` |

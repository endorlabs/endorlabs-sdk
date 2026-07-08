# Query graph join recipes

The platform **Query service** (`Query.create`) is a **kind-agnostic graph API**: one POST returns a root resource kind plus optional nested references. Each node accepts the same `list_parameters` as facade list (`filter`, `mask`, `count`, `group`, `group_by_time`, pagination, `traverse`).

**Default mental model:** `QuerySpec` + `client.Query.execute` / `at_namespace` for any root kind.

**`client.Query.Project.*`** is one **validated recipe family** for estate dashboard patterns (per-project counts and masked finding joins). Do not treat it as the full Query API.

For single-project RCA, prefer facade `list_by_project` / `count()` until a join is validated at scale.

See also [facade-helpers.md](facade-helpers.md), [list-query-performance.md](../contributing/list-query-performance.md), and the platform [query-service doc](https://docs.endorlabs.com/developers-api/rest-api/using-the-rest-api/advanced-use-cases/query-service).

## Generic Query (any root kind)

Builders live in **`endorlabs.query`** (`QuerySpec`, `Reference`, `QueryScope`).

### Namespace rule

`Query.create` POSTs to **`/v1/namespaces/{namespace}/queries`**. Use the resource's **wire namespace** (tenant root or leaf). Posting at tenant root when data lives in child namespaces can return **zero counts with no error**.

`QueryScope(namespace=…, keys=())` with empty `keys` skips UUID batching and POSTs the spec as-is. UUID batching via `keys` is only applied when the root kind supports it (`QuerySpec.root_has_uuid_keys()` — **Project only** today).

### Namespace-scoped root (no Project grain)

```python
from endorlabs import F
from endorlabs.query import QuerySpec

spec = (
    QuerySpec.root("AgentHookEvent")
    .count(filter=F("spec.agent_type") == "AGENT_CLAUDE")
)
counts = client.Query.at_namespace(
    spec,
    namespace="<leaf-or-tenant>",
    parse=lambda page: page,  # adapt to response shape
    merge=lambda pages: pages[0] if pages else {},
)
```

Non-Project root with pagination:

```python
spec = QuerySpec.root("Finding").leaf_scope().filter("context.type==CONTEXT_TYPE_MAIN")
rows = client.Query.at_namespace(
    spec,
    namespace="<leaf-namespace>",
    parse=lambda page: page.get("list", {}).get("objects", []),
    merge=lambda pages: [row for page in pages for row in page],
)
```

See `tests/unit/query/test_query_facade.py` (`test_query_at_namespace_merges_pages`).

### Multi-scope execute (Project-root joins)

```python
from endorlabs import F
from endorlabs.query import QuerySpec, Reference, QueryScope, scopes_from_projects
from endorlabs.query.parse import parse_project_reference_counts

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

Explicit scopes without project discovery:

```python
client.Query.execute(
    spec,
    [QueryScope(namespace="<leaf-namespace>")],
    parse=...,
)
```

## Validated estate recipes (`Query.Project`)

Project-sharded dashboard patterns validated via `validate_sample` before estate-scale use.

| Goal | Use |
|------|-----|
| PV count per project (many projects) | `client.Query.Project.count_pv` |
| DM count per project (many projects) | `client.Query.Project.count_dm` |
| Finding counts by category (VULN/SECRETS/MALWARE) | `client.Query.Project.count_findings_by_category` |
| Vuln finding counts by severity (CRITICAL/HIGH) | `client.Query.Project.count_findings_by_severity` |
| PRF ecosystem totals | `client.Query.Project.count_prf_by_ecosystem` |
| Masked finding rows (estate / PRF) | `client.Query.Project.collect_estate_findings` / `collect_prf_findings` |
| Topology + shard derivation | `client.Query.Project.discover` |

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

### Validation

```python
client.Query.Project.validate_sample(projects[:5], recipe="pv")
client.Query.Project.validate_sample(projects[:5], recipe="dm")
client.Query.Project.validate_sample(projects[:5], recipe="findings")
```

### Live verification (maintainers)

```bash
uv run --env-file .env python .tmp/query_workflow_probes/validate_query_facade.py -n <tenant>
uv run --env-file .env python .tmp/query_workflow_probes/probe_workflows.py recipe-parity -n <tenant>
```

Reports: `.tmp/query_workflow_probes/results/`. Integration tests: `tests/integration/client/test_query_recipes.py`.

## Resource counterexamples

When Query reduces round-trips vs when facade/sharding stays correct. Status: **Validated** (parity-checked), **Probe** (experimental), **N/A** (Query not applicable).

### Project

| Ask | Facade today | Query | Why Query can win | Keep facade | Status |
|-----|--------------|-------|-------------------|-------------|--------|
| Discover project inventory | `Project.list(traverse=True)` | N/A — Project is the discovery grain | Query does not replace root inventory list | Always for UUID/name/namespace discovery | N/A |
| Duplicate / CLI-vs-cloud audit | `Project.list` + row fields | No join benefit | Needs full Project spec | Skills `endor-duplicate-projects`, `endor-cli-vs-cloud-projects` | N/A |
| Dashboard PV/DM/finding counts per project | `*.count` × N (× categories) | `Query.Project.count_*` | O(projects×refs) → O(leaf_namespaces) POSTs | Single-repo RCA: facade acceptable | **Validated** |
| Masked finding export (estate) | `parallel_map_shards` + `Finding.list_by_project` | `Query.Project.collect_estate_findings` | One join POST per leaf NS vs N shards | Full models; checkpoint via `list_for_shards` | **Probe** |
| Topology / shard derivation | `Project.list` | `Query.Project.discover` | Same discovery cost; adds shard views | When only project rows needed | Same cost |

**Teach:** `Project.list` for discovery is correct; replacing child-resource count loops with `Query.Project.*` after discovery is where Query wins.

### Finding

| Ask | Facade | Query | Why | Keep facade | Status |
|-----|--------|-------|-----|-------------|--------|
| One project RCA rows | `Finding.list_by_project` | Overkill | Single namespace | `endor-retrieve-scan-results` | N/A |
| Category counts × many projects | `Finding.count` × 3 × N | `Query.Project.count_findings_by_category` | Collapses HTTP round-trips | MALWARE may diverge — validate | **Validated** |
| Severity counts × many projects | `Finding.count` × levels × N | `Query.Project.count_findings_by_severity` | Same join economics | Single project | **Validated** |
| PRF ecosystem totals | `Finding.count` × 4 × N | `Query.Project.count_prf_by_ecosystem` | Multi-ref single POST | Per-finding RCA | **Probe** |
| Tenant-wide totals (no per-project grain) | `Finding.count(traverse=True)` | `Query.at_namespace(QuerySpec.root("Finding").count(...))` | Scoped leaf NS vs silent-zero at wrong NS | Traverse semantics differ | **Probe** |
| New vs resolved trends | `FindingLog.list_groups` + `group_by_time` | Root `FindingLog` + `group_by_time` | Fewer round-trips if backend plan is good | Large tenants: backend-bound | **Probe** |

### ScanResult

| Ask | Facade today | Query candidate | Why Query might win | Keep facade | Status |
|-----|--------------|-----------------|---------------------|-------------|--------|
| Latest scan metadata per project | `ScanResult.list_by_project(limit=1)` × N | `Project` → `ScanResult` list ref, newest sort, `page_size=1` | N → 1 POST per leaf NS (`uuid` ↔ `meta.parent_uuid`) | Single-project scan RCA; `get_logs` | **Probe** (`scan-latest-join`) |
| Scan count in time window per project | `ScanResult.count` × N | `Project` → `ScanResult` count ref + date filter | Round-trip collapse | Full scan rows / log search | **Probe** |
| Tenant-wide scan error search | parallel `list_by_project` shards | Unlikely | Needs log body search | `--project-uuid` for interactive RCA | N/A |

### PackageVersion

| Ask | Facade | Query | Why | Keep facade | Status |
|-----|--------|-------|-----|-------------|--------|
| PV count per project (estate) | `PackageVersion.count` × N | `Query.Project.count_pv` | Primary validated Query win | Single project hydration | **Validated** |
| Full PV rows / call graph | `PackageVersion.list_by_project` | Join list only if validated | Row export needs pagination + resume | `callgraph/export`, estate pull | Facade |
| Estate pull PV sweep | `PackageVersion.list(traverse=True)` | Query count for preflight only | Count ≠ materialization | Full JSONL export | Count: validated; rows: facade |
| Namespace consumer graph | Bounded `PackageVersion.list` | Not Query | Coordinate graph | `endor-namespace-relationship-map` | N/A |

**Teach:** Query is for counts and masked joins, not replacing full PV materialization on estate pull.

### DependencyMetadata

| Ask | Facade | Query | Why | Keep facade | Status |
|-----|--------|-------|-----|-------------|--------|
| Importer DM count per project | `DependencyMetadata.count` × N | `Query.Project.count_dm` | 342→1 calls on smarsh sample | Main-context importer totals | **Validated** |
| Version cardinality (distinct versions per package) | `DependencyMetadata.list_groups` per leaf NS | Root `DM` + `group` (different shape) | Per-project count ≠ version buckets | `OutputShape.DM_VERSION_CARDINALITY` | **Semantic mismatch** |
| Estate DM row collect | `list_for_shards` | No shipped collect recipe | Rows + checkpointing | Estate pull | Facade |

**Teach:** DM is the clearest case where Query count join ≠ `list_groups` rollup — do not migrate version-cardinality workflows to `count_dm`.

## Other APIs (not `Query.create`)

| Goal | Use |
|------|-----|
| One project, full finding rows | `client.Finding.list_by_project` |
| FindingLog trends over time | `FindingLog.list_groups` today; probe Query `group_by_time` |
| OSS coordinate lookup | `QueryVulnerability` / `QueryMalware` (oss scope) |

## Topology discovery

`discover_topology` / `Query.Project.discover` returns:

- `topology.namespace_geometry` — per-leaf-namespace stats
- `topology.project_shards()` — `ProjectShard` list for facade parallel lists
- `topology.query_scopes()` — `QueryScope` list for Query POST batching

## Workflow entry points

| Workflow | Module | Query API |
| -------- | ------ | --------- |
| Online dashboard counts | `endorlabs.workflows.estate.online.dashboard` | `fetch_online_dashboard_counts` → `Query.Project.*` |
| Agent dashboard tiles | `endorlabs.workflows.agent_context.dashboard_counts` | `count_pv`, `count_findings_by_category` |
| Estate finding collect | `endorlabs.workflows.estate.collect.findings` | `collect_estate_findings` via `query_collect` |
| Compile graph PV preflight | `endorlabs.workflows.estate.analyze.compile_graph.pipeline` | `preflight_count(plane="query")` |
| Topology bootstrap | `endorlabs.workflows.estate.session` | `Query.Project.discover` |

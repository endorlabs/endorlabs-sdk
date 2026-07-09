# Query graph join recipes

The platform **Query service** (`Query.create`) is a **kind-agnostic graph API**: one POST returns a root resource kind plus optional nested references. Each node supports a **subset** of facade `list_parameters` — see [Supported patterns](#supported-patterns) below.

**Default mental model:** `QuerySpec` + `client.Query.execute` / `at_namespace` for validated join shapes.

**`client.Query.Project.*`** is one **validated recipe family** for estate dashboard patterns (per-project counts and masked finding joins). Do not treat it as the full Query API.

For single-project RCA, prefer facade `list_by_project` / `count()`. For time-bucket aggregation (FindingLog trends, log rollups), use facade **`list_groups`** — not Query.

See also [facade-helpers.md](facade-helpers.md), [contracts.md](../contracts.md), [list-query-performance.md](../contributing/list-query-performance.md), and the platform [query-service doc](https://docs.endorlabs.com/developers-api/rest-api/using-the-rest-api/advanced-use-cases/query-service).

## Supported patterns

| Mode | Query.create | Facade |
|------|--------------|--------|
| `filter`, `mask`, `traverse`, pagination | Root + nested refs | `list()` |
| `count` | Root + nested refs | `count()` |
| `group` (field paths) | Namespace-scoped **root** only | `list_groups()` |
| `group_by_time` | **Unsupported** | `list_groups()` + `ListParameters(group_by_time=True)` |
| `search_query` | Depth 0 only; no joins | `list()` |
| Graph joins | `references[]` | N/A |

**Common traps:**

- **Wrong namespace** → count=0 with no error. POST at the resource wire namespace.
- **Nested list mask** → mask parent structs (e.g. `spec.environment`), not deep sub-fields.
- **`count_dm` ≠ version buckets** → use root `DependencyMetadata` + `group` or facade `list_groups`, not `Query.Project.count_dm`.

**Time buckets example** (facade — not Query):

```python
from endorlabs.core.types import ListParameters
from endorlabs.workflows.logs.group_by_time import group_by_time_counts

buckets = group_by_time_counts(
    client.FindingLog.list_groups,
    namespace="<tenant>",
    filter="spec.operation==OPERATION_CREATE and ...",
    traverse=True,
    interval="week",
)
```

Normative agent contract: shipped `query-vs-list-semantics.md` (wheel / `.endorlabs-context/sdk/contracts/`).

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
    .filter(F("spec.agent_type") == "AGENT_CLAUDE")
    .list_parameters(count=True)
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

Integration tests: `tests/integration/client/test_query_recipes.py`.

### Collect pagination and root counts

`collect_estate_findings` / `collect_prf_findings` paginate nested reference lists automatically. The first page comes from the root Project join; follow-up pages re-POST with `meta.references[ref].list.response.next_page_token` (or `next_page_id` when token is absent) on the matching reference `list_parameters`.

```python
rows = client.Query.Project.collect_estate_findings(
    projects,
    mask="uuid,spec.level,spec.finding_categories",
    max_root_pages=None,        # cap root Project pages (rare)
    max_reference_pages=None,   # cap nested ref continuation pages
)
```

For namespace-scoped Finding totals (no per-project grain), POST at the **wire namespace** and read the count from `parse_query_root_count(result)` — not `extract_query_objects`:

```python
from endorlabs.query import QuerySpec, parse_query_root_count, query_create

spec = QuerySpec.root("Finding").list_parameters(
    count=True,
    filter=estate_filter,
    traverse=True,  # tenant-wide total; omit or False under-counts child namespaces
)
result = query_create(client.Query, namespace=leaf_ns, name="count", query_spec=spec.to_wire())
total = parse_query_root_count(result)
```

**Trap:** `Query.create` at tenant root with `traverse=False` returns only that path segment (often far below `Finding.count(traverse=True)`).

## Resource counterexamples

When Query reduces round-trips vs when facade/sharding stays correct. Status: **Validated**, **Validate on sample**, **Facade only**, **N/A**.

### Project

| Ask | Facade today | Query | Why Query can win | Keep facade | Status |
|-----|--------------|-------|-------------------|-------------|--------|
| Discover project inventory | `Project.list(traverse=True)` | N/A — Project is the discovery grain | Query does not replace root inventory list | Always for UUID/name/namespace discovery | N/A |
| Duplicate / CLI-vs-cloud audit | `Project.list` + row fields | No join benefit | Needs full Project spec | Skills `endor-duplicate-projects`, `endor-cli-vs-cloud-projects` | N/A |
| Dashboard PV/DM/finding counts per project | `*.count` × N (× categories) | `Query.Project.count_*` | O(projects×refs) → O(leaf_namespaces) POSTs | Single-repo RCA: facade acceptable | **Validated** |
| Masked finding export (estate) | `parallel_map_shards` + `Finding.list_by_project` | `Query.Project.collect_estate_findings` | One join POST per leaf NS vs N shards; ref pagination for full export | Full models; checkpoint via `list_for_shards` | **Validated** |
| Topology / shard derivation | `Project.list` | `Query.Project.discover` | Same discovery cost; adds shard views | When only project rows needed | Same cost |

**Teach:** `Project.list` for discovery is correct; replacing child-resource count loops with `Query.Project.*` after discovery is where Query wins.

### Finding

| Ask | Facade | Query | Why | Keep facade | Status |
|-----|--------|-------|-----|-------------|--------|
| One project RCA rows | `Finding.list_by_project` | Overkill | Single namespace | `endor-retrieve-scan-results` | N/A |
| Category counts × many projects | `Finding.count` × 3 × N | `Query.Project.count_findings_by_category` | Collapses HTTP round-trips | MALWARE may diverge — validate | **Validated** |
| Severity counts × many projects | `Finding.count` × levels × N | `Query.Project.count_findings_by_severity` | Same join economics | Single project | **Validated** |
| PRF ecosystem totals | `Finding.count` × 4 × N | `Query.Project.count_prf_by_ecosystem` | Multi-ref single POST | Per-finding RCA | Validate on sample |
| Tenant-wide totals (no per-project grain) | `Finding.count(traverse=True)` | `Query.at_namespace` + `Finding` root count + `parse_query_root_count` | Scoped leaf NS vs under-count at tenant root without traverse | Traverse semantics differ | **Validated** |
| New vs resolved trends | `FindingLog.list_groups` + `group_by_time` | — | Query does not support `group_by_time` | Chart skill; facade at scale | **Facade only** |

### ScanResult

| Ask | Facade today | Query candidate | Why Query might win | Keep facade | Status |
|-----|--------------|-----------------|---------------------|-------------|--------|
| Latest scan metadata per project | `ScanResult.list_by_project(limit=1)` × N | Project → ScanResult list; mask **`spec.environment`** (parent struct, not sub-fields) | N → 1 POST per leaf NS | Single-project RCA; `get_logs` | **Validated** |
| Scan count in time window per project | `ScanResult.count` × N | Project → ScanResult count ref + date filter | Round-trip collapse | Full scan rows / log search | Validate on sample |
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
| Importer DM count per project | `DependencyMetadata.count` × N | `Query.Project.count_dm` | Collapses HTTP round-trips | Main-context importer totals | **Validated** |
| Version cardinality (distinct versions per package) | `DependencyMetadata.list_groups` per leaf NS | Root `DependencyMetadata` + `group` (same filter) | Bucket parity validated | Per-project `count_dm` ≠ version buckets | **Validated** |
| Estate DM row collect | `list_for_shards` | No shipped collect recipe | Rows + checkpointing | Estate pull | Facade |

**Teach:** DM is the clearest case where Query count join ≠ `list_groups` rollup — do not migrate version-cardinality workflows to `count_dm`.

## Other APIs (not `Query.create`)

| Goal | Use |
|------|-----|
| One project, full finding rows | `client.Finding.list_by_project` |
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
| FindingLog trends | `endorlabs.workflows.findings.finding_log_trends` | Facade `FindingLog.list_groups` |

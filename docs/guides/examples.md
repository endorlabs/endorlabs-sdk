# SDK examples and skill walkthrough

Learning path for trying the SDK against a real tenant. **Skills are the source of
truth** for full workflows; this guide adds minimal API snippets and points to the
shipped playbooks.

**Prerequisites:** credentials in env (see [README.md](../../README.md#configuration)),
`ENDOR_NAMESPACE` set, and `uv run --env-file .env` when using a local `.env` file.

**Skill locations:**

- Wheel: `endorlabs.agent_knowledge_index_path()` → `skills/<id>/SKILL.md`
- Materialized: `.endorlabs-context/sdk/skills/<id>/SKILL.md` after `endorlabs.init()`

## 1. Verify auth and tenant

```python
import endorlabs

client = endorlabs.Client()
print(client.whoami())
```

Environment variables and `.env` layout: [README — Configuration](../../README.md#configuration) and [contracts.md](../contracts.md).

### Browser auth

Browser auth via `APIClient(auth_method='browser-auth')`: validates an existing token first, then falls back to interactive login. Session tokens are reused until a `401` response.

```bash
uv run python -c "from endorlabs.api_client import APIClient; c=APIClient(auth_method='browser-auth'); print(c.token)"
```

To persist a bearer token in `.env` after browser SSO:

```bash
uv run endor-auth refresh --method sso -n <tenant>
uv run --env-file .env endor-auth check --tenant <tenant>
```

See skill **endor-auth-setup** (shipped under `skills/endor-auth-setup/SKILL.md` after `init()`).

### SSO / login investigations

Use the **endor-troubleshoot-authlog** skill (see [AGENTS.md — Skills and handoffs](../../AGENTS.md#skills-and-handoffs)).

## 2. Discovery — namespaces and projects

Minimal list/traverse patterns (expanded in [Quick start](../../README.md#quick-start)):

```python
import os
import endorlabs

client = endorlabs.Client(tenant=os.getenv("ENDOR_NAMESPACE", "tenant.namespace"))

namespaces = client.Namespace.list(traverse=True)
print(f"Namespaces: {len(namespaces)}")

projects = client.Project.search_by_name(
    "github.com/org/repo",
    traverse=True,
    max_pages=2,
)
for project in projects[:5]:
    print(project.meta.name if project.meta else project.uuid)
```

For repo URL discovery, prefer **`Project.search_by_name`** over unfiltered `Project.list(traverse=True)` — see [facade-helpers.md](facade-helpers.md). Tenant-wide namespace inventory still uses `Namespace.list(traverse=True)` (shown above).

**Skill:** [endor-retrieve-scan-results](../../agent-knowledge/skills/endor-retrieve-scan-results/SKILL.md) —
Project → ScanResult → Finding hierarchy, namespace scoping, and filters.

**Guide:** [retrieving-scan-results.md](retrieving-scan-results.md) · **Accessors:** [facade-helpers.md](facade-helpers.md) · [resource-routes.md](../generated-reference/resource-routes.md)

## 3. Filters with `F()`

```python
from endorlabs import F

critical = client.Finding.list(
    filter=F("spec.level") == "FINDING_LEVEL_CRITICAL",
    traverse=True,
    max_pages=1,
)
print(f"Critical findings (first page): {len(critical)}")
```

Use `F().matches(...)` on string fields and `F().contains(...)` on array fields only.
See [contracts/list-parameters.md](../../agent-knowledge/contracts/list-parameters.md).

## 4. Discovery, cross-resource joins, streaming

```python
from endorlabs import F

# Discovery by repo URL substring (bounded list; pick row or disambiguate)
projects = client.Project.search_by_name(
    "github.com/endorlabs/endorlabs-sdk",
    traverse=True,
    max_pages=2,
)
project = projects[0] if projects else None

scan_results = client.ScanResult.list_by_project(
    project,
    sort_by="meta.create_time",
    desc=True,
    max_pages=1,
)
findings = client.Finding.list_by_project(project, max_pages=1)

count = 0
for row in client.Finding.list_iter(traverse=True, max_pages=1):
    count += 1
print(f"Findings streamed: {count}")
```

**Skill:** [endor-retrieve-scan-results](../../agent-knowledge/skills/endor-retrieve-scan-results/SKILL.md)

## 5. Field masks (sparse list rows)

```python
rows = client.Project.list(
    mask="meta.name,uuid",
    traverse=True,
    max_pages=1,
    page_size=10,
)
for row in rows:
    assert isinstance(row, dict)
    print(row.get("meta", {}).get("name"), row.get("uuid"))
```

See [consumer-ux-list-update.md](consumer-ux-list-update.md).

## 6. Scan troubleshooting — logs and diffs

When scan results look wrong or regressed, use the troubleshooting workflow (writes
artifacts under `.endorlabs-context/workspace/runs/troubleshooting-scans/`):

```bash
uv run --env-file .env python -m endorlabs.workflows.troubleshooting_scans.fetch_scan_results \
  --tenant YOUR_TENANT \
  --project-name "https://github.com/org/repo.git" \
  --limit 10
```

**Skill:** [endor-troubleshooting-scans](../../agent-knowledge/skills/endor-troubleshooting-scans/SKILL.md)

## 7. Call graph (optional)

For symbol search and path extraction from decoded call graph artifacts:

```bash
uv run --env-file .env endor-callgraph-search --help
```

For a full project context bundle including call graph export:

```bash
uv run --env-file .env endor-agent-context --help
```

**Skill:** [endor-fetch-and-search-call-graph](../../agent-knowledge/skills/endor-fetch-and-search-call-graph/SKILL.md)

## 8. Agent bootstrap (optional)

SDK API usage does not require local context files. For cwd-relative skills and
offline OpenAPI/user docs:

```python
import endorlabs

status = endorlabs.init()  # materializes sdk/ by default
# Full mirror: endorlabs.init(include_openapi=True, include_user_docs=True)
# Requires [docs] extra for user-docs sync
```

```bash
uv run endor-context --sync-openapi
```

See [AGENTS.md — Bootstrap](../../AGENTS.md#bootstrap)
and [CONTRIBUTORS.md — Optional: sync external docs](../../CONTRIBUTORS.md#optional-sync-external-docs).

## Suggested order for a first tenant session

| Step | Action | Skill |
| ---- | ------ | ----- |
| 1 | `whoami()` + list projects | retrieve-scan-results |
| 2 | Latest ScanResult + findings for one project | retrieve-scan-results |
| 3 | If scans look wrong | troubleshooting-scans |
| 4 | If reachability/graph questions | fetch-and-search-call-graph |
| 5 | Materialize skills for IDE/agents | `endorlabs.init()` / endor-context |

After **endor-troubleshooting-scans**, use scan UUIDs from the pairs/diff artifacts with
**endor-retrieve-scan-results** (`Finding.list_for_context(scan)`) for finding-level drill-down.
For policy, reachability, or dependency lineage questions, follow the **Related skills**
tables in each skill's `SKILL.md`.

Production automation should call `endorlabs.Client` and workflow modules directly;
skills are playbooks, not runtime dependencies.

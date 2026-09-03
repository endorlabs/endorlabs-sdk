# Estate workflows

Unified estate-scale workflows under `endorlabs.workflows.estate`: **pull** once into a workspace, **analyze** from disk, **summarize** IR.

## Mental model

```text
endor-estate pull    → data/*.jsonl + collect_manifest.json
endor-estate analyze → intermediate-representation/* + viz/estate_dashboard.html
endor-estate summarize → stdout / JSON summary
```

Workspace root: `.endorlabs/tasks/<namespace-slug>-<YYYY-MM-DD>/estate/`

See [workspace.md](workspace.md), [risk-cardinality.md](risk-cardinality.md), [compile-graph.md](compile-graph.md), [remediation.md](remediation.md), and [patch-fix-report.md](patch-fix-report.md). Upgrading from legacy CLI names: [changelog.md](../changelog.md) (**0.7.1 → Breaking**).

**Agents:** `endor-estate` namespace bulk pull/analyze is a maintainer/human workflow (`agent_visible: false` in `MANIFEST.json`). Do not run `endor-estate pull` unless the user explicitly requests namespace-wide bulk collect.

## CLI quick start

```bash
uv run --env-file .env endor-estate pull --namespace tenant.example.child

uv run endor-estate pull --namespace example-tenant.child --resume --workspace .endorlabs/tasks/example_tenant_child-2026-06-08/estate

uv run endor-estate analyze --namespace example-tenant.child --workspace .endorlabs/tasks/example_tenant_child-2026-06-08/estate

uv run endor-estate summarize --namespace example-tenant.child --workspace .endorlabs/tasks/example_tenant_child-2026-06-08/estate
```

## Library API

```python
import endorlabs
from endorlabs.workflows.estate import (
    analyze_workspace,
    collect_workspace,
    workspace_dir_for,
)

client = endorlabs.Client(tenant="tenant")
workspace = workspace_dir_for("tenant.example.child")
collect_workspace(client, namespace="tenant.example.child", workspace=workspace)
analyze_workspace(workspace, namespace="tenant.example.child")
```

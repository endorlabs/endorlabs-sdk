# Endor Labs SDK

[Python CI](https://github.com/endorlabs/endorlabs-sdk/actions/workflows/ci-pr-main.yml)

Type-safe, resource-oriented Python client for the Endor Labs REST API. List, get, create, update, and delete resources (projects, findings, scan results, policies, namespaces, and [the rest of the registry-backed resource set](docs/generated-reference/resources.md)) with consistent patterns for filtering, pagination, namespace traversal, and IDE-friendly typed facades.

- **Python:** 3.12+
- **API spec:** [OpenAPI (Swagger)](https://api.endorlabs.com/download/openapiv2.swagger.json)
- **Platform docs:** [docs.endorlabs.com](https://docs.endorlabs.com/)

## Start here


| You want to...                                   | Go to                                     |
| ------------------------------------------------ | ----------------------------------------- |
| **Use the SDK** in your project (API scripts, CI) | Keep reading (Installation → Quick start) — **no `init()` required** |
| **Bootstrap an AI agent** (skills, local OpenAPI) | [SDK-only vs agent bootstrap](#sdk-only-vs-agent-bootstrap) and [AGENTS.md](AGENTS.md) |
| **Try the interactive SDK demo**                 | [Demo CLI](#demo-cli)                     |
| **Contribute** to this repo                      | [CONTRIBUTORS.md](CONTRIBUTORS.md)        |


## Installation

```bash
pip install endorlabs-sdk
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv add endorlabs-sdk
```

From the repository (editable):

```bash
git clone https://github.com/endorlabs/endorlabs-sdk.git
cd endorlabs-sdk
uv sync
# or: pip install -e .
```

Verify: `uv run python -c "import endorlabs; print(endorlabs.__version__)"`

### Optional extras

| Extra | Install | Enables |
| ----- | ------- | ------- |
| `context` | `pip install 'endorlabs-sdk[context]'` | `endorlabs.init()` — materializes shipped agent bundle + optional platform OpenAPI/user docs |
| `tabular` | `pip install 'endorlabs-sdk[tabular]'` | `endorlabs.utils.tabular` DataFrame / Parquet export (pandas + pyarrow) |

CSV export from `utils.tabular` works without extras. In this repo: `uv sync --extra context --extra tabular`.

## Configuration

The SDK uses **environment variables** only (no config file loading). Precedence: constructor arguments → environment variables → built-in defaults.


| Variable                       | Purpose                                                                                        |
| ------------------------------ | ---------------------------------------------------------------------------------------------- |
| `ENDOR_API`                    | API base URL (default: `https://api.endorlabs.com`)                                            |
| `ENDOR_API_CREDENTIALS_KEY`    | API key                                                                                        |
| `ENDOR_API_CREDENTIALS_SECRET` | API secret                                                                                     |
| `ENDOR_TOKEN`                  | Bearer token. Takes precedence when present and is validated before any interactive auth flow. |
| `ENDOR_NAMESPACE`              | Default tenant namespace (e.g. `tenant.namespace`)                                             |
| `ENDOR_LOG_LEVEL`              | Optional: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`                                      |
| `ENDOR_MAX_RETRIES`            | Optional: retry count (default: 5)                                                             |


Canonical naming is `tenant.namespace.child`; do not use UUIDs in namespace paths.

Example `.env` for local runs:

```bash
ENDOR_API_CREDENTIALS_KEY=your-api-key
ENDOR_API_CREDENTIALS_SECRET=your-api-secret
ENDOR_NAMESPACE=your-tenant.namespace
ENDOR_LOG_LEVEL=INFO
```

If you use agent bootstrap (below), add `.endorlabs-context/` to your project `.gitignore` — it holds downloaded platform docs and workflow run outputs, not application source.

### Programmatic browser auth

The SDK supports browser auth mode with `APIClient`.
The SDK validates a provided token first, and if it is invalid (or missing), it falls
back to interactive browser authentication.
After a browser token is validated, it is treated as a session token: repeated
`client.token` reads do not reopen the browser. Browser reauthentication is
triggered by real `401 Unauthorized` responses.

```bash
uv run python -c "from endorlabs.api_client import APIClient; c=APIClient(auth_method='browser-auth'); print(c.token)"
```

You can also provide a candidate token and let the SDK validate/fallback automatically:

```bash
uv run python -c "from endorlabs.api_client import APIClient; c=APIClient(auth_method='browser-auth', token='your-token'); print(c.token)"
```

For shell portability (PowerShell + POSIX), prefer `uv run python -c ...` as shown above
instead of shell-specific `eval` export workflows.

### Authentication troubleshooting (Agent Skill)

For **AuthenticationLog**, **AuthorizationPolicy**, and optional **AuditLog**
correlation during SSO or tenant login investigations, use the **troubleshoot-authlog**
skill:

- **Repo clone:** [agent-skills/troubleshoot-authlog/SKILL.md](agent-skills/troubleshoot-authlog/SKILL.md)
- **Installed wheel:** `endorlabs.agent_manifest()` → `skills/troubleshoot-authlog/SKILL.md`, or materialized `.endorlabs-context/sdk/skills/troubleshoot-authlog/SKILL.md` after `init()`

Cursor users may also read `.cursor/skills/troubleshoot-authlog/SKILL.md` when mirrors are synced.

## SDK-only vs agent bootstrap

Most pip consumers use **SDK-only mode**: install, set credentials, call `endorlabs.Client(...)`.
You do **not** need `endorlabs.init()` or a `.endorlabs-context/` directory for API access,
workflows, or the demo CLI.

Use **agent bootstrap** when an AI agent (or file-based tooling) needs a cwd-relative tree of
skills, contracts, OpenAPI, and user docs.


| Mode | When | What you do |
| ---- | ---- | ----------- |
| **SDK-only** | Scripts, apps, CI, typed API usage | `pip install endorlabs-sdk` + env vars → `Client(...)` |
| **Wheel-only agent nav** | Agent reads the shipped bundle from site-packages | `endorlabs.agent_index_path()` / `agent_manifest()` — no disk materialization |
| **Local agent bootstrap** | Cursor/Claude file reads, offline platform docs | `pip install 'endorlabs-sdk[context]'` → `endorlabs.init()` |


After `init()`, the layout is:

```
.endorlabs-context/
  context.json
  sdk/              # INDEX.md, MANIFEST.json, skills/, contracts/
  platform/         # openapi/, user-docs/ (optional downloads)
  workspace/        # workflow run outputs (gitignore recommended)
```

Repo architecture and maintainer regions: [AGENTS.md](AGENTS.md#repository-layout).

### Wheel-only navigation (no `init()`)

The agent bundle ships inside the wheel. Read it from site-packages without writing cwd artifacts:

```python
import endorlabs

print(endorlabs.agent_index_path())  # .../site-packages/endorlabs/agent_bundle/INDEX.md
manifest = endorlabs.agent_manifest()
```

### Minimal bootstrap (SDK bundle only)

Materialize skills and contracts under the project cwd; skip platform downloads (no auth required):

```python
import endorlabs

status = endorlabs.init(include_openapi=False, include_user_docs=False)
print(status.agent_index_path)  # .endorlabs-context/sdk/INDEX.md
```

### Full bootstrap (bundle + platform context)

```bash
pip install 'endorlabs-sdk[context]'
```

```python
import endorlabs

status = endorlabs.init()
print(status.agent_index_path)   # .endorlabs-context/sdk/INDEX.md
print(status.openapi_path)       # .endorlabs-context/platform/openapi/openapiv2.swagger.json
print(status.user_docs_path)     # .endorlabs-context/platform/user-docs/
```

Read `status.agent_index_path`, then `MANIFEST.json`, then task skills under
`.endorlabs-context/sdk/skills/`. Run outputs belong under `.endorlabs-context/workspace/`.
Agent rules and footguns: [AGENTS.md](AGENTS.md).

## Demo CLI

The SDK includes an interactive demo wizard that walks through common API patterns and
practical workflows in a real tenant context.

Run the demo:

```bash
uv run endor-demo
uv run endor-demo --verbose
```

Demo prerequisites:

- `ENDOR_NAMESPACE` must be set (or entered in the wizard)
- Auth supports: `browser-auth`, `sso`, `google`, `github`, `gitlab`, `azureadv2`
- Credentials/tokens use the same environment variables documented in [Configuration](#configuration)

What the wizard demonstrates:

- Namespace and project discovery (`list`, `lookup`, `traverse`)
- Filter composition with `F()`
- Streaming iteration with `list_iter`
- Cross-resource querying and summaries
- Optional scan log retrieval
- Optional call graph retrieval and preview

The demo is intended as a guided learning surface; production automation should call SDK APIs directly.

## Quick start

**SDK-only mode** — the examples below do not call `endorlabs.init()`. See
[SDK-only vs agent bootstrap](#sdk-only-vs-agent-bootstrap) when wiring an AI agent.

Entry point is `endorlabs.Client` with a default tenant namespace. Each resource is exposed as a facade: `client.Namespace`, `client.Project`, `client.Finding`, `client.ScanResult`, etc., with `.list()`, `.get()`, `.create()`, `.update()`, and `.delete()`.

### Basic usage

```python
import os
import endorlabs

client = endorlabs.Client(
    tenant=os.getenv("ENDOR_NAMESPACE", "your-tenant.namespace"),
    logging_level="ERROR",   # passed to APIClient via **client_kwargs
    # Optional: pass auth_method for interactive login flows.
    # When ENDOR_TOKEN is set, it is validated and used first.
)

# List namespaces (tenant-wide with traverse=True)
namespaces = client.Namespace.list(traverse=True)
for ns in namespaces:
    print(ns.meta.name)

# List projects
projects = client.Project.list(traverse=True)
for p in projects:
    print(p.meta.name)

# Filter and limit pages
projects = client.Project.list(
    filter="meta.name==https://github.com/endorlabs/endorlabs-sdk.git",
    max_pages=1,
)

# Get by UUID
if projects:
    project = client.Project.get(projects[0].uuid)
    print(project.meta.name)
    print(project.spec.platform_source)
    # Resources are Pydantic models
    print(project.model_dump_json(indent=2))
```

### Requesting a scan and waiting for results

```python
# Resolve project by repo URL (like: endorctl api list -r Project --traverse --filter "meta.name contains <url>")
repo_url = "https://github.com/tgowan-endor/BenchmarkJava.git"
project = client.Project.lookup(
    traverse=True,
    filter=f"meta.name=={repo_url}",
)

# Request full rescan (flat kwargs; see resource update_mask / mutable fields)
client.Project.update(project, scan_state="SCAN_STATE_REQUEST_FULL_RESCAN")

# Poll until scan is idle
client.wait_until(
    lambda: (
        (p := client.Project.get(project))
        and p.processing_status.scan_state == "SCAN_STATE_IDLE"
    ),
    timeout=300,
)

# List latest scan results for the project (parent-scoped list)
scans = client.ScanResult.list(
    parent=project,
    max_pages=1,
    sort_by="meta.create_time",
    desc=True,
)
print(f"Project: {project.meta.name}; scan results: {len(scans)}")
if scans:
    print(scans[0].model_dump_json(indent=2))
```

### Alternative: transport-only APIClient

If you need direct transport access for custom endpoints, use `APIClient`
directly (the canonical resource interface is still `endorlabs.Client`):

```python
from endorlabs import APIClient

client = APIClient()
response = client.get("v1/namespaces/tenant.namespace/projects")
projects_payload = response.json()
```

Use this path when you need raw HTTP control; for typed models and consistent
namespace handling, prefer `endorlabs.Client`.

## API surface

### Resources

Registry resources are exposed as typed facades on `Client` using **PascalCase**
names that match `endorctl api … --resource <Kind>` (e.g. `Project`, `QueryVulnerability`).
The canonical current list is generated in
[docs/generated-reference/resources.md](docs/generated-reference/resources.md).

`ScanLogs` is an SDK-only custom facade for retrieving scan log messages; it is
not an endorctl `--resource` kind (use `ScanLogRequest` for CRUD on log requests).

Each facade exposes only the operations that resource supports. Hover over any facade or method in your IDE to see its docstring, parameters, and concrete return types.

### Operations

- **List:** `client.<ResourceKind>.list(traverse=..., filter=..., mask=..., sort_by=..., desc=..., max_pages=..., page_size=..., parent=...)`. Use `traverse=True` for tenant-wide listing; use `parent=resource` for child resources (e.g. `ScanResult.list(parent=project)`). A **non-empty** `mask` returns **`dict`** rows per item; omit `mask` for full Pydantic models.
- **List (parallel):** `client.<resource>.list(traverse=True, concurrent=True, max_workers=10)` queries each namespace in parallel.
- **List (streaming):** `client.<resource>.list_iter(...)` yields one item per row; with a non-empty `mask`, each yielded value may be a **`dict`** instead of a model.
- **Get / Create / Update / Delete:** `client.<resource>.get(id_or_resource)`, `.create(payload=... or **kwargs)`, `.update(resource, update_mask=... or field kwargs)`, `.delete(id_or_resource, ignore_missing=True)`.
- **Lookup:** `client.<resource>.lookup(...)` returns exactly one **model** or raises `NotFoundError` / `AmbiguousError`; it raises **`ValueError`** if a non-empty list `mask` is set (use `list()` for masked dict rows).
- **Tag / Untag:** `client.<resource>.tag(resource, tags=["reviewed"])`, `.untag(resource, keys=["deprecated"])` manage `meta.tags` on resources that support it.
- **Identity kwargs:** `client.Project.lookup(name="my-project")` — identity kwargs are mapped to filter clauses automatically (e.g. `name` → `meta.name`). Hover over a facade to see its available identity kwargs.
- **Filtering:** Use raw strings (`filter="meta.name==foo"`) or the `F()` builder: `from endorlabs import F; client.Finding.list(filter=F("spec.level") == "FINDING_LEVEL_CRITICAL")`.
- **Polling:** `client.wait_until(predicate, timeout=..., poll_interval_max=...)` for readiness loops.
- **Identity:** `client.whoami()` returns the authenticated identity name, or `None`.

Details: [docs/generated-reference/resources.md](docs/generated-reference/resources.md), [docs/contracts.md](docs/contracts.md).

## How it works

Two runtime layers, one effective registry:

- **Transport** (`api_client.py`): HTTP, auth, retries. Nothing else.
- **Resource facades** (`client_surface.py`): Typed wrappers built automatically from the effective registry. `client.Project`, `client.Finding`, etc. all use the same `ResourceRuntimeFacade` pattern (`ResourceFacade` remains as a compatibility alias).
- **Adding a resource** usually means updating model-sync inputs plus a Pydantic model, then regenerating the effective registry. No hand-written HTTP.

Details: [AGENTS.md — Architecture](AGENTS.md#architecture).

## Errors

Raised exceptions are exported from top-level `endorlabs` (implemented in `endorlabs.core.exceptions`): `EndorAPIError` (base), `UnauthorizedError`, `NotFoundError`, `PermissionDeniedError`, `ValidationError`, `ConflictError`, `RateLimitError`, `ServerError`, `AmbiguousError`, and `map_status_code_to_exception()`. All carry `status_code`, `operation`, `resource_uuid`, and `namespace` where applicable. See [docs/contracts.md](docs/contracts.md) (Errors section).

## Development

```bash
uv run pytest                            # all tests
uv run pytest -m integration -v          # integration only (needs credentials)
uv run --env-file .env pytest            # if using .env file
uv run ruff check . && uv run ruff format --check .  # lint
uv run pyright                           # type check
```

Runtime compatibility is Python 3.12+, and CI validation is currently pinned to
Python 3.13 for deterministic lint/type/test gates.

Contributors: [CONTRIBUTORS.md](CONTRIBUTORS.md). AI agents: [AGENTS.md](AGENTS.md). Doc index: [docs/README.md](docs/README.md).

## Scripts and automation

Maintainer tooling lives in `devtools/` (model sync, stub generation, debug helpers). Agent-facing tenant workflows ship in `endorlabs.workflows` (see [AGENTS.md](AGENTS.md)). **In this repo:** SAST rule management (import, export, delete, configure) lives at `agent-skills/custom-sast-rules/scripts/sast_rule_manager.py` (`.cursor/skills` is the Cursor runtime mirror). The interactive demo entrypoint is implemented in `src/endorlabs/_demo/demo_cli.py` and exposed via `endor-demo`. Optional: materialize agent context with `endorlabs.init()` (see [SDK-only vs agent bootstrap](#sdk-only-vs-agent-bootstrap)); maintainers use [devtools/README.md](devtools/README.md) and [CONTRIBUTORS.md](CONTRIBUTORS.md).

## License

MIT. See [LICENSE](LICENSE).

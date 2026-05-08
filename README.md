# Endor Labs SDK

[Python CI](https://github.com/Endor-Solutions-Architecture/endorlabs-sdk/actions/workflows/ci-pr-main.yml)

Type-safe, resource-oriented Python client for the Endor Labs REST API. List, get, create, update, and delete resources (projects, findings, scan results, policies, namespaces, and [the rest of the registry-backed resource set](docs/generated-reference/resources.md)) with consistent patterns for filtering, pagination, namespace traversal, and IDE-friendly typed facades.

- **Python:** 3.12+
- **API spec:** [OpenAPI (Swagger)](https://api.endorlabs.com/download/openapiv2.swagger.json)
- **Platform docs:** [docs.endorlabs.com](https://docs.endorlabs.com/)

## Start here


| You want to...                                   | Go to                                     |
| ------------------------------------------------ | ----------------------------------------- |
| **Use the SDK** in your project                  | Keep reading (Installation → Quick start) |
| **Try the interactive SDK demo**                 | [Demo CLI](#demo-cli)                     |
| **Contribute** to this repo                      | [CONTRIBUTORS.md](CONTRIBUTORS.md)        |
| **Work with an AI agent** (Cursor, Claude, etc.) | [AGENTS.md](AGENTS.md)                    |


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
git clone https://github.com/Endor-Solutions-Architecture/endorlabs-sdk.git
cd endorlabs-sdk
uv sync
# or: pip install -e .
```

Verify: `uv run python -c "import endorlabs; print(endorlabs.__version__)"`

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

For `**AuthenticationLog**`, `**AuthorizationPolicy**`, and optional `**AuditLog**`
correlation during SSO / tenant login investigations, use the **troubleshoot-authlog**
Agent Skill: [skills-src/troubleshoot-authlog/SKILL.md](skills-src/troubleshoot-authlog/SKILL.md)
(`.cursor/skills` is the mirrored runtime path used by Cursor).

Run from the repo root:

```bash
uv run --env-file .env python skills-src/troubleshoot-authlog/troubleshoot_authlog.py --help
```

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
    filter="meta.name==https://github.com/Endor-Solutions-Architecture/endorlabs-sdk.git",
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

- **List:** `client.<ResourceKind>.list(traverse=..., filter=..., mask=..., sort_by=..., desc=..., max_pages=..., page_size=..., parent=...)`. Use `traverse=True` for tenant-wide listing; use `parent=resource` for child resources (e.g. `ScanResult.list(parent=project)`).
- **List (parallel):** `client.<resource>.list(traverse=True, concurrent=True, max_workers=10)` queries each namespace in parallel.
- **List (streaming):** `client.<resource>.list_iter(...)` yields resources one at a time for memory-efficient pagination.
- **Get / Create / Update / Delete:** `client.<resource>.get(id_or_resource)`, `.create(payload=... or **kwargs)`, `.update(resource, update_mask=... or field kwargs)`, `.delete(id_or_resource, ignore_missing=True)`.
- **Lookup:** `client.<resource>.lookup(...)` returns exactly one result or raises `NotFoundError` / `AmbiguousError`.
- **Tag / Untag:** `client.<resource>.tag(resource, tags=["reviewed"])`, `.untag(resource, keys=["deprecated"])` manage `meta.tags` on resources that support it.
- **Identity kwargs:** `client.Project.lookup(name="my-project")` — identity kwargs are mapped to filter clauses automatically (e.g. `name` → `meta.name`). Hover over a facade to see its available identity kwargs.
- **Filtering:** Use raw strings (`filter="meta.name==foo"`) or the `F()` builder: `from endorlabs import F; client.Finding.list(filter=F("spec.level") == "FINDING_LEVEL_CRITICAL")`.
- **Polling:** `client.wait_until(predicate, timeout=..., poll_interval_max=...)` for readiness loops.
- **Identity:** `client.whoami()` returns the authenticated identity name, or `None`.

Details: [docs/generated-reference/resources.md](docs/generated-reference/resources.md), [docs/contracts.md](docs/contracts.md).

## How it works

Two layers, one registry:

- **Transport** (`api_client.py`): HTTP, auth, retries. Nothing else.
- **Resource facades** (`client_surface.py`): Typed wrappers built automatically from a registry. `client.Project`, `client.Finding`, etc. are all the same `ResourceFacade` pattern.
- **Adding a resource** = one registry entry + a Pydantic model. No hand-written HTTP.

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

Maintainer tooling lives in `devtools/` (model sync, stub generation, debug helpers). Agent-facing tenant workflows ship in `endorlabs.workflows` (see [AGENTS.md](AGENTS.md)). For SAST rule management (import, export, delete, configure), see `skills-src/custom-sast-rules/scripts/sast_rule_manager.py` (`.cursor/skills` is the mirror path in Cursor runtime). The interactive demo entrypoint is implemented in `src/endorlabs/_demo/demo_cli.py` and exposed via `endor-demo`. Optional: sync OpenAPI and user docs into `.endorlabs-context/` via [devtools/README.md](devtools/README.md) and [CONTRIBUTORS.md](CONTRIBUTORS.md).

## License

MIT. See [LICENSE](LICENSE).

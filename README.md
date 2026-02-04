# Endor Cockpit

[![Python CI](https://github.com/endor-solutions-architecture/endor-cockpit/actions/workflows/ci.yml/badge.svg)](https://github.com/endor-solutions-architecture/endor-cockpit/actions/workflows/ci.yml)

Python SDK for the Endor Labs security platform. It provides a type-safe, resource-oriented client for the Endor Labs REST API: list, get, create, update, and delete resources (projects, findings, scan results, policies, namespaces, and others) with consistent patterns for filtering, pagination, and namespace traversal.

- **Python:** 3.13
- **API spec:** [OpenAPI (Swagger)](https://api.endorlabs.com/download/openapiv2.swagger.json)
- **Platform docs:** [docs.endorlabs.com](https://docs.endorlabs.com/)

## Installation

```bash
pip install endor-cockpit
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv add endor-cockpit
```

From the repository (editable):

```bash
git clone https://github.com/endor-solutions-architecture/endor-cockpit.git
cd endor-cockpit
uv sync
# or: pip install -e .
```

## Configuration

The SDK uses **environment variables** only (no config file loading). Precedence: constructor arguments → environment variables → built-in defaults.

| Variable | Purpose |
|----------|---------|
| `ENDOR_API` | API base URL (default: `https://api.endorlabs.com`) |
| `ENDOR_API_CREDENTIALS_KEY` | API key |
| `ENDOR_API_CREDENTIALS_SECRET` | API secret |
| `ENDOR_NAMESPACE` | Default tenant namespace (e.g. `tenant.namespace`) |
| `ENDOR_LOG_LEVEL` | Optional: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `ENDOR_MAX_RETRIES` | Optional: retry count (default: 5) |

Canonical naming is `tenant.namespace.child`; do not use UUIDs in namespace paths.

Example `.env` for local runs:

```bash
ENDOR_API_CREDENTIALS_KEY=your-api-key
ENDOR_API_CREDENTIALS_SECRET=your-api-secret
ENDOR_NAMESPACE=your-tenant.namespace
ENDOR_LOG_LEVEL=INFO
```

## Quick start

Entry point is `endorlabs.Client` with a default tenant namespace. Each resource is exposed as a facade: `client.namespace`, `client.project`, `client.finding`, `client.scan_result`, etc., with `.list()`, `.get()`, `.create()`, `.update()`, and `.delete()`.

### Basic usage

```python
import os
import endorlabs

client = endorlabs.Client(
    tenant=os.getenv("ENDOR_NAMESPACE", "your-tenant.namespace"),
    logging_level="ERROR",
    auth_method="api-key",
)

# List namespaces (tenant-wide with traverse=True)
namespaces = client.namespace.list(traverse=True)
for ns in namespaces:
    print(ns.meta.name)

# List projects
projects = client.project.list(traverse=True)
for p in projects:
    print(p.meta.name)

# Filter and limit pages
projects = client.project.list(
    filter="meta.name==https://github.com/Endor-Solutions-Architecture/endor-cockpit.git",
    max_pages=1,
)

# Get by UUID
if projects:
    project = client.project.get(projects[0].uuid)
    print(project.meta.name)
    print(project.spec.platform_source)
    # Resources are Pydantic models
    print(project.model_dump_json(indent=2))
```

### Requesting a scan and waiting for results

```python
# Resolve project by repo URL (like: endorctl api list -r Project --traverse --filter "meta.name contains <url>")
repo_url = "https://github.com/tgowan-endor/BenchmarkJava.git"
project = client.project.lookup(
    traverse=True,
    filter=f"meta.name=={repo_url}",
)

# Request full rescan (flat kwargs; see resource update_mask / mutable fields)
client.project.update(project, scan_state="SCAN_STATE_REQUEST_FULL_RESCAN")

# Poll until scan is idle
client.wait_until(
    lambda: (
        (p := client.project.get(project))
        and p.processing_status.scan_state == "SCAN_STATE_IDLE"
    ),
    timeout=300,
)

# List latest scan results for the project (parent-scoped list)
scans = client.scan_result.list(
    parent=project,
    max_pages=1,
    sort_by="meta.create_time",
    desc=True,
)
print(f"Project: {project.meta.name}; scan results: {len(scans)}")
if scans:
    print(scans[0].model_dump_json(indent=2))
```

### Alternative: transport + module-level API

If you prefer the raw transport and explicit resource modules:

```python
from endorlabs import APIClient
from endorlabs.resources import namespace, project

client = APIClient()
namespaces = namespace.list_namespaces(client, "tenant.namespace")
projects = project.list_projects(client, "tenant.namespace", traverse=True)
```

Same behavior; use when you need only the HTTP client or module-level calls.

## API surface

- **Resources:** All registry resources are exposed on `Client`: `namespace`, `project`, `repository`, `repository_version`, `finding`, `scan_result`, `scan_profile`, `policy`, `authorization_policy`, `installation`, `package_version`, `package_license`, `dependency_metadata`, `metric`, `linter_result`, `api_key`, `audit_log`, `finding_log`, `semgrep_rule`. Some resources have no update or delete (e.g. `api_key`, `audit_log`, `finding_log`); those raise `NotImplementedError` for those operations.
- **List:** `client.<resource>.list(traverse=..., filter=..., mask=..., sort_by=..., desc=..., max_pages=..., page_size=..., parent=...)`. Use `traverse=True` for tenant-wide listing; use `parent=resource` for child resources (e.g. `scan_result.list(parent=project)`).
- **Get / Create / Update / Delete:** `client.<resource>.get(id_or_resource)`, `.create(payload)`, `.update(resource, update_mask=... or field kwargs)`, `.delete(id_or_resource)`. For update, either pass `update_mask` (comma-separated field paths) or use the facade's accepted field kwargs (e.g. `scan_state` on project).
- **Lookup:** `client.project.lookup(traverse=..., filter=...)` returns a single project or raises.
- **Polling:** `client.wait_until(predicate, timeout=..., interval=...)` for readiness loops.

Details: [docs/reference/resources.md](docs/reference/resources.md), [docs/conventions.md](docs/conventions.md).

## Errors

Raised exceptions live in `endorlabs.exceptions`: `EndorAPIError` (base), `UnauthorizedError`, `NotFoundError`, `PermissionDeniedError`, `ValidationError`, `ConflictError`, `RateLimitError`, `ServerError`, `AmbiguousError`, and `map_status_code_to_exception()`. All carry `status_code`, `operation`, `resource_uuid`, and `namespace` where applicable. See [docs/conventions.md](docs/conventions.md) (Errors section).

## Development

```bash
# Tests
uv run pytest

# With env from file
uv run --env-file .env pytest

# Integration tests (require valid credentials)
uv run pytest -m integration -v

# Lint and format
uv run ruff check .
uv run ruff format .

# Type check
uv run pyright
```

Contributors: see [CONTRIBUTORS.md](CONTRIBUTORS.md). AI/agent integration: [AGENTS.md](AGENTS.md). Doc index: [docs/README.md](docs/README.md).

## Scripts and automation

Pre-built scripts under `maneuvers/` (e.g. notification policies, exception policies, tag findings) can be run with `uv run python maneuvers/<script>.py --help`. Optional: sync OpenAPI and user docs into `external_docs/` via [scripts/README.md](scripts/README.md) and [CONTRIBUTORS.md](CONTRIBUTORS.md).

## License

MIT. See [LICENSE](LICENSE).

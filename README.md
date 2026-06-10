# Endor Labs SDK

[Python CI](https://github.com/endorlabs/endorlabs-sdk/actions/workflows/ci-pr-main.yml)

Type-safe, resource-oriented Python client for the Endor Labs REST API. List, get, create, update, and delete resources (projects, findings, scan results, policies, namespaces, and [the rest of the registry-backed resource set](docs/generated-reference/resources.md)) with consistent patterns for filtering, pagination, namespace traversal, and IDE-friendly typed facades.

- **Python:** 3.12+ (CI gates run on 3.13 — see [CONTRIBUTORS.md](CONTRIBUTORS.md))
- **API spec:** [OpenAPI (Swagger)](https://api.endorlabs.com/download/openapiv2.swagger.json)
- **Platform docs:** [docs.endorlabs.com](https://docs.endorlabs.com/)

## Start here


| You want to…                                        | Go to                                                                                          |
| --------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| **Use the SDK** (API scripts, CI)                   | Installation → [Quick start](#quick-start) — **no `init()` required**                          |
| **Bootstrap an AI agent** (skills, offline OpenAPI) | [AGENTS.md](AGENTS.md)                                                                         |
| **Try the SDK on a real tenant**                    | [Try it with skills](#try-it-with-skills) → [docs/guides/examples.md](docs/guides/examples.md) |
| **SDK contracts and deep reference**                | [docs/README.md](docs/README.md)                                                               |
| **Contribute to this repo**                         | [CONTRIBUTORS.md](CONTRIBUTORS.md)                                                             |


## Installation

```bash
pip install endorlabs
```

Or with [uv](https://github.com/astral-sh/uv):

```bash
uv add endorlabs
```

From the repository (editable):

```bash
git clone https://github.com/endorlabs/endorlabs-sdk.git
cd endorlabs-sdk
uv sync
# or: pip install -e .
```

Verify: `uv run python -c "import endorlabs; print(endorlabs.__version__)"`

Source repo: [`endorlabs/endorlabs-sdk`](https://github.com/endorlabs/endorlabs-sdk) — PyPI distribution name is **`endorlabs`** (`import endorlabs`).

### Optional extras


| Extra     | Install                                | Enables                                                                               |
| --------- | -------------------------------------- | ------------------------------------------------------------------------------------- |
| `docs`    | `pip install 'endorlabs[docs]'`    | User-docs sync (`include_user_docs=True`); OpenAPI download works on the base install |
| `analytics` | `pip install 'endorlabs[analytics]'` | `endorlabs.utils.tabular` DataFrame / Parquet export (pandas + pyarrow); estate graph metrics and community detection (igraph + leidenalg) |


CSV export from `utils.tabular` works without extras. In this repo: `uv sync --extra docs --extra analytics`.

## Configuration

The SDK uses **environment variables** only (no config file loading). Precedence: constructor arguments → environment variables → built-in defaults.


| Variable                       | Purpose                                                   |
| ------------------------------ | --------------------------------------------------------- |
| `ENDOR_API`                    | API base URL (default: `https://api.endorlabs.com`)       |
| `ENDOR_API_CREDENTIALS_KEY`    | API key                                                   |
| `ENDOR_API_CREDENTIALS_SECRET` | API secret                                                |
| `ENDOR_TOKEN`                  | Bearer token; validated first when set                    |
| `ENDOR_NAMESPACE`              | Default tenant namespace (e.g. `tenant.namespace`)        |
| `ENDOR_LOG_LEVEL`              | Optional: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `ENDOR_MAX_RETRIES`            | Optional: retry count (default: 5)                        |


Canonical naming is `tenant.namespace.child`; do not use UUIDs in namespace paths. Full semantics: [docs/contracts.md](docs/contracts.md).

Example `.env` for local runs:

```bash
ENDOR_API_CREDENTIALS_KEY=your-api-key
ENDOR_API_CREDENTIALS_SECRET=your-api-secret
ENDOR_NAMESPACE=your-tenant.namespace
ENDOR_LOG_LEVEL=INFO
```

If you use agent bootstrap, add `.endorlabs-context/` to your project `.gitignore` (manifest + workflow outputs). The SDK logs a warning for agents to ask the user; it does not edit `.gitignore` automatically. Print the line: `uv run endor-context --print-gitignore-line`.

### Programmatic browser auth

Browser auth via `APIClient(auth_method='browser-auth')`: validates an existing token first, then falls back to interactive login. Session tokens are reused until a `401` response.

```bash
uv run python -c "from endorlabs.api_client import APIClient; c=APIClient(auth_method='browser-auth'); print(c.token)"
```

For shell portability (PowerShell + POSIX), prefer `uv run python -c ...` over shell-specific export workflows.

SSO/login investigations: **endor-troubleshoot-authlog** skill under `agent-knowledge/skills/` (see [AGENTS.md — Skills](AGENTS.md#agent-skills-on-demand-workflows)).

## Surfaces


| Surface                                 | When                                                                                                                                                        |
| --------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `endorlabs.Client`                      | Default typed API access                                                                                                                                    |
| `endorlabs.APIClient`                   | Raw HTTP transport                                                                                                                                          |
| `endorlabs.init()` / `endor-context`    | Materialize agent knowledge; opt-in OpenAPI/user-docs — see [AGENTS.md](AGENTS.md)                                                                          |
| `endorlabs.workflows` + console scripts | Tenant workflows — inventory in shipped `MANIFEST.json` (`workflows`, `workflows/entries.json`) and `[project.scripts]` in [pyproject.toml](pyproject.toml) |


Naming: authoring `agent-knowledge/` → shipped `src/endorlabs/agent_knowledge/` → runtime `.endorlabs-context/sdk/`. Details: [AGENTS.md — Naming](AGENTS.md#naming).

## Try it with skills

After [Configuration](#configuration), use shipped agent skills as guided walkthroughs (no separate demo CLI):

1. [endor-retrieve-scan-results](agent-knowledge/skills/endor-retrieve-scan-results/SKILL.md) — project → ScanResult → Finding
2. [endor-troubleshooting-scans](agent-knowledge/skills/endor-troubleshooting-scans/SKILL.md) — scan pipeline, logs, aggregate diffs
3. [endor-fetch-and-search-call-graph](agent-knowledge/skills/endor-fetch-and-search-call-graph/SKILL.md) — optional call graph search

Session order and snippets: [docs/guides/examples.md](docs/guides/examples.md). Skills ship in the wheel (`endorlabs.agent_knowledge_index_path()`) or `.endorlabs-context/sdk/skills/` after `init()`.

## Quick start

**SDK-only** — examples below do not call `endorlabs.init()`. For agent bootstrap, see [AGENTS.md](AGENTS.md).

Entry point: `endorlabs.Client(tenant=...)`. Resources are **PascalCase** facades (`client.Project`, `client.Finding`, …) matching `endorctl api … --resource <Kind>`.

### Basic usage

```python
import os
import endorlabs

client = endorlabs.Client(
    tenant=os.getenv("ENDOR_NAMESPACE", "your-tenant.namespace"),
    logging_level="ERROR",
)

namespaces = client.Namespace.list(traverse=True)
projects = client.Project.list(traverse=True, max_pages=1)

if projects:
    project = client.Project.get(projects[0].uuid)
    print(project.meta.name)
```

**List field masks:** a non-empty `mask=` on `list()` returns `list[dict]` wire JSON rows, not
full Pydantic models. Omit `mask` when you need typed resources end-to-end. See
[docs/guides/consumer-ux-list-update.md](docs/guides/consumer-ux-list-update.md).

**Large estate lists:** for project-scoped resources at scale, use
[`endorlabs.tools.list_sharding`](src/endorlabs/tools/list_sharding.py) or the `endor-estate`
workflow CLI (see [docs/contributing/list-query-performance.md](docs/contributing/list-query-performance.md)).

### Requesting a scan and waiting for results

```python
repo_url = "https://github.com/tgowan-endor/BenchmarkJava.git"
project = client.Project.lookup(traverse=True, filter=f"meta.name=={repo_url}")

client.Project.update(project, scan_state="SCAN_STATE_REQUEST_FULL_RESCAN")

client.wait_until(
    lambda: (
        (p := client.Project.get(project))
        and p.processing_status.scan_state == "SCAN_STATE_IDLE"
    ),
    timeout=300,
)

scans = client.ScanResult.list(
    parent=project,
    max_pages=1,
    sort_by="meta.create_time",
    desc=True,
)
```

More patterns (filters, `F()`, masks, namespace scoping): [docs/guides/consumer-ux-list-update.md](docs/guides/consumer-ux-list-update.md), [docs/guides/retrieving-scan-results.md](docs/guides/retrieving-scan-results.md).

### Transport-only `APIClient`

```python
from endorlabs import APIClient

client = APIClient()
response = client.get("v1/namespaces/tenant.namespace/projects")
```

Prefer `endorlabs.Client` for typed models and namespace handling.

## API surface

- **Resource inventory:** [docs/generated-reference/resources.md](docs/generated-reference/resources.md) (generated; do not hand-maintain lists in README)
- **Operations, list parameters, masks, errors:** [docs/contracts.md](docs/contracts.md)
- **Consumer UX (filter vs mask, flat kwargs):** [docs/guides/consumer-ux-list-update.md](docs/guides/consumer-ux-list-update.md)
- **Custom facade:** `ScanLogs` (log lines) — not an endorctl `--resource` kind; use `ScanLogRequest` for CRUD on log requests

## Architecture

Transport (`api_client.py`) + registry-driven facades (`client_surface.py`, `facade.py`). Contributor detail: [docs/contributing/architecture.md](docs/contributing/architecture.md). Agent/repo map: [AGENTS.md](AGENTS.md).

## Errors

Exported from top-level `endorlabs` (`endorlabs.core.exceptions`): `EndorAPIError`, `UnauthorizedError`, `NotFoundError`, `PermissionDeniedError`, `ValidationError`, `ConflictError`, `RateLimitError`, `ServerError`, `AmbiguousError`, `MethodNotSupportedError`, and `map_status_code_to_exception()`. See [docs/contracts.md](docs/contracts.md) (Errors).

## Development

Lint, test, and contributor workflow: [CONTRIBUTORS.md](CONTRIBUTORS.md). Maintainer automation: [devtools/README.md](devtools/README.md). Doc index: [docs/README.md](docs/README.md). AI agents: [AGENTS.md](AGENTS.md).

## License

MIT. See [LICENSE](LICENSE).

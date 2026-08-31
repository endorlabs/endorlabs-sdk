---
id: endor-namespace-scoping
tags: [list, traverse, namespace]
summary: >-
  Resolve Project first; pass namespace=project.namespace on project-scoped lists.
---

# Namespace scoping

## OSS catalog plane

`Vulnerability`, `Malware`, `QueryVulnerability`, and `QueryMalware` use registry
`scope="oss"`. List/get and catalog query creates hit `/v1/namespaces/oss/…`
regardless of `Client(tenant=…)`. OpenAPI paths for these kinds are already
parameterized as `{tenant_meta.namespace}`; the SDK **forces** the literal `oss`
plane via `resource_scope_overrides.json`.

**Customer investigations prefer the tenant plane:** use **`MalwareExposure`** /
**`MalwareExposureQuery`**, Finding malware category
(`FINDING_CATEGORY_MALWARE`), and **`PackageFirewallLog`** under the customer
namespace. Treat `QueryMalware` / `Malware` as **catalog identity**
(“is this coordinate malware?”) — secondary for blast-radius / exposure asks.
Do not delete or ignore-tenant→oss callers; soft-deprecate means docs/skills
preference, not removing the facades.

## Resource-scoped operations

When you have a resource instance (from `list(traverse=True)`), pass the resource object to
`get`, `update`, or `delete` so namespace is resolved from the resource.

- **List/filter scoped to a resource:** Use **`namespace=resource.namespace`** or
  `list(parent=resource)` where supported.
- **Discovery:** Root namespace + `traverse=True` (concurrent namespace fan-out is
  the SDK default; pass `concurrent=False` to opt out).

## Project-scoped lists (MUST)

`Client(tenant=<client_tenant>)` with default `traverse=False` lists **only that path segment**—not
child namespaces where projects usually live. A filter such as `spec.project_uuid==…` does **not**
widen the path.

**Resolve the `Project` row first**, then pass **`namespace=project.namespace`** on downstream lists
(`Finding`, `ScanResult`, `PackageVersion`, `DependencyMetadata`, …). Otherwise you often get
**empty results with no error** (the SDK may emit a `UserWarning` on empty tenant-root lists for
these resources).

**Do not confuse:** `Client(tenant=…)` (auth) with **`--namespace` scope** on bulk workflows (`endor-estate pull -n …`) — namespace scope may be tenant root **or** a child namespace; see [docs/estate/README.md](https://github.com/endorlabs/endorlabs-sdk/blob/main/docs/estate/README.md). Do not run bulk pull unless the user explicitly requests it.

Alternatives:

- `Client(tenant=project.namespace)` for the rest of the session, or
- `traverse=True` only when deliberately searching tenant-wide (higher cost).
  Pass `concurrent=False` for a single sequential traverse query.

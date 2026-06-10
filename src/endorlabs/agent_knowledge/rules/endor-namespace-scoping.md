---
id: endor-namespace-scoping
tags:
- list
- traverse
- namespace
summary: Resolve Project first; pass namespace=project.namespace on project-scoped
  lists.
---

# Namespace scoping

## OSS catalog plane

`Vulnerability`, `Malware`, `QueryVulnerability`, and `QueryMalware` use registry `scope="oss"`.
List/get and catalog query creates hit `/v1/namespaces/oss/…` regardless of `Client(tenant=…)`.

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

**Do not confuse:** `Client(tenant=…)` (auth) with **`--namespace` scope** on bulk workflows (`endor-estate pull -n …`) — namespace scope may be tenant root **or** a child namespace; see [docs/estate/README.md](../../docs/estate/README.md). Do not run bulk pull unless the user explicitly requests it.

Alternatives:

- `Client(tenant=project.namespace)` for the rest of the session, or
- `traverse=True` only when deliberately searching tenant-wide (higher cost).
  Pass `concurrent=False` for a single sequential traverse query.

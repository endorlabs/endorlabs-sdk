---
id: namespace-scoping
tags:
- list
- traverse
- namespace
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
- **Discovery:** Root namespace + `traverse=True` (e.g. `Project.list(traverse=True)`).

## Project-scoped lists (MUST)

`Client(tenant=<estate_root>)` with default `traverse=False` lists **only that path segment**—not
child namespaces where projects usually live. A filter such as `spec.project_uuid==…` does **not**
widen the path.

**Resolve the `Project` row first**, then pass **`namespace=project.namespace`** on downstream lists
(`Finding`, `ScanResult`, `PackageVersion`, `DependencyMetadata`, …). Otherwise you often get
**empty results with no error**.

Alternatives:

- `Client(tenant=project.namespace)` for the rest of the session, or
- `traverse=True` only when deliberately searching tenant-wide (higher cost).

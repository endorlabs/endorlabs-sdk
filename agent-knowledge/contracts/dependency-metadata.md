---
id: dependency-metadata
tags: [analytics, dependency-metadata]
---

# DependencyMetadata

## Wire path (tenant namespace)

`DependencyMetadata` list and group operations use the **customer tenant namespace** on the wire
(`validate_namespace`), not the literal `oss` catalog plane.

Estate analytics workflows:

- Discover namespaces once with `Namespace.list(traverse=True)`.
- Run grouped/counting queries with `traverse=False` on `DependencyMetadata` per namespace.

## Field semantics vs wire path

`spec.dependency_data.namespace == "oss"` describes **data plane semantics** inside dependency
records—it does **not** mean you should list DependencyMetadata under `/namespaces/oss/…` for
tenant estate reporting.

## Project-scoped queries

When correlating DependencyMetadata with a project, pass **`namespace=project.namespace`** after
resolving the `Project` row. See `rules/endor-namespace-scoping.md`.

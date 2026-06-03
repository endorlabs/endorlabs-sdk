# Changelog

## Unreleased

### Breaking

- **Unknown flat `create()` kwargs** on resources with OpenAPI convenience metadata now raise **`TypeError`** instead of being silently ignored (including pass-through `CreateXPayload(**kwargs)` builders).
- **Unknown flat `list()` kwargs** raise **`TypeError`** instead of being dropped when building `ListParameters`.
- **`list()` / `list_iter()` with a non-empty list field mask** (`mask=` or `ListParameters.mask`, non-empty after strip) now returns **`dict[str, Any]`** rows (shallow-copied wire JSON) instead of constructing full Pydantic resource models. Callers that assumed `list[Project]` (etc.) when using `mask` must use **`isinstance(row, dict)`**, narrow keys manually, or **omit `mask`** when typed models are required.
- **`lookup()`** raises **`ValueError`** if an effective non-empty list mask is set, because `lookup` is defined to return a single typed resource. Use **`list()`** / **`list_iter()`** for masked responses.

### Fixed

- **`VectorStoreQuery.create(..., metadata_filter=...)`** — flat `metadata_filter` is promoted into `spec` and sent on the wire (previously dropped by the builder).
- **`Vulnerability` / `Malware` list/get** — facades now use OSS scope (`/v1/namespaces/oss/…`) via `resource_scope_overrides.json`, matching the global catalog plane (previously used the client tenant namespace).
- **`QueryVulnerability` / `QueryMalware` create** — facades now use OSS scope for catalog-by-version POSTs (`-n oss` in product docs), matching `ListVulnerability` / `ListMalware` routing (previously used the client tenant namespace and often returned 503).

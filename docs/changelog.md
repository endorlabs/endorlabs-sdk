# Changelog

## Unreleased

### Breaking

- **`list()` / `list_iter()` with a non-empty list field mask** (`mask=` or `ListParameters.mask`, non-empty after strip) now returns **`dict[str, Any]`** rows (shallow-copied wire JSON) instead of constructing full Pydantic resource models. Callers that assumed `list[Project]` (etc.) when using `mask` must use **`isinstance(row, dict)`**, narrow keys manually, or **omit `mask`** when typed models are required.
- **`lookup()`** raises **`ValueError`** if an effective non-empty list mask is set, because `lookup` is defined to return a single typed resource. Use **`list()`** / **`list_iter()`** for masked responses.

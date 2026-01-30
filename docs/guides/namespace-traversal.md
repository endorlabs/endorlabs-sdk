# Namespace Traversal

Use `ListParameters(traverse=True)` with the resource's `list_*` function for tenant-wide list operations. The API then queries all child namespaces recursively in a single call. Applies to list operations across resources (e.g. finding, package_version, dependency_metadata, project, scan_result). Pass the same `list_params` to filter, mask, page_size, etc. See [conventions.md](../conventions.md) for traverse and list params. See notebooks for runnable examples.

## Long-running operations and progress

When using `traverse=True` or listing over many pages, operations can take a long time. No timeout is applied; the user controls how long to wait.

Listing logs one INFO message at start (resource, namespace, traverse, max_pages) and one at completion (item count). DEBUG shows request/response activity. No per-page progress callback is provided.

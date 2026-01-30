# Scan logs and ScanLogRequest

## Relationship (OpenAPI + endorctl)

- **Scan log** (concept): The actual log entries (level, timestamp, json_payload, tags). These are **not** a separate API resource. They are returned inside a ScanLogRequest response.
- **ScanLogRequest**: The only API surface for scan logs. Single path: `POST /v1/namespaces/{tenant_meta.namespace}/scan-log-requests`. No GET, LIST, PATCH, or DELETE.

**OpenAPI (openapiv2.swagger.json):**

- Path: `/v1/namespaces/{tenant_meta.namespace}/scan-log-requests` — **post** only.
- Operation: `ScanLogRequestService_CreateScanLogRequest` (CreateScanLogRequest).
- Response: `v1ScanLogRequest`; `spec` includes `log_messages` (array of `v1ScanLogRequestLogMessage`).
- Definitions: `v1ScanLogRequest`, `v1ScanLogRequestSpec`, `v1ScanLogRequestLogMessage` (level, json_payload, tags, timestamp).

**endorctl:**

- `endorctl api list -r ScanLogRequest` → "list operation not implemented for resource: ScanLogRequest".
- `endorctl api list -r ScanLog` → "invalid resource: ScanLog" (no separate ScanLog resource).
- endorctl exposes a tool `get_scan_logs`; UX is "get scan logs" (data), not "list ScanLogRequest".

So: **scan logs** = data returned when you **create** a ScanLogRequest (response `spec.log_messages`). **ScanLogRequest** = request-based API to retrieve that data.

## SDK today

- Module: `endorlabs.resources.scan_log_request`.
- `create_scan_log_request(client, namespace, payload)` → returns `ScanLogRequest` with `spec.log_messages`.
- `get_scan_result_logs(client, namespace, scan_result_uuid, ...)` → convenience that creates a request and returns `list[ScanLogRequestLogMessage]`.
- Not in `RESOURCE_REGISTRY` (no list/get/update/delete); correctly excluded per architecture.

## Recommended abstraction for Client UX

Expose scan logs through the Client in the same style as other workflows (e.g. retrieving-scan-results: project → scan_result → finding), **without** putting ScanLogRequest in the registry (it is not CRUD).

**Option A — Dedicated `scan_logs` facade (recommended):**

- Add a **non-registry** facade: `client.scan_logs` with a single method `get_logs(scan_result_uuid, namespace=None, max_entries=100, ...)` that delegates to `get_scan_result_logs`.
- Wire it in `Client.__init__` alongside the registry loop (one explicit line), same way other “workflow” entrypoints could be added.
- UX: get a scan result (e.g. from `client.scan_results.list()` or `.get(uuid)`), then `client.scan_logs.get_logs(scan_result_uuid)`.

**Option B — ScanResult-centric:**

- Add `get_logs(scan_result_uuid, ...)` on the scan_results facade. Would require extending `ResourceFacade` or adding a specialized facade for scan results (e.g. `ScanResultFacade` with an extra method). More invasive.

**Recommendation:** Option A. Single place for “get scan logs” that mirrors endorctl’s `get_scan_logs` and keeps the registry strictly for CRUD resources; scan_log_request remains a module-level, request-based API with a thin Client convenience.

## Workflow (one-line steps)

1. Get ScanResult UUID (e.g. list scan results for a project, take one).
2. Call `client.scan_logs.get_logs(scan_result_uuid)` (after implementing Option A).

Resources: `endorlabs.resources.scan_log_request`, `.scan_result`; [retrieving-scan-results.md](retrieving-scan-results.md) for project → scan result; [reference/resources.md](../reference/resources.md).

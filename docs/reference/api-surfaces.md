# API Surfaces (generated)

Auto-generated inventories for stable/public surfaces.

## Top-level exports (`endorlabs.__all__`)

- `APIClient`
- `AmbiguousError`
- `Client`
- `ConflictError`
- `EndorAPIError`
- `F`
- `FilterExpression`
- `MethodNotSupportedError`
- `NotFoundError`
- `PermissionDeniedError`
- `RateLimitError`
- `ServerError`
- `UnauthorizedError`
- `ValidationError`
- `dependency_metadata`
- `finding`
- `init`
- `installation`
- `linter_result`
- `malware`
- `map_status_code_to_exception`
- `metric`
- `namespace`
- `package_version`
- `policy`
- `project`
- `query_malware`
- `query_vulnerability`
- `repository`
- `repository_version`
- `vulnerability`

## Resource modules (`endorlabs.resources.__all__`)

- `api_key`
- `audit_log`
- `authentication_log`
- `authorization_policy`
- `code_owners`
- `dependency_metadata`
- `endor_license`
- `finding`
- `finding_log`
- `installation`
- `invitation`
- `linter_result`
- `malware`
- `metric`
- `namespace`
- `notification_target`
- `package_license`
- `package_version`
- `policy`
- `policy_template`
- `project`
- `query_malware`
- `query_vulnerability`
- `repository`
- `repository_version`
- `scan_log_request`
- `scan_profile`
- `scan_result`
- `scan_workflow`
- `scan_workflow_result`
- `semgrep_rule`
- `version_upgrade`
- `vulnerability`

## Facade method signatures

### Compact facade view

| Method | Primary purpose | Key parameters |
|--------|------------------|----------------|
| `list` | List resources with paging/filtering | `traverse`, `namespace`, `list_params`, `filter`, `mask`, `max_pages` |
| `lookup` | Return exactly one matching resource | `filter`, identity kwargs via `filter_kwarg_map`, `max_pages` |
| `list_iter` | Streaming iteration over list results | same as `list`, iterator output |
| `get` | Fetch one resource by id or resource object | `id_or_resource`, `namespace` |
| `create` | Create resource from payload or builder kwargs | `payload`, `name`, `description`, `namespace_uuid`, `namespace`, `**kwargs` |
| `update` | Patch resource with `update_mask` or field kwargs | `id_or_resource`, `payload`, `update_mask`, `meta_description`, `meta_tags` |
| `delete` | Delete resource by id or object | `name_or_resource`, `namespace`, `ignore_missing` |
| `tag` / `untag` | Tag management on resources supporting tags | `id_or_resource`, `tags`/`keys`, `namespace` |

### `_ListableFacade` methods

- `list(self, traverse: 'bool' = False, concurrent: 'bool' = False, max_workers: 'int' = 10, namespace: 'str | None' = None, list_params: 'ListParameters | None' = None, max_pages: 'int | None' = None, parent: 'Any' = None, filter: 'str | FilterExpression | None' = None, mask: 'str | None' = None, page_size: 'int | None' = None, page_token: 'str | None' = None, page_id: 'str | None' = None, sort_by: 'str | None' = None, desc: 'bool | None' = None, count: 'bool | None' = None, from_date: 'str | None' = None, to_date: 'str | None' = None, archive: 'bool | None' = None, pr_uuid: 'str | None' = None, **kwargs: 'Any') -> 'list[T]'`
- `lookup(self, traverse: 'bool' = False, concurrent: 'bool' = False, max_workers: 'int' = 10, namespace: 'str | None' = None, list_params: 'ListParameters | None' = None, max_pages: 'int' = 2, parent: 'Any' = None, filter: 'str | FilterExpression | None' = None, mask: 'str | None' = None, page_size: 'int | None' = None, page_token: 'str | None' = None, page_id: 'str | None' = None, sort_by: 'str | None' = None, desc: 'bool | None' = None, count: 'bool | None' = None, from_date: 'str | None' = None, to_date: 'str | None' = None, archive: 'bool | None' = None, pr_uuid: 'str | None' = None, **kwargs: 'Any') -> 'T'`
- `list_iter(self, traverse: 'bool' = False, concurrent: 'bool' = False, namespace: 'str | None' = None, list_params: 'ListParameters | None' = None, max_pages: 'int | None' = None, parent: 'Any' = None, filter: 'str | FilterExpression | None' = None, mask: 'str | None' = None, page_size: 'int | None' = None, page_token: 'str | None' = None, page_id: 'str | None' = None, sort_by: 'str | None' = None, desc: 'bool | None' = None, count: 'bool | None' = None, from_date: 'str | None' = None, to_date: 'str | None' = None, archive: 'bool | None' = None, pr_uuid: 'str | None' = None, **kwargs: 'Any') -> 'Iterator[T]'`

### `ResourceFacade` methods

- `get(self, id_or_resource: 'str | T', namespace: 'str | None' = None) -> 'T'`
- `create(self, payload: 'Any' = None, *, name: 'str | None' = None, description: 'str | None' = None, namespace_uuid: 'str | None' = None, namespace: 'str | None' = None, **kwargs: 'Any') -> 'T'`
- `update(self, id_or_resource: 'str | T', payload: 'Any | None' = None, *, update_mask: 'str | None' = None, meta_description: 'str | None' = None, meta_tags: 'list[str] | None' = None, namespace: 'str | None' = None, **kwargs: 'Any') -> 'T'`
- `delete(self, name_or_resource: 'str | T', namespace: 'str | None' = None, *, ignore_missing: 'bool' = False) -> 'bool'`
- `tag(self, id_or_resource: 'str | T', tags: 'list[str]', namespace: 'str | None' = None) -> 'T'`
- `untag(self, id_or_resource: 'str | T', keys: 'list[str]', namespace: 'str | None' = None) -> 'T'`

## Client resources (registry-driven)

| Attr | Resource path | Scope | Parent kind | Supported ops |
|------|---------------|-------|-------------|---------------|
| api_key | api-keys | tenant | — | list, get, create, delete |
| audit_log | audit-logs | tenant | — | list, get, create, delete |
| authentication_log | authentication-logs | system | — | list, get |
| authorization_policy | authorization-policies | tenant | — | list, get, create, update, delete |
| code_owners | codeowners | tenant | — | list, get, create, update, delete |
| dependency_metadata | dependency-metadata | oss | — | list, get, create, update, delete |
| endor_license | endor-licenses | system | — | list, get |
| finding | findings | tenant | — | list, get, create, update, delete |
| finding_log | finding-logs | tenant | — | list, get, create, delete |
| installation | installations | tenant | — | list, get, create, update, delete |
| invitation | invitations | tenant | — | list, get, create, update, delete |
| linter_result | linter-results | tenant | — | list, get, create, delete |
| malware | malware | oss | — | list, get |
| metric | metrics | tenant | — | list, get, create, update, delete |
| namespace | namespaces | tenant | — | list, get, create, update, delete |
| notification_target | notification-targets | tenant | — | list, get, create, update, delete |
| package_license | package-licenses | oss | — | list, get, create, update, delete |
| package_version | package-versions | tenant | — | list, get, create, update, delete |
| policy | policies | tenant | — | list, get, create, update, delete |
| policy_template | policy-templates | system | — | list, get |
| project | projects | tenant | — | list, get, create, update, delete |
| query_malware | queries/malware | oss | — | create |
| query_vulnerability | queries/vulnerabilities | oss | — | create |
| repository | repositories | tenant | — | list, get, create, update, delete |
| repository_version | repository-versions | tenant | project | list, get, create, update, delete |
| scan_log_request | scan-log-requests | tenant | — | create |
| scan_profile | scan-profiles | tenant | — | list, get, create, update, delete |
| scan_result | scan-results | tenant | project | list, get, create, update, delete |
| scan_workflow | scan-workflows | tenant | — | list, get, delete |
| scan_workflow_result | scan-workflow-results | tenant | — | list, get, delete |
| semgrep_rule | semgrep-rules | tenant | — | list, get, create, update, delete |
| version_upgrade | version-upgrades | tenant | — | list, get, delete |
| vulnerability | vulnerabilities | oss | — | list, get |

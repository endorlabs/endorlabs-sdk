# API Surfaces (generated)

Auto-generated inventories for stable/public surfaces.

## Top-level exports (`endorlabs.__all__`)

## Model-sync coverage snapshot

- mapped entities: `215`
- generated artifact files: `153`
- facade contract resources: `41`
- registry parity status: `pass`
- operation metadata entries: `749`
- payload schema resources: `41`
- runtime model import index entries: `41`

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
- `sync_agent_skills`
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
- `pr_comment_config`
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
| `list` | List resources with paging/filtering; non-empty `mask` → `dict` rows | `traverse`, `namespace`, `list_params`, `filter`, `mask`, `max_pages` |
| `lookup` | Return exactly one matching **model** (no list `mask`) | `filter`, identity kwargs via `filter_kwarg_map`, `max_pages` |
| `list_iter` | Stream list results; non-empty `mask` → dict items | same as `list`, iterator output |
| `get` | Fetch one resource by id or resource object | `id_or_resource`, `namespace` |
| `create` | Create resource from payload or builder kwargs | `payload`, `name`, `description`, `namespace_uuid`, `namespace`, `**kwargs` |
| `update` | Patch resource with `update_mask` or field kwargs | `id_or_resource`, `payload`, `update_mask`, `meta_description`, `meta_tags` |
| `delete` | Delete resource by id or object | `name_or_resource`, `namespace`, `ignore_missing` |
| `tag` / `untag` | Tag management on resources supporting tags | `id_or_resource`, `tags`/`keys`, `namespace` |

### `_ListableFacade` methods

- `list(self, traverse: 'bool' = False, concurrent: 'bool' = False, max_workers: 'int' = 10, namespace: 'str | None' = None, list_params: 'ListParameters | None' = None, max_pages: 'int | None' = None, parent: 'Any' = None, filter: 'str | FilterExpression | None' = None, mask: 'str | None' = None, page_size: 'int | None' = None, page_token: 'str | None' = None, page_id: 'str | None' = None, sort_by: 'str | None' = None, desc: 'bool | None' = None, count: 'bool | None' = None, from_date: 'str | None' = None, to_date: 'str | None' = None, archive: 'bool | None' = None, pr_uuid: 'str | None' = None, ci_run_uuid: 'str | None' = None, **kwargs: 'Any') -> 'list[T] | list[dict[str, Any]]'`
- `lookup(self, traverse: 'bool' = False, concurrent: 'bool' = False, max_workers: 'int' = 10, namespace: 'str | None' = None, list_params: 'ListParameters | None' = None, max_pages: 'int' = 2, parent: 'Any' = None, filter: 'str | FilterExpression | None' = None, mask: 'str | None' = None, page_size: 'int | None' = None, page_token: 'str | None' = None, page_id: 'str | None' = None, sort_by: 'str | None' = None, desc: 'bool | None' = None, count: 'bool | None' = None, from_date: 'str | None' = None, to_date: 'str | None' = None, archive: 'bool | None' = None, pr_uuid: 'str | None' = None, ci_run_uuid: 'str | None' = None, **kwargs: 'Any') -> 'T'`
- `list_iter(self, traverse: 'bool' = False, concurrent: 'bool' = False, namespace: 'str | None' = None, list_params: 'ListParameters | None' = None, max_pages: 'int | None' = None, parent: 'Any' = None, filter: 'str | FilterExpression | None' = None, mask: 'str | None' = None, page_size: 'int | None' = None, page_token: 'str | None' = None, page_id: 'str | None' = None, sort_by: 'str | None' = None, desc: 'bool | None' = None, count: 'bool | None' = None, from_date: 'str | None' = None, to_date: 'str | None' = None, archive: 'bool | None' = None, pr_uuid: 'str | None' = None, ci_run_uuid: 'str | None' = None, **kwargs: 'Any') -> 'Iterator[T | dict[str, Any]]'`

### `ResourceRuntimeFacade` methods (`ResourceFacade` alias)

- `get(self, id_or_resource: 'str | T', namespace: 'str | None' = None) -> 'T'`
- `create(self, payload: 'Any' = None, *, name: 'str | None' = None, description: 'str | None' = None, namespace_uuid: 'str | None' = None, namespace: 'str | None' = None, **kwargs: 'Any') -> 'T'`
- `update(self, id_or_resource: 'str | T', payload: 'Any | None' = None, *, update_mask: 'str | None' = None, meta_description: 'str | None' = None, meta_tags: 'list[str] | None' = None, namespace: 'str | None' = None, **kwargs: 'Any') -> 'T'`
- `delete(self, name_or_resource: 'str | T', namespace: 'str | None' = None, *, ignore_missing: 'bool' = False) -> 'bool'`
- `tag(self, id_or_resource: 'str | T', tags: 'list[str]', namespace: 'str | None' = None) -> 'T'`
- `untag(self, id_or_resource: 'str | T', keys: 'list[str]', namespace: 'str | None' = None) -> 'T'`

## Client resources (registry-driven)

| Attr | Resource path | Scope | Parent kind | Supported ops |
|------|---------------|-------|-------------|---------------|
| APIKey | api-keys | tenant | — | list, get, create, delete |
| AuditLog | audit-logs | tenant | — | list, get, create, delete |
| AuthenticationLog | authentication-logs | tenant | — | list, get |
| AuthorizationPolicy | authorization-policies | tenant | — | list, get, create, update, delete |
| CodeOwners | codeowners | tenant | — | list, get, create, update, delete |
| DependencyMetadata | dependency-metadata | tenant | — | list, get, create, delete |
| EndorLicense | endor-licenses | tenant | — | list, get |
| Finding | findings | tenant | — | list, get, create, update, delete |
| FindingLog | finding-logs | tenant | — | list, get, create, delete |
| Installation | installations | tenant | — | list, get, create, update, delete |
| Invitation | invitations | tenant | — | list, get, create, update, delete |
| LinterResult | linter-results | tenant | — | list, get, create, delete |
| Malware | malware | tenant | — | list, get |
| Metric | metrics | tenant | — | list, get, create, update, delete |
| Namespace | namespaces | tenant | — | list, get, create, update, delete |
| NotificationTarget | notification-targets | tenant | — | list, get, create, update, delete |
| PRCommentConfig | pr-comment-configs | tenant | — | list, get, create, update, delete |
| PackageFirewallLog | package-firewall-logs | tenant | — | list, get |
| PackageLicense | package-licenses | tenant | — | list, get, create, update, delete |
| PackageVersion | package-versions | tenant | — | list, get, create, update, delete |
| Policy | policies | tenant | — | list, get, create, update, delete |
| PolicyTemplate | policy-templates | tenant | — | list, get |
| Project | projects | tenant | — | list, get, create, update, delete |
| QueryMalware | queries/malware | tenant | — | create |
| QueryVulnerability | queries/vulnerabilities | tenant | — | create |
| Repository | repositories | tenant | — | list, get, create, update, delete |
| RepositoryVersion | repository-versions | tenant | project | list, get, create, update, delete |
| ScanLogRequest | scan-log-requests | tenant | — | create |
| ScanProfile | scan-profiles | tenant | — | list, get, create, update, delete |
| ScanResult | scan-results | tenant | project | list, get, create, update, delete |
| ScanWorkflow | scan-workflows | tenant | — | list, get, delete |
| ScanWorkflowResult | scan-workflow-results | tenant | — | list, get, delete |
| SemgrepRule | semgrep-rules | tenant | — | list, get, create, update, delete |
| V1IdentityProvider | identity-providers | tenant | — | list, get |
| V1Query | queries | tenant | — | create |
| V1QuerySimilarPackages | queries/similar-packages | tenant | — | create |
| V1SavedQuery | saved-queries | tenant | — | list, get |
| VectorStore | vector-stores | tenant | — | list, get |
| VectorStoreQuery | queries/vector-stores | tenant | — | create |
| VersionUpgrade | version-upgrades | tenant | — | list, get, delete |
| Vulnerability | vulnerabilities | tenant | — | list, get |

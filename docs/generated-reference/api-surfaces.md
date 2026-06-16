# API Surfaces (generated)

Auto-generated inventories for stable/public surfaces.

## Model-sync coverage snapshot

- facade contract resources: `41`
- canonical entities (union): `41`

Normative usage: [facade-helpers.md](../guides/facade-helpers.md).

## Top-level exports (`endorlabs.__all__`)

- `APIClient`
- `AmbiguousError`
- `Client`
- `ConflictError`
- `EndorAPIError`
- `F`
- `FilterExpression`
- `ListParameters`
- `MethodNotSupportedError`
- `NotFoundError`
- `PermissionDeniedError`
- `RateLimitError`
- `ServerError`
- `UnauthorizedError`
- `ValidationError`
- `agent_knowledge_bootstrap_paths`
- `agent_knowledge_dir`
- `agent_knowledge_index_path`
- `agent_knowledge_manifest`
- `agent_knowledge_rule_ids`
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
- `call_graph_data`
- `call_graph_data_proto`
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
| `list_iter` | Stream list results; non-empty `mask` → dict items | same as `list`, iterator output |
| `get` | Fetch one resource by id or resource object | `id_or_resource`, `namespace` |
| `create` | Create resource from payload or builder kwargs | `payload`, `name`, `description`, `namespace_uuid`, `namespace`, `**kwargs` |
| `update` | Patch resource with `update_mask` or field kwargs | `id_or_resource`, `payload`, `update_mask`, `meta_description`, `meta_tags` |
| `delete` | Delete resource by id or object | `name_or_resource`, `namespace`, `ignore_missing` |
| `tag` / `untag` | Tag management on resources supporting tags | `id_or_resource`, `tags`/`keys`, `namespace` |

### `_ListableFacade` methods

- `list(self, traverse: 'bool' = False, concurrent: 'bool' = True, max_workers: 'int' = 10, namespace: 'str | None' = None, list_params: 'ListParameters | None' = None, max_pages: 'int | None' = None, parent: 'Any' = None, filter: 'str | FilterExpression | None' = None, mask: 'str | None' = None, page_size: 'int | None' = None, page_token: 'str | None' = None, page_id: 'str | None' = None, sort_by: 'str | None' = None, desc: 'bool | None' = None, count: 'bool | None' = None, from_date: 'str | None' = None, to_date: 'str | None' = None, archive: 'bool | None' = None, pr_uuid: 'str | None' = None, ci_run_uuid: 'str | None' = None, **kwargs: 'Any') -> 'list[T] | list[dict[str, Any]]'`
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
| IdentityProvider | identity-providers | tenant | — | list, get |
| Installation | installations | tenant | — | list, get, create, update, delete |
| Invitation | invitations | tenant | — | list, get, create, update, delete |
| LinterResult | linter-results | tenant | — | list, get, create, delete |
| Malware | malware | oss | — | list, get |
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
| Query | queries | tenant | — | create |
| QueryMalware | queries/malware | oss | — | create |
| QuerySimilarPackages | queries/similar-packages | tenant | — | create |
| QueryVulnerability | queries/vulnerabilities | oss | — | create |
| Repository | repositories | tenant | — | list, get, create, update, delete |
| RepositoryVersion | repository-versions | tenant | project | list, get, create, update, delete |
| SavedQuery | saved-queries | tenant | — | list, get |
| ScanLogRequest | scan-log-requests | tenant | — | create |
| ScanProfile | scan-profiles | tenant | — | list, get, create, update, delete |
| ScanResult | scan-results | tenant | project | list, get, create, update, delete |
| ScanWorkflow | scan-workflows | tenant | — | list, get, delete |
| ScanWorkflowResult | scan-workflow-results | tenant | — | list, get, delete |
| SemgrepRule | semgrep-rules | tenant | — | list, get, create, update, delete |
| VectorStore | vector-stores | tenant | — | list, get |
| VectorStoreQuery | queries/vector-stores | tenant | — | create |
| VersionUpgrade | version-upgrades | tenant | — | list, get, delete |
| Vulnerability | vulnerabilities | oss | — | list, get |

## Identity lane (`search_by_*`)

Bounded list discovery; returns `list[T]` (not `RouteResult`).

| Facade | Method | Match |
|--------|--------|-------|
| `Project` | `Project.search_by_name` | Substring on `meta.name`; partial UUID match |
| `VectorStore` | `VectorStore.search_by_name` | Substring on `meta.name` |
| `AuthorizationPolicy` | `AuthorizationPolicy.search_by_claims` | Claims substring match |
| `Vulnerability` | `Vulnerability.search_by_vuln_alias` | Vuln alias substring (OSS scope) |

## Relationship accessors (generated)

From `route_contract.py`. Return `RouteResult` — use `.values` or `.value`.
Full edge inventory: [resource-routes.md](resource-routes.md).

| Public method | From → To | Edge id | Wire kind | Returns |
|---------------|-----------|---------|-----------|---------|
| `DependencyMetadata.list_for_context` | ScanResult → DependencyMetadata | `scan.dependency_metadata` | `list_by_context_partition` | RouteResult → `.values` |
| `Finding.list_by_project` | Project → Finding | `project.findings` | `list_by_uuid_field` | RouteResult → `.values` |
| `Finding.list_for_context` | ScanResult → Finding | `scan.findings` | `list_by_context_partition` | RouteResult → `.values` |
| `Finding.to_dependency_metadata` | Finding → DependencyMetadata | `finding.dependency_metadata.by_package` | `list_by_attribute` | RouteResult → `.value` (fallback path) |
| `FindingLog.list_for_context` | ScanResult → FindingLog | `scan.finding_logs` | `list_by_context_partition` | RouteResult → `.values` |
| `LinterResult.list_for_context` | ScanResult → LinterResult | `scan.linter_results` | `list_by_context_partition` | RouteResult → `.values` |
| `Metric.list_for_context` | ScanResult → Metric | `scan.metrics` | `list_by_context_partition` | RouteResult → `.values` |
| `PackageLicense.list_for_context` | ScanResult → PackageLicense | `scan.package_licenses` | `list_by_context_partition` | RouteResult → `.values` |
| `PackageVersion.list_by_project` | Project → PackageVersion | `project.package_versions` | `list_by_uuid_field` | RouteResult → `.values` |
| `PackageVersion.list_for_context` | ScanResult → PackageVersion | `scan.package_versions` | `list_by_context_partition` | RouteResult → `.values` |
| `RepositoryVersion.list_for_context` | ScanResult → RepositoryVersion | `scan.repository_versions` | `list_by_context_partition` | RouteResult → `.values` |
| `ScanResult.list_by_project` | Project → ScanResult | `project.scan_results` | `list_by_parent` | RouteResult → `.values` |
| `ScanWorkflowResult.list_for_context` | ScanResult → ScanWorkflowResult | `scan.scan_workflow_results` | `list_by_context_partition` | RouteResult → `.values` |
| `VersionUpgrade.list_for_context` | ScanResult → VersionUpgrade | `scan.version_upgrades` | `list_by_context_partition` | RouteResult → `.values` |

## Custom and wire facades

| Facade | Method | Purpose |
|--------|--------|---------|
| `CallGraphData` | `decode(package_version, …)` | Decoded call graph JSON for a PackageVersion |
| `CallGraphData` | `fetch(package_version, …)` | Raw CallGraphData wire envelope |
| `ScanResult` | `get_logs(scan_result, …)` | Scan log messages via ScanLogRequest API |

## Universal list helpers (`ListableFacade`)

Available on every listable registry facade unless noted.

| Method | Purpose |
|--------|---------|
| `count(**list_kwargs)` | Server-side row count |
| `list_groups(*, paths, **kwargs)` | Group-by aggregation buckets |
| `latest(sort_by=..., **kwargs)` | Newest single row (`max_pages=1`) |
| `latest_created(**kwargs)` | Sugar for `sort_by="meta.create_time"` |
| `latest_updated(**kwargs)` | Sugar for `sort_by="meta.update_time"` |
| `parent(resource)` | GET parent row via registry `parent_kind` |

`list(count=True)` emits `DeprecationWarning` and delegates to `count()`.

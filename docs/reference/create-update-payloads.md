# Create/Update payload reference (decoupled facade)

Per-resource request shapes for create and update. Used by `build_create_payload` (and optional `build_update_payload`) when the facade accepts kwargs; payload types remain the internal contract for the API layer.

## Facade create kwargs

The facade exposes `name`, `description`, and `namespace_uuid` as convenience params merged into the builder path. **Resource-specific required or optional args** (e.g. project: `repository_url`, `language`, `framework`; metric: `analytic`, `project_uuid`, `metric_values`) must be passed as additional kwargs to `create(...)` and are defined by each resource's `build_create_payload` signature. For namespace create, the parent scope is the `namespace=` argument to `create()` (the scope under which the namespace is created), not a builder kwarg; the builder takes `name` and `description` only.

## Create payloads (CreateXPayload)

| Resource | Module | Required fields | Optional / notes |
|----------|--------|-----------------|------------------|
| namespace | namespace | meta.name (meta via NamespaceMetaCreate) | tenant_meta_namespace = parent; spec.managed |
| project | project | meta (ProjectMetaCreate), namespace_uuid | |
| finding | finding | CreateFindingPayload fields | spec, meta per API |
| repository | repository | CreateRepositoryPayload | |
| repository_version | repository_version | CreateRepositoryVersionPayload | parent_kind=project |
| policy | policy | CreatePolicyPayload | |
| authorization_policy | authorization_policy | CreateAuthorizationPolicyPayload | |
| package_version | package_version | CreatePackageVersionPayload | |
| package_license | package_license | CreatePackageLicensePayload | OSS; namespace ignored |
| dependency_metadata | dependency_metadata | CreateDependencyMetadataPayload | OSS; no update; namespace ignored |
| installation | installation | CreateInstallationPayload | |
| scan_profile | scan_profile | meta.name (ScanProfileMetaCreate), spec (ScanProfileSpecCreate) | propagate |
| scan_result | scan_result | CreateScanResultPayload | parent_kind=project |
| linter_result | linter_result | CreateLinterResultPayload | |
| metric | metric | CreateMetricPayload | |
| semgrep_rule | semgrep_rule | CreateSemgrepRulePayload | validate_yaml |
| api_key | api_key | CreateAPIKeyPayload | create only |
| audit_log | audit_log | CreateAuditLogPayload | create only |
| finding_log | finding_log | CreateFindingLogPayload | create only |
| notification_target | notification_target | CreateNotificationTargetPayload | |
| code_owners | code_owners | CreateCodeOwnersPayload | |
| invitation | invitation | CreateInvitationPayload | |

## Update payloads (UpdateXPayload / Resource)

Update uses `update_mask` + payload (or kwargs via `resource.update(facade, **kwargs)`). The **canonical** allowed create fields are the resource’s `build_create_payload` signature and CreateXPayload; the **canonical** allowed update fields are the model’s `get_mutable_fields_cls()`. The facade’s explicit params (e.g. `name`, `meta_description`) are a subset. Mutable fields are resource-specific; see each resource module and BaseResource.get_mutable_fields() / get_update_kwarg_to_path().

## List identity (list/lookup by name)

**List/lookup by identity** (e.g. `list(name="...")`, `lookup(name="...")`) is supported only for resources that have an identity filter map. Currently: project, repository, policy, namespace, scan_profile, scan_result, finding, authorization_policy, repository_version, installation, notification_target, metric, semgrep_rule, package_version, invitation, code_owners. For other resources use `filter=` explicitly (e.g. `filter='meta.name=="my-name"'`).

## Resources with no create/update (skip)

- scan_workflow, scan_workflow_result, version_upgrade (list/get only)
- authentication_log, endor_license, policy_template (system; list/get only)

## Special cases

- **namespace:** create under parent namespace; the parent is the `namespace=` argument to `create()`, not a builder kwarg. Builder takes `name` and `description` only.
- **dependency_metadata / package_license:** OSS; namespace param ignored in create.
- **linter_result:** update uses UpdateLinterResultPayload; update_mask required.

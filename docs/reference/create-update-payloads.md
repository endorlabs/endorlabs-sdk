# Create/Update payload reference (decoupled facade)

Per-resource request shapes for create and update. Used by `build_create_payload` (and optional `build_update_payload`) when the facade accepts kwargs; payload types remain the internal contract for the API layer.

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

## Resources with no create/update (skip)

- scan_workflow, scan_workflow_result, version_upgrade (list/get only)
- authentication_log, endor_license, policy_template (system; list/get only)

## Special cases

- **namespace:** create under parent namespace; builder: parent_namespace + name (+ description, spec.managed).
- **dependency_metadata / package_license:** OSS; namespace param ignored in create.
- **linter_result:** update uses UpdateLinterResultPayload; update_mask required.

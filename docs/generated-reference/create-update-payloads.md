# Create/Update payload reference (generated)

Auto-generated from `RESOURCE_REGISTRY`, builder return types,
and payload models.
Model sync mapping: `workspace/model-sync/custom_mapping/mapping/entity_mapping.json` (337 entities).

## Create payload/builders

| Resource | SDK create support | Builder | Payload model | Required fields | Optional fields |
|----------|--------------------|---------|---------------|-----------------|-----------------|
## Model-sync coverage snapshot

- mapped entities: `337`
- generated artifact files: `219`
- facade contract resources: `33`
- registry parity status: `pass`
- operation metadata entries: `709`
- payload schema resources: `33`
- runtime model import index entries: `33`

| api_key | yes | build_create_payload | CreateAPIKeyPayload | meta, spec | propagate |
| audit_log | yes | build_create_payload | CreateAuditLogPayload | meta, spec | propagate |
| authentication_log | no | N/A | N/A | N/A | N/A |
| authorization_policy | yes | build_create_payload | CreateAuthorizationPolicyPayload | meta, spec | propagate |
| code_owners | yes | build_create_payload | CreateCodeOwnersPayload | meta, spec | none |
| dependency_metadata | yes | build_create_payload | CreateDependencyMetadataPayload | meta, spec | none |
| endor_license | no | N/A | N/A | N/A | N/A |
| finding | yes | build_create_payload | CreateFindingPayload | context, meta, spec | none |
| finding_log | yes | build_create_payload | CreateFindingLogPayload | context, meta, spec | none |
| installation | yes | build_create_payload | CreateInstallationPayload | meta, spec | none |
| invitation | yes | build_create_payload | CreateInvitationPayload | meta, spec | none |
| linter_result | yes | build_create_payload | CreateLinterResultPayload | meta, spec | none |
| malware | no | N/A | N/A | N/A | N/A |
| metric | yes | build_create_payload | CreateMetricPayload | meta, spec | none |
| namespace | yes | build_create_payload | CreateNamespacePayload | meta | none |
| notification_target | yes | build_create_payload | CreateNotificationTargetPayload | meta, spec | propagate |
| package_license | yes | build_create_payload | CreatePackageLicensePayload | meta, spec | none |
| package_version | yes | build_create_payload | CreatePackageVersionPayload | meta, spec | none |
| policy | yes | build_create_payload | CreatePolicyPayload | meta, spec | propagate |
| policy_template | no | N/A | N/A | N/A | N/A |
| project | yes | build_create_payload | CreateProjectPayload | meta, namespace_uuid | none |
| query_malware | yes | build_create_payload | CreateQueryMalwarePayload | meta, spec | none |
| query_vulnerability | yes | build_create_payload | CreateQueryVulnerabilityPayload | meta, spec | none |
| repository | yes | build_create_payload | CreateRepositoryPayload | meta, spec | none |
| repository_version | yes | build_create_payload | CreateRepositoryVersionPayload | meta, spec | none |
| scan_log_request | yes | N/A | N/A | N/A | N/A |
| scan_profile | yes | build_create_payload | CreateScanProfilePayload | meta, spec | propagate |
| scan_result | yes | build_create_payload | CreateScanResultPayload | context, meta, spec | none |
| scan_workflow | no | N/A | N/A | N/A | N/A |
| scan_workflow_result | no | N/A | N/A | N/A | N/A |
| semgrep_rule | yes | build_create_payload | CreateSemgrepRulePayload | meta, spec | disabled, propagate |
| version_upgrade | no | N/A | N/A | N/A | N/A |
| vulnerability | no | N/A | N/A | N/A | N/A |

## Update mutable fields

| Resource | SDK update support | Mutable field paths (`get_mutable_fields_cls`) |
|----------|--------------------|----------------------------------------------|
| api_key | no | meta.description, meta.tags |
| audit_log | no | meta.description, meta.tags |
| authentication_log | no | meta.description, meta.tags |
| authorization_policy | yes | meta.name, meta.description, meta.tags, spec, propagate |
| code_owners | yes | meta.description, meta.tags |
| dependency_metadata | yes | meta.name, meta.description, meta.tags, spec |
| endor_license | no | meta.description, meta.tags |
| finding | yes | meta.tags, spec.finding_tags, spec.dismiss, spec.remediation, context.tags |
| finding_log | no | meta.description, meta.tags |
| installation | yes | meta.name, meta.description, meta.tags, spec |
| invitation | yes | meta.description, meta.tags |
| linter_result | no | meta.name, meta.description, meta.tags, spec |
| malware | no | meta.description, meta.tags |
| metric | yes | meta.name, meta.description, meta.tags, spec |
| namespace | yes | meta.description |
| notification_target | yes | meta.description, meta.tags |
| package_license | yes | meta.name, meta.description, meta.tags, spec |
| package_version | yes | meta.name, meta.description, meta.tags, spec |
| policy | yes | meta.name, meta.description, meta.tags, spec.rule, spec.disable, spec.project_selector, spec.project_exceptions, spec.template_values, propagate |
| policy_template | no | meta.description, meta.tags |
| project | yes | meta.description, meta.tags, processing_status.scan_state, processing_status.disable_automated_scan |
| query_malware | no | meta.description, meta.tags |
| query_vulnerability | no | meta.description, meta.tags |
| repository | yes | meta.name, meta.description, meta.tags, spec |
| repository_version | yes | meta.name, meta.description, meta.tags, spec |
| scan_log_request | no | meta.description, meta.tags |
| scan_profile | yes | meta.name, meta.description, meta.tags, spec |
| scan_result | yes | meta.name, meta.description, meta.tags, spec |
| scan_workflow | no | meta.description, meta.tags |
| scan_workflow_result | no | meta.description, meta.tags |
| semgrep_rule | yes | meta.name, meta.description, meta.tags, spec |
| version_upgrade | no | meta.description, meta.tags |
| vulnerability | no | meta.description, meta.tags |

## Identity kwargs (`list()` / `lookup()` helpers)

| Resource | Identity kwargs -> filter paths |
|----------|---------------------------------|
| api_key | — |
| audit_log | — |
| authentication_log | — |
| authorization_policy | name->meta.name |
| code_owners | name->meta.name |
| dependency_metadata | — |
| endor_license | — |
| finding | name->meta.name |
| finding_log | — |
| installation | name->meta.name |
| invitation | name->meta.name |
| linter_result | — |
| malware | name->meta.name |
| metric | name->meta.name |
| namespace | name->meta.name |
| notification_target | name->meta.name |
| package_license | — |
| package_version | name->meta.name |
| policy | name->meta.name, policy_type->spec.policy_type |
| policy_template | — |
| project | name->meta.name |
| query_malware | — |
| query_vulnerability | — |
| repository | git_url->spec.vcs_url, name->meta.name, vcs_url->spec.vcs_url |
| repository_version | name->meta.name |
| scan_log_request | — |
| scan_profile | name->meta.name |
| scan_result | name->meta.name |
| scan_workflow | — |
| scan_workflow_result | — |
| semgrep_rule | name->meta.name |
| version_upgrade | — |
| vulnerability | name->meta.name |

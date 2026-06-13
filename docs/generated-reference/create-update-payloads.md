# Create/Update payload reference (generated)

Auto-generated from `RESOURCE_REGISTRY`, builder return types,
and payload models.
Model sync contract: `src/endorlabs/generated/registry_contract.py` (41 resources, 41 canonical entities).

## Model-sync coverage snapshot

- facade contract resources: `41`
- canonical entities (union): `41`

## Create payload/builders

| Resource | SDK create support | Builder | Payload model | Required fields | Optional fields |
|----------|--------------------|---------|---------------|-----------------|-----------------|
| APIKey | yes | build_create_payload | CreateAPIKeyPayload | meta, spec | propagate |
| AuditLog | yes | build_create_payload | CreateAuditLogPayload | meta, spec | propagate |
| AuthenticationLog | no | N/A | N/A | N/A | N/A |
| AuthorizationPolicy | yes | build_create_payload | CreateAuthorizationPolicyPayload | meta, spec | propagate |
| CodeOwners | yes | build_create_payload | CreateCodeOwnersPayload | meta, spec | none |
| DependencyMetadata | yes | build_create_payload | CreateDependencyMetadataPayload | meta, spec | none |
| EndorLicense | no | N/A | N/A | N/A | N/A |
| Finding | yes | build_create_payload | CreateFindingPayload | context, meta, spec | none |
| FindingLog | yes | build_create_payload | CreateFindingLogPayload | context, meta, spec | none |
| IdentityProvider | no | build_create_payload | CreateIdentityProviderPayload | meta, spec | none |
| Installation | yes | build_create_payload | CreateInstallationPayload | meta, spec | none |
| Invitation | yes | build_create_payload | CreateInvitationPayload | meta, spec | none |
| LinterResult | yes | build_create_payload | CreateLinterResultPayload | meta, spec | none |
| Malware | no | N/A | N/A | N/A | N/A |
| Metric | yes | build_create_payload | CreateMetricPayload | meta, spec | none |
| Namespace | yes | build_create_payload | CreateNamespacePayload | meta | none |
| NotificationTarget | yes | build_create_payload | CreateNotificationTargetPayload | meta, spec | propagate |
| PRCommentConfig | yes | build_create_payload | CreatePRCommentConfigPayload | meta, spec | propagate |
| PackageFirewallLog | no | build_create_payload | CreatePackageFirewallLogPayload | meta, spec | none |
| PackageLicense | yes | build_create_payload | CreatePackageLicensePayload | meta, spec | none |
| PackageVersion | yes | build_create_payload | CreatePackageVersionPayload | meta, spec | none |
| Policy | yes | build_create_payload | CreatePolicyPayload | meta, spec | propagate |
| PolicyTemplate | no | N/A | N/A | N/A | N/A |
| Project | yes | build_create_payload | CreateProjectPayload | meta, namespace_uuid | none |
| Query | yes | build_create_payload | CreateQueryPayload | meta, spec | none |
| QueryMalware | yes | build_create_payload | CreateQueryMalwarePayload | meta, spec | none |
| QuerySimilarPackages | yes | build_create_payload | CreateQuerySimilarPackagesPayload | meta, spec | none |
| QueryVulnerability | yes | build_create_payload | CreateQueryVulnerabilityPayload | meta, spec | none |
| Repository | yes | build_create_payload | CreateRepositoryPayload | meta, spec | none |
| RepositoryVersion | yes | build_create_payload | CreateRepositoryVersionPayload | meta, spec | none |
| SavedQuery | no | build_create_payload | CreateSavedQueryPayload | meta, spec | none |
| ScanLogRequest | yes | N/A | N/A | N/A | N/A |
| ScanProfile | yes | build_create_payload | CreateScanProfilePayload | meta, spec | propagate |
| ScanResult | yes | build_create_payload | CreateScanResultPayload | context, meta, spec | none |
| ScanWorkflow | no | N/A | N/A | N/A | N/A |
| ScanWorkflowResult | no | N/A | N/A | N/A | N/A |
| SemgrepRule | yes | build_create_payload | CreateSemgrepRulePayload | meta, spec | disabled, propagate |
| VectorStore | no | N/A | N/A | N/A | N/A |
| VectorStoreQuery | yes | build_create_payload | CreateVectorStoreQueryPayload | meta, spec | none |
| VersionUpgrade | no | N/A | N/A | N/A | N/A |
| Vulnerability | no | N/A | N/A | N/A | N/A |

## Update mutable fields

| Resource | SDK update support | Mutable field paths (`get_mutable_fields_cls`) |
|----------|--------------------|----------------------------------------------|
| APIKey | no | meta.description, meta.tags |
| AuditLog | no | meta.description, meta.tags |
| AuthenticationLog | no | meta.description, meta.tags |
| AuthorizationPolicy | yes | meta.description, meta.name, meta.tags, propagate, spec |
| CodeOwners | yes | meta.description, meta.tags |
| DependencyMetadata | no | meta.description, meta.name, meta.tags, spec |
| EndorLicense | no | meta.description, meta.tags |
| Finding | yes | context.tags, meta.tags, spec.dismiss, spec.finding_tags, spec.remediation |
| FindingLog | no | meta.description, meta.tags |
| IdentityProvider | no | — |
| Installation | yes | meta.description, meta.name, meta.tags, spec |
| Invitation | yes | meta.description, meta.tags |
| LinterResult | no | meta.description, meta.name, meta.tags, spec |
| Malware | no | meta.description, meta.tags |
| Metric | yes | meta.description, meta.name, meta.tags, spec |
| Namespace | yes | meta.description |
| NotificationTarget | yes | meta.description, meta.tags |
| PRCommentConfig | yes | meta.description, meta.tags |
| PackageFirewallLog | no | — |
| PackageLicense | yes | meta.description, meta.name, meta.tags, spec |
| PackageVersion | yes | meta.description, meta.name, meta.tags, spec |
| Policy | yes | meta.description, meta.name, meta.tags, propagate, spec.disable, spec.project_exceptions, spec.project_selector, spec.rule, spec.template_values |
| PolicyTemplate | no | meta.description, meta.tags |
| Project | yes | meta.description, meta.tags, processing_status.disable_automated_scan, processing_status.scan_state |
| Query | no | — |
| QueryMalware | no | meta.description, meta.tags |
| QuerySimilarPackages | no | — |
| QueryVulnerability | no | meta.description, meta.tags |
| Repository | yes | meta.description, meta.name, meta.tags, spec |
| RepositoryVersion | yes | meta.description, meta.name, meta.tags, spec |
| SavedQuery | no | — |
| ScanLogRequest | no | meta.description, meta.tags |
| ScanProfile | yes | meta.description, meta.name, meta.tags, spec |
| ScanResult | yes | meta.description, meta.name, meta.tags, spec |
| ScanWorkflow | no | meta.description, meta.tags |
| ScanWorkflowResult | no | meta.description, meta.tags |
| SemgrepRule | yes | meta.description, meta.name, meta.tags, spec |
| VectorStore | no | meta.description, meta.tags |
| VectorStoreQuery | no | meta.description, meta.tags |
| VersionUpgrade | no | meta.description, meta.tags |
| Vulnerability | no | meta.description, meta.tags |

## Identity kwargs (`list()` helpers)

| Resource | Identity kwargs -> filter paths |
|----------|---------------------------------|
| APIKey | — |
| AuditLog | — |
| AuthenticationLog | — |
| AuthorizationPolicy | name->meta.name |
| CodeOwners | name->meta.name |
| DependencyMetadata | — |
| EndorLicense | — |
| Finding | name->meta.name |
| FindingLog | — |
| IdentityProvider | — |
| Installation | name->meta.name |
| Invitation | name->meta.name |
| LinterResult | — |
| Malware | name->meta.name |
| Metric | name->meta.name |
| Namespace | name->meta.name |
| NotificationTarget | name->meta.name |
| PRCommentConfig | name->meta.name |
| PackageFirewallLog | — |
| PackageLicense | — |
| PackageVersion | name->meta.name |
| Policy | name->meta.name, policy_type->spec.policy_type |
| PolicyTemplate | — |
| Project | name->meta.name |
| Query | — |
| QueryMalware | — |
| QuerySimilarPackages | — |
| QueryVulnerability | — |
| Repository | git_url->spec.vcs_url, name->meta.name, vcs_url->spec.vcs_url |
| RepositoryVersion | name->meta.name |
| SavedQuery | — |
| ScanLogRequest | — |
| ScanProfile | name->meta.name |
| ScanResult | name->meta.name |
| ScanWorkflow | — |
| ScanWorkflowResult | — |
| SemgrepRule | name->meta.name |
| VectorStore | name->meta.name |
| VectorStoreQuery | — |
| VersionUpgrade | — |
| Vulnerability | name->meta.name |

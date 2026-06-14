# Resources (SDK API Surface)

Auto-generated from `src/endorlabs/registry.py` and OpenAPI spec.
Model sync contract: `src/endorlabs/generated/registry_contract.py` (41 resources, 41 canonical entities).
Each operation column is `sdk/spec` where spec is derived from OpenAPI
collection and item paths.

Legend:
- `yes/yes`: SDK operation exists and OpenAPI operation exists.
- `no/yes`: API supports it, SDK intentionally does not expose it on
  the facade.
- `yes/no`: SDK exposes operation but collection/item OpenAPI
  method was not found.
- `no/no`: operation not exposed by SDK and not present in OpenAPI paths.
- Scope values: `tenant` (default namespace resolution), `oss`
  (namespace fixed to `oss`).

## Model-sync coverage snapshot

- facade contract resources: `41`
- canonical entities (union): `41`

| Resource | List (sdk/spec) | Get (sdk/spec) | Create (sdk/spec) | Update (sdk/spec) | Delete (sdk/spec) | Scope | Parent | Limitations |
|----------|------------------|----------------|-------------------|-------------------|-------------------|-------|--------|-------------|
| APIKey | yes/yes | yes/yes | yes/yes | no/no | yes/yes | tenant | — | — |
| AuditLog | yes/yes | yes/yes | yes/yes | no/no | yes/yes | tenant | — | — |
| AuthenticationLog | yes/yes | yes/yes | no/yes | no/no | no/yes | tenant | — | Tenant-context read-only resource |
| AuthorizationPolicy | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | — |
| CodeOwners | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | — |
| DependencyMetadata | yes/yes | yes/yes | yes/yes | no/no | yes/yes | tenant | — | Relationship resource; see dependency-metadata contract |
| EndorLicense | yes/yes | yes/yes | no/yes | no/no | no/yes | tenant | — | Tenant-context read-only resource |
| Finding | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | Scan-generated |
| FindingLog | yes/yes | yes/yes | yes/yes | no/no | yes/yes | tenant | — | — |
| IdentityProvider | yes/yes | yes/yes | no/yes | no/no | no/yes | tenant | — | — |
| Installation | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | Platform-managed |
| Invitation | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | — |
| LinterResult | yes/yes | yes/yes | yes/yes | no/no | yes/yes | tenant | — | Scan-generated |
| Malware | yes/yes | yes/yes | no/yes | no/no | no/yes | oss | — | OSS-scoped malware dataset |
| Metric | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | Analytics-generated |
| Namespace | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | — |
| NotificationTarget | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | — |
| PRCommentConfig | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | — |
| PackageFirewallLog | yes/yes | yes/yes | no/yes | no/no | no/yes | tenant | — | — |
| PackageLicense | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | — |
| PackageVersion | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | Scan-discovered; API may return 501 for PATCH |
| Policy | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | Rego in payload |
| PolicyTemplate | yes/yes | yes/yes | no/yes | no/no | no/yes | tenant | — | Tenant-context read-only resource |
| Project | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | Platform-managed |
| Query | no/no | no/no | yes/yes | no/no | no/no | tenant | — | — |
| QueryMalware | no/no | no/no | yes/yes | no/no | no/no | oss | — | Request-based query endpoint (create only) |
| QuerySimilarPackages | no/no | no/no | yes/yes | no/no | no/no | tenant | — | — |
| QueryVulnerability | no/no | no/no | yes/yes | no/no | no/no | oss | — | Request-based query endpoint (create only) |
| Repository | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | Platform-managed |
| RepositoryVersion | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | project | Platform-managed |
| SavedQuery | yes/yes | yes/yes | no/yes | no/no | no/yes | tenant | — | — |
| ScanLogRequest | no/no | no/no | yes/yes | no/no | no/no | tenant | — | Request-based only; no list/get/delete for log messages |
| ScanProfile | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | — |
| ScanResult | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | project | Scan-generated |
| ScanWorkflow | yes/yes | yes/yes | no/yes | no/no | yes/yes | tenant | — | Platform-managed |
| ScanWorkflowResult | yes/yes | yes/yes | no/yes | no/no | yes/yes | tenant | — | Platform-managed |
| SemgrepRule | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | — |
| VectorStore | yes/yes | yes/yes | no/yes | no/no | no/yes | tenant | — | — |
| VectorStoreQuery | no/no | no/no | yes/yes | no/no | no/no | tenant | — | — |
| VersionUpgrade | yes/yes | yes/yes | no/yes | no/no | yes/yes | tenant | — | Platform-managed |
| Vulnerability | yes/yes | yes/yes | no/yes | no/no | no/yes | oss | — | OSS-scoped vulnerability dataset |

Spec (local preferred): `.endorlabs-context/platform/openapi/openapiv2.swagger.json`.
Fallback URL: `https://api.endorlabs.com/download/openapiv2.swagger.json`.

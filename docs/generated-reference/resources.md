# Resources (SDK API Surface)

Auto-generated from `src/endorlabs/registry.py` and OpenAPI spec.
Model sync mapping: `workspace/model-sync/custom_mapping/mapping/entity_mapping.json` (211 entities).
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

| Resource | List (sdk/spec) | Get (sdk/spec) | Create (sdk/spec) | Update (sdk/spec) | Delete (sdk/spec) | Scope | Parent | Limitations |
|----------|------------------|----------------|-------------------|-------------------|-------------------|-------|--------|-------------|
## Model-sync coverage snapshot

- mapped entities: `211`
- generated artifact files: `151`
- facade contract resources: `41`
- registry parity status: `pass`
- operation metadata entries: `739`
- payload schema resources: `41`
- runtime model import index entries: `41`

| APIKey | yes/yes | yes/yes | yes/yes | no/no | yes/yes | tenant | — | — |
| AuditLog | yes/yes | yes/yes | yes/yes | no/no | yes/yes | tenant | — | — |
| AuthenticationLog | yes/yes | yes/yes | no/yes | no/no | no/yes | tenant | — | — |
| AuthorizationPolicy | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | — |
| CodeOwners | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | — |
| DependencyMetadata | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | oss | — | — |
| EndorLicense | yes/yes | yes/yes | no/yes | no/no | no/yes | tenant | — | — |
| Finding | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | — |
| FindingLog | yes/yes | yes/yes | yes/yes | no/no | yes/yes | tenant | — | — |
| Installation | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | — |
| Invitation | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | — |
| LinterResult | yes/yes | yes/yes | yes/yes | no/no | yes/yes | tenant | — | — |
| Malware | yes/yes | yes/yes | no/yes | no/no | no/yes | oss | — | — |
| Metric | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | — |
| Namespace | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | — |
| NotificationTarget | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | — |
| PRCommentConfig | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | — |
| PackageLicense | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | oss | — | — |
| PackageVersion | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | — |
| Policy | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | — |
| PolicyTemplate | yes/yes | yes/yes | no/yes | no/no | no/yes | tenant | — | — |
| Project | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | — |
| QueryMalware | no/no | no/no | yes/yes | no/no | no/no | oss | — | — |
| QueryVulnerability | no/no | no/no | yes/yes | no/no | no/no | oss | — | — |
| Repository | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | — |
| RepositoryVersion | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | project | — |
| ScanLogRequest | no/no | no/no | yes/yes | no/no | no/no | tenant | — | — |
| ScanProfile | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | — |
| ScanResult | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | project | — |
| ScanWorkflow | yes/yes | yes/yes | no/yes | no/no | yes/yes | tenant | — | — |
| ScanWorkflowResult | yes/yes | yes/yes | no/yes | no/no | yes/yes | tenant | — | — |
| SemgrepRule | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | — |
| V1IdentityProvider | yes/yes | yes/yes | no/yes | no/no | no/yes | tenant | — | — |
| V1PackageFirewallLog | yes/yes | yes/yes | no/yes | no/no | no/yes | tenant | — | — |
| V1Query | yes/no | yes/no | no/yes | no/no | no/no | tenant | — | — |
| V1QuerySimilarPackages | yes/no | yes/no | no/yes | no/no | no/no | tenant | — | — |
| V1SavedQuery | yes/yes | yes/yes | no/yes | no/no | no/yes | tenant | — | — |
| VectorStore | yes/yes | yes/yes | no/yes | no/no | no/yes | tenant | — | — |
| VectorStoreQuery | no/no | no/no | yes/yes | no/no | no/no | tenant | — | — |
| VersionUpgrade | yes/yes | yes/yes | no/yes | no/no | yes/yes | tenant | — | — |
| Vulnerability | yes/yes | yes/yes | no/yes | no/no | no/yes | oss | — | — |

Spec (local preferred): `.endorlabs-context/openapiv2.swagger.json`.
Fallback URL: `https://api.endorlabs.com/download/openapiv2.swagger.json`.

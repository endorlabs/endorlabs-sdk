# Resources (SDK API Surface)

Auto-generated from `src/endorlabs/registry.py` and OpenAPI spec.
Model sync contract: `src/endorlabs/generated/registry_contract.py` (46 resources, 46 canonical entities).
Each operation column is `sdk/spec` where spec is derived from OpenAPI
collection and item paths.

Legend:
- `yes/yes`: SDK operation exists and OpenAPI operation exists.
- `no/yes`: API supports it, SDK intentionally does not expose it on
  the facade.
- `yes/no`: SDK exposes operation but collection/item OpenAPI
  method was not found.
- `no/no`: operation not exposed by SDK and not present in OpenAPI paths.
- **Limitations** = customer user-space semantics (from
  `resource_user_space.json`); **sdk/spec** shows SDK exposure vs OpenAPI.
- Scope values: `tenant` (default namespace resolution), `oss`
  (namespace fixed to `oss`).

Customer **tenant admin** (`SYSTEM_ROLE_ADMIN`) is the primary writer
where user-space docs say `admin-only` or `yes`. Endor internal account
gates (`IsCallerEndorAccount`) are additional field/route restrictions.

## Model-sync coverage snapshot

- facade contract resources: `46`
- canonical entities (union): `46`

| Resource | List (sdk/spec) | Get (sdk/spec) | Create (sdk/spec) | Update (sdk/spec) | Delete (sdk/spec) | Scope | Parent | Limitations |
|----------|------------------|----------------|-------------------|-------------------|-------------------|-------|--------|-------------|
| APIKey | yes/yes | yes/yes | yes/yes | no/no | yes/yes | tenant | — | Admin-managed programmatic credentials |
| AuditLog | yes/yes | yes/yes | no/yes | no/no | no/yes | tenant | — | Append-only audit trail |
| AuthenticationLog | yes/yes | yes/yes | no/yes | no/no | no/yes | tenant | — | Tenant-context read-only resource |
| AuthorizationPolicy | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | Permission grants for identities |
| CodeOwners | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | Project-scoped code ownership |
| DependencyMetadata | yes/yes | yes/yes | yes/yes | no/no | yes/yes | tenant | — | Relationship resource; see dependency-metadata contract |
| EndorLicense | yes/yes | yes/yes | no/yes | no/no | no/yes | tenant | — | Tenant-context read-only resource |
| Finding | yes/yes | yes/yes | no/yes | yes/no | yes/yes | tenant | — | Scan-generated |
| FindingLog | yes/yes | yes/yes | no/yes | no/no | no/yes | tenant | — | Finding state history log |
| HuggingFaceOrganization | yes/yes | yes/yes | no/yes | no/no | no/yes | tenant | — | HF org inventory after Installation sync; configure via Installation |
| IdentityProvider | yes/yes | yes/yes | no/yes | no/no | no/yes | tenant | — | SSO identity provider configuration |
| Installation | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | Platform-managed |
| Invitation | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | User invitations |
| LinterResult | yes/yes | yes/yes | no/yes | no/no | no/yes | tenant | — | Scan-generated |
| Malware | yes/yes | yes/yes | no/yes | no/no | no/yes | oss | — | OSS-scoped malware catalog |
| MalwareExposure | yes/yes | yes/yes | no/yes | no/no | no/yes | tenant | — | Tenant malware exposure index |
| MalwareExposureQuery | no/no | no/no | yes/yes | no/no | no/no | tenant | — | Query tenant malware exposure |
| Metric | yes/yes | yes/yes | no/yes | no/no | no/yes | tenant | — | Analytics-generated |
| Namespace | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | Tenant hierarchy nodes |
| NotificationTarget | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | Notification delivery endpoints |
| PRCommentConfig | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | PR comment integration settings |
| PackageFirewallLog | yes/yes | yes/yes | no/yes | no/no | no/yes | tenant | — | Package firewall audit events |
| PackageLicense | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | Package license metadata |
| PackageManager | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | Package manager integration settings |
| PackageVersion | yes/yes | yes/yes | no/yes | yes/no | yes/yes | tenant | — | Scan-discovered; API may return 501 for PATCH |
| Policy | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | Rego in payload |
| PolicyTemplate | yes/yes | yes/yes | no/yes | no/no | no/yes | tenant | — | Read-only policy templates |
| Project | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | Platform-managed registration; scan inventory is derived |
| Query | no/no | no/no | yes/yes | no/no | no/no | tenant | — | Graph join query (create only) |
| QueryMalware | no/no | no/no | yes/yes | no/no | no/no | oss | — | Request-based query endpoint (create only) |
| QuerySimilarPackages | no/no | no/no | yes/yes | no/no | no/no | tenant | — | Similar-package query (create only) |
| QueryVulnerability | no/no | no/no | yes/yes | no/no | no/no | oss | — | Request-based query endpoint (create only) |
| Repository | yes/yes | yes/yes | no/yes | yes/no | no/yes | tenant | — | Platform-managed |
| RepositoryVersion | yes/yes | yes/yes | no/yes | yes/no | no/yes | tenant | project | Platform-managed |
| SavedQuery | yes/yes | yes/yes | no/yes | no/no | no/yes | tenant | — | Saved query definitions |
| ScanLogRequest | no/no | no/no | yes/yes | no/no | no/no | tenant | — | Request-based only; no list/get/delete for log messages |
| ScanProfile | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | Scan configuration profiles |
| ScanResult | yes/yes | yes/yes | no/yes | yes/no | yes/yes | tenant | project | Scan-generated |
| ScanWorkflow | yes/yes | yes/yes | no/yes | no/no | yes/yes | tenant | — | Platform-managed |
| ScanWorkflowResult | yes/yes | yes/yes | no/yes | no/no | yes/yes | tenant | — | Platform-managed |
| SemgrepRule | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | Custom SAST rules |
| SystemConfig | yes/yes | yes/yes | no/yes | yes/no | no/yes | tenant | — | Singleton per namespace; onboard-seeded; ADMIN update |
| VectorStore | yes/yes | yes/yes | no/yes | no/no | no/yes | tenant | — | Vector store inventory (read-only) |
| VectorStoreQuery | no/no | no/no | yes/yes | no/no | no/no | tenant | — | Natural-language vector store query |
| VersionUpgrade | yes/yes | yes/yes | no/yes | no/no | yes/yes | tenant | — | Platform-managed |
| Vulnerability | yes/yes | yes/yes | no/yes | no/no | no/yes | oss | — | OSS-scoped vulnerability dataset |

Spec (local preferred): `.endorlabs/_cache/openapi.json`.
Fallback URL: `https://api.endorlabs.com/download/openapiv2.swagger.json`.

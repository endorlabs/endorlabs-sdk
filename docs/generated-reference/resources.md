# Resources (SDK API Surface)

Auto-generated from `src/endorlabs/registry.py` and OpenAPI spec.
Model sync mapping: `workspace/model-sync/custom_mapping/mapping/entity_mapping.json` (337 entities).
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
  (namespace fixed to `oss`),
  `system` (system-owned resources; additional SDK constraints may apply).

| Resource | List (sdk/spec) | Get (sdk/spec) | Create (sdk/spec) | Update (sdk/spec) | Delete (sdk/spec) | Scope | Parent | Limitations |
|----------|------------------|----------------|-------------------|-------------------|-------------------|-------|--------|-------------|
## Model-sync coverage snapshot

- mapped entities: `337`
- generated artifact files: `219`
- facade contract resources: `33`
- registry parity status: `pass`
- operation metadata entries: `709`
- payload schema resources: `33`
- runtime model import index entries: `33`

| api_key | yes/yes | yes/yes | yes/yes | no/no | yes/yes | tenant | — | — |
| audit_log | yes/yes | yes/yes | yes/yes | no/no | yes/yes | tenant | — | — |
| authentication_log | yes/yes | yes/yes | no/yes | no/no | no/yes | system | — | System-owned; get only for namespace="oss" |
| authorization_policy | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | — |
| code_owners | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | — |
| dependency_metadata | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | oss | — | OSS namespace; relationship resource |
| endor_license | yes/yes | yes/yes | no/yes | no/no | no/yes | system | — | System-owned; get only for namespace="oss" |
| finding | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | Scan-generated |
| finding_log | yes/yes | yes/yes | yes/yes | no/no | yes/yes | tenant | — | — |
| installation | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | Platform-managed |
| invitation | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | — |
| linter_result | yes/yes | yes/yes | yes/yes | no/no | yes/yes | tenant | — | Scan-generated |
| malware | yes/yes | yes/yes | no/yes | no/no | no/yes | oss | — | OSS-scoped malware dataset |
| metric | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | Analytics-generated |
| namespace | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | — |
| notification_target | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | — |
| package_license | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | oss | — | — |
| package_version | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | Scan-discovered; API may return 501 for PATCH |
| policy | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | Rego in payload |
| policy_template | yes/yes | yes/yes | no/yes | no/no | no/yes | system | — | System-owned; get only for namespace="oss" |
| project | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | Platform-managed |
| query_malware | no/no | no/no | yes/yes | no/no | no/no | oss | — | Request-based query endpoint (create only) |
| query_vulnerability | no/no | no/no | yes/yes | no/no | no/no | oss | — | Request-based query endpoint (create only) |
| repository | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | Platform-managed |
| repository_version | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | project | Platform-managed |
| scan_log_request | no/no | no/no | yes/yes | no/no | no/no | tenant | — | Request-based only; no list/get/delete for log messages |
| scan_profile | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | — |
| scan_result | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | project | Scan-generated |
| scan_workflow | yes/yes | yes/yes | no/yes | no/no | yes/yes | tenant | — | Platform-managed |
| scan_workflow_result | yes/yes | yes/yes | no/yes | no/no | yes/yes | tenant | — | Platform-managed |
| semgrep_rule | yes/yes | yes/yes | yes/yes | yes/no | yes/yes | tenant | — | — |
| version_upgrade | yes/yes | yes/yes | no/yes | no/no | yes/yes | tenant | — | Platform-managed |
| vulnerability | yes/yes | yes/yes | no/yes | no/no | no/yes | oss | — | OSS-scoped vulnerability dataset |

Spec (local preferred): `.endorlabs-context/openapiv2.swagger.json`.
Fallback URL: `https://api.endorlabs.com/download/openapiv2.swagger.json`.

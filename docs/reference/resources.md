# Resources (SDK API Surface)

One table: resource name, operations, limitations. See OpenAPI spec for full schema.

| Resource | List | Get | Create | Update | Delete | Limitations |
|----------|------|-----|--------|--------|--------|-------------|
| namespace | yes | yes | yes | yes (update_mask required) | yes | — |
| project | yes | yes | no | yes (update_mask) | no | Platform-managed |
| repository | yes | yes | no | yes (update_mask) | no | Platform-managed |
| repository_version | yes | yes | no | yes (update_mask) | no | Platform-managed |
| package_version | yes | yes | no | yes (update_mask) | no | Scan-discovered; API may return 501 for PATCH |
| finding | yes | yes | no | yes (update_mask) | no | Scan-generated |
| scan_result | yes | yes | no | yes (update_mask) | no | Scan-generated |
| scan_profile | yes | yes | yes | yes (update_mask) | yes | — |
| policy | yes | yes | yes | yes (update_mask) | yes | — |
| authorization_policy | yes | yes | yes | yes (update_mask) | yes | — |
| api_key | yes | yes | yes | no | yes | — |
| audit_log | yes | yes | no | no | no | Active + archived; see module |
| installation | yes | yes | no | yes (update_mask) | no | Platform-managed |
| metric | yes | yes | no | yes (update_mask) | no | Analytics-generated |
| dependency_metadata | yes | yes | no | yes (update_mask) | no | OSS namespace; relationship resource |
| linter_result | yes | yes | no | yes (update_mask) | no | Scan-generated |
| finding_log | yes | yes | no | no | no | — |
| package_license | yes | yes | no | yes (update_mask) | no | OSS namespace |
| scan_log_request | no | no | yes (request-based) | no | no | Request-based API; see module |
| semgrep_rule | yes | yes | yes | yes (update_mask) | yes | — |

Spec path: `external_docs/openapi-swagger.json`. Deep-dive: [namespace.md](namespace.md).

# Resources (SDK API Surface)

The table matches the SDK registry; OpenAPI paths are under `/v1/namespaces/{tenant_meta.namespace}/<segment>` (source of truth: [registry.py](../../src/endorlabs/registry.py) and the spec). The SDK exposes all operations; see `endorlabs.resources.<name>` and docstrings for signatures, return types, and raised exceptions.

**Update:** For resources with Update = yes, `update_mask` is **required** (comma-separated field paths). Sparse PATCH is always used.

| Resource | List | Get | Create | Update | Delete | Limitations |
|----------|------|-----|--------|--------|--------|-------------|
| namespace | yes | yes | yes | yes (update_mask required) | yes | — |
| project | yes | yes | yes | yes (update_mask required) | yes | Platform-managed |
| repository | yes | yes | yes | yes (update_mask required) | yes | Platform-managed |
| repository_version | yes | yes | yes | yes (update_mask required) | yes | Platform-managed |
| package_version | yes | yes | yes | yes (update_mask required) | yes | Scan-discovered; API may return 501 for PATCH |
| finding | yes | yes | yes | yes (update_mask required) | yes | Scan-generated |
| scan_result | yes | yes | yes | yes (update_mask required) | yes | Scan-generated |
| scan_profile | yes | yes | yes | yes (update_mask required) | yes | — |
| policy | yes | yes | yes | yes (update_mask required) | yes | Rego in payload; Rego reference: [docs.endorlabs.com](https://docs.endorlabs.com/). |
| authorization_policy | yes | yes | yes | yes (update_mask required) | yes | — |
| api_key | yes | yes | yes | no | yes | — |
| audit_log | yes | yes | yes | no | yes | Active + archived; see module |
| installation | yes | yes | yes | yes (update_mask required) | yes | Platform-managed |
| metric | yes | yes | yes | yes (update_mask required) | yes | Analytics-generated |
| dependency_metadata | yes | yes | yes | no | yes | OSS namespace; relationship resource |
| linter_result | yes | yes | yes | no | yes | Scan-generated |
| finding_log | yes | yes | yes | no | yes | — |
| package_license | yes | yes | yes | yes (update_mask required) | yes | OSS namespace |
| scan_log_request | no | no | yes (request-based) | no | no | Request-based only; scan logs = response `spec.log_messages`; no LIST/GET for scan logs. See module. |
| semgrep_rule | yes | yes | yes | yes (update_mask required) | yes | — |
| authentication_log | yes | yes (oss only) | no | no | no | System-owned; GET only when namespace is "oss"; use list() for system/tenant. |
| endor_license | yes | yes (oss only) | no | no | no | System-owned; GET only when namespace is "oss"; use list() for system/tenant. |
| policy_template | yes | yes (oss only) | no | no | no | System-owned; GET only when namespace is "oss"; use list() for system/tenant. |

System-owned resources (authentication_log, endor_license, policy_template) are typed as `SystemResourceFacade[T]` on the Client; `.get(id, namespace="oss")` is supported; for system/tenant namespace use `client.<resource>.list()`. OSS-scoped resources (dependency_metadata, package_license) are typed as `OssResourceFacade[T]`; namespace is fixed to "oss" (no namespace param required).

Spec: <https://api.endorlabs.com/download/openapiv2.swagger.json> (workflow downloads to `external_docs/` in CI). Deep-dive: [namespace.md](namespace.md).


"""Generated create convenience field lists for build_create_payload helpers."""

from __future__ import annotations

A_P_I_KEY_SPEC_FIELDS = ("permissions", "expiration_time")
A_P_I_KEY_SPEC_REQUIRED = ("permissions", "expiration_time")
A_P_I_KEY_META_FIELDS = ()
A_P_I_KEY_PAYLOAD_TOP_LEVEL_FIELDS = ("meta", "propagate", "tenant_meta")

AUDIT_LOG_SPEC_FIELDS = (
    "operation",
    "message_uuid",
    "message_kind",
    "payload",
    "error",
    "claims",
    "remote_address",
)
AUDIT_LOG_SPEC_REQUIRED = ("operation",)
AUDIT_LOG_META_FIELDS = ()
AUDIT_LOG_PAYLOAD_TOP_LEVEL_FIELDS = ("meta", "tenant_meta")

AUTHENTICATION_LOG_SPEC_FIELDS = (
    "success",
    "authorized_tenants",
    "error_message",
    "status",
    "claims",
    "remote_address",
    "uri",
)
AUTHENTICATION_LOG_SPEC_REQUIRED = ()
AUTHENTICATION_LOG_META_FIELDS = ()
AUTHENTICATION_LOG_PAYLOAD_TOP_LEVEL_FIELDS = ("meta", "tenant_meta")

AUTHORIZATION_POLICY_SPEC_FIELDS = (
    "clause",
    "target_namespaces",
    "propagate",
    "permissions",
    "expiration_time",
)
AUTHORIZATION_POLICY_SPEC_REQUIRED = (
    "clause",
    "target_namespaces",
    "propagate",
    "permissions",
)
AUTHORIZATION_POLICY_META_FIELDS = ()
AUTHORIZATION_POLICY_PAYLOAD_TOP_LEVEL_FIELDS = ("meta", "propagate", "tenant_meta")

CODE_OWNERS_SPEC_FIELDS = ("patterns", "version")
CODE_OWNERS_SPEC_REQUIRED = ()
CODE_OWNERS_META_FIELDS = ()
CODE_OWNERS_PAYLOAD_TOP_LEVEL_FIELDS = ("meta", "tenant_meta")

DEPENDENCY_METADATA_SPEC_FIELDS = ("data",)
DEPENDENCY_METADATA_SPEC_REQUIRED = ()
DEPENDENCY_METADATA_META_FIELDS = ("name",)
DEPENDENCY_METADATA_PAYLOAD_TOP_LEVEL_FIELDS = ("meta", "tenant_meta")

ENDOR_LICENSE_SPEC_FIELDS = (
    "target_namespace",
    "type",
    "read_access_until",
    "write_access_until",
    "bundle_info",
    "quota",
    "is_customer",
    "excluded_feature_types",
    "license_configurations",
    "salesforce_account_id",
    "scan_credit_grants",
    "credits_period_start",
)
ENDOR_LICENSE_SPEC_REQUIRED = ("target_namespace",)
ENDOR_LICENSE_META_FIELDS = ()
ENDOR_LICENSE_PAYLOAD_TOP_LEVEL_FIELDS = ("meta", "tenant_meta")

FINDING_SPEC_FIELDS = (
    "project_uuid",
    "last_processed",
    "level",
    "summary",
    "finding_tags",
    "target_uuid",
    "extra_key",
    "dismiss",
    "remediation",
    "finding_metadata",
    "method",
    "target_dependency_package_name",
    "target_dependency_name",
    "target_dependency_version",
    "explanation",
    "remediation_action",
    "source_code_version",
    "reachable_paths",
    "ecosystem",
    "finding_categories",
    "relationship",
    "latest_version",
    "dependency_file_paths",
    "approximation",
    "proposed_version",
    "exceptions",
    "actions",
    "fixing_upgrades",
    "fixing_patch",
    "code_owners",
    "location_urls",
    "call_graph_analysis_type",
    "snooze",
    "ignore",
)
FINDING_SPEC_REQUIRED = (
    "project_uuid",
    "last_processed",
    "level",
    "summary",
    "finding_tags",
    "target_uuid",
    "extra_key",
)
FINDING_META_FIELDS = ()
FINDING_PAYLOAD_TOP_LEVEL_FIELDS = ("context", "meta", "tenant_meta")

FINDING_LOG_SPEC_FIELDS = (
    "finding_uuid",
    "finding_parent_kind",
    "finding_parent_uuid",
    "operation",
    "introduced_at",
    "method",
    "level",
    "finding_tags",
    "finding_categories",
    "resolved_at",
    "days_unresolved",
    "ecosystem",
    "target_uuid",
    "target_dependency_package_name",
    "approximation",
    "finding_parent_name",
    "snooze",
    "location",
)
FINDING_LOG_SPEC_REQUIRED = (
    "finding_uuid",
    "finding_parent_kind",
    "finding_parent_uuid",
    "operation",
    "introduced_at",
    "method",
    "level",
    "finding_tags",
    "finding_categories",
)
FINDING_LOG_META_FIELDS = ()
FINDING_LOG_PAYLOAD_TOP_LEVEL_FIELDS = ("context", "meta", "tenant_meta")

IDENTITY_PROVIDER_SPEC_FIELDS = ("oidc_provider", "saml_provider")
IDENTITY_PROVIDER_SPEC_REQUIRED = ()
IDENTITY_PROVIDER_META_FIELDS = ()
IDENTITY_PROVIDER_PAYLOAD_TOP_LEVEL_FIELDS = ("meta", "propagate", "tenant_meta")

INSTALLATION_SPEC_FIELDS = (
    "public",
    "external_id",
    "suspended",
    "project_uuids",
    "login",
    "invalid",
    "enabled_features",
    "platform_source",
    "platform_type",
    "github_config",
    "azure_config",
    "gitlab_config",
    "bitbucket_config",
    "huggingface_config",
    "include_archived_repos",
    "installation_error_message",
    "scm_app_uuid",
    "cleanup_stale_namespaces",
)
INSTALLATION_SPEC_REQUIRED = ()
INSTALLATION_META_FIELDS = ()
INSTALLATION_PAYLOAD_TOP_LEVEL_FIELDS = (
    "meta",
    "processing_status",
    "propagate",
    "tenant_meta",
)

INVITATION_SPEC_FIELDS = ("user_email",)
INVITATION_SPEC_REQUIRED = ("user_email",)
INVITATION_META_FIELDS = ()
INVITATION_PAYLOAD_TOP_LEVEL_FIELDS = ("meta", "tenant_meta")

LINTER_RESULT_SPEC_FIELDS = (
    "project_uuid",
    "origin",
    "level",
    "extra_key",
    "version",
    "sarif_result",
    "ai_result",
    "ecosystem",
    "semgrep",
    "secret",
    "aisast",
    "fingerprints",
    "fingerprint_count",
    "distribution_format",
    "ref",
    "storage_location",
    "suppressed",
    "linter_correctness_analyses",
    "endor_fingerprint",
)
LINTER_RESULT_SPEC_REQUIRED = ("project_uuid", "origin", "level", "extra_key")
LINTER_RESULT_META_FIELDS = ()
LINTER_RESULT_PAYLOAD_TOP_LEVEL_FIELDS = ("context", "meta", "tenant_meta")

MALWARE_SPEC_FIELDS = (
    "ecosystem",
    "package_name",
    "ranges",
    "version",
    "status",
    "pkg_release_date",
    "malware_detected_on",
    "advisory_published",
    "advisory_last_updated",
    "reasons",
    "purl",
    "summary",
    "contested",
    "contested_reason",
    "source",
    "aliases",
    "references",
    "upsert_key",
    "package_version",
    "additional_notes",
    "cwe_id",
    "deletion_exempt",
)
MALWARE_SPEC_REQUIRED = ("ecosystem", "package_name")
MALWARE_META_FIELDS = ()
MALWARE_PAYLOAD_TOP_LEVEL_FIELDS = ("meta", "tenant_meta")

METRIC_SPEC_FIELDS = ("analytic", "project_uuid", "metric_values", "raw")
METRIC_SPEC_REQUIRED = ("analytic", "project_uuid", "metric_values")
METRIC_META_FIELDS = ()
METRIC_PAYLOAD_TOP_LEVEL_FIELDS = ("context", "meta", "tenant_meta")

NAMESPACE_SPEC_FIELDS = ("managed",)
NAMESPACE_SPEC_REQUIRED = ()
NAMESPACE_META_FIELDS = ()
NAMESPACE_PAYLOAD_TOP_LEVEL_FIELDS = ("meta", "tenant_meta")

NOTIFICATION_TARGET_SPEC_FIELDS = ("action", "custom_template")
NOTIFICATION_TARGET_SPEC_REQUIRED = ("action",)
NOTIFICATION_TARGET_META_FIELDS = ()
NOTIFICATION_TARGET_PAYLOAD_TOP_LEVEL_FIELDS = ("meta", "propagate", "tenant_meta")

P_R_COMMENT_CONFIG_SPEC_FIELDS = ("template", "platform_type")
P_R_COMMENT_CONFIG_SPEC_REQUIRED = ("template",)
P_R_COMMENT_CONFIG_META_FIELDS = ()
P_R_COMMENT_CONFIG_PAYLOAD_TOP_LEVEL_FIELDS = ("meta", "propagate", "tenant_meta")

PACKAGE_FIREWALL_LOG_SPEC_FIELDS = (
    "ecosystem",
    "package_name",
    "package_version",
    "request_type",
    "block_reason",
    "malware_uuid",
    "api_key_id",
    "remote_address",
    "request_uri",
    "blocked_at",
    "package_age_hours",
    "reason",
    "action",
    "package_license",
    "action_at",
    "cvss_severity_level",
    "cvss_vuln_uuid",
    "api_key_name",
    "user",
)
PACKAGE_FIREWALL_LOG_SPEC_REQUIRED = ("ecosystem", "package_name")
PACKAGE_FIREWALL_LOG_META_FIELDS = ()
PACKAGE_FIREWALL_LOG_PAYLOAD_TOP_LEVEL_FIELDS = ("meta", "tenant_meta")

PACKAGE_LICENSE_SPEC_FIELDS = (
    "code_licenses",
    "package_manager_licenses",
    "copyrights",
    "declared_code_licenses",
    "license_text",
    "all_licenses",
    "project_uuid",
    "version",
)
PACKAGE_LICENSE_SPEC_REQUIRED = ()
PACKAGE_LICENSE_META_FIELDS = ()
PACKAGE_LICENSE_PAYLOAD_TOP_LEVEL_FIELDS = ("context", "meta", "tenant_meta")

PACKAGE_VERSION_SPEC_FIELDS = (
    "project_uuid",
    "source_code_reference",
    "release_timestamp",
    "unresolved_dependencies",
    "resolved_dependencies",
    "resolution_errors",
    "language",
    "relative_path",
    "container_metadata",
    "bazel_metadata",
    "code_owners",
    "call_graph_available",
    "precomputed_call_graph_state",
)
PACKAGE_VERSION_SPEC_REQUIRED = ("project_uuid",)
PACKAGE_VERSION_META_FIELDS = ()
PACKAGE_VERSION_PAYLOAD_TOP_LEVEL_FIELDS = (
    "context",
    "meta",
    "processing_status",
    "tenant_meta",
)

POLICY_SPEC_FIELDS = (
    "policy_type",
    "rule",
    "project_selector",
    "project_exceptions",
    "resource_kinds",
    "disable",
    "query_statements",
    "template_uuid",
    "template_values",
    "template_version",
    "template_parameters",
    "finding_level",
    "group_by_fields",
    "finding_categories",
    "admission",
    "finding",
    "notification",
    "exception",
)
POLICY_SPEC_REQUIRED = ("policy_type",)
POLICY_META_FIELDS = ()
POLICY_PAYLOAD_TOP_LEVEL_FIELDS = ("meta", "propagate", "tenant_meta")

POLICY_TEMPLATE_SPEC_FIELDS = (
    "rule",
    "query_statements",
    "policy_type",
    "version",
    "template_parameters",
    "resource_kinds",
    "default_enabled",
    "finding_level",
    "group_by_fields",
    "release_notes",
    "deprecated",
    "finding_categories",
    "admission",
    "finding",
)
POLICY_TEMPLATE_SPEC_REQUIRED = ("rule", "query_statements", "policy_type", "version")
POLICY_TEMPLATE_META_FIELDS = ()
POLICY_TEMPLATE_PAYLOAD_TOP_LEVEL_FIELDS = ("meta", "propagate", "tenant_meta")

PROJECT_SPEC_FIELDS = (
    "platform_source",
    "git",
    "unsupported",
    "sbom",
    "model",
    "toolchain_profile_uuid",
    "scan_profile_uuid",
    "is_archived",
)
PROJECT_SPEC_REQUIRED = ("platform_source",)
PROJECT_META_FIELDS = ()
PROJECT_PAYLOAD_TOP_LEVEL_FIELDS = ("meta", "processing_status", "tenant_meta")

QUERY_SPEC_FIELDS = ("query_spec",)
QUERY_SPEC_REQUIRED = ()
QUERY_META_FIELDS = ()
QUERY_PAYLOAD_TOP_LEVEL_FIELDS = ("meta", "tenant_meta")

QUERY_MALWARE_SPEC_FIELDS = (
    "package_version_name",
    "package_version_names",
    "purls",
    "mask",
)
QUERY_MALWARE_SPEC_REQUIRED = ()
QUERY_MALWARE_META_FIELDS = ("name",)
QUERY_MALWARE_PAYLOAD_TOP_LEVEL_FIELDS = (
    "meta",
    "response",
    "responses",
    "tenant_meta",
)

QUERY_SIMILAR_PACKAGES_SPEC_FIELDS = ("name", "edit_distance", "repo", "exact_match")
QUERY_SIMILAR_PACKAGES_SPEC_REQUIRED = ("name",)
QUERY_SIMILAR_PACKAGES_META_FIELDS = ()
QUERY_SIMILAR_PACKAGES_PAYLOAD_TOP_LEVEL_FIELDS = ("meta", "tenant_meta")

QUERY_VULNERABILITY_SPEC_FIELDS = (
    "package_version_name",
    "package_version_names",
    "vulnerability_name_query",
    "purls",
    "mask",
    "vulnerability_type",
)
QUERY_VULNERABILITY_SPEC_REQUIRED = ()
QUERY_VULNERABILITY_META_FIELDS = ("name",)
QUERY_VULNERABILITY_PAYLOAD_TOP_LEVEL_FIELDS = (
    "meta",
    "response",
    "responses",
    "tenant_meta",
)

REPOSITORY_SPEC_FIELDS = (
    "platform_source",
    "http_clone_url",
    "default_branch",
    "external_id",
    "owner",
    "create_time",
    "update_time",
    "contributors",
    "commit_hashes",
    "languages",
    "tags",
    "branch_protections",
    "vulnerability_alerts_enabled",
    "org",
    "repository_license",
)
REPOSITORY_SPEC_REQUIRED = ("platform_source", "http_clone_url", "default_branch")
REPOSITORY_META_FIELDS = ()
REPOSITORY_PAYLOAD_TOP_LEVEL_FIELDS = ("ingested_object", "meta", "tenant_meta")

REPOSITORY_VERSION_SPEC_FIELDS = ("version", "last_commit_date")
REPOSITORY_VERSION_SPEC_REQUIRED = ()
REPOSITORY_VERSION_META_FIELDS = ()
REPOSITORY_VERSION_PAYLOAD_TOP_LEVEL_FIELDS = (
    "context",
    "meta",
    "scan_object",
    "tenant_meta",
)

SAVED_QUERY_SPEC_FIELDS = ("query", "monitor", "query_type", "is_default")
SAVED_QUERY_SPEC_REQUIRED = ()
SAVED_QUERY_META_FIELDS = ()
SAVED_QUERY_PAYLOAD_TOP_LEVEL_FIELDS = ("meta", "propagate", "tenant_meta")

SCAN_LOG_REQUEST_SPEC_FIELDS = (
    "max_entries",
    "start_time",
    "newest_first",
    "admin_filter",
    "log_levels",
    "scan_request_uuid",
    "project_uuid",
    "installation_uuid",
    "onprem_scheduler_uuid",
    "scan_result_uuid",
    "execution_id",
    "admin_search",
    "end_time",
    "traverse",
)
SCAN_LOG_REQUEST_SPEC_REQUIRED = ("max_entries",)
SCAN_LOG_REQUEST_META_FIELDS = ()
SCAN_LOG_REQUEST_PAYLOAD_TOP_LEVEL_FIELDS = ("meta", "tenant_meta")

SCAN_PROFILE_SPEC_FIELDS = (
    "toolchain_profile",
    "automated_scan_parameters",
    "remediation_parameters",
    "is_default",
    "security_review_scanner_parameters",
    "exporter_parameters",
    "ai_sast_analysis_parameters",
)
SCAN_PROFILE_SPEC_REQUIRED = ()
SCAN_PROFILE_META_FIELDS = ()
SCAN_PROFILE_PAYLOAD_TOP_LEVEL_FIELDS = ("meta", "propagate", "tenant_meta")

SCAN_RESULT_SPEC_FIELDS = (
    "status",
    "type",
    "errors",
    "warnings",
    "infos",
    "start_time",
    "end_time",
    "stats",
    "refs",
    "environment",
    "has_panic",
    "exit_code",
    "logs",
    "policies_triggered",
    "warning_findings",
    "blocking_findings",
    "runtimes",
    "all_findings",
    "deleted_findings",
    "languages_detected",
    "exception_findings",
    "findings",
    "provisioning_result_uuid",
    "versions",
    "ecosystem_pkg_counts",
    "ecosystem_dep_counts",
    "components_executed",
    "deleted_package_versions",
    "provisioning_result",
)
SCAN_RESULT_SPEC_REQUIRED = ("status", "type")
SCAN_RESULT_META_FIELDS = ()
SCAN_RESULT_PAYLOAD_TOP_LEVEL_FIELDS = ("context", "meta", "tenant_meta")

SCAN_WORKFLOW_SPEC_FIELDS = (
    "steps",
    "remediation_parameters",
    "automated_scan_parameters",
)
SCAN_WORKFLOW_SPEC_REQUIRED = ()
SCAN_WORKFLOW_META_FIELDS = ()
SCAN_WORKFLOW_PAYLOAD_TOP_LEVEL_FIELDS = ("meta", "tenant_meta")

SCAN_WORKFLOW_RESULT_SPEC_FIELDS = (
    "status",
    "start_time",
    "end_time",
    "execution_id",
    "workflow_results",
    "stats",
    "versions",
)
SCAN_WORKFLOW_RESULT_SPEC_REQUIRED = ("status",)
SCAN_WORKFLOW_RESULT_META_FIELDS = ()
SCAN_WORKFLOW_RESULT_PAYLOAD_TOP_LEVEL_FIELDS = ("context", "meta", "tenant_meta")

SEMGREP_RULE_SPEC_FIELDS = ("rule", "disabled", "yaml")
SEMGREP_RULE_SPEC_REQUIRED = ()
SEMGREP_RULE_META_FIELDS = ()
SEMGREP_RULE_PAYLOAD_TOP_LEVEL_FIELDS = ("disabled", "meta", "propagate", "tenant_meta")

VECTOR_STORE_SPEC_FIELDS = ("vector_store_uuid", "query", "metadata_filter")
VECTOR_STORE_SPEC_REQUIRED = ("vector_store_uuid", "query")
VECTOR_STORE_META_FIELDS = ("name",)
VECTOR_STORE_PAYLOAD_TOP_LEVEL_FIELDS = ("meta", "tenant_meta")

VECTOR_STORE_QUERY_SPEC_FIELDS = ("vector_store_uuid", "query", "metadata_filter")
VECTOR_STORE_QUERY_SPEC_REQUIRED = ("vector_store_uuid", "query")
VECTOR_STORE_QUERY_META_FIELDS = ("name",)
VECTOR_STORE_QUERY_PAYLOAD_TOP_LEVEL_FIELDS = ("meta", "tenant_meta")

VERSION_UPGRADE_SPEC_FIELDS = (
    "project_uuid",
    "name",
    "upgrade_info",
    "configuration",
    "stats",
    "prioritized_upgrades",
    "all_upgrades",
    "finding_fixing_upgrades",
)
VERSION_UPGRADE_SPEC_REQUIRED = ("project_uuid", "name")
VERSION_UPGRADE_META_FIELDS = ()
VERSION_UPGRADE_PAYLOAD_TOP_LEVEL_FIELDS = ("context", "meta", "tenant_meta")

VULNERABILITY_SPEC_FIELDS = (
    "package_version_name",
    "package_version_names",
    "vulnerability_name_query",
    "purls",
    "mask",
    "vulnerability_type",
)
VULNERABILITY_SPEC_REQUIRED = ()
VULNERABILITY_META_FIELDS = ("name",)
VULNERABILITY_PAYLOAD_TOP_LEVEL_FIELDS = (
    "meta",
    "response",
    "responses",
    "tenant_meta",
)

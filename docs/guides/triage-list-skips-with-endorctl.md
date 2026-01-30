# Triage list skips with endorctl

When tests skip with "No resources in scope", "List returned 404", or "Backend returned ServerError (list)", use `endorctl api list` to validate and triage whether the namespace has data for that resource.

## Command

```bash
endorctl api list -r <RESOURCE> --traverse -n endor-solutions-tgowan --log-level error
```

Use **PascalCase** for `<RESOURCE>` (e.g. `Finding`, `Project`, `Installation`, `Repository`, `RepositoryVersion`, `Policy`, `PackageVersion`, `ScanResult`). Add `-o table` or `--page-size 5` to limit output. `DependencyMetadata` can be slow or time out with traverse.

## Resources that can trigger list skips

| Test file / context | endorctl `-r` (PascalCase) | Example command |
|--------------------|----------------------------|------------------|
| test_finding.py | Finding | `endorctl api list -r Finding --traverse -n endor-solutions-tgowan --log-level error` |
| test_project.py | Project | `endorctl api list -r Project --traverse -n endor-solutions-tgowan --log-level error` |
| test_repository.py | Repository | `endorctl api list -r Repository --traverse -n endor-solutions-tgowan --log-level error` |
| test_repository_version.py | RepositoryVersion | `endorctl api list -r RepositoryVersion --traverse -n endor-solutions-tgowan --log-level error` |
| test_installation.py | Installation | `endorctl api list -r Installation --traverse -n endor-solutions-tgowan --log-level error` |
| test_policy.py | Policy | `endorctl api list -r Policy --traverse -n endor-solutions-tgowan --log-level error` |
| test_authorization_policy.py | AuthorizationPolicy | `endorctl api list -r AuthorizationPolicy --traverse -n endor-solutions-tgowan --log-level error` |
| test_package_version.py | PackageVersion | `endorctl api list -r PackageVersion --traverse -n endor-solutions-tgowan --log-level error` |
| test_package_license.py | PackageLicense | `endorctl api list -r PackageLicense --traverse -n endor-solutions-tgowan --log-level error` |
| test_dependency_metadata.py | DependencyMetadata | `endorctl api list -r DependencyMetadata --traverse -n endor-solutions-tgowan --log-level error` (can be slow) |
| test_scan_profile.py | ScanProfile | `endorctl api list -r ScanProfile --traverse -n endor-solutions-tgowan --log-level error` |
| test_scan_result.py | ScanResult | `endorctl api list -r ScanResult --traverse -n endor-solutions-tgowan --log-level error` |
| test_scan_log_request.py | ScanResult (then POST scan-log-requests) | `endorctl api list -r ScanResult --traverse -n endor-solutions-tgowan --log-level error` |
| test_linter_result.py | LinterResult | `endorctl api list -r LinterResult --traverse -n endor-solutions-tgowan --log-level error` |
| test_metric.py | Metric | `endorctl api list -r Metric --traverse -n endor-solutions-tgowan --log-level error` |
| test_finding_log.py | FindingLog, Finding | `endorctl api list -r FindingLog --traverse -n endor-solutions-tgowan --log-level error` |
| test_audit_log.py | AuditLog | `endorctl api list -r AuditLog --traverse -n endor-solutions-tgowan --log-level error` |
| test_semgrep_rule.py | SemgrepRule | `endorctl api list -r SemgrepRule --traverse -n endor-solutions-tgowan --log-level error` |
| test_api_key.py | APIKey | `endorctl api list -r APIKey --traverse -n endor-solutions-tgowan --log-level error` |
| test_namespaces.py | Namespace | `endorctl api list -r Namespace --traverse -n endor-solutions-tgowan --log-level error` |
| test_retrieving_scan_results_workflow.py | Project, ScanResult, Finding | Same `-r` values as above |

## Skip reasons

- **No resources in scope (empty; may be filter/auth/scope)** — List returned 200 with empty list. Run the endorctl command above; if it also returns empty, the namespace has no data for that resource (or filter/auth applies).
- **List returned 404 (filter/auth or scope)** — API returned 404 for the list request. endorctl will show whether the same call returns 404.
- **Backend returned ServerError (list); skip** — API returned 5xx or SDK got a validation/backend error (e.g. "Spec not fully defined"). endorctl may return the same error or succeed; compare to triage.

## Validation run (endor-solutions-tgowan, --traverse, --log-level error)

Run with endorctl v1.7.786:

| Resource | Result |
|----------|--------|
| Finding | OK (exit 0; large output) |
| Project | OK (exit 0) |
| Installation | OK (exit 0; 2 rows in table) |
| Repository | OK (exit 0) |
| RepositoryVersion | OK (exit 0; 3 rows with --page-size 3) |
| Policy | OK (exit 0) |
| PackageVersion | OK (exit 0) |
| ScanResult | OK (exit 0) |
| DependencyMetadata | Timed out (traverse can be very slow) |

List skips for **Finding** in tests are likely due to SDK/backend handling (e.g. "Spec not fully defined") rather than missing data; endorctl returns data. Use `--page-size 5` or `-o table` to keep output manageable.

## One-liners to validate list resources

```bash
# Bash (PascalCase -r)
for r in Finding Project Installation Repository RepositoryVersion Policy ScanResult PackageVersion; do
  echo "=== $r ==="
  endorctl api list -r "$r" --traverse -n endor-solutions-tgowan --log-level error --page-size 2 2>/dev/null | head -5
done
```

```powershell
# PowerShell (PascalCase -r)
$resources = @("Finding","Project","Installation","Repository","RepositoryVersion","Policy","ScanResult","PackageVersion")
foreach ($r in $resources) {
  Write-Host "=== $r ==="
  endorctl api list -r $r --traverse -n endor-solutions-tgowan --log-level error --page-size 2 2>$null
}
```

# Retrieving ScanResult Objects and Metrics

## Overview

ScanResult objects contain comprehensive metadata about security scans, including scan configuration, environment details, runtime statistics, policies triggered, and references to findings. This guide shows how to retrieve ScanResult objects and navigate from repository URLs to scan results and findings.

## Key Concepts

### ScanResult vs Findings

- **`endorctl scan --output-type json`**: Returns an array of **Finding** objects (security findings, vulnerabilities, etc.) - does NOT create a ScanResult
- **ScanResult objects**: Contain scan metadata, environment details, runtime statistics, and references to findings via UUIDs
- **Relationship**: `ScanResult.spec.findings` contains UUIDs of all findings discovered by the scan

### Data Model Relationships

```
Project (meta.name = repository URL)
  └── ScanResult (meta.parent_uuid = Project UUID)
      └── Finding UUIDs (spec.findings[] = List of Finding UUIDs)
          └── Finding (context.scan_uuid = ScanResult UUID, spec.project_uuid = Project UUID)
```

### Namespace Traversal

**Critical**: Use `--traverse` flag when namespace is unknown or you need to search across all namespaces. Without `--traverse`, queries only search the specified namespace. If `$ENDOR_NAMESPACE` is not set, always use `--traverse` with the tenant namespace.

### Field Masking vs jq

**Use `--field-mask` for efficiency**: Server-side filtering reduces payload size and network transfer. Use `jq` only when you need:
- Array element extraction (e.g., `spec.findings[]`)
- Complex transformations
- Nested dictionary access that field-mask doesn't support well

**Example**: To get only UUIDs, use `--field-mask "uuid"` instead of downloading full objects and filtering with `jq`.

## Sequential Workflow: Repository URL → ScanResult → Findings

### Step 1: Get Project UUID from Repository URL

Find the Project using the repository Git URL. The Project's `meta.name` field contains the full repository URL:

```bash
# Get Project by repository URL (use --traverse if namespace unknown)
# Use --field-mask to return only UUID (more efficient)
REPO_URL="https://github.com/owner/repo.git"

PROJECT_UUID=$(endorctl api list -r Project \
  --traverse \
  --filter "meta.name==\"${REPO_URL}\"" \
  --field-mask "uuid" \
  --output-type json | jq -r '.list.objects[0].uuid')

echo "Project UUID: ${PROJECT_UUID}"
```

**Alternative filters** if `meta.name` doesn't match:
- `spec.git.web_url=="https://api.github.com/owner/repo"` (API GitHub format)
- `spec.git.http_clone_url=="https://github.com/owner/repo.git"` (HTTP clone URL)

### Step 2: Get Most Recent ScanResult for Project

Get the most recent ScanResult using the parent relationship:

```bash
# Get most recent ScanResult (use --traverse, sort by create_time descending, limit to 1)
# Use --field-mask to return only UUID (more efficient)
SCAN_RESULT_UUID=$(endorctl api list -r ScanResult \
  --traverse \
  --filter "meta.parent_uuid==${PROJECT_UUID}" \
  --sort-path "meta.create_time" \
  --sort-order "descending" \
  --page-size 1 \
  --field-mask "uuid" \
  --output-type json | jq -r '.list.objects[0].uuid')

echo "ScanResult UUID: ${SCAN_RESULT_UUID}"
```

### Step 3: Get Findings from ScanResult

Extract Finding UUIDs from the ScanResult and retrieve them:

```bash
# Get ScanResult with only findings field (use --field-mask for efficiency)
SCAN_RESULT=$(endorctl api get -r ScanResult \
  --uuid ${SCAN_RESULT_UUID} \
  --field-mask "spec.findings" \
  --output-type json)

# Extract Finding UUIDs from spec.findings array (jq needed for array extraction)
FINDING_UUIDS=$(echo $SCAN_RESULT | jq -r '.spec.findings[]?')

# Retrieve each Finding (use --field-mask if you only need specific fields)
for finding_uuid in $FINDING_UUIDS; do
  endorctl api get -r Finding \
    --uuid $finding_uuid \
    --field-mask "spec.level,spec.finding_categories,spec.finding_metadata" \
    --output-type json
done
```

**Alternative**: If `spec.findings` is empty, try filtering Findings by scan UUID:

```bash
# Get Findings by scan UUID (use --traverse)
endorctl api list -r Finding \
  --traverse \
  --filter "context.scan_uuid==${SCAN_RESULT_UUID}" \
  --output-type json
```

## Complete Workflow Script

```bash
#!/bin/bash
# Complete workflow: Repository URL → Project → ScanResult → Findings

REPO_URL="${1:-https://github.com/owner/repo.git}"
TENANT_NAMESPACE="${ENDOR_NAMESPACE:-endor-solutions-tgowan}"

# Step 1: Get Project UUID
echo "Step 1: Finding Project by repository URL..."
PROJECT_UUID=$(endorctl api list -r Project \
  --traverse \
  --filter "meta.name==\"${REPO_URL}\"" \
  --field-mask "uuid" \
  --output-type json | jq -r '.list.objects[0].uuid')

if [ -z "$PROJECT_UUID" ] || [ "$PROJECT_UUID" == "null" ]; then
  echo "Error: Project not found for ${REPO_URL}"
  exit 1
fi

echo "Found Project UUID: ${PROJECT_UUID}"

# Step 2: Get most recent ScanResult
echo "Step 2: Getting most recent ScanResult..."
SCAN_RESULT_UUID=$(endorctl api list -r ScanResult \
  --traverse \
  --filter "meta.parent_uuid==${PROJECT_UUID}" \
  --sort-path "meta.create_time" \
  --sort-order "descending" \
  --page-size 1 \
  --field-mask "uuid" \
  --output-type json | jq -r '.list.objects[0].uuid')

if [ -z "$SCAN_RESULT_UUID" ] || [ "$SCAN_RESULT_UUID" == "null" ]; then
  echo "Warning: No ScanResult found for Project ${PROJECT_UUID}"
  echo "Attempting to get Findings directly by Project UUID..."
  endorctl api list -r Finding \
    --traverse \
    --filter "spec.project_uuid==${PROJECT_UUID}" \
    --output-type json
  exit 0
fi

echo "Found ScanResult UUID: ${SCAN_RESULT_UUID}"

# Step 3: Get ScanResult and extract Finding UUIDs
echo "Step 3: Retrieving ScanResult and extracting Finding UUIDs..."
SCAN_RESULT=$(endorctl api get -r ScanResult \
  --uuid ${SCAN_RESULT_UUID} \
  --field-mask "spec.findings" \
  --output-type json)

FINDING_UUIDS=$(echo $SCAN_RESULT | jq -r '.spec.findings[]?' 2>/dev/null)

if [ -z "$FINDING_UUIDS" ]; then
  echo "Warning: No Finding UUIDs in ScanResult spec.findings"
  echo "Attempting to get Findings by context.scan_uuid..."
  endorctl api list -r Finding \
    --traverse \
    --filter "context.scan_uuid==${SCAN_RESULT_UUID}" \
    --output-type json
  exit 0
fi

# Step 4: Retrieve each Finding
echo "Step 4: Retrieving Findings..."
echo "$FINDING_UUIDS" | while read -r finding_uuid; do
  if [ ! -z "$finding_uuid" ]; then
    echo "Retrieving Finding: ${finding_uuid}"
    endorctl api get -r Finding \
      --uuid "$finding_uuid" \
      --field-mask "spec.level,spec.finding_categories,spec.finding_metadata" \
      --output-type json
  fi
done
```

## Key Filter Fields

### Project Lookup
- `meta.name` - Full repository URL (e.g., `https://github.com/owner/repo.git`)
- `spec.git.web_url` - API GitHub URL format (e.g., `https://api.github.com/owner/repo`)
- `spec.git.http_clone_url` - HTTP clone URL

### ScanResult Lookup
- `meta.parent_uuid` - Project UUID (most efficient filter)
- `meta.create_time` - Use for sorting to get most recent
- `spec.status` - Scan status (`STATUS_SUCCESS`, `STATUS_FAILURE`, etc.)
- `spec.versions[].sha` - Commit SHA (optional refinement)
- `spec.refs[]` - Branch names (optional refinement)
- `context.type` - Context type (e.g., `CONTEXT_TYPE_MAIN`)

### Finding Lookup
- `context.scan_uuid` - ScanResult UUID (direct relationship)
- `spec.project_uuid` - Project UUID (fallback if scan_uuid not available)
- `meta.create_time` - Use for sorting

## Common Queries

### Get Latest ScanResult for a Project

```bash
# Use --field-mask to return only needed fields (more efficient)
endorctl api list -r ScanResult \
  --traverse \
  --filter "meta.parent_uuid==<project-uuid>" \
  --sort-path "meta.create_time" \
  --sort-order "descending" \
  --page-size 1 \
  --field-mask "uuid,spec.status,spec.start_time,spec.end_time"
```

### Get ScanResults with Specific Status

```bash
# Successful scans
endorctl api list -r ScanResult \
  --traverse \
  --filter "spec.status==STATUS_SUCCESS"

# Failed scans
endorctl api list -r ScanResult \
  --traverse \
  --filter "spec.status==STATUS_FAILURE"
```

### Get Scan Statistics

**Use `--field-mask` for efficiency**: Server-side filtering reduces payload size and network transfer. Use `jq` only when you need array element extraction or complex transformations.

```bash
SCAN_RESULT_UUID="<scan-result-uuid>"

# Efficient: Use --field-mask to return only needed fields (server-side filtering)
endorctl api get -r ScanResult \
  --uuid ${SCAN_RESULT_UUID} \
  --field-mask "spec.status,spec.start_time,spec.end_time,spec.stats" \
  --output-type json
```

**Comprehensive statistics extraction** (using `--field-mask` + `jq` for nested dict access):

```bash
SCAN_RESULT_UUID="<scan-result-uuid>"

# Get ScanResult with stats field only (efficient)
SCAN_RESULT=$(endorctl api get -r ScanResult \
  --uuid ${SCAN_RESULT_UUID} \
  --field-mask "spec.status,spec.start_time,spec.end_time,spec.stats,spec.policies_triggered" \
  --output-type json)

# Extract comprehensive statistics
echo $SCAN_RESULT | jq '{
  status: .spec.status,
  start_time: .spec.start_time,
  end_time: .spec.end_time,
  scan_duration_seconds: (
    (.["spec"]["end_time"] | fromdateiso8601) - 
    (.["spec"]["start_time"] | fromdateiso8601)
  ),
  dependencies: {
    total: .spec.stats.dependency_count_total,
    full_analysis: .spec.stats.dependency_analysis_num_full,
    approximate: .spec.stats.dependency_analysis_num_approximate
  },
  findings: {
    critical: .spec.stats.findings_critical,
    high: .spec.stats.findings_high,
    medium: .spec.stats.findings_medium,
    low: .spec.stats.findings_low,
    dismissed: .spec.stats.findings_dismissed
  },
  call_graph: {
    attempted: .spec.stats.call_graph_attempted,
    available: .spec.stats.call_graph_available,
    errors: .spec.stats.call_graph_errors
  },
  policies: {
    admission_enabled: .spec.stats.num_admission_policies_enabled,
    admission_evaluated: .spec.stats.policy_admission_num_evaluated,
    admission_triggered: .spec.stats.policy_admission_num_triggered,
    finding_enabled: .spec.stats.num_finding_policies_enabled,
    exception_enabled: .spec.stats.num_exception_policies_enabled,
    remediation_enabled: .spec.stats.num_remediation_policies_enabled,
    triggered_uuids: .spec.policies_triggered
  },
  packages: {
    versions: .spec.stats.package_versions
  },
  scan_result: {
    success: .spec.stats.scan_success,
    failures: .spec.stats.scan_failures
  }
}'
```

### Get Findings for a ScanResult

**Note on `--field-mask` vs `jq`**: Use `--field-mask` for simple field extraction (more efficient). Use `jq` when you need to extract array elements (like `spec.findings[]`) or perform transformations that field-mask doesn't support.

```bash
SCAN_RESULT_UUID="<scan-result-uuid>"

# Method 1: Extract Finding UUIDs from spec.findings array
# Use --field-mask to get only the findings field (efficient)
SCAN_RESULT=$(endorctl api get -r ScanResult \
  --uuid ${SCAN_RESULT_UUID} \
  --field-mask "spec.findings" \
  --output-type json)

# Extract Finding UUIDs (jq needed for array element extraction)
FINDING_UUIDS=$(echo $SCAN_RESULT | jq -r '.spec.findings[]?')

# Retrieve each Finding (use --field-mask if you only need specific fields)
for finding_uuid in $FINDING_UUIDS; do
  endorctl api get -r Finding \
    --uuid $finding_uuid \
    --field-mask "spec.level,spec.finding_categories,spec.finding_metadata.title" \
    --output-type json
done

# Method 2: Filter by context.scan_uuid (use --traverse, more efficient for many findings)
endorctl api list -r Finding \
  --traverse \
  --filter "context.scan_uuid==${SCAN_RESULT_UUID}" \
  --field-mask "spec.level,spec.finding_categories,spec.finding_metadata.title" \
  --output-type json
```

## ScanResult Field Reference

### Metadata (`meta`)
- `uuid` - Unique identifier
- `name` - Scan result name (auto-generated)
- `create_time` - Creation timestamp
- `parent_uuid` - UUID of parent Project

### Specification (`spec`)
- `status` - Scan status (`STATUS_SUCCESS`, `STATUS_FAILURE`, `STATUS_PARTIAL_SUCCESS`, `STATUS_RUNNING`)
- `type` - Scan type (typically `TYPE_ALL_SCANS`)
- `start_time` - Scan start timestamp
- `end_time` - Scan end timestamp
- `stats` - Dictionary of scan statistics (see Statistics Fields below)
- `environment` - Host environment details (OS, architecture, endorctl version, tools)
- `findings` - List of Finding UUIDs discovered by the scan
- `warning_findings` - List of warning Finding UUIDs
- `blocking_findings` - List of blocking Finding UUIDs
- `policies_triggered` - List of policy UUIDs triggered
- `runtimes` - Dictionary of scan type runtimes (milliseconds)
- `exit_code` - Endorctl exit code
- `logs` - User-facing log output

### Statistics Fields (`spec.stats`)

The `stats` dictionary contains comprehensive scan metrics:

**Finding Statistics:**
- `findings_critical`, `findings_high`, `findings_medium`, `findings_low` - Finding counts by severity
- `findings_dismissed` - Count of dismissed findings

**Dependency Statistics:**
- `dependency_count_total` - Total dependencies analyzed
- `dependency_count_max`, `dependency_count_mean`, `dependency_count_median`, `dependency_count_min` - Dependency count statistics
- `dependency_analysis_num_full` - Number of dependencies with full analysis
- `dependency_analysis_num_approximate` - Number of dependencies with approximate analysis

**Call Graph Statistics:**
- `call_graph_attempted` - Number of call graph analyses attempted
- `call_graph_available` - Number of call graphs successfully generated
- `call_graph_errors` - Number of call graph generation errors

**Policy Statistics:**
- `num_admission_policies_enabled` - Number of admission policies enabled
- `num_finding_policies_enabled` - Number of finding policies enabled
- `num_exception_policies_enabled` - Number of exception policies enabled
- `num_remediation_policies_enabled` - Number of remediation policies enabled
- `policy_admission_num_evaluated` - Number of admission policies evaluated
- `policy_admission_num_triggered` - Number of admission policies triggered
- `policy_admission_num_matches` - Number of admission policy matches
- `policy_admission_time_evaluating` - Time spent evaluating admission policies (ms)
- `policy_admission_time_loading_data` - Time spent loading data for admission policies (ms)
- Similar fields for `policy_exception_*` and `policy_remediation_*`

**Package Statistics:**
- `package_versions` - Number of package versions processed

**Scan Result:**
- `scan_success` - Number of successful scans (typically 1 or 0)
- `scan_failures` - Number of scan failures

### Context (`context`)
- `id` - Context ID (e.g., "default" for main branch)
- `type` - Context type (e.g., `CONTEXT_TYPE_MAIN`)

## Troubleshooting

### No Results Returned

**Problem**: Queries return empty results.

**Solutions**:
1. Add `--traverse` flag to search across all namespaces
2. Verify filter syntax (use `==` for equality, ensure UUIDs are quoted)
3. Check that scans have been run (ScanResults are created when scans run without `--dry-run`)
4. Verify authentication credentials

### Cannot Find Project

**Problem**: Project lookup fails.

**Solutions**:
1. Try alternative filters: `spec.git.web_url` or `spec.git.http_clone_url`
2. Use `--traverse` to search all namespaces
3. Verify repository URL format matches exactly (including `.git` suffix)

### Finding UUIDs Not in spec.findings

**Problem**: `spec.findings` array is empty but Findings exist.

**Solutions**:
1. Use fallback: Filter Findings by `context.scan_uuid` with `--traverse`
2. Filter Findings by `spec.project_uuid` as alternative
3. Check if Findings were created in a different namespace (use `--traverse`)

## Best Practices

1. **Always use --traverse**: Unless you know the exact namespace, use `--traverse` to avoid missing results
2. **Use --field-mask for efficiency**: Server-side filtering reduces payload size. Use `jq` only when you need array element extraction (like `spec.findings[]`) or complex transformations
3. **Cache Project UUID**: Projects don't change frequently, so cache the Project UUID lookup
4. **Use page-size 1**: When you only need the most recent ScanResult, use `--page-size 1`
5. **Sort efficiently**: Sort by `meta.create_time` descending to get newest first
6. **Filter at API level**: Use filters rather than retrieving all results and filtering client-side

## Related Resources
- [endorctl api Command Reference](https://docs.endorlabs.com/endorctl/commands/api/) - Complete API command documentation

---
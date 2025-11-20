# Find Scan Config for Finding - endorctl Commands

This document provides endorctl commands to find the ScanConfig that created a given Finding.

## Problem

Given a Finding UUID, we need to determine which scan created it. The approach is:
1. Get Finding by UUID to retrieve its creation date and project UUID
2. Search through all ScanResult resources for the same project
3. Filter ScanResults where `scan_start < finding.created < scan_end`
4. Return `spec.environment.config.ScanConfig` from matching ScanResults

## Step-by-Step Commands

### Step 1: Get Finding Details

Get the Finding by UUID to retrieve its creation date and project UUID:

```bash
# Get Finding by UUID
FINDING_UUID="your-finding-uuid-here"
NAMESPACE="your-namespace"

endorctl api get \
  --resource Finding \
  --uuid "$FINDING_UUID" \
  --field-mask "meta.create_time,spec.project_uuid,meta.name" \
  | jq '{finding_uuid: .uuid, finding_name: .meta.name, create_time: .meta.create_time, project_uuid: .spec.project_uuid}'
```

**Output example:**
```json
{
  "finding_uuid": "0123456789abcdef01234567",
  "finding_name": "Vulnerability in package",
  "create_time": "2024-01-15T10:30:00Z",
  "project_uuid": "0123456789abcdef01234567"
}
```

**Note:** UUIDs in the Endor Labs API are 24-character hexadecimal strings without hyphens.

Save the values:
```bash
FINDING_CREATE_TIME="2024-01-15T10:30:00Z"
PROJECT_UUID="0123456789abcdef01234567"
```

### Step 2: List ScanResults for the Project

List all ScanResult resources for the project:

```bash
endorctl api list \
  --resource ScanResult \
  --filter "meta.parent_uuid==\"$PROJECT_UUID\"" \
  --list-all \
  --field-mask "uuid,meta.name,spec.start_time,spec.end_time,spec.environment.config" \
  | jq '.list.objects[] | {uuid: .uuid, name: .meta.name, start_time: .spec.start_time, end_time: .spec.end_time, config: .spec.environment.config}'
```

### Step 3: Filter Matching ScanResults

Filter ScanResults where the finding was created during the scan:

```bash
# This command lists all ScanResults and filters in jq
endorctl api list \
  --resource ScanResult \
  --filter "meta.parent_uuid==\"$PROJECT_UUID\"" \
  --list-all \
  --field-mask "uuid,meta.name,spec.start_time,spec.end_time,spec.environment.config" \
  | jq --arg finding_time "$FINDING_CREATE_TIME" \
    '.list.objects[] | 
    select(.spec.start_time != null and .spec.end_time != null) |
    select(.spec.start_time <= $finding_time and .spec.end_time >= $finding_time) |
    {uuid: .uuid, name: .meta.name, start_time: .spec.start_time, end_time: .spec.end_time, scan_config: .spec.environment.config}'
```

### Step 4: Extract ScanConfig

To get just the ScanConfig from matching ScanResults:

```bash
endorctl api list \
  --resource ScanResult \
  --filter "meta.parent_uuid==\"$PROJECT_UUID\"" \
  --list-all \
  --field-mask "spec.environment.config" \
  | jq --arg finding_time "$FINDING_CREATE_TIME" \
    '.list.objects[] | 
    select(.spec.start_time != null and .spec.end_time != null) |
    select(.spec.start_time <= $finding_time and .spec.end_time >= $finding_time) |
    .spec.environment.config'
```

## Complete One-Liner Script

Here's a complete bash script that does all steps:

```bash
#!/bin/bash
# find_scan_config_for_finding.sh

FINDING_UUID="$1"
NAMESPACE="$2"

if [ -z "$FINDING_UUID" ] || [ -z "$NAMESPACE" ]; then
  echo "Usage: $0 <finding-uuid> <namespace>"
  exit 1
fi

# Step 1: Get Finding details
echo "Getting Finding details..."
FINDING_DATA=$(endorctl api get \
  --resource Finding \
  --uuid "$FINDING_UUID" \
  --field-mask "meta.create_time,spec.project_uuid,meta.name" \
  | jq -r '{create_time: .meta.create_time, project_uuid: .spec.project_uuid, name: .meta.name}')

FINDING_CREATE_TIME=$(echo "$FINDING_DATA" | jq -r '.create_time')
PROJECT_UUID=$(echo "$FINDING_DATA" | jq -r '.project_uuid')
FINDING_NAME=$(echo "$FINDING_DATA" | jq -r '.name')

echo "Finding: $FINDING_NAME"
echo "Created: $FINDING_CREATE_TIME"
echo "Project: $PROJECT_UUID"
echo ""

# Step 2 & 3: List and filter ScanResults
echo "Searching for matching ScanResults..."
endorctl api list \
  --resource ScanResult \
  --filter "meta.parent_uuid==\"$PROJECT_UUID\"" \
  --list-all \
  --field-mask "uuid,meta.name,spec.start_time,spec.end_time,spec.environment.config" \
  | jq --arg finding_time "$FINDING_CREATE_TIME" \
    '.list.objects[] | 
    select(.spec.start_time != null and .spec.end_time != null) |
    select(.spec.start_time <= $finding_time and .spec.end_time >= $finding_time) |
    {
      scan_uuid: .uuid,
      scan_name: .meta.name,
      scan_start: .spec.start_time,
      scan_end: .spec.end_time,
      scan_config: .spec.environment.config
    }'
```

**Usage:**
```bash
chmod +x find_scan_config_for_finding.sh
./find_scan_config_for_finding.sh "your-finding-uuid" "your-namespace"
```

## PowerShell Versions

Here are the same commands formatted for PowerShell with proper line breaks:

### Step 1: Get Finding Details

```powershell
# Set variables
$FINDING_UUID = "your-finding-uuid-here"
$NAMESPACE = "your-namespace"

# Get Finding by UUID
endorctl api get `
  --resource Finding `
  --uuid $FINDING_UUID `
  --field-mask "meta.create_time,spec.project_uuid,meta.name" `
  | ConvertFrom-Json | Select-Object @{
    Name='finding_uuid';Expression={$_.uuid}
  }, @{
    Name='finding_name';Expression={$_.meta.name}
  }, @{
    Name='create_time';Expression={$_.meta.create_time}
  }, @{
    Name='project_uuid';Expression={$_.spec.project_uuid}
  }
```

**Output example:**
```json
{
  "finding_uuid": "0123456789abcdef01234567",
  "finding_name": "Vulnerability in package",
  "create_time": "2024-01-15T10:30:00Z",
  "project_uuid": "0123456789abcdef01234567"
}
```

**Note:** UUIDs in the Endor Labs API are 24-character hexadecimal strings without hyphens.

Save the values:
```powershell
$FINDING_CREATE_TIME = "2024-01-15T10:30:00Z"
$PROJECT_UUID = "project-uuid-123"
```

### Step 2: List ScanResults for the Project

```powershell
endorctl api list `
  --resource ScanResult `
  --filter "meta.parent_uuid==`"$PROJECT_UUID`"" `
  --list-all `
  --field-mask "uuid,meta.name,spec.start_time,spec.end_time,spec.environment.config" `
  | ConvertFrom-Json | Select-Object -ExpandProperty list | 
  Select-Object -ExpandProperty objects | 
  Select-Object @{
    Name='uuid';Expression={$_.uuid}
  }, @{
    Name='name';Expression={$_.meta.name}
  }, @{
    Name='start_time';Expression={$_.spec.start_time}
  }, @{
    Name='end_time';Expression={$_.spec.end_time}
  }, @{
    Name='config';Expression={$_.spec.environment.config}
  }
```

### Step 3: Filter Matching ScanResults

```powershell
# Filter ScanResults where finding was created during the scan
endorctl api list `
  --resource ScanResult `
  --filter "meta.parent_uuid==`"$PROJECT_UUID`"" `
  --list-all `
  --field-mask "uuid,meta.name,spec.start_time,spec.end_time,spec.environment.config" `
  | ConvertFrom-Json | Select-Object -ExpandProperty list | 
  Select-Object -ExpandProperty objects | 
  Where-Object {
    $_.spec.start_time -ne $null -and 
    $_.spec.end_time -ne $null -and
    [DateTime]$_.spec.start_time -le [DateTime]$FINDING_CREATE_TIME -and
    [DateTime]$_.spec.end_time -ge [DateTime]$FINDING_CREATE_TIME
  } | 
  Select-Object @{
    Name='uuid';Expression={$_.uuid}
  }, @{
    Name='name';Expression={$_.meta.name}
  }, @{
    Name='start_time';Expression={$_.spec.start_time}
  }, @{
    Name='end_time';Expression={$_.spec.end_time}
  }, @{
    Name='scan_config';Expression={$_.spec.environment.config}
  }
```

### Step 4: Extract ScanConfig

```powershell
# Get just the ScanConfig from matching ScanResults
endorctl api list `
  --resource ScanResult `
  --filter "meta.parent_uuid==`"$PROJECT_UUID`"" `
  --list-all `
  --field-mask "spec.environment.config" `
  | ConvertFrom-Json | Select-Object -ExpandProperty list | 
  Select-Object -ExpandProperty objects | 
  Where-Object {
    $_.spec.start_time -ne $null -and 
    $_.spec.end_time -ne $null -and
    [DateTime]$_.spec.start_time -le [DateTime]$FINDING_CREATE_TIME -and
    [DateTime]$_.spec.end_time -ge [DateTime]$FINDING_CREATE_TIME
  } | 
  Select-Object -ExpandProperty spec | 
  Select-Object -ExpandProperty environment | 
  Select-Object -ExpandProperty config
```

### Complete PowerShell Script

Here's a complete PowerShell script that does all steps:

```powershell
# find_scan_config_for_finding.ps1
param(
    [Parameter(Mandatory=$true)]
    [string]$FindingUuid,
    
    [Parameter(Mandatory=$true)]
    [string]$Namespace
)

# Step 1: Get Finding details
Write-Host "Getting Finding details..." -ForegroundColor Cyan
$findingData = endorctl api get `
  --resource Finding `
  --uuid $FindingUuid `
  --field-mask "meta.create_time,spec.project_uuid,meta.name" `
  | ConvertFrom-Json

$findingCreateTime = $findingData.meta.create_time
$projectUuid = $findingData.spec.project_uuid
$findingName = $findingData.meta.name

Write-Host "Finding: $findingName" -ForegroundColor Green
Write-Host "Created: $findingCreateTime" -ForegroundColor Green
Write-Host "Project: $projectUuid" -ForegroundColor Green
Write-Host ""

# Step 2 & 3: List and filter ScanResults
Write-Host "Searching for matching ScanResults..." -ForegroundColor Cyan
$scanResults = endorctl api list `
  --resource ScanResult `
  --filter "meta.parent_uuid==`"$projectUuid`"" `
  --list-all `
  --field-mask "uuid,meta.name,spec.start_time,spec.end_time,spec.environment.config" `
  | ConvertFrom-Json | 
  Select-Object -ExpandProperty list | 
  Select-Object -ExpandProperty objects | 
  Where-Object {
    $_.spec.start_time -ne $null -and 
    $_.spec.end_time -ne $null -and
    [DateTime]$_.spec.start_time -le [DateTime]$findingCreateTime -and
    [DateTime]$_.spec.end_time -ge [DateTime]$findingCreateTime
  } | 
  Select-Object @{
    Name='scan_uuid';Expression={$_.uuid}
  }, @{
    Name='scan_name';Expression={$_.meta.name}
  }, @{
    Name='scan_start';Expression={$_.spec.start_time}
  }, @{
    Name='scan_end';Expression={$_.spec.end_time}
  }, @{
    Name='scan_config';Expression={$_.spec.environment.config}
  }

if ($scanResults) {
    $scanResults | ConvertTo-Json -Depth 10
} else {
    Write-Host "No matching ScanResults found." -ForegroundColor Yellow
}
```

**Usage:**
```powershell
.\find_scan_config_for_finding.ps1 -FindingUuid "your-finding-uuid" -Namespace "your-namespace"
```

## Alternative: Using curl

If you prefer using curl directly:

```bash
# Set your token
export ENDOR_TOKEN="your-token-here"
export NAMESPACE="your-namespace"
export FINDING_UUID="your-finding-uuid"

# Step 1: Get Finding
FINDING_DATA=$(curl -s \
  --header "Authorization: Bearer $ENDOR_TOKEN" \
  "https://api.endorlabs.com/v1/namespaces/$NAMESPACE/findings/$FINDING_UUID?field_mask=meta.create_time,spec.project_uuid,meta.name" \
  | jq -r '{create_time: .meta.create_time, project_uuid: .spec.project_uuid}')

FINDING_CREATE_TIME=$(echo "$FINDING_DATA" | jq -r '.create_time')
PROJECT_UUID=$(echo "$FINDING_DATA" | jq -r '.project_uuid')

# Step 2 & 3: List and filter ScanResults
curl -s \
  --header "Authorization: Bearer $ENDOR_TOKEN" \
  "https://api.endorlabs.com/v1/namespaces/$NAMESPACE/scan-results?list_parameters.filter=meta.parent_uuid==\"$PROJECT_UUID\"&list_parameters.list_all=true&field_mask=uuid,meta.name,spec.start_time,spec.end_time,spec.environment.config" \
  | jq --arg finding_time "$FINDING_CREATE_TIME" \
    '.list.objects[] | 
    select(.spec.start_time != null and .spec.end_time != null) |
    select(.spec.start_time <= $finding_time and .spec.end_time >= $finding_time) |
    .spec.environment.config'
```

## Notes

- The `--list-all` flag is important to get all ScanResults, not just the first page
- The `--field-mask` flag limits the response size by only requesting needed fields
- Time comparisons in jq use string comparison, which works for ISO 8601 format
- If multiple ScanResults match, all will be returned (possible if scans overlap)
- The `spec.environment.config` field contains the full ScanConfig used by endorctl


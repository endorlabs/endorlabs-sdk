# find_scan_config_for_finding.ps1
# Find ScanConfig for Finding - PowerShell Script
#
# Given a Finding UUID, this script finds the ScanResult resources that could
# have created the finding by:
# 1. Getting the Finding by UUID to retrieve its creation date and project UUID
# 2. Searching through all ScanResult resources for the same project
# 3. Filtering ScanResults where scan_start < finding.created < scan_end
# 4. Returning spec.environment.config.ScanConfig from matching ScanResults
#
# Usage:
#   .\find_scan_config_for_finding.ps1 -FindingUuid "abc123-def456-..." -Namespace "your-namespace"

param(
    [Parameter(Mandatory=$true)]
    [string]$FindingUuid,
    
    [Parameter(Mandatory=$true)]
    [string]$Namespace
)

# Step 1: Get Finding details
Write-Host "Getting Finding details..." -ForegroundColor Cyan
try {
    $findingData = endorctl api get `
        --resource Finding `
        --uuid $FindingUuid `
        --field-mask "meta.create_time,spec.project_uuid,meta.name" `
        | ConvertFrom-Json
} catch {
    Write-Host "Error getting Finding: $_" -ForegroundColor Red
    exit 1
}

if (-not $findingData) {
    Write-Host "Finding not found: $FindingUuid" -ForegroundColor Red
    exit 1
}

$findingCreateTime = $findingData.meta.create_time
$projectUuid = $findingData.spec.project_uuid
$findingName = $findingData.meta.name

if (-not $findingCreateTime -or -not $projectUuid) {
    Write-Host "Finding missing required fields (create_time or project_uuid)" -ForegroundColor Red
    exit 1
}

Write-Host "Finding: $findingName" -ForegroundColor Green
Write-Host "Created: $findingCreateTime" -ForegroundColor Green
Write-Host "Project: $projectUuid" -ForegroundColor Green
Write-Host ""

# Step 2 & 3: List and filter ScanResults
Write-Host "Searching for matching ScanResults..." -ForegroundColor Cyan
try {
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
} catch {
    Write-Host "Error listing ScanResults: $_" -ForegroundColor Red
    exit 1
}

if ($scanResults) {
    Write-Host "Found $($scanResults.Count) matching ScanResult(s):" -ForegroundColor Green
    Write-Host ""
    $scanResults | ConvertTo-Json -Depth 10
} else {
    Write-Host "No matching ScanResults found." -ForegroundColor Yellow
    exit 0
}


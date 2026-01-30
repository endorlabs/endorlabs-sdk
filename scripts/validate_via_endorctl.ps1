# Validate SDK test scenarios via endorctl api (list/get with filter and mask).
# Run from repo root. Uses ENDOR_NAMESPACE if set; endorctl uses its own config.
# Bash equivalent: set ENDOR_NAMESPACE; run same endorctl api list/get commands.

$ErrorActionPreference = "Continue"

Write-Host "=== Validate via endorctl (list/mask/filter) ===" -ForegroundColor Cyan

# Check endorctl available
try {
    $null = Get-Command endorctl -ErrorAction Stop
} catch {
    Write-Host "SKIP: endorctl not in PATH. Install endorctl to run validation." -ForegroundColor Yellow
    exit 0
}

$ns = $env:ENDOR_NAMESPACE
if (-not $ns) {
    Write-Host "INFO: ENDOR_NAMESPACE not set; endorctl will use its config (e.g. ~/.endorctl/config.yaml)" -ForegroundColor Gray
}

function Invoke-EndorctlList {
    param([string]$Resource, [string]$Filter = "", [string]$Mask = "", [bool]$Traverse = $false)
    $args = @("api", "list", "-r", $Resource, "-o", "json")
    if ($Filter) { $args += "--filter"; $args += $Filter }
    if ($Mask)   { $args += "--field-mask"; $args += $Mask }
    if ($Traverse) { $args += "--traverse" }
    $raw = & endorctl @args 2>&1 | Where-Object { $_ -notmatch "DEBUG" }
    $raw -join "`n" | ConvertFrom-Json -ErrorAction SilentlyContinue
}

function Invoke-EndorctlGet {
    param([string]$Resource, [string]$Uuid)
    $raw = & endorctl api get -r $Resource --uuid $Uuid -o json 2>&1 | Where-Object { $_ -notmatch "DEBUG" }
    $raw -join "`n" | ConvertFrom-Json -ErrorAction SilentlyContinue
}

# 1. Project advanced filtering (filter + mask)
Write-Host "`n[1] Project list (filter + mask)" -ForegroundColor Yellow
$proj = Invoke-EndorctlList -Resource "Project" -Filter "spec.platform_source==PLATFORM_SOURCE_GITHUB" -Mask "meta.name,spec.platform_source"
if ($proj -and $proj.list -and $proj.list.objects) {
    $count = $proj.list.objects.Count
    Write-Host "  Objects: $count" -ForegroundColor Green
    if ($count -gt 0) {
        $first = $proj.list.objects[0]
        $keys = ($first.PSObject.Properties | Select-Object -ExpandProperty Name) -join ","
        Write-Host "  First object keys: $keys" -ForegroundColor Gray
    }
} else {
    Write-Host "  No data or error (check namespace/auth)" -ForegroundColor Gray
}

# 2. Repository (filter + mask + traverse)
Write-Host "`n[2] Repository list (filter + mask + traverse)" -ForegroundColor Yellow
$repo = Invoke-EndorctlList -Resource "Repository" -Filter "spec.platform_source==PLATFORM_SOURCE_GITHUB" -Mask "meta.name,spec.platform_source" -Traverse $true
if ($repo -and $repo.list -and $repo.list.objects) {
    Write-Host "  Objects: $($repo.list.objects.Count)" -ForegroundColor Green
} else {
    Write-Host "  No data or error" -ForegroundColor Gray
}

# 3. RepositoryVersion (filter + mask + traverse)
Write-Host "`n[3] RepositoryVersion list (filter + mask + traverse)" -ForegroundColor Yellow
$rv = Invoke-EndorctlList -Resource "RepositoryVersion" -Filter "spec.platform_source==PLATFORM_SOURCE_GITHUB" -Mask "meta.name,spec.platform_source" -Traverse $true
if ($rv -and $rv.list -and $rv.list.objects) {
    Write-Host "  Objects: $($rv.list.objects.Count)" -ForegroundColor Green
} else {
    Write-Host "  No data or error" -ForegroundColor Gray
}

# 4. ScanProfile (filter + mask)
Write-Host "`n[4] ScanProfile list (filter + mask)" -ForegroundColor Yellow
$sp = Invoke-EndorctlList -Resource "ScanProfile" -Mask "meta.name,spec.name" -Traverse $true
if ($sp -and $sp.list -and $sp.list.objects) {
    Write-Host "  Objects: $($sp.list.objects.Count)" -ForegroundColor Green
} else {
    Write-Host "  No data or error" -ForegroundColor Gray
}

# 5. PackageLicense (mask only; API uses oss namespace)
Write-Host "`n[5] PackageLicense list (mask)" -ForegroundColor Yellow
$pl = Invoke-EndorctlList -Resource "PackageLicense" -Mask "meta.name,spec.project_uuid"
if ($pl -and $pl.list -and $pl.list.objects) {
    Write-Host "  Objects: $($pl.list.objects.Count)" -ForegroundColor Green
    if ($pl.list.objects.Count -gt 0) {
        $first = $pl.list.objects[0]
        $keys = ($first.PSObject.Properties | Select-Object -ExpandProperty Name) -join ","
        Write-Host "  First object keys: $keys" -ForegroundColor Gray
    }
} else {
    Write-Host "  No data or error" -ForegroundColor Gray
}

# 6. AuthorizationPolicy list
Write-Host "`n[6] AuthorizationPolicy list" -ForegroundColor Yellow
$ap = Invoke-EndorctlList -Resource "AuthorizationPolicy"
if ($ap -and $ap.list -and $ap.list.objects) {
    Write-Host "  Objects: $($ap.list.objects.Count)" -ForegroundColor Green
} else {
    Write-Host "  No data or error" -ForegroundColor Gray
}

# 7. Finding get by UUID (optional: need a valid finding UUID from a scan)
Write-Host "`n[7] Finding get (optional; requires valid finding UUID)" -ForegroundColor Yellow
$findingList = Invoke-EndorctlList -Resource "Finding" -Mask "uuid" -Traverse $true
if ($findingList -and $findingList.list -and $findingList.list.objects -and $findingList.list.objects.Count -gt 0) {
    $fuuid = $findingList.list.objects[0].uuid
    $f = Invoke-EndorctlGet -Resource "Finding" -Uuid $fuuid
    if ($f -and $f.uuid) {
        Write-Host "  Get by UUID OK (namespace from endorctl config)" -ForegroundColor Green
    } else {
        Write-Host "  Get returned no object (wrong namespace?)" -ForegroundColor Gray
    }
} else {
    Write-Host "  No findings to test get" -ForegroundColor Gray
}

Write-Host "`n=== Done ===" -ForegroundColor Cyan
Write-Host "Use output above to see if list+mask returns full or partial objects (keys on first item)." -ForegroundColor Gray

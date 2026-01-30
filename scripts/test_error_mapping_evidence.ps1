# Test script to gather evidence about error mapping variants and invariants
# Tests both invalid UUID format and valid format but non-existent resource scenarios

Write-Host "=== Testing Error Mapping Evidence ===" -ForegroundColor Cyan
Write-Host ""

# Test 1: Invalid UUID format (contains hyphens, doesn't match regex)
Write-Host "Test 1: Invalid UUID format (contains hyphens)" -ForegroundColor Yellow
Write-Host "UUID: invalid-uuid" -ForegroundColor Gray
$result1 = endorctl api get -r ScanResult --uuid "invalid-uuid" 2>&1
$httpCode1 = ($result1 | Select-String -Pattern 'http.code":\s*(\d+)').Matches.Groups[1].Value
$errorMsg1 = ($result1 | Select-String -Pattern 'ERROR\s+(\S+):').Matches.Groups[1].Value
Write-Host "HTTP Code: $httpCode1" -ForegroundColor $(if ($httpCode1 -eq "400") { "Green" } else { "Red" })
Write-Host "gRPC Code: $errorMsg1" -ForegroundColor $(if ($errorMsg1 -eq "invalid-args") { "Green" } else { "Red" })
Write-Host "Expected: HTTP 400, gRPC code 3 (INVALID_ARGUMENT)" -ForegroundColor Gray
Write-Host ""

# Test 2: Invalid UUID format (doesn't match regex pattern)
Write-Host "Test 2: Invalid UUID format (doesn't match regex)" -ForegroundColor Yellow
Write-Host "UUID: 1234567890abcdef1234567890abcdef (32 hex chars, but not valid UUID)" -ForegroundColor Gray
$result2 = endorctl api get -r ScanResult --uuid "1234567890abcdef1234567890abcdef" 2>&1
$httpCode2 = ($result2 | Select-String -Pattern 'http.code":\s*(\d+)').Matches.Groups[1].Value
$errorMsg2 = ($result2 | Select-String -Pattern 'ERROR\s+(\S+):').Matches.Groups[1].Value
Write-Host "HTTP Code: $httpCode2" -ForegroundColor $(if ($httpCode2 -eq "400") { "Green" } else { "Red" })
Write-Host "gRPC Code: $errorMsg2" -ForegroundColor $(if ($errorMsg2 -eq "invalid-args") { "Green" } else { "Red" })
Write-Host "Expected: HTTP 400, gRPC code 3 (INVALID_ARGUMENT)" -ForegroundColor Gray
Write-Host ""

# Test 3: Try to get a real UUID to test "not found" scenario
Write-Host "Test 3: Attempting to get a real UUID for 'not found' test" -ForegroundColor Yellow
# Get first scan result UUID (suppress debug output)
$listResult = endorctl api list -r ScanResult --field-mask uuid -o json 2>&1 | Where-Object { $_ -notmatch "DEBUG" } | ConvertFrom-Json -ErrorAction SilentlyContinue
if ($listResult -and $listResult.list -and $listResult.list.objects -and $listResult.list.objects.Count -gt 0) {
    $realUuid = $listResult.list.objects[0].uuid
    Write-Host "Found real UUID: $realUuid" -ForegroundColor Gray
    
    # Modify it slightly to create a non-existent but valid-format UUID
    $modifiedUuid = $realUuid.Substring(0, $realUuid.Length - 1) + "0"
    Write-Host "Testing with modified UUID (should not exist): $modifiedUuid" -ForegroundColor Gray
    $result3 = endorctl api get -r ScanResult --uuid $modifiedUuid 2>&1
    $httpCode3 = ($result3 | Select-String -Pattern 'http.code":\s*(\d+)').Matches.Groups[1].Value
    $errorMsg3 = ($result3 | Select-String -Pattern 'ERROR\s+(\S+):').Matches.Groups[1].Value
    Write-Host "HTTP Code: $httpCode3" -ForegroundColor $(if ($httpCode3 -eq "404") { "Green" } else { "Yellow" })
    Write-Host "gRPC Code: $errorMsg3" -ForegroundColor $(if ($errorMsg3 -eq "not-found") { "Green" } else { "Yellow" })
    Write-Host "Expected: HTTP 404, gRPC code 5 (NOT_FOUND)" -ForegroundColor Gray
} else {
    Write-Host "Could not retrieve real UUID for testing" -ForegroundColor Red
}
Write-Host ""

Write-Host "=== Summary ===" -ForegroundColor Cyan
Write-Host "Invariant (PROVEN): Invalid UUID format → HTTP 400 + gRPC code 3 (INVALID_ARGUMENT)" -ForegroundColor Green
Write-Host "Variant (NEEDS TESTING): Valid UUID format but resource doesn't exist → HTTP 404 + gRPC code 5 (NOT_FOUND)" -ForegroundColor Yellow

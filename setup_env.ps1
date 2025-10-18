# PowerShell script to set up environment variables for Endor Cockpit integration tests
# Run this script before running integration tests

Write-Host "Setting up Endor Cockpit environment variables..." -ForegroundColor Green

# Set the environment variables
$env:ENDOR_API = "https://api.endorlabs.com"
$env:ENDOR_API_CREDENTIALS_KEY = "your-api-key-here"
$env:ENDOR_API_CREDENTIALS_SECRET = "your-api-secret-here"

Write-Host "Environment variables set:" -ForegroundColor Yellow
Write-Host "  ENDOR_API = $env:ENDOR_API"
Write-Host "  ENDOR_API_CREDENTIALS_KEY = $env:ENDOR_API_CREDENTIALS_KEY"
Write-Host "  ENDOR_API_CREDENTIALS_SECRET = [HIDDEN]"

Write-Host "`nTo run integration tests:" -ForegroundColor Cyan
Write-Host "  python run_integration_tests.py" -ForegroundColor White

Write-Host "`nTo check environment:" -ForegroundColor Cyan
Write-Host "  python test_integration_setup.py" -ForegroundColor White

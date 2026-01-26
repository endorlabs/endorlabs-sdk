# PowerShell script to ensure ENDOR_TOKEN is set
# Usage: . .\scripts\Set-EndorToken.ps1
# Or add to your PowerShell profile for automatic loading

$ErrorActionPreference = "SilentlyContinue"

# Get project root (assuming script is in scripts/)
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptPath
$envFile = Join-Path $projectRoot ".env"

# Load .env file if it exists (uv best practice)
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim() -replace '^["\']|["\']$', ''
            if (-not [Environment]::GetEnvironmentVariable($name, "Process")) {
                [Environment]::SetEnvironmentVariable($name, $value, "Process")
            }
        }
    }
}

# Ensure ENDOR_TOKEN is set and valid
if (-not $env:ENDOR_TOKEN) {
    $ensureScript = Join-Path $scriptPath "ensure_endor_token.py"
    if (Test-Path $ensureScript) {
        Write-Host "🔐 Ensuring ENDOR_TOKEN is set..." -ForegroundColor Cyan
        $token = python $ensureScript --quiet 2>$null
        if ($token) {
            $env:ENDOR_TOKEN = $token
            Write-Host "✅ ENDOR_TOKEN set" -ForegroundColor Green
        }
    }
}

# Set UV_ENV_FILE for uv to automatically load .env
if (-not $env:UV_ENV_FILE) {
    $env:UV_ENV_FILE = ".env"
}

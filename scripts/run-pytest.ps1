# PowerShell script to run pytest with .env file loaded
# Usage: .\scripts\run-pytest.ps1 [pytest arguments]
# Or: uv run --env-file .env pytest [pytest arguments]

param(
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$PytestArgs
)

# Ensure we're in the project root
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptPath
Set-Location $projectRoot

# Run pytest with .env file explicitly loaded
uv run --env-file .env pytest @PytestArgs

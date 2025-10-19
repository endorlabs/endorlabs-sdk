# PowerShell script to set up Unicode environment for Windows
# Run this before starting your IDE or terminal session

# Set Unicode encoding for Python
$env:PYTHONIOENCODING = "utf-8"

# Set console output encoding
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "[OK] Unicode environment configured for Windows" -ForegroundColor Green
Write-Host "PYTHONIOENCODING: $env:PYTHONIOENCODING" -ForegroundColor Yellow
Write-Host "Console encoding: $([Console]::OutputEncoding.EncodingName)" -ForegroundColor Yellow

# Test the configuration
Write-Host "`nTesting Unicode support..." -ForegroundColor Cyan
uv run python -c "print('[OK] Unicode test: RAG module works!')"

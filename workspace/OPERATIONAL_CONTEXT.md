# Endor Cockpit: Operational Context Guide

## Environment Setup

### System Information
- **OS**: Windows 11
- **Shell**: PowerShell 7 (`C:\Program Files\PowerShell\7\pwsh.exe`)
- **IDE**: Cursor IDE (authenticated as repo owner)
- **GitHub CLI**: Installed at `C:\Program Files\GitHub CLI\gh.exe` (not in PATH by default)

### GitHub CLI Setup
```powershell
# Add GitHub CLI to PATH (temporary)
$env:PATH += ";C:\Program Files\GitHub CLI"

# Verify installation
gh --version

# Authenticate (if not already done)
gh auth login

# Test repository access
gh repo view endor-solutions-tgowan/endor-cockpit
```

### Environment Variables
```powershell
# Endor Labs API Configuration
$env:ENDOR_API = "https://api.endorlabs.com"
$env:ENDOR_API_CREDENTIALS_KEY = "your-api-key-here"
$env:ENDOR_API_CREDENTIALS_SECRET = "your-api-secret-here"
$env:ENDOR_NAMESPACE = "endor-solutions-tgowan.cockpit"
```

### Project Structure
- **Repository**: `endor-solutions-tgowan/endor-cockpit`
- **Branch**: `dev`
- **Build System**: UV (with Poetry for endorctl compatibility)
- **Test Framework**: pytest with integration markers
- **Linting**: ruff
- **Coverage**: pytest-cov

## CI/CD Integration

### GitHub Actions Status
- **Workflow**: `.github/workflows/ci.yml`
- **Jobs**: resolve-dependencies, lint, test, security, coverage
- **Integration Tests**: Marked with `@pytest.mark.integration`
- **Environment Variables**: Set in GitHub repository secrets

### CI Monitoring Scripts
- `check_ci_simple.ps1` - Simple CI status check
- `ci_manager.ps1` - Comprehensive CI management
- `ci_integration.ps1` - CI integration monitoring

## Development Workflow

### Local Testing
```bash
# Run unit tests only
uv run pytest -m "not integration"

# Run integration tests (requires environment variables)
uv run pytest -m integration

# Run all tests
uv run pytest

# Lint and fix
uv run ruff check . --fix
```

### Security Scanning
```bash
# Local scan with endorctl
endorctl scan

# Scan with specific project name
endorctl scan --project-name endor-cockpit
```

## Key Learnings

### Namespace Management
- **Canonical Naming**: Use hierarchical names (e.g., `tenant.parent.child`)
- **Parent Namespaces**: Always use canonical names, not UUIDs
- **API Permissions**: Based on canonical naming, not UUIDs

### Policy Management
- **Exception Policies**: Use `endorctl:allow` comments for immediate fixes
- **Policy Creation**: May require manual UI configuration
- **False Positives**: Handle via code comments or policy exceptions

### Testing Strategy
- **Unit Tests**: Fast, no external dependencies
- **Integration Tests**: Require API credentials, marked with `@pytest.mark.integration`
- **Environment Checks**: Tests skip gracefully if credentials missing

## Troubleshooting

### Common Issues
1. **GitHub CLI not found**: Add to PATH or use full path
2. **API credentials missing**: Set environment variables
3. **Integration test failures**: Check credentials and permissions
4. **Linting errors**: Run `ruff check . --fix`

### File Locations
- **Workspace**: `workspace/` (user-specific, gitignored)
- **Documentation**: `docs/agents/`
- **Tests**: `tests/`
- **CI Configuration**: `.github/workflows/ci.yml`

## Quick Commands

### Repository Management
```bash
# Check CI status
gh run list --branch dev

# View latest run
gh run view

# Trigger workflow
gh workflow run ci.yml
```

### Development
```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Lint code
uv run ruff check .

```

### Security
```bash
# Scan project
endorctl scan

# Check findings
endorctl findings list
```

## Notes
- This context is specific to the Windows 11 development environment
- GitHub CLI requires PATH configuration for immediate use
- Integration tests require proper API credentials
- Workspace folder is user-specific and excluded from version control

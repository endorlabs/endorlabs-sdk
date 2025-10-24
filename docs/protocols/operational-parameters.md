# Operational Parameters Protocol

> **L2 (System State Tracking) - Monitor and maintain system operational state**

## Overview

This protocol defines the operational parameters that should be tracked and monitored to ensure system health and effective agent operation.

## System State Tracking

### Environment Status
**Location**: `.workspace/validation.log`
**Parameters**:
- Validated timestamp
- Credential status (valid/invalid/expired)
- API connectivity status
- Dependency versions

**Monitoring**:
- Check validation.log before operations
- Re-validate if timestamp > 24 hours
- Alert on credential expiration

### Development State
**Location**: Various sources
**Parameters**:
- Linting status (ruff check)
- Test coverage (pytest --cov)
- Security scan results (endorctl scan)
- Documentation freshness

**Monitoring**:
- Run linting before commits
- Check test coverage regularly
- Security scan before releases
- Sync docs after changes

### Schema Drift Tracking
**Location**: Resource model files
**Parameters**:
- Unknown fields in API responses
- New enum values
- Changed response structures
- Deprecated endpoints

**Monitoring**:
- Watch for warnings in logs
- Update models when drift detected
- Document breaking changes

### CI/CD State Tracking
**Location**: `.github/workflows/ci.yml`, GitHub Actions
**Parameters**:
- Environment variable configuration (vars vs secrets)
- Test classification (unit vs integration)
- Python version compatibility
- Dependency installation status

**Monitoring**:
- Verify environment variable references in CI workflows
- Ensure proper test classification for API-dependent tests
- Check Python version alignment between local and CI
- Monitor dependency installation across Python versions

**Common Issues**:
- **Environment Variables**: Use `${{ vars.VARIABLE }}` for repository variables, `${{ secrets.SECRET }}` for encrypted secrets
- **Test Classification**: Mark API-dependent tests with `@pytest.mark.integration`
- **Variable Scope**: Integration tests receive environment variables, unit tests do not
- **Python Versions**: Ensure `requires-python` in `pyproject.toml` aligns with CI matrix

## Implementation

### For Agents
1. **Check system state** before operations
2. **Monitor drift warnings** in logs
3. **Update knowledge base** when needed
4. **Report issues** to maintenance protocols

### For Maintenance
1. **Regular validation** of system state
2. **Proactive updates** of knowledge base
3. **Schema drift detection** and response
4. **Performance monitoring** and optimization

## Success Criteria

- ✅ Environment status is current (< 24 hours)
- ✅ Knowledge base is fresh (< 7 days)
- ✅ Development state is clean (no linting errors)
- ✅ Schema drift is monitored and addressed
- ✅ CI/CD configuration is correct (environment variables, test classification)

## Related Protocols

- [Mandatory Context Protocol](mandatory-context.md) - L1

---

*This protocol ensures system health and effective operation by monitoring key operational parameters.*

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

### Knowledge Base State
**Location**: `holocron_data/vector_db_manifest.json`
**Parameters**:
- Last sync timestamp
- Chunk count and coverage
- Query performance metrics
- Schema drift detection

**Monitoring**:
- Check manifest for freshness
- Re-sync if timestamp > 7 days
- Monitor query performance

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

## Related Protocols

- [Mandatory Context Protocol](mandatory-context.md) - L1
- [Knowledge Sync Protocol](knowledge-sync.md) - L2/L3
- [Documentation Standards](documentation-standards.md) - L2

---

*This protocol ensures system health and effective operation by monitoring key operational parameters.*

# Knowledge Base Maintenance Guide

> **Maintaining the freshness and accuracy of the Endor Cockpit knowledge base**

## Overview

The Endor Cockpit knowledge base is a **portable shared learning index** that contains comprehensive documentation, API patterns, best practices, and operational procedures. This guide explains how to maintain its accuracy and freshness.

## When to Update the Knowledge Base

### Contradictions Found
- **API Behavior**: When actual API behavior differs from documented patterns
- **Error Messages**: When error messages or responses don't match documentation
- **Workflows**: When established procedures no longer work as documented
- **Security**: When security requirements or compliance standards change

### New Discoveries
- **Best Practices**: When better patterns are discovered through experience
- **Workarounds**: When solutions to common problems are found
- **Optimizations**: When more efficient approaches are identified
- **Integration Patterns**: When new integration methods are developed

### System Changes
- **API Updates**: When Endor Labs API changes or new endpoints are added
- **Dependencies**: When dependency versions or requirements change
- **Tools**: When development tools or processes are updated
- **Infrastructure**: When deployment or operational procedures change

## How to Identify Contradictions

### During Development
1. **Query First**: Always start by searching the repo
2. **Compare Results**: Check if the retrieved information matches external_docs
3. **Test Assumptions**: Verify that documented patterns actually work
4. **Note Discrepancies**: Document any differences found and surface to user.

### During Operations
1. **Monitor Outcomes**: Track whether documented procedures succeed
2. **Error Analysis**: Analyze failures against documented troubleshooting
3. **Performance**: Note when documented optimizations don't work
4. **User Feedback**: Collect feedback on documentation accuracy

### During Testing
1. **Integration Tests**: Check if tests pass with documented patterns
2. **Edge Cases**: Verify documented workarounds for edge cases
3. **Error Handling**: Test documented error recovery procedures
4. **Security**: Validate documented security practices

## Best Practices

### For AI Agents
1. **Always Query First**: Start every task by querying the knowledge base
2. **Verify Information**: Cross-check retrieved information with reality
3. **Report Contradictions**: Document any discrepancies found
4. **Update When Needed**: Incorporate new learnings into the knowledge base

### For Developers
1. **Document Changes**: Update documentation when making code changes
2. **Test Documentation**: Verify that documented procedures work
3. **Share Learnings**: Contribute new patterns and best practices
4. **Maintain Accuracy**: Keep documentation current and accurate

### For Operations
1. **Monitor Effectiveness**: Track whether documented procedures work
2. **Collect Feedback**: Gather input on documentation usefulness
3. **Update Procedures**: Modify documentation when processes change
4. **Share Knowledge**: Contribute operational insights to the knowledge base

## Automated Documentation & Drift Detection

The Endor Cockpit project includes automated workflows to maintain documentation freshness and detect schema drift:

### Documentation Sync

**Workflow**: `.github/workflows/sync-external-docs.yml`

- **Schedule**: Weekly on Mondays at 2 AM UTC
- **Purpose**: Downloads and updates external documentation
- **Operations**:
  - Downloads OpenAPI specification from Endor Labs API
  - Downloads user documentation from docs.endorlabs.com
  - Commits updates automatically

**Manual Execution**:
```bash
python scripts/unified_docs_workflow.py --update-docs-only
```

### Schema Drift Detection

**Workflow**: `.github/workflows/schema-drift-detection.yml`

- **Schedule**: 
  - Hourly (endorctl version checks)
  - Weekly on Mondays at 3 AM UTC (after docs sync)
- **Purpose**: Detects discrepancies between API responses and Pydantic models
- **Operations**:
  - Runs integration tests with drift detection
  - Parses schema drift warnings
  - Creates GitHub issues for new drifts
  - Generates drift reports

**Manual Execution**:
```bash
python scripts/unified_docs_workflow.py --check-drift-only
```

### Unified Workflow

For complete workflow execution (docs + drift detection):

```bash
python scripts/unified_docs_workflow.py --all
```

**Key Features**:
- Ensures docs are fresh before drift detection
- Only runs drift detection if docs were updated (unless `--force`)
- Creates actionable GitHub issues for new drifts
- Provides comprehensive logging and reporting

**Documentation**: See [Unified Documentation & Schema Drift Workflow](rules-of-engagement/docs-drift-workflow.md) for complete details.

### When to Run Manually

Run the unified workflow manually when:
- **Before Major Changes**: Update docs and check drift before implementing new features
- **After API Updates**: When Endor Labs API is updated, check for drift
- **During Development**: Verify models match API responses during development
- **Troubleshooting**: When encountering unexpected API behavior

### Monitoring Workflows

- **GitHub Actions**: Check workflow runs in the Actions tab
- **Drift Issues**: Review issues with label `schema-drift`
- **Drift Reports**: Check `schema_drift_report.json` artifacts in workflow runs

## Conclusion

The knowledge base is a living system that requires active maintenance to remain valuable. By following these practices, we ensure that the Endor Cockpit knowledge base remains accurate, comprehensive, and useful for all AI agents and developers working with the system.

Remember: **Query First, Verify Always, Update When Needed**

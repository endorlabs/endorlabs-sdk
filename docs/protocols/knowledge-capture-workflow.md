# Knowledge Capture Workflow

> **L1 (Essential - Always Required) - Systematic approach to capture, review, and promote technical learnings into permanent documentation**

## Overview

This protocol establishes a systematic workflow for capturing technical learnings during SDK development, API debugging, and endorctl usage, then promoting valuable insights into permanent documentation.

---

## Phase 1: Capture Phase

> **L1 CRITICAL**: This phase is mandatory for all agent operations. Every significant discovery must be captured.

### When to Create Logbook Entries

**MANDATORY**: Create a new logbook entry for:
- **API debugging sessions** where unexpected behavior occurs
- **SDK development** when encountering errors or quirks
- **endorctl usage** when commands fail or behave unexpectedly
- **Integration testing** when tests fail due to API issues
- **Schema drift detection** when new fields appear in API responses
- **Permission issues** when operations fail with 403/401 errors
- **Any technical discovery** that could help future agents

### Required Information for Each Entry

> **L1 ESSENTIAL**: All entries must follow the template format exactly. Incomplete entries cannot be promoted.

**Template Compliance**:
- Use `_LOGBOOK_TEMPLATE.md` format exactly
- Include all required sections
- Provide specific function calls and error messages
- Include working code examples in resolution

**Resource Type Tagging**:
- Tag entries with relevant resource types: `project`, `finding`, `policy`, `namespace`, `scan`
- Include operation type: `debugging`, `api-quirk`, `schema-drift`, `permissions`, `testing`
- Add context tags: `crud`, `patching`, `tagging`, `authentication`, `validation`

### Format Compliance Checklist

- [ ] **Task**: Clear description of what was being attempted
- [ ] **Context**: Resource types, related files, RAG queries, terminal output
- [ ] **Attempted Approach**: Specific function calls, API endpoints, commands
- [ ] **Unexpected Behavior**: Expected vs actual behavior, error messages
- [ ] **Resolution**: Working solution with exact function signatures
- [ ] **Key Learning**: One-sentence summary of core insight
- [ ] **Relevant Documentation**: SDK references, test files, API endpoints
- [ ] **Miscellaneous Notes**: Additional context and follow-up items
- [ ] **Tags**: Appropriate categorization
- [ ] **Reviewed for Promotion**: Checkbox marked when ready

---

## Phase 2: Review Phase

> **L1 MANDATORY**: This phase must be completed before any commit. No code changes can be committed without reviewing logbook entries.

### Pre-Commit Checklist

**REQUIRED**: Before any commit, review logbook entries:

1. **Check for entries** marked "Reviewed for Promotion"
2. **Validate completeness** of entry information
3. **Assess value** for future agents
4. **Request user approval** for promotion

### Entry Completeness Validation

**Required Elements**:
- Complete task description
- Sufficient context for reproduction
- Clear attempted approach with code examples
- Detailed unexpected behavior description
- Working resolution with exact function calls
- Actionable key learning
- Proper documentation references
- Appropriate tagging

**Quality Criteria**:
- **Reproducible**: Another agent could follow the steps
- **Actionable**: Clear solution provided
- **Contextual**: Sufficient background information
- **Referenced**: Links to relevant documentation
- **Categorized**: Proper tagging for discovery

### Promotion Criteria

An entry is ready for promotion if it:
- **Solves a real problem** encountered during development
- **Provides working code examples** that can be reused
- **Documents API quirks** or unexpected behavior
- **Contains insights** valuable for future agents
- **Includes proper references** to SDK and documentation
- **Follows template format** completely

### User Approval Workflow

**Pre-Commit Process**:
1. **Identify entries** marked "Reviewed for Promotion"
2. **Summarize learnings** for user review
3. **Request approval** for valuable entries
4. **If approved**: Proceed to promotion phase
5. **If rejected**: Mark entry as [REJECTED - YYYY-MM-DD] with reason

---

## Phase 3: Promotion Phase

> **L1 CRITICAL**: This phase ensures valuable learnings are preserved in permanent documentation. Without promotion, knowledge is lost.

### Identifying Target Documentation Files

**Resource-Specific Issues**:
- Target: `docs/knowledge/endor-data-model/[resource].md`
- Section: Troubleshooting
- Format: Standardized troubleshooting entry

**API Quirks**:
- Target: `docs/SPECIFICATION.md`
- Section: API Corrections
- Format: Quirk description with workaround

**Architectural Learnings**:
- Target: `docs/agents/[relevant-guide].md`
- Section: Based on learning type
- Format: Integration into existing content

**Testing Patterns**:
- Target: `tests/README.md` or test file comments
- Section: Testing guidance
- Format: Pattern documentation

### Integration Approach

**Troubleshooting Section Format**:
```markdown
### Issue: [Problem Description]

**Date Discovered**: YYYY-MM-DD
**Logbook Reference**: `workspace/logbook.md#YYYY-MM-DD-title`

**Symptoms**: [What you observe]

**Root Cause**: [Why it happens]

**Solution**: [How to fix]
```python
# Working code pattern
```

**Prevention**: [How to avoid in future]

---
```

**API Corrections Format**:
```markdown
### [API Endpoint] - [Issue Description]

**Date Discovered**: YYYY-MM-DD
**Logbook Reference**: `workspace/logbook.md#YYYY-MM-DD-title`

**Issue**: [What doesn't work as expected]

**Workaround**: [How to work around it]
```python
# Working code pattern
```

**Notes**: [Additional context]

---
```

### Timestamp and Attribution

**Required Elements**:
- **Date Discovered**: When issue was first encountered
- **Last Updated**: When solution was last verified
- **Logbook Reference**: Link to original entry
- **Attribution**: Reference to discovery context

### Vector Database Rebuild Trigger

After promoting learnings:
1. **Update documentation** with new content
2. **Rebuild vector database** to index new content
3. **Verify RAG queries** can find new information
4. **Mark logbook entry** as [PROMOTED - YYYY-MM-DD]

---

## Phase 4: Maintenance Phase

### Regular Review Cycles

**Weekly Review**:
- Check for new logbook entries
- Review entries marked for promotion
- Assess quality and completeness
- Request user approval for valuable entries

**Monthly Review**:
- Consolidate related learnings
- Update documentation with new insights
- Archive outdated information
- Rebuild vector database

### Staleness Detection

**Indicators of Stale Information**:
- **Outdated API references** (old endpoints, deprecated functions)
- **Superseded solutions** (better approaches discovered)
- **Resolved issues** (API bugs fixed, workarounds no longer needed)
- **Deprecated patterns** (new best practices available)

**Staleness Handling**:
- **Update timestamps** when information is verified
- **Mark as deprecated** when superseded
- **Archive old entries** when no longer relevant
- **Update vector database** with current information

### Consolidation Opportunities

**Related Learnings**:
- **Group similar issues** into comprehensive troubleshooting guides
- **Merge related API quirks** into unified documentation
- **Consolidate testing patterns** into best practices
- **Combine architectural insights** into design principles

**Consolidation Process**:
1. **Identify related entries** in logbook
2. **Create comprehensive documentation** covering all aspects
3. **Update individual entries** with references to consolidated docs
4. **Archive original entries** after consolidation
5. **Rebuild vector database** with consolidated content

### Archive Management

**Archive Criteria**:
- **Promoted entries** older than 6 months
- **Superseded solutions** with better alternatives
- **Resolved issues** no longer occurring
- **Deprecated patterns** replaced by new best practices

**Archive Process**:
1. **Move to archive** section in logbook
2. **Update references** in documentation
3. **Maintain traceability** with archive timestamps
4. **Preserve context** for historical reference

---

## Workflow Diagram

```
Encounter Issue/Learning
         ↓
Document in workspace/logbook.md (using template)
         ↓
Mark checkbox "Reviewed for Promotion"
         ↓
Pre-commit: Request user approval for promotion into specific locations
         ↓
If approved: AI reviews entry
         ↓
AI identifies relevant archive files
         ↓
AI integrates into:
- docs/endor-data-model/[resource].md (Troubleshooting)
- docs/agents/[relevant-guide].md (if architectural)
- docs/SPECIFICATION.md (if API quirk)
         ↓
Add timestamp and reference to original logbook entry
         ↓
Rebuild vector database with new content
         ↓
Mark logbook entry as [PROMOTED - YYYY-MM-DD]
```

---

## Success Metrics

### Capture Phase
- **Entry Completeness**: All required sections filled
- **Template Compliance**: Format matches template exactly
- **Context Sufficiency**: Enough information for reproduction
- **Tagging Accuracy**: Appropriate categorization

### Review Phase
- **Quality Assessment**: Entries meet promotion criteria
- **User Approval**: Valuable learnings identified
- **Completeness Check**: All required elements present
- **Value Evaluation**: Future agent benefit assessed

### Promotion Phase
- **Target Identification**: Correct documentation files selected
- **Integration Quality**: Learnings properly integrated
- **Timestamp Accuracy**: Discovery dates preserved
- **Traceability**: Logbook references maintained

### Maintenance Phase
- **Regular Reviews**: Consistent review cycles
- **Staleness Detection**: Outdated information identified
- **Consolidation**: Related learnings combined
- **Archive Management**: Proper information lifecycle

---

## Benefits

1. **Systematic Learning Capture**: No knowledge lost during development
2. **Quality Control**: User approval gate ensures value
3. **Traceability**: Link from docs back to original discovery
4. **Consistency**: Template ensures uniform format
5. **Scalability**: Protocol guides all future agents
6. **Efficiency**: Agents can query protocols for maintenance guidance
7. **Maintainability**: Clear processes for information lifecycle
8. **RAG Optimization**: Structured content for vector database indexing

---

*This protocol ensures that technical learnings are systematically captured, reviewed, and promoted into permanent documentation, creating a comprehensive knowledge base for all AI agents working with Endor Cockpit.*

# Troubleshooting Protocol

> **L1 (Essential - Always Required) - Issue resolution workflow**

## Overview

This protocol provides a systematic approach to resolving development issues while capturing learnings for future reference.

## Troubleshooting Workflow

### 1. Start Logbook Entry
- [ ] Create entry in `.workspace/logbook.md` using `_LOGBOOK_TEMPLATE.md`
- [ ] Document task being attempted
- [ ] Record context (resource types, files, terminal output)
- [ ] Note attempted approach with specific function calls

### 2. Research Phase
- [ ] Query holocron for related issues: `python -m holocron query "issue description"`
- [ ] Search existing documentation for similar problems
- [ ] Check `.workspace/logbook.md` for previous solutions
- [ ] Review API specification for expected behavior

### 3. Investigation Phase
- [ ] Read SDK code and API spec
- [ ] Check error logs and validation output
- [ ] Test with endorctl to verify API behavior
- [ ] User knowledge checkpoint (ask if they know something not captured)

### 4. Validation Phase
- [ ] Write ephemeral tests to validate theories
- [ ] Test different approaches systematically
- [ ] Document unexpected behavior vs expected
- [ ] Capture error messages and stack traces

### 5. Resolution Phase
- [ ] Implement working solution
- [ ] Document exact function signatures that work
- [ ] Test solution thoroughly
- [ ] Update logbook entry with resolution

### 6. Knowledge Promotion
- [ ] Mark logbook entry "Reviewed for Promotion"
- [ ] Follow [Knowledge Capture Workflow](../knowledge-capture-workflow.md)
- [ ] Update relevant documentation
- [ ] Sync knowledge base with `python -m holocron sync`

## Common Issue Patterns

### API Issues
- **403 Forbidden**: Check canonical naming vs UUIDs
- **404 Not Found**: Verify resource exists and namespace correct
- **400 Bad Request**: Check payload structure and required fields
- **Empty Results**: Verify response parsing (list.objects structure)

### Code Issues
- **Import Errors**: Check path setup and module structure
- **Validation Errors**: Review Pydantic model definitions
- **Schema Drift**: Check for new API fields not in models
- **Type Errors**: Verify Optional return types

### Environment Issues
- **Authentication**: Verify environment variables set
- **Network**: Check API endpoint accessibility
- **Permissions**: Confirm namespace access rights

## Logbook Entry Template

```markdown
## Task: [Clear description of what was being attempted]

**Context**: [Resource types, related files, RAG queries, terminal output]

**Attempted Approach**: [Specific function calls, API endpoints, commands]

**Unexpected Behavior**: [Expected vs actual behavior, error messages]

**Resolution**: [Working solution with exact function signatures]

**Key Learning**: [One-sentence summary of core insight]

**Relevant Documentation**: [SDK references, test files, API endpoints]

**Miscellaneous Notes**: [Additional context and follow-up items]

**Tags**: [resource_type, operation_type, context]

**Reviewed for Promotion**: [ ] (checkbox when ready)
```

## Success Criteria

- ✅ Issue resolved with working solution
- ✅ Logbook entry created with complete information
- ✅ Knowledge captured for future reference
- ✅ Documentation updated if applicable
- ✅ Knowledge base synced

## Related Protocols

- [Knowledge Capture Workflow](../knowledge-capture-workflow.md) - For promoting learnings
- [Development Protocol](development-protocol.md) - For implementing fixes
- [Code Commit Protocol](code-commit-protocol.md) - For committing solutions

---

*This protocol ensures systematic issue resolution while building institutional knowledge.*

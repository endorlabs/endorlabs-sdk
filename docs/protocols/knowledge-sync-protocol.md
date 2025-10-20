# Knowledge Sync Protocol

> **L2/L3 (Detailed - Context-Specific) - Systematic knowledge capture and promotion workflow**

## Overview

This protocol defines the systematic process for capturing, reviewing, and promoting agent discoveries into permanent documentation. It ensures valuable learnings are preserved and made available to future agents.

## Phase 1: Capture

### When to Capture
- **Debugging sessions** with unexpected behavior
- **API discoveries** not documented elsewhere
- **Workflow solutions** that could help future agents
- **Integration patterns** that work well
- **Error resolutions** with specific fixes

### Capture Format
Use the structured format in `_LOGBOOK_TEMPLATE.md`:

```markdown
## Entry: [YYYY-MM-DD HH:MM] - [Brief Description]

### Task
What was being attempted?

### Context
- Resource types involved
- Related files
- RAG query results
- Terminal output
- API responses

### Attempted Approach
- Specific function calls
- API endpoints used
- Commands executed
- Code changes made

### Unexpected Behavior
- Expected vs actual behavior
- Error messages
- Unexpected responses
- Performance issues

### Resolution
- Working solution
- Exact function signatures
- Correct API usage
- Final code changes

### Key Learning
One-sentence summary of the core insight discovered.

### Relevant Documentation
- SDK references
- Test files
- API endpoints
- Documentation sections

### Miscellaneous Notes
- Additional context
- Follow-up items
- Related discoveries
- Future considerations

### Tags
- Resource type (project, finding, policy, namespace)
- Operation type (create, read, update, delete, query)
- Context (debugging, implementation, testing, documentation)

### Reviewed for Promotion
- [ ] Ready for promotion to permanent documentation
- [ ] Contains valuable universal knowledge
- [ ] Solution is reusable
- [ ] Documentation is clear and complete
```

### Capture Guidelines
- **Log immediately** during debugging sessions
- **Include complete context** (files, commands, responses)
- **Document exact solutions** (function calls, API usage)
- **Tag appropriately** for future retrieval
- **Use structured format** for consistency

## Phase 2: Review

### Review Criteria
Entries are ready for promotion when they contain:

- [ ] **Valuable universal knowledge** that helps other agents
- [ ] **Reusable solutions** for common problems
- [ ] **Clear documentation** of the discovery process
- [ ] **No sensitive information** (credentials, internal details)
- [ ] **Complete context** for understanding the solution

### Review Process
1. **Weekly review** of new entries
2. **Identify promotion candidates** based on criteria
3. **Mark entries** as "Reviewed for Promotion"
4. **Document promotion rationale** in entry

### Review Checklist
- [ ] Entry contains valuable universal knowledge
- [ ] Solution is reusable by other agents
- [ ] Documentation is clear and complete
- [ ] No sensitive information included
- [ ] Tags are appropriate for retrieval
- [ ] Context is sufficient for understanding

## Phase 3: Promotion

### Promotion Targets
Identify the appropriate documentation location:

- **Resource-specific issues** → `docs/endor-data-model/[resource].md#troubleshooting`
- **API quirks** → `docs/SPECIFICATION.md#api-corrections`
- **Workflow patterns** → `docs/protocols/[relevant-protocol].md`
- **Architectural insights** → `docs/agents/[relevant-guide].md`
- **Testing patterns** → `tests/README.md` or test file comments

### Promotion Process
1. **Extract key learnings** from logbook entry
2. **Identify target documentation** file
3. **Add troubleshooting section** if not exists
4. **Include timestamp and logbook reference**
5. **Update cross-references** in related docs
6. **Mark entry as promoted** in logbook

### Promotion Format
```markdown
## Troubleshooting

### [Issue Description] - [Date]
**Source**: Logbook entry [YYYY-MM-DD]

**Problem**: [Brief description of the issue]

**Solution**: [Step-by-step resolution]

**Prevention**: [How to avoid this issue]

**Related**: [Links to relevant documentation]
```

## Phase 4: Maintenance

### Regular Tasks
- **Weekly**: Review new entries for promotion candidates
- **Monthly**: Archive promoted entries when superseded
- **Quarterly**: Clean up outdated entries

### Archive Process
1. **Move promoted entries** to archive directory
2. **Update logbook** with archive reference
3. **Clean up outdated entries** when superseded
4. **Maintain archive** for historical reference

### Archive Commands
```bash
# Archive promoted entries
mv .workspace/logbook.md .workspace/archive/logbook-$(date +%Y-%m).md

# Start fresh logbook
cp _LOGBOOK_TEMPLATE.md .workspace/logbook.md
```

## Integration with Holocron

### Knowledge Base Sync
After promoting entries to documentation:

1. **Update documentation** with new learnings
2. **Run knowledge sync**: `python -m holocron sync`
3. **Verify retrieval**: `python -m holocron query "new learning"`
4. **Test agent workflow** with updated knowledge

### Vector Database Updates
- **New content** is automatically indexed
- **Updated content** replaces old versions
- **Cross-references** are maintained
- **Search results** include new learnings

## Success Criteria

- ✅ All significant discoveries are captured
- ✅ Valuable learnings are promoted to documentation
- ✅ Knowledge base stays current with discoveries
- ✅ Future agents can find relevant solutions
- ✅ Documentation quality improves over time

## Related Protocols

- [Mandatory Context Protocol](mandatory-context.md) - L1
- [Operational Parameters Protocol](operational-parameters.md) - L2
- [Documentation Standards Protocol](documentation-standards.md) - L2

---

*This protocol ensures systematic capture and promotion of valuable agent discoveries into permanent documentation.*

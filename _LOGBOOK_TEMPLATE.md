# Logbook Template

Use this template for capturing technical learnings during SDK development, API debugging, or endorctl usage.

---

## Entry Template

### [YYYY-MM-DD HH:MM] - [Brief Title]

**Task**: [What were you trying to accomplish?]

**Context**: 
- Resource Type(s): [project, finding, policy, namespace, etc.]
- Related Files: [List SDK files, test files involved]
- RAG Query: [If applicable, what did you query?]
- Terminal Output: [Link to relevant log section or paste key output]

**Attempted Approach**:
[What did you try? Include specific function calls, API endpoints, commands]
```python
# Example code or commands attempted
```

**Unexpected Behavior**:
[What happened that was different from expected?]
- Expected: [What you thought would happen]
- Actual: [What actually happened]
- Error Messages: [Exact error messages if applicable]

**Resolution**:
[How was the issue resolved? Include exact SDK-native function calls]
```python
# Working solution with exact function signatures
from endor_cockpit.resources import resource_name
result = resource_name.function_name(client, params)
```

**Key Learning**:
[One-sentence summary of the core insight]

**Relevant Documentation**:
- SDK Reference: `src/endor_cockpit/resources/[file].py:[line-range]`
- Related Tests: `tests/test_[resource].py:[line-range]`
- API Endpoint: `[METHOD] /v1/endpoint`

**Miscellaneous Notes**:
[Any additional context, related issues, or follow-up items]

**Tags**: `[debugging, api-quirk, schema-drift, permissions, etc.]`

- [ ] **Reviewed for Promotion** (Check when ready for archive)

---

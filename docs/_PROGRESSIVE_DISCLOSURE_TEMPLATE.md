# Resource/Topic Name

## 🚨 Essential Context
[3-5 critical bullets, ~100 tokens]

**Purpose**: Must-know information for safe operation
**Format**: Bullet points with actionable guidance
**Example**:
- Projects have immutable UUIDs and repository URLs
- Use `update_mask` for partial updates: `["tags", "description"]`
- Full details: [Project Resource Documentation](#architecture)

## Quick Reference
[Common operations, ~500 tokens]

**Purpose**: Frequently used operations and patterns
**Format**: Code examples, common workflows, quick lookup
**Example**:
```python
# Create project
project = project.create_project(client, namespace, payload)

# Update project tags
payload = UpdateProjectPayload(tags=["new-tag"], update_mask=["tags"])
updated = project.update_project(client, namespace, project_uuid, payload)
```

## Detailed Guide
[Comprehensive information, ~2000 tokens]

**Purpose**: Complete understanding of the resource
**Format**: Full documentation, examples, edge cases
**Sections**:
- Architecture overview
- Data model details
- CRUD operations
- Error handling
- Best practices

## Advanced Topics
[Edge cases, optimization, ~1000 tokens]

**Purpose**: Expert-level information
**Format**: Complex scenarios, performance optimization, advanced patterns
**Sections**:
- Performance considerations
- Advanced error handling
- Integration patterns
- Optimization techniques

## Troubleshooting
[Common issues with solutions]

**Purpose**: Problem resolution
**Format**: Issue → Solution pairs
**Example**:
- **Issue**: "403 Forbidden when updating project"
- **Solution**: Check namespace permissions, verify canonical naming
- **Prevention**: Run `python scripts/validate_environment.py`

## Cross-References

**Related Resources**:
- [Related Resource 1](link)
- [Related Resource 2](link)

**Protocols**:
- [Relevant Protocol](link)

**Examples**:
- [Code Examples](link)

---

*This template ensures consistent progressive disclosure across all documentation. Essential Context should be process-oriented, not content-oriented.*

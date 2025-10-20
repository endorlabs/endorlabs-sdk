# Documentation Standards Protocol

> **L2 (Extracted from analysis docs) - Standards for maintaining documentation quality and consistency**

## Overview

This protocol defines the standards for creating, maintaining, and updating documentation to ensure consistency, quality, and effective agent operation.

## Documentation Structure

### Progressive Disclosure Template
**Template**: `docs/_PROGRESSIVE_DISCLOSURE_TEMPLATE.md`
**Structure**:
1. **Essential Context** (3-5 bullets, ~100 tokens)
2. **Quick Reference** (~500 tokens)
3. **Detailed Guide** (~2000 tokens)
4. **Advanced Topics** (~1000 tokens)
5. **Troubleshooting** (Common issues with solutions)

### Essential Context Standards
**Purpose**: Must-know information for safe operation
**Format**: Bullet points with actionable guidance
**Content**: Process-oriented, not content-oriented
**Example**:
- Projects have immutable UUIDs and repository URLs
- Use `update_mask` for partial updates: `["tags", "description"]`
- Full details: [Project Resource Documentation](#architecture)

## Content Standards

### Single Source of Truth
**Principle**: Each concept has exactly one detailed source
**Implementation**:
- Canonical source contains full information
- Other locations have essential bullets + link
- Cross-references point to canonical source
- No duplicate detailed content

### Query-First Workflow
**Principle**: Content retrieved on-demand, not pre-loaded
**Implementation**:
- Essential context focuses on process
- Detailed content retrieved via query
- Context window preserved for important content
- Token efficiency through on-demand retrieval

### RAG Optimization
**Principle**: Content structured for semantic search
**Implementation**:
- Clear section headers for chunking
- Consistent terminology across docs
- Cross-references for related content
- Metadata for better retrieval

## Maintenance Standards

### Update Workflow
1. **Identify need** for documentation update
2. **Query knowledge base** for existing content
3. **Update canonical source** with new information
4. **Update cross-references** if needed
5. **Sync knowledge base** with `python -m holocron sync`
6. **Validate changes** with agent workflow test

### Quality Assurance
**Before publishing**:
- [ ] Content follows progressive disclosure template
- [ ] Essential context is process-oriented
- [ ] Cross-references are accurate
- [ ] No duplicate detailed content
- [ ] Knowledge base synced

### Version Control
**File naming**: Use descriptive names
**Directory structure**: Follow established hierarchy
**Cross-references**: Use relative paths
**Backup**: Archive old versions in `.workspace/analysis/`

## Implementation

### For Content Creators
1. **Follow template** for new documentation
2. **Check canonical sources** before creating
3. **Update cross-references** when changing content
4. **Sync knowledge base** after changes

### For Agents
1. **Query first** for unknown concepts
2. **Check essential context** in relevant docs
3. **Follow canonical sources** for detailed info
4. **Log discoveries** in `.workspace/logbook.md`

## Success Criteria

- ✅ All docs follow progressive disclosure template
- ✅ Essential context is process-oriented
- ✅ Single source of truth maintained
- ✅ Cross-references are accurate
- ✅ Knowledge base is current

## Related Protocols

- [Mandatory Context Protocol](mandatory-context.md) - L1
- [Operational Parameters Protocol](operational-parameters.md) - L2
- [Knowledge Sync Protocol](knowledge-sync.md) - L2/L3

---

*This protocol ensures documentation quality and consistency through standardized structure and maintenance procedures.*

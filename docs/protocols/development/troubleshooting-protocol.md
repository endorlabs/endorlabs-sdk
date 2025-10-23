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
- [ ] Query holocron for related issues: `uv run python -m holocron query "issue description"`
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
- [ ] Sync knowledge base with `uv run python -m holocron sync`

## 🚨 **Critical Debugging Patterns**

### **1. PATCH Endpoint Debugging Journey**

#### **Problem**: PATCH operations failing with 501 "Method Not Allowed"
**Initial Error**: `requests.exceptions.HTTPError: 501 Server Error: Not Implemented`

**Debugging Steps**:
1. **Wrong URL Pattern**: Initially used `PATCH /v1/namespaces/{namespace}/projects/{uuid}`
2. **OpenAPI Spec Check**: Found correct pattern in `.workspace/downloads/openapi-swagger.json`
3. **Discovery**: PATCH endpoints expect UUID in request body, not URL path
4. **Solution**: Changed to `PATCH /v1/namespaces/{namespace}/projects` with UUID in body

**Key Learning**: Always check OpenAPI spec for actual endpoint patterns, not assumptions.

#### **Problem**: PATCH requiring full object structure
**Error**: `400 Bad Request - invalid Project.Meta.Name: value is required`

**Debugging Steps**:
1. **Full Object Required**: API complained about missing required fields
2. **OpenAPI Spec Re-examination**: Found `v1UpdateRequest` with `update_mask` field
3. **Discovery**: `update_mask` allows partial updates
4. **Solution**: Implemented `update_mask` for efficient partial updates

**Key Learning**: API specs contain critical fields like `update_mask` that enable efficient operations.

#### **Problem**: Tags not persisting despite 200 OK response
**Symptoms**: API returns success but tags don't appear in subsequent GET requests

**Debugging Steps**:
1. **Response Analysis**: API returned updated tags in response
2. **Persistence Check**: Re-fetching showed tags missing
3. **Pydantic Model Investigation**: Found missing `tags` field in `ProjectMeta`
4. **Root Cause**: Pydantic model didn't include `tags: Optional[List[str]] = None`
5. **Solution**: Added missing field to model

**Key Learning**: API responses can be correct but Pydantic models must include all fields for proper parsing.

### **2. Test Structure Restructuring Debugging**

#### **Problem**: Multiple redundant test files with overlapping functionality
**Symptoms**: 5+ test files with similar test cases, hard to maintain

**Debugging Steps**:
1. **Pattern Analysis**: Identified `test_<resource>.py` pattern from existing `test_namespace.py`
2. **Consolidation Strategy**: Group all operations per resource in single files
3. **Naming Convention**: Follow `endorctl` pattern with singular resource names
4. **Implementation**: Created `test_project.py`, `test_finding.py` with comprehensive coverage

**Key Learning**: Follow existing patterns and consolidate related functionality.

#### **Problem**: Test execution failures due to class name mismatches
**Error**: `NameError: name 'TestResourceGetOperations' is not defined`

**Debugging Steps**:
1. **Class Renaming**: Changed from `TestResourceGetOperations` to `TestResourceOperations`
2. **Main Execution Block**: Updated class references in `if __name__ == "__main__"`
3. **Method Updates**: Updated test method calls to match new class structure

**Key Learning**: Maintain consistency between class names and references throughout test files.

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

# Systematic Debugging Workflow

> **Step-by-step debugging approach for resolving implementation issues**

## 🚨 **Critical Debugging Patterns**

### **1. PATCH Endpoint Debugging Journey**

#### **Problem**: PATCH operations failing with 501 "Method Not Allowed"
**Initial Error**: `requests.exceptions.HTTPError: 501 Server Error: Not Implemented`

**Debugging Steps**:
1. **Wrong URL Pattern**: Initially used `PATCH /v1/namespaces/{namespace}/projects/{uuid}`
2. **OpenAPI Spec Check**: Found correct pattern in `tmp/openapiv2.swagger.json`
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

### **3. Finding Resource Debugging Journey**

#### **Problem**: SDK returning no findings while `endorctl` shows findings exist
**Symptoms**: `list_findings()` returning empty list, but `endorctl api list -r Finding` shows 100+ findings

**Debugging Steps**:
1. **Endpoint Verification**: Confirmed correct endpoint `/v1/namespaces/{namespace}/findings`
2. **Authentication Check**: Verified APIClient authentication working
3. **Response Parsing Analysis**: Found different response handling between projects and findings modules
4. **Pattern Comparison**: Projects used `client.get()` + `res.json()` + `data.get("list", {}).get("objects", [])`
5. **Findings Module**: Was using direct `client.get()` which returned `False` on auth errors
6. **Solution**: Updated findings module to use same pattern as projects

**Key Learning**: Resource modules handle authentication differently than direct API calls.

#### **Problem**: Complex Pydantic model validation failures
**Error**: Multiple validation errors due to API response complexity

**Debugging Steps**:
1. **Live Data Analysis**: Used `endorctl` output to understand actual API structure
2. **Field Mapping**: Mapped 30+ fields in `FindingSpec`, 15+ in `FindingMeta`
3. **Type Flexibility**: Added `Union[List[str], dict]` for fields that can be lists or empty objects
4. **Optional Fields**: Made most fields optional to handle API variations
5. **Schema Drift Detection**: Implemented comprehensive monitoring for unknown fields

**Key Learning**: Real API responses are much more complex than initial assumptions.

## 🔧 **Systematic Debugging Workflow**

### **Step 1: Information Gathering**
1. **Query RAG Knowledge Base**: Check for existing patterns and solutions
2. **Check OpenAPI Spec**: Look for service endpoints and request structures
3. **Use Live Data**: `endorctl` provides actual API response structure
4. **Review Existing Implementations**: Use working implementations as templates

### **Step 2: Systematic Testing**
1. **Start with GET Operations**: Understand structure before implementing
2. **Test with Minimal Data**: Start with single field updates
3. **Document All Errors**: Record all errors and responses
4. **Compare with Working Implementations**: Use established patterns

### **Step 3: Solution Implementation**
1. **Apply Discovered Patterns**: Use consistent patterns across all resources
2. **Test Thoroughly**: Test with real data and edge cases
3. **Document All Learnings**: Record all debugging steps and discoveries
4. **Update Knowledge Base**: Propagate learnings for future agents

## 🚨 **Red Flags to Watch For**

### **API Endpoint Issues**
- **501 Method Not Allowed**: Check endpoint URL pattern
- **400 Bad Request**: Check required fields and request structure
- **Empty Results**: Check response parsing pattern
- **Authentication Issues**: Use resource modules instead of direct calls

### **Pydantic Model Issues**
- **Missing Fields**: Compare with live API data
- **Type Mismatches**: Use `Union` types for flexible fields
- **Validation Errors**: Make fields optional for API variations

### **Test Structure Issues**
- **Redundant Files**: Consolidate by resource type
- **Naming Inconsistency**: Follow existing patterns
- **Class References**: Maintain consistency between names and references

## 📚 **Information Surfacing Techniques**

### **RAG Knowledge Base First**
```python
from endor_cockpit.rag import query_vector_db

# Always start with knowledge base
results = query_vector_db("How do I implement {Resource} resources?")
results = query_vector_db("What are the API endpoints for {resource}?")
results = query_vector_db("What are the common pitfalls for {resource} implementation?")
```

### **OpenAPI Spec Analysis**
```bash
# Search for service endpoints
grep -i "{Resource}Service" tmp/openapiv2.swagger.json
grep -A 20 -B 5 "{Resource}Service" tmp/openapiv2.swagger.json
```

### **Live Data Analysis**
```bash
# Use endorctl to understand actual data structure
endorctl api list -r Project
endorctl api list -r Finding
endorctl api list -r Policy
```

### **Collaborative Workspace**
```python
# Use workspace.py for experimentation
# Document all debugging steps and discoveries
# Test different approaches systematically
```

## 🎯 **Future Agent Guidance**

### **When Facing Similar Problems**:
1. **Start with RAG**: Query knowledge base for existing patterns
2. **Check OpenAPI Spec**: Look for service endpoints and request structures
3. **Use Live Data**: `endorctl` provides actual API response structure
4. **Follow Patterns**: Use existing working implementations as templates
5. **Document Everything**: Record all debugging steps and discoveries
6. **Update Knowledge Base**: Propagate learnings for future agents

### **Critical Discoveries Added**:
1. **Universal API Response Pattern**: `{"list": {"objects": [...]}}`
2. **PATCH Endpoint Patterns**: UUID in request body, not URL path
3. **Update Mask Implementation**: Enables efficient partial updates
4. **Resource Module Patterns**: Consistent authentication and response handling
5. **Schema Drift Detection**: Comprehensive monitoring for API evolution

### **Process Improvements Added**:
1. **Test Structure Standardization**: `test_<resource>.py` pattern
2. **Debugging Workflow**: Systematic approach to problem-solving
3. **Information Surfacing**: RAG → API Spec → endorctl → APIClient
4. **Collaborative Workspace**: Systematic experimentation and documentation

---

*This debugging workflow provides a systematic approach to resolving implementation issues and ensures consistent problem-solving across all AI agents.*

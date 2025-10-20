# Error Handling and Troubleshooting Patterns

> **Comprehensive error handling strategies and troubleshooting patterns for Endor Labs API integration**

## 🚨 **Critical Error Patterns**

### **1. API Endpoint Issues**

#### **501 Method Not Allowed**
**Error**: `requests.exceptions.HTTPError: 501 Server Error: Not Implemented`

**Root Cause**: Wrong URL pattern - UUID in URL path instead of request body

**Solution**:
```python
# WRONG: UUID in URL path
PATCH /v1/namespaces/{namespace}/projects/{uuid}

# CORRECT: UUID in request body
PATCH /v1/namespaces/{namespace}/projects
# Request body: {"object": {"uuid": "...", ...}}
```

#### **400 Bad Request - Missing Required Fields**
**Error**: `400 Bad Request - invalid Project.Meta.Name: value is required`

**Root Cause**: API requires full object structure for PATCH operations

**Solution**:
```python
# Use update_mask for partial updates
{
  "object": {"uuid": "...", "meta": {"tags": ["new-tag"]}},
  "request": {"update_mask": "meta.tags"}
}
```

#### **403 Forbidden - Permission Denied**
**Error**: `403 Forbidden - Permission denied`

**Root Cause**: Using UUIDs as parents instead of canonical naming

**Solution**:
```python
# WRONG: Use UUID as parent
parent_namespace.uuid  # "68f3b2956795a2693a0f5bec" - FAILS!

# CORRECT: Use canonical naming
canonical_parent = f"{tenant_namespace}.{parent_name}"
# Example: "endor-solutions-tgowan.cockpit.integration-test-parent"
```

### **2. Pydantic Model Issues**

#### **Missing Fields in Model**
**Error**: Tags not persisting despite 200 OK response

**Root Cause**: Pydantic model missing `tags` field

**Solution**:
```python
# Problem: Missing tags field
class ProjectMeta(BaseModel):
    name: str
    description: str
    # Missing: tags field!

# Solution: Add missing field
class ProjectMeta(BaseModel):
    name: str
    description: str
    tags: Optional[List[str]] = None  # Added this!
```

#### **Type Mismatches**
**Error**: `TypeError: Object of type FindingLevel is not JSON serializable`

**Root Cause**: Enum values not being serialized to strings

**Solution**:
```python
# Problem: Direct enum serialization
request_data["object"]["spec"] = {
    "level": finding.spec.level,  # Enum object
    "finding_tags": new_tags
}

# Solution: Convert enum to string
request_data["object"]["spec"] = {
    "level": str(finding.spec.level.value) if hasattr(finding.spec.level, 'value') else str(finding.spec.level),
    "finding_tags": new_tags
}
```

#### **Validation Errors**
**Error**: Multiple validation errors due to API response complexity

**Root Cause**: API responses more complex than initial assumptions

**Solution**:
```python
# Use flexible typing for API variations
class FindingSpec(BaseModel):
    finding_categories: Optional[List[str]] = None
    location_urls: Optional[Union[List[str], dict]] = None  # Can be list or empty object
    references: Optional[Union[List[dict], dict]] = None    # Can be list or empty object
```

### **3. Authentication Issues**

#### **SDK vs endorctl Discrepancy**
**Symptoms**: SDK returning no findings while `endorctl` shows 100+ findings

**Root Cause**: Different response handling patterns between projects and findings modules

**Solution**:
```python
# CORRECT: Use consistent pattern
headers = client.default_headers
res = client.get(f"v1/namespaces/{tenant_meta_namespace}/{resource}", headers=headers)
data = res.json()
objects = data.get("list", {}).get("objects", [])

# WRONG: Direct client.get() without headers
response = client.get(endpoint)  # May return False on auth errors
```

## 🔧 **Systematic Error Handling**

### **Comprehensive Error Handling Pattern**
```python
def safe_resource_operation(operation_func, *args, **kwargs):
    """Safely execute resource operations with proper error handling."""
    try:
        result = operation_func(*args, **kwargs)
        if result:
            print(f"✅ Operation successful")
            return result
        else:
            print("⚠️ Operation completed but returned no result")
            return None
    except ValidationError as e:
        print(f"❌ Validation error: {e}")
        print("💡 Check Pydantic model fields against live API data")
        return None
    except HTTPError as e:
        if e.response.status_code == 403:
            print(f"❌ Permission denied: {e}")
            print("💡 Check if you're using canonical naming instead of UUIDs")
        elif e.response.status_code == 404:
            print(f"❌ Resource not found: {e}")
            print("💡 Check endpoint URL and resource UUID")
        elif e.response.status_code == 400:
            print(f"❌ Bad request: {e}")
            print("💡 Check request payload format and required fields")
        elif e.response.status_code == 501:
            print(f"❌ Method not allowed: {e}")
            print("💡 Check endpoint URL pattern (UUID in body, not path)")
        else:
            print(f"❌ API error: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None
```

### **Resource-Specific Error Handling**
```python
def safe_namespace_operation(operation_func, *args, **kwargs):
    """Safely execute namespace operations with proper error handling."""
    try:
        result = operation_func(*args, **kwargs)
        if result:
            print(f"✅ Namespace operation successful")
            return result
        else:
            print("⚠️ Operation completed but returned no result")
            return None
    except ValidationError as e:
        print(f"❌ Validation error: {e}")
        return None
    except HTTPError as e:
        if e.response.status_code == 403:
            print(f"❌ Permission denied: {e}")
            print("💡 Check if you're using canonical naming instead of UUIDs")
        elif e.response.status_code == 404:
            print(f"❌ Resource not found: {e}")
        else:
            print(f"❌ API error: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None
```

## 🚨 **Red Flags and Solutions**

### **Common Error Codes**

#### **403 Forbidden**
- **Cause**: Permission denied, wrong namespace format
- **Solution**: Use canonical naming instead of UUIDs
- **Check**: `namespace = "endor-solutions-tgowan.cockpit"` (not UUID)

#### **404 Not Found**
- **Cause**: Resource not found, wrong endpoint
- **Solution**: Check endpoint URL and resource UUID
- **Check**: Verify resource exists and UUID is correct

#### **400 Bad Request**
- **Cause**: Invalid payload format, missing required fields
- **Solution**: Check request payload format and required fields
- **Check**: Use `update_mask` for partial updates

#### **501 Method Not Allowed**
- **Cause**: Wrong endpoint URL pattern
- **Solution**: Check endpoint URL pattern (UUID in body, not path)
- **Check**: Use correct PATCH endpoint format

#### **429 Too Many Requests**
- **Cause**: Rate limited
- **Solution**: Implement retry logic with exponential backoff
- **Check**: Add delays between requests

### **Authentication Issues**
- **Use resource modules**: Instead of direct API calls
- **Check headers**: Ensure proper authentication headers
- **Verify credentials**: Check environment variables

### **Response Parsing Issues**
- **Use universal pattern**: `data.get("list", {}).get("objects", [])`
- **Check response structure**: Verify API response format
- **Handle empty responses**: Check for empty lists vs None

## 🔧 **Debugging Workflow**

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

## 📚 **Information Surfacing Techniques**

### **RAG Knowledge Base First**
```python
from endor_cockpit.rag import query_vector_db

# Always start with knowledge base
results = query_vector_db("How do I handle 403 Forbidden errors?")
results = query_vector_db("What are the common pitfalls for {resource} implementation?")
results = query_vector_db("How do I debug PATCH endpoint issues?")
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

*This error handling guide provides comprehensive strategies for resolving implementation issues and ensures consistent problem-solving across all AI agents.*

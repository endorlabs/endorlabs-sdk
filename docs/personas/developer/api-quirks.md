# API Quirks & Workarounds

> **Known API discrepancies and practical workarounds**

## 🚨 **Critical API Quirks**

### **Namespace Operations: Canonical Naming Requirement**

#### **The Problem**
OpenAPI spec suggests using UUIDs for parent namespaces, but the actual API requires canonical naming.

#### **OpenAPI Spec Says**
```json
{
  "paths": {
    "/namespaces": {
      "post": {
        "parameters": [
          {
            "name": "parent_namespace",
            "in": "query",
            "type": "string",
            "description": "Parent namespace identifier"
          }
        ]
      }
    }
  }
}
```

#### **Actual API Behavior**
- **Parameter**: `parent_namespace` (query parameter)
- **Format**: Must use canonical hierarchical naming (`tenant.namespace.child`)
- **NOT UUIDs**: Using namespace UUIDs as parent returns `403 Forbidden`

#### **Workaround**
```python
# ❌ WRONG - Will fail with 403 Forbidden
child_namespace = namespaces.create_namespace(client, parent_namespace.uuid, payload)

# ✅ CORRECT - Use canonical naming
canonical_parent = f"{tenant_namespace}.{parent_name}"
child_namespace = namespaces.create_namespace(client, canonical_parent, payload)
```

#### **Error Response**
```json
{
  "code": 7,
  "message": "Unauthorized request for given endpoint",
  "details": [
    {
      "@type": "type.googleapis.com/internal.endor.ai.rpc.v1.HTTPErrorInfo",
      "status_code": 403,
      "redirect_url": ""
    }
  ]
}
```

---

### **Namespace Retrieval: Missing Parent Parameter**

#### **The Problem**
OpenAPI spec doesn't document the required `parent_namespace` parameter for GET operations.

#### **OpenAPI Spec Says**
```json
{
  "paths": {
    "/namespaces/{uuid}": {
      "get": {
        "parameters": [
          {
            "name": "uuid",
            "in": "path",
            "required": true,
            "type": "string"
          }
        ]
      }
    }
  }
}
```

#### **Actual API Behavior**
- **Missing Parameter**: `parent_namespace` query parameter is required
- **Format**: Must be canonical name (not UUID)
- **Purpose**: Permission validation - API key must have access to parent namespace

#### **Workaround**
```python
# ❌ WRONG - Will fail with 403 Forbidden
namespace = namespaces.get_namespace(client, namespace_uuid)

# ✅ CORRECT - Include parent_namespace parameter
namespace = namespaces.get_namespace(client, parent_namespace, namespace_uuid)
```

---

### **Namespace Updates: Missing Update Operations**

#### **The Problem**
OpenAPI spec doesn't document PUT operations for namespace updates.

#### **OpenAPI Spec Says**
- No PUT/PATCH endpoints for namespace updates
- No update payload schemas defined

#### **Actual API Behavior**
- **PUT `/namespaces/{uuid}`**: Available but not documented
- **Required Parameters**: `parent_namespace` (canonical name), `uuid`
- **Payload**: `UpdateNamespacePayload` with `NamespaceMetaUpdate`

#### **Workaround**
```python
# These classes were missing from initial SDK
class NamespaceMetaUpdate(BaseModel):
    description: Optional[str] = Field(None)

class UpdateNamespacePayload(BaseModel):
    meta: NamespaceMetaUpdate

# Usage
payload = UpdateNamespacePayload(
    meta=NamespaceMetaUpdate(description="Updated description")
)
namespace = namespaces.update_namespace(client, parent_namespace, namespace_uuid, payload)
```

---

### **Namespace Descriptions: Empty Values Allowed**

#### **The Problem**
OpenAPI spec requires non-empty descriptions, but API returns empty descriptions.

#### **OpenAPI Spec Says**
```json
{
  "NamespaceMeta": {
    "description": {
      "type": "string",
      "minLength": 1
    }
  }
}
```

#### **Actual API Behavior**
- **Empty descriptions**: API returns namespaces with empty descriptions
- **Validation**: Input validation allows empty strings
- **SDK Fix**: Use `Field("")` instead of `Field(..., min_length=1)`

#### **Workaround**
```python
# ❌ WRONG - Will fail with validation error
class NamespaceMeta(BaseModel):
    description: str = Field(..., min_length=1)  # Empty descriptions not allowed

# ✅ CORRECT - Allow empty descriptions
class NamespaceMeta(BaseModel):
    description: str = Field("")  # Empty descriptions allowed
```

---

## 🔧 **Permission Model Quirks**

### **API Key Permission Scope**

#### **The Problem**
OpenAPI spec doesn't document the permission model.

#### **OpenAPI Spec Says**
- Generic "authentication required" for all endpoints
- No permission model documentation

#### **Actual API Behavior**
- **Tenant-level permissions**: API key scoped to tenant namespace
- **Hierarchical permissions**: Can create children within allowed scope
- **Cross-tenant forbidden**: Cannot access other tenants' resources
- **UUID-based operations forbidden**: Must use canonical naming for parent relationships

#### **Workaround**
```python
def check_permissions(client: APIClient, operation: str, target: str) -> bool:
    """Check if operation is allowed on target."""
    try:
        # Test operation with minimal payload
        if operation == "create_namespace":
            test_payload = CreateNamespacePayload(
                meta=NamespaceMeta(name="test", description="")
            )
            result = namespaces.create_namespace(client, target, test_payload)
            return result is not None
        return False
    except HTTPError as e:
        if e.response.status_code == 403:
            return False
        raise
```

---

## 📊 **Response Format Quirks**

### **API Response Structure Pattern**
**Problem**: API returns `{"list": {"objects": [...]}}` structure, not direct arrays
**Root Cause**: Service-based API organization
**Solution**: Parse response correctly
```python
# WRONG: data = res.json().get("projects", [])
# CORRECT: data = res.json().get("list", {}).get("objects", [])
```

### **Path Parameter Requirements**
**Problem**: Must use `tenant_meta.namespace` (canonical) not `namespace_uuid`
**Root Cause**: API requires canonical namespace format
**Solution**: Use canonical namespace format
```python
# WRONG: f"v1/namespaces/{namespace_uuid}/projects"
# CORRECT: f"v1/namespaces/{tenant_meta_namespace}/projects"
```

### **Namespace List Response**

#### **The Problem**
OpenAPI spec doesn't include all response fields.

#### **OpenAPI Spec Says**
```json
{
  "namespaces": [
    {
      "uuid": "string",
      "meta": {
        "name": "string",
        "description": "string"
      }
    }
  ]
}
```

#### **Actual API Behavior**
```json
{
  "namespaces": [
    {
      "uuid": "68f3b2956795a2693a0f5bec",
      "meta": {
        "name": "namespace-name",
        "description": "",  // Can be empty
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
      }
    }
  ]
}
```

#### **Workaround**
```python
class NamespaceMeta(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field("")  # Empty descriptions allowed
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
```

---

## 🎯 **Common Error Patterns**

### **403 Forbidden Errors**

#### **Causes**
- Using UUIDs as parent namespaces
- Accessing resources outside permission scope
- Cross-tenant resource access
- Invalid canonical naming format

#### **Solutions**
```python
def handle_403_error(operation: str, target: str) -> str:
    """Provide actionable error messages for 403 errors."""
    if "parent_namespace" in operation:
        return f"Use canonical naming for parent_namespace: '{target}' -> 'tenant.namespace'"
    elif "cross-tenant" in operation:
        return f"Cross-tenant access forbidden: '{target}'"
    else:
        return f"Permission denied for operation: '{operation}' on '{target}'"
```

### **Validation Errors**

#### **Causes**
- Empty required fields
- Invalid field formats
- Missing required parameters

#### **Solutions**
```python
def validate_namespace_payload(payload: dict) -> dict:
    """Validate and fix common namespace payload issues."""
    if "meta" not in payload:
        payload["meta"] = {}
    
    if "description" not in payload["meta"]:
        payload["meta"]["description"] = ""
    
    return payload
```

---

## 🔍 **Testing Quirks**

### **Integration Test Patterns**

#### **Successful Hierarchy Testing**
```python
def test_namespace_hierarchy(api_client, tenant_namespace):
    """Test namespace hierarchy operations."""
    parent_name = f"integration-test-parent-{int(time.time())}"
    
    # Create parent namespace
    parent_namespace = create_test_namespace(
        api_client, tenant_namespace, parent_name, "Parent namespace"
    )
    
    # Create canonical parent name
    canonical_parent = f"{tenant_namespace}.{parent_name}"
    
    # Create child namespace using canonical parent
    child_namespace = create_test_namespace(
        api_client, canonical_parent, child_name, "Child namespace"
    )
    
    # List namespaces under canonical parent
    child_namespaces = namespaces.list_namespaces(api_client, canonical_parent)
    assert len(child_namespaces) > 0
```

#### **Permission Testing Pattern**
```python
def test_permissions(api_client, tenant_namespace):
    """Test what operations are allowed."""
    # Test tenant-level operations
    result = namespaces.create_namespace(api_client, tenant_namespace, payload)
    assert result is not None  # Should work
    
    # Test hierarchy operations
    canonical_parent = f"{tenant_namespace}.{parent_name}"
    result = namespaces.create_namespace(api_client, canonical_parent, payload)
    assert result is not None  # Should work if permissions allow
```

---

## 🎯 **Best Practices for Handling Quirks**

### **1. Always Use Canonical Naming**
- Use `tenant.namespace.child` format for hierarchy operations
- Never use UUIDs as parent namespaces
- Build canonical names dynamically: `f"{tenant}.{parent}.{child}"`

### **2. Handle Empty Descriptions**
- API may return namespaces with empty descriptions
- Use `Field("")` instead of `Field(..., min_length=1)` for descriptions
- Validate input but allow empty output

### **3. Test Permission Scope**
- Always test what operations are allowed
- Use permission checkers to validate scope
- Handle 403 errors gracefully

### **4. Use Integration Tests**
- Test with real API endpoints
- Validate against live backend
- Clean up test objects automatically

---

## 📚 **Related Documentation**

- **[Architecture Guide](./architecture.md)**: Endor Data Model deep-dive
- **[Testing Guide](./testing-guide.md)**: Testing patterns for quirks
- **[Contributing Guide](./contributing.md)**: How to document new quirks

---

*This document should be updated whenever new API quirks are discovered during development or testing.*

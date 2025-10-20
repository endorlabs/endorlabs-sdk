# Endor Labs API Specification Corrections

> **Ground Truth API Behavior vs OpenAPI Spec Discrepancies**

## 🎯 **Purpose**

This document captures known discrepancies between the OpenAPI specification (`tmp/openapiv2.swagger.json`) and actual Endor Labs API behavior. These corrections ensure agents work with the real API, not the machine-generated spec.

## 📋 **Critical API Corrections**

### **Namespace Operations: Canonical Naming Requirement**

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
- **Example**: `"endor-solutions-tgowan.cockpit.integration-test-parent"`

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

### **Namespace Retrieval: Parent Namespace Parameter**

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

#### **Correct Usage**
```python
# GET /namespaces/{uuid}?parent_namespace={canonical_name}
def get_namespace(client: APIClient, parent_namespace: str, namespace_uuid: str) -> Optional[Namespace]
```

### **Namespace Updates: Missing Update Operations**

#### **OpenAPI Spec Says**
- No PUT/PATCH endpoints for namespace updates
- No update payload schemas defined

#### **Actual API Behavior**
- **PUT `/namespaces/{uuid}`**: Available but not documented
- **Required Parameters**: `parent_namespace` (canonical name), `uuid`
- **Payload**: `UpdateNamespacePayload` with `NamespaceMetaUpdate`

#### **Missing SDK Classes**
```python
# These classes were missing from initial SDK
class NamespaceMetaUpdate(BaseModel):
    description: Optional[str] = Field(None)

class UpdateNamespacePayload(BaseModel):
    meta: NamespaceMetaUpdate
```

### **Namespace Descriptions: Empty Values Allowed**

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

#### **Correct Pydantic Model**
```python
class NamespaceMeta(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field("")  # Empty descriptions allowed
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
```

## 🔧 **Permission Model Corrections**

### **API Key Permission Scope**

#### **OpenAPI Spec Says**
- Generic "authentication required" for all endpoints
- No permission model documentation

#### **Actual API Behavior**
- **Tenant-level permissions**: API key scoped to tenant namespace
- **Hierarchical permissions**: Can create children within allowed scope
- **Cross-tenant forbidden**: Cannot access other tenants' resources
- **UUID-based operations forbidden**: Must use canonical naming for parent relationships

### **Error Code Mapping**

#### **Common Error Codes**
```json
{
  "7": "Unauthorized request for given endpoint (403 Forbidden)",
  "12": "Method Not Allowed (501 Not Implemented)",
  "3": "Invalid argument (400 Bad Request)"
}
```

#### **Permission Denied Scenarios**
- Using UUIDs as parent namespaces
- Accessing resources outside permission scope
- Cross-tenant resource access
- Invalid canonical naming format

## 📊 **Response Format Corrections**

### **Namespace List Response**

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

### **Error Response Format**

#### **Standard Error Structure**
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

## 🎯 **SDK Implementation Corrections**

### **Required Function Signatures**

#### **Namespace Operations**
```python
# All namespace operations require parent_namespace parameter
def list_namespaces(client: APIClient, parent_namespace: str) -> List[Namespace]
def get_namespace(client: APIClient, parent_namespace: str, namespace_uuid: str) -> Optional[Namespace]
def create_namespace(client: APIClient, parent_namespace: str, payload: CreateNamespacePayload) -> Optional[Namespace]
def update_namespace(client: APIClient, parent_namespace: str, namespace_uuid: str, payload: UpdateNamespacePayload) -> Optional[Namespace]
def delete_namespace(client: APIClient, parent_namespace: str, namespace_uuid: str) -> bool
```

#### **Canonical Naming Helper**
```python
def build_canonical_name(tenant_namespace: str, *path_components: str) -> str:
    """Build canonical namespace name from components."""
    return ".".join([tenant_namespace] + list(path_components))

# Usage
canonical_parent = build_canonical_name("endor-solutions-tgowan.cockpit", "parent", "child")
```

## 🔍 **Testing Corrections**

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

## 📚 **Reference Links**

- **OpenAPI Spec**: `tmp/openapiv2.swagger.json` (92K lines)
- **SDK Implementation**: `src/endor_cockpit/resources/namespaces.py`
- **Integration Tests**: `tests/test_integration.py`
- **Agent Insights**: `docs/agents/insights.md`

## 🎯 **Last Updated**

- **2025-10-18**: Initial specification corrections documented
- **Source**: Integration testing and API exploration
- **Validation**: Confirmed against live Endor Labs API

---

*This document should be updated whenever new API discrepancies are discovered during development or testing.*

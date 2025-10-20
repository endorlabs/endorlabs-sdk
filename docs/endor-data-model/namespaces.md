# Namespace Resource Deep-Dive

> **Comprehensive guide to namespace resources in Endor Labs platform**

## 🏗️ **Namespace Architecture**

### **Hierarchical Structure**
Namespaces in Endor Labs follow a hierarchical structure with canonical naming:

```
Tenant (endor-solutions-tgowan.cockpit)
├── Namespace (tenant.namespace)
│   ├── Child Namespace (tenant.namespace.child)
│   │   └── Grandchild (tenant.namespace.child.grandchild)
│   └── Sibling Namespace (tenant.namespace.sibling)
└── Other Namespace (tenant.other-namespace)
```

### **Canonical Naming System**
**CRITICAL**: Endor Labs uses canonical hierarchical naming, not UUIDs.

#### **Naming Convention**
```
{tenant}.{namespace}.{child}.{grandchild}
```

#### **Examples**
```
endor-solutions-tgowan.cockpit                    # Tenant
endor-solutions-tgowan.cockpit.integration-test  # Namespace
endor-solutions-tgowan.cockpit.integration-test.child  # Child namespace
```

---

## 📊 **Namespace Data Model**

### **Core Properties**
```python
class Namespace(BaseModel):
    uuid: str                    # Unique identifier
    meta: NamespaceMeta         # Metadata
    created_at: datetime        # Creation timestamp
    updated_at: datetime        # Last update timestamp
```

### **Metadata Structure**
```python
class NamespaceMeta(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field("")  # Empty descriptions allowed
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
```

### **Creation Payload**
```python
class NamespaceMetaCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field("")

class CreateNamespacePayload(BaseModel):
    meta: NamespaceMetaCreate
```

### **Update Payload**
```python
class NamespaceMetaUpdate(BaseModel):
    description: Optional[str] = Field(None)

class UpdateNamespacePayload(BaseModel):
    meta: NamespaceMetaUpdate
```

---

## 🔧 **Namespace Operations**

### **List Namespaces**
```python
def list_namespaces(client: APIClient, parent_namespace: str) -> List[Namespace]:
    """List all namespaces in a parent namespace."""
    # Implementation details
```

### **Get Namespace**
```python
def get_namespace(
    client: APIClient, 
    parent_namespace: str, 
    namespace_uuid: str
) -> Optional[Namespace]:
    """Get a specific namespace by UUID."""
    # Implementation details
```

### **Create Namespace**
```python
def create_namespace(
    client: APIClient, 
    parent_namespace: str, 
    payload: CreateNamespacePayload
) -> Optional[Namespace]:
    """Create a new namespace within parent namespace."""
    # Implementation details
```

### **Update Namespace**
```python
def update_namespace(
    client: APIClient, 
    parent_namespace: str, 
    namespace_uuid: str, 
    payload: UpdateNamespacePayload
) -> Optional[Namespace]:
    """Update an existing namespace."""
    # Implementation details
```

### **Delete Namespace**
```python
def delete_namespace(
    client: APIClient, 
    parent_namespace: str, 
    namespace_uuid: str
) -> bool:
    """Delete a namespace."""
    # Implementation details
```

---

## 🔐 **Permission Model**

### **Access Control**
- **Tenant-level permissions**: API key scoped to tenant namespace
- **Hierarchical permissions**: Can create children within allowed scope
- **Cross-tenant forbidden**: Cannot access other tenants' resources
- **UUID-based operations forbidden**: Must use canonical naming for parent relationships

### **Permission Scopes**
```python
# Tenant-level operations
tenant_namespace = "endor-solutions-tgowan.cockpit"
namespaces.list_namespaces(client, tenant_namespace)

# Hierarchy operations
canonical_parent = f"{tenant_namespace}.{parent_name}"
namespaces.create_namespace(client, canonical_parent, payload)
```

---

## 🚨 **Common Issues**

### **403 Forbidden Errors**
**Cause**: Using UUIDs as parent namespaces
**Solution**: Use canonical naming format

```python
# ❌ WRONG - Will fail with 403 Forbidden
child_namespace = namespaces.create_namespace(client, parent_namespace.uuid, payload)

# ✅ CORRECT - Use canonical naming
canonical_parent = f"{tenant_namespace}.{parent_name}"
child_namespace = namespaces.create_namespace(client, canonical_parent, payload)
```

### **Missing Parent Parameter**
**Cause**: OpenAPI spec doesn't document required `parent_namespace` parameter
**Solution**: Always include parent_namespace parameter

```python
# ❌ WRONG - Will fail with 403 Forbidden
namespace = namespaces.get_namespace(client, namespace_uuid)

# ✅ CORRECT - Include parent_namespace parameter
namespace = namespaces.get_namespace(client, parent_namespace, namespace_uuid)
```

### **Empty Descriptions**
**Cause**: API returns namespaces with empty descriptions
**Solution**: Use `Field("")` instead of `Field(..., min_length=1)`

```python
# ❌ WRONG - Will fail with validation error
class NamespaceMeta(BaseModel):
    description: str = Field(..., min_length=1)  # Empty descriptions not allowed

# ✅ CORRECT - Allow empty descriptions
class NamespaceMeta(BaseModel):
    description: str = Field("")  # Empty descriptions allowed
```

---

## 🧪 **Testing Patterns**

### **Hierarchy Testing**
```python
def test_namespace_hierarchy(api_client, tenant_namespace):
    """Test namespace hierarchy operations."""
    parent_name = f"integration-test-parent-{int(time.time())}"
    
    # Create parent namespace
    parent_namespace = create_test_namespace(
        api_client, tenant_namespace, parent_name, "Parent namespace"
    )
    assert parent_namespace is not None
    
    # Create canonical parent name
    canonical_parent = f"{tenant_namespace}.{parent_name}"
    
    # Create child namespace using canonical parent
    child_name = f"integration-test-child-{int(time.time())}"
    child_namespace = create_test_namespace(
        api_client, canonical_parent, child_name, "Child namespace"
    )
    assert child_namespace is not None
    
    # List namespaces under canonical parent
    child_namespaces = namespaces.list_namespaces(api_client, canonical_parent)
    assert len(child_namespaces) > 0
```

### **Permission Testing**
```python
def test_permissions(api_client, tenant_namespace):
    """Test what operations are allowed."""
    # Test tenant-level operations
    test_payload = CreateNamespacePayload(
        meta=NamespaceMeta(name="test", description="Test")
    )
    result = namespaces.create_namespace(api_client, tenant_namespace, test_payload)
    assert result is not None  # Should work
    
    # Test hierarchy operations
    canonical_parent = f"{tenant_namespace}.test-parent"
    result = namespaces.create_namespace(api_client, canonical_parent, test_payload)
    assert result is not None  # Should work if permissions allow
```

---

## 📚 **Related Resources**

- **[API Corrections](../api-corrections/namespace-api.md)** - Known API issues
- **[Examples](../examples/create-namespace-hierarchy.md)** - Step-by-step examples
- **[Relationships](./relationships.md)** - Namespace relationships

---

## Troubleshooting

### Issue: Namespace Creation with Invalid Parent

**Date Discovered**: 2025-10-19

**Symptoms**: 
- Namespace creation fails with 403 Forbidden
- "Parent namespace not found" error
- Cross-tenant namespace creation fails

**Root Cause**: 
- Using UUID instead of canonical name for parent
- Attempting cross-tenant operations
- Invalid parent namespace format

**Solution**: 
```python
# ❌ INCORRECT - Using UUID as parent
parent_namespace = "68f3b2956795a2693a0f5bec"

# ✅ CORRECT - Using canonical name
parent_namespace = "endor-solutions-tgowan.cockpit.integration-test"

# Create child namespace
child_result = create_namespace(
    client, 
    parent_namespace, 
    child_payload
)
```

**Prevention**: Always use canonical names for parent-child relationships.

---

### Issue: Namespace Hierarchy Depth Limits

**Date Discovered**: 2025-10-19

**Symptoms**: 
- Deep namespace creation fails
- "Maximum depth exceeded" error
- Cannot create nested namespaces beyond certain level

**Root Cause**: 
- API enforces maximum hierarchy depth
- Too many nested levels in namespace structure
- Platform limits on namespace nesting

**Solution**: 
```python
# ❌ INCORRECT - Too deep nesting
deep_namespace = "tenant.ns.level1.level2.level3.level4.level5"

# ✅ CORRECT - Flatten hierarchy
flat_namespace = "tenant.ns.level1-level2-level3"
```

**Prevention**: Design flat namespace structures within depth limits.

---

### Issue: Namespace Permission Errors

**Date Discovered**: 2025-10-19

**Symptoms**: 
- 403 Forbidden on namespace operations
- Cannot access child namespaces
- Permission denied for namespace updates

**Root Cause**: 
- Insufficient permissions for namespace operations
- Cross-tenant access attempts
- Missing namespace access rights

**Solution**: 
```python
# ✅ CORRECT - Check permissions before operations
def check_namespace_access(client, namespace_name):
    try:
        namespace = get_namespace(client, namespace_name)
        return True
    except PermissionError:
        logger.error(f"Access denied to namespace: {namespace_name}")
        return False
    except Exception as e:
        logger.error(f"Error checking namespace access: {e}")
        return False
```

**Prevention**: Always verify namespace access before operations.

---

*This resource guide provides comprehensive information about namespace resources in the Endor Labs platform.*

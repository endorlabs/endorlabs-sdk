# API Patterns and Best Practices

> **Critical API patterns and implementation strategies for Endor Labs resources**

## ⚠️ **API Operations Support Matrix**

> **CRITICAL**: Not all resources support all HTTP methods. Always check the Resource Guide before implementing operations.

| Resource | GET | POST | PATCH | DELETE | Notes |
|----------|-----|------|-------|--------|-------|
| **Project** | ✅ | ✅ | ✅ | ✅ | Full CRUD support |
| **Policy** | ✅ | ✅ | ✅ | ❌ | No DELETE support |
| **Namespace** | ✅ | ✅ | ✅ | ❌ | No DELETE support |
| **Finding** | ✅ | ❌ | ✅ | ❌ | Read-only creation, supports updates |
| **PackageVersion** | ✅ | ❌ | ❌ | ❌ | Read-only resource |
| **Repository** | ✅ | ❌ | ❌ | ❌ | Read-only resource |
| **RepositoryVersion** | ✅ | ❌ | ❌ | ❌ | Read-only resource |

### **Implementation Guidelines**
- **Always check Resource Guide** before implementing operations
- **Skip unsupported operations** in tests (use `pytest.skip()`)
- **Validate API capabilities** before writing tests
- **Use Resource Guide as authoritative source** for operation support

## 🎯 **Universal API Response Pattern**

### **Standard Response Structure**
All Endor Labs resources follow the same API response pattern:

```python
# Universal pattern for all resources
headers = client.default_headers
res = client.get(f"v1/namespaces/{tenant_meta_namespace}/{resource}", headers=headers)
data = res.json()
objects = data.get("list", {}).get("objects", [])
```

### **Response Structure**
```json
{
  "list": {
    "objects": [
      {
        "meta": {...},
        "spec": {...},
        "tenant_meta": {"namespace": "endor-solutions-tgowan.cockpit"},
        "uuid": "..."
      }
    ]
  }
}
```

**NOT**: Direct array `[...]` or other structures.

## 🔧 **PATCH Endpoint Patterns**

### **Critical PATCH Implementation**
PATCH endpoints expect UUID in request body, not URL path:

```python
# WRONG: UUID in URL path
PATCH /v1/namespaces/{namespace}/projects/{uuid}

# CORRECT: UUID in request body
PATCH /v1/namespaces/{namespace}/projects
# Request body: {"object": {"uuid": "...", ...}}
```

### **Update Mask Implementation**
Use `update_mask` for efficient partial updates:

```python
{
  "object": {"uuid": "...", "meta": {"tags": ["new-tag"]}},
  "request": {"update_mask": "meta.tags"}
}
```

## 🏗️ **Resource Module Patterns**

### **Consistent Authentication and Response Handling**
```python
def list_{resource}s(client: APIClient, tenant_meta_namespace: str) -> List[{Resource}]:
    """List all {resource}s in the specified namespace."""
    try:
        headers = client.default_headers
        res = client.get(f"v1/namespaces/{tenant_meta_namespace}/{resource}s", headers=headers)
        data = res.json()
        objects = data.get("list", {}).get("objects", [])
        return [{Resource}(**item) for item in objects]
    except Exception as e:
        logger.error(f"Error listing {resource}s: {e}", exc_info=True)
        return []
```

### **Resource Module vs Direct API Calls**
```python
# CORRECT: Use resource modules
projects = list_projects(client, namespace)  # Handles auth correctly

# MAY FAIL: Direct API calls
response = client.get(endpoint)  # May return False on auth errors
```

## 🔍 **Schema Drift Detection Patterns**

### **Proactive Schema Monitoring**
```python
class {Resource}(BaseModel):
    meta: {Resource}Meta
    spec: {Resource}Spec
    tenant_meta: TenantMeta
    uuid: str
    
    @field_validator('*', mode='before')
    @classmethod
    def detect_schema_drift(cls, v, info):
        """Detect and log schema drift for unknown fields."""
        if info.field_name and isinstance(v, dict):
            model_fields = {
                'meta': {'create_time', 'update_time', 'name', 'description', ...},
                'spec': {'project_uuid', 'level', 'method', 'ecosystem', ...}
            }
            
            if info.field_name in model_fields:
                SchemaDriftDetector.extract_unknown_fields(
                    v, model_fields[info.field_name], f"{Resource}.{info.field_name}"
                )
        return v
```

### **Flexible Enum Implementation**
```python
class FlexibleEnum(str, Enum):
    """Base class for flexible enums that can handle unknown values."""
    
    @classmethod
    def _missing_(cls, value):
        """Handle unknown enum values gracefully."""
        logger.warning(f"Unknown {cls.__name__} value: {value}. Adding as dynamic enum.")
        obj = str.__new__(cls, value)
        obj._name_ = value
        obj._value_ = value
        return obj

class FindingLevel(FlexibleEnum):
    CRITICAL = "FINDING_LEVEL_CRITICAL"
    HIGH = "FINDING_LEVEL_HIGH"
    # Handles unknown values gracefully
```

## 📊 **Type Flexibility for API Variations**

### **Handling API Response Variations**
```python
class FindingSpec(BaseModel):
    finding_categories: Optional[List[str]] = None
    location_urls: Optional[Union[List[str], dict]] = None  # Can be list or empty object
    references: Optional[Union[List[dict], dict]] = None    # Can be list or empty object
```

### **Optional Fields for API Variations**
```python
class FindingMeta(BaseModel):
    name: str
    description: Optional[str] = None
    create_time: Optional[str] = None
    update_time: Optional[str] = None
    upsert_time: Optional[str] = None
    tags: Optional[List[str]] = None
```

## 🚨 **Common Error Patterns**

### **API Endpoint Issues**
- **Wrong URL Pattern**: Check OpenAPI spec for actual endpoints
- **Authentication Failures**: Use resource modules instead of direct API calls
- **Response Parsing**: Use consistent pattern across all resource modules

### **Pydantic Model Issues**
- **Missing Fields**: Compare with live API data
- **Type Mismatches**: Use `Union` types for flexible fields
- **Validation Errors**: Make fields optional for API variations

### **Test Structure Issues**
- **Redundant Files**: Consolidate by resource type
- **Naming Inconsistency**: Follow existing patterns
- **Class References**: Maintain consistency between names and references

## 🔧 **Implementation Best Practices**

### **1. Live Data Analysis First**
```python
# Analyze live data before creating models
headers = client.default_headers
res = client.get(f"v1/namespaces/{namespace}/{resource}", headers=headers)
data = res.json()
objects = data.get("list", {}).get("objects", [])

if objects:
    sample = objects[0]
    print("Sample object keys:", list(sample.keys()))
    print("Sample object spec keys:", list(sample.get('spec', {}).keys()))
    print("Sample object meta keys:", list(sample.get('meta', {}).keys()))
```

### **2. Schema Drift Detection from Start**
```python
# Implement schema drift detection from the start
class {Resource}(BaseModel):
    meta: {Resource}Meta
    spec: {Resource}Spec
    
    @field_validator('*', mode='before')
    @classmethod
    def detect_schema_drift(cls, v, info):
        """Detect and log schema drift for unknown fields."""
        # Implementation here
        return v
```

### **3. Universal API Pattern**
```python
# Use universal pattern for all resources
def list_{resource}s(client: APIClient, tenant_meta_namespace: str) -> List[{Resource}]:
    """List all {resource}s in the specified namespace."""
    try:
        headers = client.default_headers
        res = client.get(f"v1/namespaces/{tenant_meta_namespace}/{resource}s", headers=headers)
        data = res.json()
        objects = data.get("list", {}).get("objects", [])
        return [{Resource}(**item) for item in objects]
    except Exception as e:
        logger.error(f"Error listing {resource}s: {e}", exc_info=True)
        return []
```

## 📚 **Resource-Specific Patterns**

### **Projects**
- **Service**: `ProjectService`
- **Endpoint**: `/v1/namespaces/{tenant_meta.namespace}/projects`
- **Purpose**: Git repository representation
- **Key fields**: `meta`, `processing_status`, `spec`, `tenant_meta`

### **Findings**
- **Service**: `FindingService`
- **Endpoint**: `/v1/namespaces/{tenant_meta.namespace}/findings`
- **Purpose**: Security scan results
- **Key fields**: `meta`, `severity`, `status`, `details`

### **Policies**
- **Service**: `PolicyService`
- **Endpoint**: `/v1/namespaces/{tenant_meta.namespace}/policies`
- **Purpose**: Security policy definitions
- **Key fields**: `meta`, `rules`, `actions`, `scope`

## 🎯 **Success Metrics**

### **Implementation Efficiency**
- **Time to working resource**: < 1 hour (down from 2-3 hours)
- **Zero breaking changes**: All API responses parse successfully
- **Schema drift detection**: Proactive monitoring of API evolution
- **Type safety**: Comprehensive enum coverage

### **Quality Indicators**
- **Real-world validation**: Test with actual API data
- **Error handling**: Graceful handling of API variations
- **Documentation**: Clear field descriptions and examples
- **Maintainability**: Easy to extend and modify

---

*These API patterns ensure consistent, high-quality implementation of all Endor Labs resources in the Cockpit SDK.*

# Schema Drift Detection Implementation

> **Technical implementation guide for proactive API schema monitoring**

## 🎯 **Overview**

Schema drift detection is a critical component for handling API evolution gracefully. This guide provides technical implementation details for implementing schema drift detection across all Endor Labs resources.

## 🔧 **Current Implementation Analysis**

### **Per-Resource Schema Drift Detection**
```python
# Each resource implements its own schema drift detection
class Finding(BaseModel):
    @field_validator('*', mode='before')
    @classmethod
    def detect_schema_drift(cls, v, info):
        """Detect and log schema drift for unknown fields."""
        if info.field_name and isinstance(v, dict):
            model_fields = {
                'meta': {'create_time', 'update_time', 'name', 'description', ...},
                'spec': {'project_uuid', 'level', 'method', 'ecosystem', ...},
                'context': {'id', 'type', 'scan_uuid', 'tags', ...}
            }
            
            if info.field_name in model_fields:
                SchemaDriftDetector.extract_unknown_fields(
                    v, model_fields[info.field_name], f"Finding.{info.field_name}"
                )
        return v
```

### **Pros of Current Approach**
- ✅ **Explicit**: Clear field definitions for each resource
- ✅ **Resource-specific**: Tailored to each resource's structure
- ✅ **Maintainable**: Easy to understand and modify
- ✅ **Debuggable**: Clear logging with resource context

### **Cons of Current Approach**
- ❌ **Repetitive**: Similar code across all resources
- ❌ **Maintenance**: Need to update each resource individually
- ❌ **Inconsistency**: Risk of different implementations
- ❌ **Scalability**: Becomes unwieldy with many resources

## 🚀 **Alternative Implementation Approaches**

### **Approach 1: Base Model with Schema Drift Detection**

```python
class BaseResourceModel(BaseModel):
    """Base model with built-in schema drift detection."""
    
    @field_validator('*', mode='before')
    @classmethod
    def detect_schema_drift(cls, v, info):
        """Detect and log schema drift for unknown fields."""
        if info.field_name and isinstance(v, dict):
            # Get field definitions from class
            field_definitions = getattr(cls, '_field_definitions', {})
            
            if info.field_name in field_definitions:
                SchemaDriftDetector.extract_unknown_fields(
                    v, 
                    field_definitions[info.field_name], 
                    f"{cls.__name__}.{info.field_name}"
                )
        return v

class Finding(BaseResourceModel):
    """Finding resource with schema drift detection."""
    
    # Define field expectations
    _field_definitions = {
        'meta': {'create_time', 'update_time', 'name', 'description', ...},
        'spec': {'project_uuid', 'level', 'method', 'ecosystem', ...},
        'context': {'id', 'type', 'scan_uuid', 'tags', ...}
    }
    
    meta: FindingMeta
    spec: FindingSpec
    context: Context
    uuid: str
```

**Pros**:
- ✅ **DRY**: Single implementation for all resources
- ✅ **Consistent**: Same behavior across all resources
- ✅ **Maintainable**: Update once, applies everywhere

**Cons**:
- ❌ **Complexity**: More complex base class
- ❌ **Flexibility**: Less flexibility for resource-specific needs
- ❌ **Debugging**: Harder to debug resource-specific issues

### **Approach 2: Mixin Pattern**

```python
class SchemaDriftMixin:
    """Mixin for resources that need schema drift detection."""
    
    @field_validator('*', mode='before')
    @classmethod
    def detect_schema_drift(cls, v, info):
        """Detect and log schema drift for unknown fields."""
        if info.field_name and isinstance(v, dict):
            # Get field definitions from class
            field_definitions = getattr(cls, '_field_definitions', {})
            
            if info.field_name in field_definitions:
                SchemaDriftDetector.extract_unknown_fields(
                    v, 
                    field_definitions[info.field_name], 
                    f"{cls.__name__}.{info.field_name}"
                )
        return v

class Finding(BaseModel, SchemaDriftMixin):
    """Finding resource with schema drift detection."""
    
    _field_definitions = {
        'meta': {'create_time', 'update_time', 'name', 'description', ...},
        'spec': {'project_uuid', 'level', 'method', 'ecosystem', ...},
        'context': {'id', 'type', 'scan_uuid', 'tags', ...}
    }
    
    meta: FindingMeta
    spec: FindingSpec
    context: Context
    uuid: str

class SimpleResource(BaseModel):
    """Simple resource without schema drift detection."""
    name: str
    description: str
```

**Pros**:
- ✅ **Selective**: Only apply to resources that need it
- ✅ **Flexible**: Can be mixed in as needed
- ✅ **DRY**: Single implementation for complex resources

**Cons**:
- ❌ **Inconsistency**: Some resources have it, others don't
- ❌ **Complexity**: Need to decide which resources need it
- ❌ **Maintenance**: Still need to maintain field definitions

### **Approach 3: Decorator Pattern**

```python
def schema_drift_detection(field_definitions: dict):
    """Decorator for schema drift detection."""
    def decorator(cls):
        @field_validator('*', mode='before')
        @classmethod
        def detect_schema_drift(cls, v, info):
            """Detect and log schema drift for unknown fields."""
            if info.field_name and isinstance(v, dict):
                if info.field_name in field_definitions:
                    SchemaDriftDetector.extract_unknown_fields(
                        v, 
                        field_definitions[info.field_name], 
                        f"{cls.__name__}.{info.field_name}"
                    )
            return v
        
        cls.detect_schema_drift = detect_schema_drift
        return cls
    return decorator

@schema_drift_detection({
    'meta': {'create_time', 'update_time', 'name', 'description', ...},
    'spec': {'project_uuid', 'level', 'method', 'ecosystem', ...},
    'context': {'id', 'type', 'scan_uuid', 'tags', ...}
})
class Finding(BaseModel):
    meta: FindingMeta
    spec: FindingSpec
    context: Context
    uuid: str
```

**Pros**:
- ✅ **Clean**: Clean separation of concerns
- ✅ **Flexible**: Easy to apply to different resources
- ✅ **Explicit**: Clear field definitions

**Cons**:
- ❌ **Complexity**: More complex decorator implementation
- ❌ **Debugging**: Harder to debug decorator issues
- ❌ **Maintenance**: Need to maintain decorator and field definitions

## 📊 **Scalability Analysis**

### **Resource Complexity Classification**

| Resource Type | Complexity | Schema Drift Detection | Approach |
|---------------|------------|------------------------|----------|
| **Simple** | Low | Optional | Current approach |
| **Medium** | Medium | Recommended | Mixin pattern |
| **Complex** | High | Required | Base model or mixin |

### **Resource Examples**

**Simple Resources** (Basic CRUD, minimal nested structures):
- `Namespace`: Basic metadata, minimal nesting
- `User`: Simple user information
- `Token`: Authentication tokens

**Medium Resources** (Some complexity, moderate nesting):
- `Project`: Git repository information, processing status
- `Scan`: Scan results and metadata
- `Policy`: Security policies and rules

**Complex Resources** (High complexity, extensive nesting):
- `Finding`: 30+ fields, multiple categories, complex enums
- `Secret`: Secret detection with complex metadata
- `Vulnerability`: Vulnerability details with remediation

### **Recommended Approach by Resource Type**

```python
# Simple Resources - No schema drift detection needed
class Namespace(BaseModel):
    uuid: str
    meta: NamespaceMeta

# Medium Resources - Optional schema drift detection
class Project(BaseModel, SchemaDriftMixin):
    _field_definitions = {
        'meta': {'create_time', 'update_time', 'name', 'description', ...},
        'processing_status': {'scan_state', 'scan_time', 'scan_error', ...},
        'spec': {'git_info', 'language', 'framework', ...}
    }
    
    meta: ProjectMeta
    processing_status: ProcessingStatus
    spec: ProjectSpec
    uuid: str

# Complex Resources - Required schema drift detection
class Finding(BaseModel, SchemaDriftMixin):
    _field_definitions = {
        'meta': {'create_time', 'update_time', 'name', 'description', ...},
        'spec': {'project_uuid', 'level', 'method', 'ecosystem', ...},
        'context': {'id', 'type', 'scan_uuid', 'tags', ...}
    }
    
    meta: FindingMeta
    spec: FindingSpec
    context: Context
    uuid: str
```

## 🚀 **Implementation Strategy**

### **Phase 1: Keep Current Approach**
- **Rationale**: Current approach works well for existing resources
- **Action**: No changes needed for Finding, Project, Namespace
- **Timeline**: Immediate

### **Phase 2: Implement Mixin Pattern**
- **Rationale**: Provides flexibility for new resources
- **Action**: Create `SchemaDriftMixin` for new resources
- **Timeline**: Next resource implementation

### **Phase 3: Evaluate Base Model Approach**
- **Rationale**: Consider for future scalability
- **Action**: Implement base model for new complex resources
- **Timeline**: When implementing 5+ new resources

### **Phase 4: Automated Field Definition Generation**
- **Rationale**: Reduce maintenance overhead
- **Action**: Auto-generate field definitions from live data
- **Timeline**: Future enhancement

## 🔧 **SchemaDriftDetector Implementation**

### **Core Detection Logic**
```python
class SchemaDriftDetector:
    """Detects and logs schema drift for unknown fields."""
    
    @staticmethod
    def extract_unknown_fields(data: dict, known_fields: set, context: str) -> None:
        """Extract and log unknown fields from API response."""
        if not isinstance(data, dict):
            return
            
        unknown_fields = set(data.keys()) - known_fields
        
        if unknown_fields:
            logger.warning(
                f"Schema drift detected in {context}: "
                f"Unknown fields: {sorted(unknown_fields)}. "
                f"Consider updating the model to include these fields."
            )
            
            # Log detailed information for debugging
            for field in unknown_fields:
                value = data[field]
                logger.info(
                    f"Unknown field '{field}' in {context}: "
                    f"type={type(value).__name__}, value={repr(value)[:100]}"
                )
```

### **Integration with Pydantic Models**
```python
@field_validator('*', mode='before')
@classmethod
def detect_schema_drift(cls, v, info):
    """Detect and log schema drift for unknown fields."""
    if info.field_name and isinstance(v, dict):
        model_fields = {
            'meta': {'create_time', 'update_time', 'name', 'description', ...},
            'spec': {'project_uuid', 'level', 'method', 'ecosystem', ...},
            'context': {'id', 'type', 'scan_uuid', 'tags', ...}
        }
        
        if info.field_name in model_fields:
            SchemaDriftDetector.extract_unknown_fields(
                v, model_fields[info.field_name], f"{cls.__name__}.{info.field_name}"
            )
    return v
```

## 📈 **Success Metrics**

### **Implementation Efficiency**
- **Time to implement new resource**: < 1 hour
- **Maintenance overhead**: Minimal
- **Consistency**: High across all resources

### **Quality Indicators**
- **Schema drift detection**: Proactive monitoring
- **Type safety**: Comprehensive coverage
- **Maintainability**: Easy to extend and modify

## ✅ **Recommendations**

**Current Approach**: Keep current per-resource implementation for existing resources (Finding, Project, Namespace).

**Future Approach**: Use mixin pattern for new resources, with base model approach for complex resources.

**Implementation Plan**: 
1. **Immediate**: Keep current approach for existing resources
2. **Next**: Implement mixin pattern for new resources
3. **Future**: Consider base model approach for complex resources
4. **Long-term**: Automated field definition generation

**Status: 🎯 SCALABLE APPROACH IDENTIFIED** - Ready for efficient resource modeling with appropriate schema drift detection strategy.

---

*This schema drift detection implementation ensures proactive monitoring of API evolution and graceful handling of breaking changes.*

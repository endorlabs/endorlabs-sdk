# Testing and Validation Workflow

> **Systematic approach to testing resource implementations and ensuring quality**

## 🎯 **Test Structure Standardization**

### **Previous Approach (Problematic)**
```
tests/
├── test_resource_get_operations.py
├── test_resource_operations.py
├── test_tag_management.py
├── test_patch_with_update_mask.py
└── test_comprehensive_tag_fix.py
```

### **Improved Approach (Recommended)**
```
tests/
├── test_namespace.py    # All namespace operations
├── test_project.py      # All project operations  
├── test_finding.py      # All finding operations
└── test_tool_*.py       # Tool-specific tests
```

### **Key Benefits**
- **Intuitive Organization**: Follows `endorctl` naming pattern
- **Consolidated Operations**: All resource operations in single files
- **Reduced Redundancy**: Eliminates duplicate test files
- **Maintainable Structure**: Easy to find and update tests
- **Consistent Naming**: `test_<resource>.py` with singular resource names

## 📋 **Test Implementation Pattern**

### **Standard Test Class Structure**
```python
class TestProject:
    """Test cases for Project resource operations."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        self.client = APIClient()
        self.namespace = os.getenv('ENDOR_NAMESPACE', 'endor-solutions-tgowan.cockpit')
        
        # Ensure we have test data
        self.projects = projects.list_projects(self.client, self.namespace)
        
        # Skip tests if no data available
        if not self.projects:
            pytest.skip("No projects available for testing")
    
    def test_project_get_list(self):
        """Test GET projects operation."""
        # Implementation here
    
    def test_project_get_by_uuid(self):
        """Test GET project by UUID operation."""
        # Implementation here
    
    def test_project_patch_tags(self):
        """Test PATCH operations using tag management."""
        # Implementation here
    
    def test_project_operations_summary(self):
        """Generate summary of project operations."""
        # Implementation here
```

## 🔧 **Common Test Restructuring Issues**

### **1. Class Name Mismatches**
```python
# Problem: Inconsistent class names
class TestResourceGetOperations:  # Old name

# In main execution block:
test_instance = TestResourceGetOperations()  # Fails!

# Solution: Consistent naming
class TestResourceOperations:  # New name
test_instance = TestResourceOperations()  # Works!
```

### **2. Redundant Test Files**
```bash
# Problem: Multiple overlapping files
tests/
├── test_resource_get_operations.py
├── test_resource_operations.py
├── test_tag_management.py
├── test_patch_with_update_mask.py
└── test_comprehensive_tag_fix.py

# Solution: Consolidate by resource
tests/
├── test_namespace.py    # All namespace operations
├── test_project.py      # All project operations
└── test_finding.py      # All finding operations
```

### **3. Method Reference Updates**
```python
# Problem: Old method references
test_instance.test_patch_operation_limitations()  # Method doesn't exist

# Solution: Update to new method names
test_instance.test_projects_patch_tags()
test_instance.test_findings_patch_tags()
```

## 🚨 **PATCH Endpoint Testing Patterns**

### **Common PATCH Debugging Issues**

#### **1. 501 Method Not Allowed Error**
```bash
# WRONG: UUID in URL path
PATCH /v1/namespaces/{namespace}/projects/{uuid}

# CORRECT: UUID in request body
PATCH /v1/namespaces/{namespace}/projects
# Request body: {"object": {"uuid": "...", ...}}
```

#### **2. 400 Bad Request - Missing Required Fields**
```bash
# Problem: API requires full object structure
# Solution: Use update_mask for partial updates
{
  "object": {"uuid": "...", "meta": {"tags": ["new-tag"]}},
  "request": {"update_mask": "meta.tags"}
}
```

#### **3. Tags Not Persisting Despite 200 OK**
```python
# Problem: Pydantic model missing tags field
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

## 📊 **Test Quality Assurance**

### **Implementation Complete When:**
- [ ] GET operations return actual data (not empty lists)
- [ ] Pydantic models validate without errors
- [ ] All CRUD operations work correctly
- [ ] Resource module follows established patterns
- [ ] Documentation updated with learnings
- [ ] Tests pass for all operations
- [ ] .workspace/workspace.py demonstrates working functionality

### **Test Structure Success Metrics**
- [ ] No one-off scripts in .workspace
- [ ] Single .workspace/workspace.py file for experimentation
- [ ] All learnings documented
- [ ] Repeatable process established
- [ ] Ready for next resource implementation

## 🔧 **Restructuring Strategy**

### **Step 1: Follow Existing Patterns**
- Use `test_namespace.py` as template
- Follow `endorctl` naming pattern with singular resource names
- Group all operations per resource in single files

### **Step 2: Consolidate by Resource**
- Group all operations per resource
- Update all references (class names, method names, imports)
- Test thoroughly to verify all functionality works after restructuring

### **Step 3: Update All References**
- Class names, method names, imports
- Test thoroughly: Verify all functionality works after restructuring

## 📚 **Testing Best Practices**

### **Test Data Management**
```python
@pytest.fixture(autouse=True)
def setup(self):
    """Set up test environment."""
    self.client = APIClient()
    self.namespace = os.getenv('ENDOR_NAMESPACE', 'endor-solutions-tgowan.cockpit')
    
    # Ensure we have test data
    self.projects = projects.list_projects(self.client, self.namespace)
    
    # Skip tests if no data available
    if not self.projects:
        pytest.skip("No projects available for testing")
```

### **Error Handling in Tests**
```python
def test_project_operations_with_error_handling(self):
    """Test project operations with comprehensive error handling."""
    try:
        # Test operation
        result = self.operation()
        assert result is not None
        print(f"[SUCCESS] Operation completed: {result}")
    except Exception as e:
        print(f"[ERROR] Operation failed: {e}")
        # Handle specific error types
        if "403" in str(e):
            print("[INFO] Permission denied - check namespace format")
        elif "404" in str(e):
            print("[INFO] Resource not found - check UUID")
        else:
            print(f"[ERROR] Unexpected error: {e}")
        raise
```

### **Test Documentation**
```python
def test_project_operations_summary(self):
    """Generate a summary of project operations."""
    print(f"\n=== PROJECT OPERATIONS SUMMARY ===")
    
    print("GET Operations:")
    print(f"  - List Projects: GET /v1/namespaces/{self.namespace}/projects")
    print(f"  - Get Project: GET /v1/namespaces/{self.namespace}/projects/{{uuid}}")
    
    print("PATCH Operations (Tag Management):")
    print(f"  - Update Project Tags: PATCH /v1/namespaces/{self.namespace}/projects")
    print("  - Uses update_mask for efficient partial updates")
    print("  - Project tags: meta.tags field")
    
    print("Success Metrics:")
    print(f"  - Projects Retrieved: {len(self.projects)}")
    print("  - GET Operations: Working")
    print("  - PATCH Operations: Working with update_mask")
    print("  - Tag Management: Functional for user-defined tags")
```

## 🎯 **Success Metrics**

### **Test Structure Success**
- [ ] Intuitive organization following `endorctl` pattern
- [ ] Consolidated operations per resource
- [ ] Reduced redundancy and maintenance overhead
- [ ] Consistent naming and structure

### **Test Quality Success**
- [ ] All operations tested and working
- [ ] Error handling comprehensive
- [ ] Documentation clear and helpful
- [ ] Ready for production use

---

*This testing workflow ensures consistent, high-quality testing of all Endor Labs resources in the Cockpit SDK.*

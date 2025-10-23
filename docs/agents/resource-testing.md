# Resource Testing Strategies

> **Comprehensive testing strategies for Endor Labs resource implementations**

## 🎯 **Testing Overview**

This guide provides comprehensive testing strategies for Endor Labs resource implementations, covering test structure, patterns, and best practices.

## 📋 **Test Structure Standardization**

### **Recommended Test Structure**
```
tests/
├── test_namespace.py    # All namespace operations
├── test_project.py      # All project operations  
├── test_finding.py      # All finding operations
└── test_tool_*.py       # Tool-specific tests
```

### **Test Class Pattern**
```python
class Test{Resource}:
    """Test cases for {Resource} resource operations."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test environment."""
        self.client = APIClient()
        self.namespace = os.getenv('ENDOR_NAMESPACE', 'endor-solutions-tgowan.cockpit')
        
        # Ensure we have test data
        self.{resource}s = {resource}s.list_{resource}s(self.client, self.namespace)
        
        # Skip tests if no data available
        if not self.{resource}s:
            pytest.skip("No {resource}s available for testing")
    
    def test_{resource}_get_list(self):
        """Test GET {resource}s operation."""
        # Implementation here
    
    def test_{resource}_get_by_uuid(self):
        """Test GET {resource} by UUID operation."""
        # Implementation here
    
    def test_{resource}_patch_tags(self):
        """Test PATCH operations using tag management."""
        # Implementation here
    
    def test_{resource}_operations_summary(self):
        """Generate summary of {resource} operations."""
        # Implementation here
```

## 🔧 **Testing Patterns**

### **1. GET Operations Testing**

#### **List Resources**
```python
def test_{resource}_get_list(self):
    """Test GET {resource}s operation."""
    print(f"\n=== TESTING GET {RESOURCE}S ===")
    
    # Test list_{resource}s
    {resource}s_list = {resource}s.list_{resource}s(self.client, self.namespace)
    assert isinstance({resource}s_list, list), "Should return a list of {resource}s"
    assert len({resource}s_list) > 0, "Should have at least one {resource}"
    
    print(f"Found {len({resource}s_list)} {resource}s")
    
    # Print details for the first few {resource}s
    for {resource} in {resource}s_list[:5]:
        print(f"{Resource} {resource}.uuid: {resource}.meta.name}")
        if {resource}.meta.tags:
            print(f"  {Resource} tags: {resource}.meta.tags}")
        else:
            print(f"  {Resource} has no tags")
```

#### **Get Resource by UUID**
```python
def test_{resource}_get_by_uuid(self):
    """Test GET {resource} by UUID operation."""
    print(f"\n=== TESTING GET {RESOURCE} BY UUID ===")
    
    # Get a specific {resource}
    {resource}_uuid = self.{resource}s[0].uuid
    {resource} = {resource}s.get_{resource}(self.client, self.namespace, {resource}_uuid)
    assert {resource} is not None, f"Should retrieve {resource} {resource}_uuid}"
    assert {resource}.uuid == {resource}_uuid, "Retrieved {resource} UUID mismatch"
    
    print(f"Successfully retrieved {resource}: {resource}.uuid}")
    print(f"{Resource} name: {resource}.meta.name}")
    if {resource}.meta.tags:
        print(f"{Resource} tags: {resource}.meta.tags}")
    else:
        print(f"{Resource} has no tags")
```

### **2. PATCH Operations Testing**

#### **Tag Management Testing**
```python
def test_{resource}_patch_tags(self):
    """Test PATCH operations on {resource}s using tag management."""
    print(f"\n=== TESTING {RESOURCE} PATCH OPERATIONS ===")
    
    {resource} = self.{resource}s[0]
    print(f"Testing {resource}: {resource}.uuid}")
    
    # Test adding a tag
    test_tag = "test-patch-{resource}-tag"
    updated_{resource} = add_{resource}_tag(self.client, self.namespace, {resource}.uuid, test_tag)
    assert updated_{resource} is not None, f"Should successfully add {resource} tag"
    
    # Verify tag was added
    tags_after_add = list_{resource}_tags(self.client, self.namespace, {resource}.uuid)
    assert test_tag in tags_after_add, "Tag should be present after add"
    print(f"[SUCCESS] Added tag '{test_tag}' to {resource}")
    
    # Test removing the tag
    final_{resource} = remove_{resource}_tag(self.client, self.namespace, {resource}.uuid, test_tag)
    assert final_{resource} is not None, f"Should successfully remove {resource} tag"
    
    # Verify tag was removed
    tags_after_remove = list_{resource}_tags(self.client, self.namespace, {resource}.uuid)
    assert test_tag not in tags_after_remove, "Tag should be removed"
    print(f"[SUCCESS] Removed tag '{test_tag}' from {resource}")
```

### **3. Structure Analysis Testing**

#### **Resource Structure Analysis**
```python
def test_{resource}_structure_analysis(self):
    """Analyze the structure of a {Resource} resource."""
    print(f"\n=== {RESOURCE} STRUCTURE ANALYSIS ===")
    {resource} = self.{resource}s[0]
    print(f"Analyzing {resource}: {resource}.uuid} - {resource}.meta.name}")
    
    print(f"{Resource} meta fields: {[field for field in dir({resource}.meta) if not field.startswith('_')]}")
    if hasattr({resource}.meta, 'tags'):
        print(f"{Resource} meta tags: {resource}.meta.tags}")
    else:
        print(f"{Resource} meta does not have tags field")
    
    print(f"{Resource} spec fields: {[field for field in dir({resource}.spec) if not field.startswith('_')]}")
    if hasattr({resource}.spec, 'finding_tags'):
        print(f"{Resource} spec finding_tags: {resource}.spec.finding_tags}")
    else:
        print(f"{Resource} spec does not have finding_tags field")
```

### **4. Operations Summary Testing**

#### **Resource Operations Summary**
```python
def test_{resource}_operations_summary(self):
    """Generate a summary of {resource} operations."""
    print(f"\n=== {RESOURCE} OPERATIONS SUMMARY ===")
    
    print("GET Operations:")
    print(f"  - List {Resource}s: GET /v1/namespaces/{self.namespace}/{resource}s")
    print(f"  - Get {Resource}: GET /v1/namespaces/{self.namespace}/{resource}s/{{uuid}}")
    
    print("PATCH Operations (Tag Management):")
    print(f"  - Update {Resource} Tags: PATCH /v1/namespaces/{self.namespace}/{resource}s")
    print("  - Uses update_mask for efficient partial updates")
    print(f"  - {Resource} tags: meta.tags field")
    
    print("Success Metrics:")
    print(f"  - {Resource}s Retrieved: {len(self.{resource}s)}")
    print("  - GET Operations: Working")
    print("  - PATCH Operations: Working with update_mask")
    print(f"  - Tag Management: Functional for user-defined tags")
```

## 🚨 **Common Testing Issues**

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

## 🔧 **Testing Best Practices**

### **1. Test Data Management**
```python
@pytest.fixture(autouse=True)
def setup(self):
    """Set up test environment."""
    self.client = APIClient()
    self.namespace = os.getenv('ENDOR_NAMESPACE', 'endor-solutions-tgowan.cockpit')
    
    # Ensure we have test data
    self.{resource}s = {resource}s.list_{resource}s(self.client, self.namespace)
    
    # Skip tests if no data available
    if not self.{resource}s:
        pytest.skip("No {resource}s available for testing")
```

### **2. Error Handling in Tests**
```python
def test_{resource}_operations_with_error_handling(self):
    """Test {resource} operations with comprehensive error handling."""
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

### **3. Test Documentation**
```python
def test_{resource}_operations_summary(self):
    """Generate a summary of {resource} operations."""
    print(f"\n=== {RESOURCE} OPERATIONS SUMMARY ===")
    
    print("GET Operations:")
    print(f"  - List {Resource}s: GET /v1/namespaces/{self.namespace}/{resource}s")
    print(f"  - Get {Resource}: GET /v1/namespaces/{self.namespace}/{resource}s/{{uuid}}")
    
    print("PATCH Operations (Tag Management):")
    print(f"  - Update {Resource} Tags: PATCH /v1/namespaces/{self.namespace}/{resource}s")
    print("  - Uses update_mask for efficient partial updates")
    print(f"  - {Resource} tags: meta.tags field")
    
    print("Success Metrics:")
    print(f"  - {Resource}s Retrieved: {len(self.{resource}s)}")
    print("  - GET Operations: Working")
    print("  - PATCH Operations: Working with update_mask")
    print(f"  - Tag Management: Functional for user-defined tags")
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

## 🎯 **Testing Success Metrics**

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

## 📚 **Resource-Specific Testing Examples**

### **Project Resource Testing**
```python
class TestProject:
    """Test cases for Project resource operations."""
    
    def test_project_get_list(self):
        """Test GET projects operation."""
        projects_list = projects.list_projects(self.client, self.namespace)
        assert isinstance(projects_list, list)
        assert len(projects_list) > 0
        print(f"Found {len(projects_list)} projects")
    
    def test_project_patch_tags(self):
        """Test PATCH operations on projects using tag management."""
        project = self.projects[0]
        test_tag = "test-patch-project-tag"
        
        # Test adding tag
        updated_project = add_project_tag(self.client, self.namespace, project.uuid, test_tag)
        assert updated_project is not None
        
        # Test removing tag
        final_project = remove_project_tag(self.client, self.namespace, project.uuid, test_tag)
        assert final_project is not None
```

### **Finding Resource Testing**
```python
class TestFinding:
    """Test cases for Finding resource operations."""
    
    def test_finding_get_list(self):
        """Test GET findings operation."""
        findings_list = findings.list_findings(self.client, self.namespace)
        assert isinstance(findings_list, list)
        assert len(findings_list) > 0
        print(f"Found {len(findings_list)} findings")
    
    def test_finding_patch_tags(self):
        """Test PATCH operations on findings using tag management."""
        finding = self.findings[0]
        test_tag = "test-patch-finding-tag"
        
        # Test adding meta tag
        updated_finding = add_finding_tag(self.client, self.namespace, finding.uuid, test_tag, "meta")
        assert updated_finding is not None
        
        # Test removing meta tag
        final_finding = remove_finding_tag(self.client, self.namespace, finding.uuid, test_tag, "meta")
        assert final_finding is not None
```

---

*This resource testing guide ensures comprehensive, high-quality testing of all Endor Labs resources in the Cockpit SDK.*

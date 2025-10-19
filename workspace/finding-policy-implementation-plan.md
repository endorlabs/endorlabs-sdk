# Finding and Policy Resource Implementation Plan

> **Based on Research → Log → Update Knowledge Base Workflow**

## 🎯 **Implementation Overview**

### **Objective**
Implement Finding and Policy resource modules following the established Project resource pattern, using the comprehensive workflow discovered in the knowledge base.

### **Research Findings Summary**
- **Knowledge Base**: Contains resource implementation workflow (Score: 0.698)
- **API Spec**: Has FindingService and PolicyService endpoints
- **Authentication**: endorctl conflicts with SDK, use SDK approach
- **Pattern**: Follow established Project resource implementation pattern

## 📋 **Implementation Plan**

### **Phase 1: Finding Resource Implementation**

#### **Step 1.1: API Specification Analysis**
- **Target**: Find FindingService endpoints in OpenAPI spec
- **Expected Pattern**: `/v1/namespaces/{tenant_meta.namespace}/findings`
- **Operations**: GET (list), GET (get), POST (create), PATCH (update), DELETE (delete)

#### **Step 1.2: Pydantic Model Creation**
- **Base Model**: `Finding` with metadata, severity, status, details
- **Create Model**: `CreateFindingPayload` for new findings
- **Update Model**: `UpdateFindingPayload` for modifications
- **Reference**: Use `docs/knowledge/endor-data-model/findings.md` for structure

#### **Step 1.3: Resource Module Implementation**
- **File**: `src/endor_cockpit/resources/findings.py`
- **Functions**: `list_findings()`, `get_finding()`, `create_finding()`, `update_finding()`, `delete_finding()`
- **Pattern**: Follow `projects.py` implementation exactly

#### **Step 1.4: Testing Strategy**
- **GET Operations First**: Test list and get operations
- **Response Structure**: Expect `{"list": {"objects": [...]}}` pattern
- **Path Parameters**: Use `tenant_meta.namespace` (canonical namespace)
- **Workspace Testing**: Use `workspace/workspace.py` for experimentation

### **Phase 2: Policy Resource Implementation**

#### **Step 2.1: API Specification Analysis**
- **Target**: Find PolicyService endpoints in OpenAPI spec
- **Expected Pattern**: `/v1/namespaces/{tenant_meta.namespace}/policies`
- **Operations**: GET (list), GET (get), POST (create), PATCH (update), DELETE (delete)

#### **Step 2.2: Pydantic Model Creation**
- **Base Model**: `Policy` with metadata, rules, actions, scope
- **Create Model**: `CreatePolicyPayload` for new policies
- **Update Model**: `UpdatePolicyPayload` for modifications
- **Reference**: Use `docs/knowledge/endor-data-model/policies.md` for structure

#### **Step 2.3: Resource Module Implementation**
- **File**: `src/endor_cockpit/resources/policies.py`
- **Functions**: `list_policies()`, `get_policy()`, `create_policy()`, `update_policy()`, `delete_policy()`
- **Pattern**: Follow `projects.py` implementation exactly

#### **Step 2.4: Testing Strategy**
- **GET Operations First**: Test list and get operations
- **Response Structure**: Expect `{"list": {"objects": [...]}}` pattern
- **Path Parameters**: Use `tenant_meta.namespace` (canonical namespace)
- **Workspace Testing**: Use `workspace/workspace.py` for experimentation

### **Phase 3: Integration and Documentation**

#### **Step 3.1: Resource Module Integration**
- **Update**: `src/endor_cockpit/resources/__init__.py`
- **Import**: Add findings and policies to main imports
- **Testing**: Update `workspace/workspace.py` with new test functions

#### **Step 3.2: Knowledge Base Updates**
- **Finding Implementation Guide**: Create `docs/knowledge/endor-data-model/finding-implementation-guide.md`
- **Policy Implementation Guide**: Create `docs/knowledge/endor-data-model/policy-implementation-guide.md`
- **Update Log**: Document all learnings in `workspace/log.md`
- **Rebuild**: Run `uv run python workflow/init_vector_db.py --rebuild`

#### **Step 3.3: Documentation Updates**
- **Developer Guide**: Update with Finding and Policy patterns
- **API Quirks**: Document any Finding/Policy specific quirks
- **Common Pitfalls**: Add Finding/Policy specific pitfalls
- **Troubleshooting**: Add Finding/Policy troubleshooting steps

## 🛠️ **Implementation Workflow**

### **For Each Resource (Finding, Policy):**

#### **Step 1: Research (RAG → API Spec → SDK Testing)**
```python
# Use workspace.py research functions
research_findings = research_findings_policies()
api_spec_findings = analyze_api_spec()
```

#### **Step 2: API Specification Analysis**
- Search OpenAPI spec for `{Resource}Service` endpoints
- Document endpoint patterns and parameters
- Identify response structures

#### **Step 3: GET Operations First**
```python
# Test basic GET operations in workspace.py
def test_findings():
    findings_list = findings.list_findings(client, namespace)
    print(f"Found {len(findings_list)} findings")

def test_policies():
    policies_list = policies.list_policies(client, namespace)
    print(f"Found {len(policies_list)} policies")
```

#### **Step 4: Pydantic Model Creation**
- Model from live data + API spec
- Handle optional fields correctly
- Validate against actual API responses

#### **Step 5: Full CRUD Implementation**
- Implement all CRUD operations
- Follow established patterns from `projects.py`
- Test each operation incrementally

#### **Step 6: Documentation and Knowledge Base**
- Document all learnings
- Update relevant documentation
- Rebuild knowledge base

## 🎯 **Success Metrics**

### **Technical Success:**
- [ ] Finding resource module fully functional
- [ ] Policy resource module fully functional
- [ ] All CRUD operations working
- [ ] Pydantic models validate correctly
- [ ] No linting errors
- [ ] Security scan clean

### **Documentation Success:**
- [ ] Implementation guides created
- [ ] Knowledge base updated
- [ ] All learnings documented
- [ ] Troubleshooting guides updated
- [ ] API quirks documented

### **Workflow Success:**
- [ ] Research → Log → Update Knowledge Base workflow followed
- [ ] All findings documented in workspace/log.md
- [ ] Knowledge base rebuilt with new context
- [ ] Ready for next resource implementation

## 🚀 **Next Actions**

1. **Start with Finding Resources**: Follow Phase 1 implementation
2. **Use Workspace.py**: All experimentation in collaborative workspace
3. **Follow Established Patterns**: Copy from `projects.py` exactly
4. **Document Everything**: Log all learnings and decisions
5. **Update Knowledge Base**: Propagate learnings to relevant docs

**Status: 📋 READY TO IMPLEMENT - Comprehensive plan based on research findings**

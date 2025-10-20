# Endor Cockpit: AI Agent Integration Guide

> **Universal Anchor for All AI Agents**

## 🚀 **Quick Start (30 seconds)**

### **Knowledge Base First**
**CRITICAL**: Always query the vector database before any operations. This portable shared learning index contains:
- API patterns and best practices
- Known quirks and workarounds
- Security guidelines and compliance requirements
- Operational procedures and troubleshooting


```python
from endor_cockpit.rag import query_vector_db

# Query before any operation
results = query_vector_db("How do I create a namespace?")
# Review results, then proceed with confidence
```

**Workflow**: Query → Verify → Act → Update if contradictions found

### **Agent Type Selection**
- **🤖 SDK Developer**: [Development Guide](./docs/personas/developer/README.md) → [Architecture](./docs/personas/developer/architecture.md)
- **🔧 SDK User**: [Usage Guide](./docs/personas/developer/README.md) → [API Quirks](./docs/personas/developer/api-quirks.md)
- **🔍 Security Scanner**: [Security Guide](./docs/personas/security/README.md) → [Findings Guide](./docs/personas/security/findings-guide.md)
- **⚙️ Operations Admin**: [Operations Guide](./docs/personas/operations/README.md) → [Namespace Admin](./docs/personas/operations/namespace-admin.md)

### **Critical Requirements**
- **Security**: Always run `endorctl scan` before code changes are committed pushed to the remote repository.
- **Linting**: Max 88 chars/line, sorted imports, no trailing whitespace
- **Dependencies**: Pin exact versions, avoid `latest` or `>=`
- **Environment**: Set `ENDOR_API`, `ENDOR_API_CREDENTIALS_KEY`, `ENDOR_API_CREDENTIALS_SECRET`

---

## 📋 **Project Context**

**Endor Cockpit** is a production-ready foundational service:
- **Purpose**: Administer, operate and scan with Endor Labs tooling through REST APIs
- **Data Classification**: Public (no PII handling)
- **Deployment**: Production environment, global region
- **Security**: Paramount importance
- **Architecture**: Resource-oriented SDK pattern

---

## 🎯 **Documentation Style Guide**

### **Template-Based Documentation**

All Endor Labs documentation follows standardized templates for consistency and RAG optimization.

#### **Resource Documentation**
- **Template**: `docs/endor-data-model/_RESOURCE_TEMPLATE.md`
- **Structure**: Architecture → Data Model → Operations → Relationships → Common Issues → Testing Patterns → (Optional) Troubleshooting
- **RAG Metadata**: Required for vector database indexing
- **Status Markers**: Only ✅ IMPLEMENTED (no conceptual/planned markers)

#### **Documentation Standards**
- **Direct SDK References**: Point to actual SDK classes and functions with line numbers
- **Real Examples**: Use working code examples that reference actual SDK implementations
- **Validation**: All references must be accurate and current
- **Cross-References**: Link to related resources and templates

#### **Template Usage**
1. **Copy template** from `_RESOURCE_TEMPLATE.md` or other `*_TEMPLATE.md` files for formatting
2. **Replace placeholders** with actual resource information
3. **Fill content** based on actual SDK implementation
4. **Validate references** to ensure all function/class references exist
5. **Test RAG queries** to ensure content is discoverable

#### **RAG Optimization**
- **Semantic Chunking**: Structure content for optimal vector database retrieval
- **Header Hierarchy**: H1/H2/H3 boundaries for chunking
- **Metadata Extraction**: Enhanced metadata for better search results
- **Cross-References**: Link between related documentation sections

---


## 🔑 **API Patterns & Documentation**

### **Trust but Verify**
- **Primary Source**: Always check function docstrings and module documentation first
- **Resource Documentation**: See `src/endor_cockpit/resources/[resource].py` for comprehensive API patterns
- **Canonical Naming**: Refer to namespace.py documentation for hierarchical naming requirements
- **Validation**: Verify API patterns against actual SDK implementation before use

---

## 🔍 **Real-World Usage Patterns**

### **Finding Analysis Patterns**

**Pattern**: Retrieve and analyze findings by severity, category, and ecosystem
```python
# Get all findings in namespace
findings = finding.list_findings(client, namespace)

# Filter by severity
critical_findings = [f for f in findings if f.spec.level == FindingLevel.CRITICAL]

# Filter by category
vulnerability_findings = [f for f in findings 
                         if 'FINDING_CATEGORY_VULNERABILITY' in (f.spec.finding_categories or [])]

# Filter by project
project_findings = [f for f in findings if f.spec.project_uuid == project_uuid]
```

**Pattern**: Analyze finding distribution across multiple dimensions
```python
# Analyze finding distribution
severity_counts = {}
category_counts = {}
ecosystem_counts = {}

for finding in findings:
    # Severity analysis
    severity = str(finding.spec.level)
    severity_counts[severity] = severity_counts.get(severity, 0) + 1
    
    # Category analysis
    categories = finding.spec.finding_categories or []
    for category in categories:
        category_counts[category] = category_counts.get(category, 0) + 1
    
    # Ecosystem analysis
    ecosystem = str(finding.spec.ecosystem) if finding.spec.ecosystem else 'Unknown'
    ecosystem_counts[ecosystem] = ecosystem_counts.get(ecosystem, 0) + 1
```

### **Project Management Patterns**

**Pattern**: List and analyze projects with processing status
```python
# Get all projects in namespace
projects = project.list_projects(client, namespace)

# Filter by scan state
idle_projects = [p for p in projects if p.processing_status.scan_state == "SCAN_STATE_IDLE"]
scanning_projects = [p for p in projects if p.processing_status.scan_state == "SCAN_STATE_SCANNING"]

# Analyze project distribution
platform_counts = {}
for project in projects:
    platform = project.spec.platform_source
    platform_counts[platform] = platform_counts.get(platform, 0) + 1
```

**Pattern**: Update project tags and metadata
```python
# Update project tags
payload = UpdateProjectPayload(
    tags=["security-reviewed", "production-ready"],
    update_mask=["tags"]
)
updated_project = project.update_project(client, namespace, project_uuid, payload, "tags")
```

### **Namespace Hierarchy Patterns**

**Pattern**: Create and manage namespace hierarchies
```python
# Create child namespace
child_payload = CreateNamespacePayload(
    meta=NamespaceMeta(
        name="child-namespace",
        description="Child namespace for testing"
    )
)
child_result = create_namespace(client, parent_namespace, child_payload)

# List namespaces in hierarchy
namespaces = list_namespaces(client, parent_namespace)
```

### **Policy Management Patterns**

**Pattern**: Create and manage security policies
```python
# Create ML_FINDING policy
policy_payload = CreatePolicyPayload(
    meta=PolicyMeta(
        name="Security Policy",
        description="Custom security policy"
    ),
    spec=PolicySpec(
        policy_type=PolicyType.ML_FINDING,
        rule="""package security

configure[result] {
  result = {
    "security_method": {
      "disable": false,
      "parameters": {
        "enable_security": {
          "bool_value": true
        }
      }
    }
  }
}""",
        disable=False
    )
)
new_policy = policy.create_policy(client, namespace, policy_payload)
```

### **Common Pitfalls & Solutions**

**❌ Wrong Path Parameter**
```python
# WRONG - Using UUID instead of canonical namespace
client.get(f"v1/namespaces/{namespace_uuid}/projects")

# CORRECT - Use canonical namespace
client.get(f"v1/namespaces/{tenant_meta_namespace}/projects")
```

**❌ Wrong Response Parsing**
```python
# WRONG - Expecting direct arrays
data = res.json().get("projects", [])

# CORRECT - Use list.objects structure
data = res.json().get("list", {}).get("objects", [])
```

**❌ Missing Update Mask**
```python
# WRONG - Missing update_mask parameter
payload = UpdateProjectPayload(tags=["new-tag"])

# CORRECT - Include update_mask
payload = UpdateProjectPayload(
    tags=["new-tag"],
    update_mask=["tags"]
)
```

---

## 🛠️ **Development Workflow**

### **Pre-Development Checklist**
- [ ] Line length ≤ 88 characters
- [ ] Imports sorted and unused removed
- [ ] No trailing whitespace or blank line whitespace
- [ ] F-strings only with placeholders
- [ ] Dependencies pinned (no `latest`)

### **Quick Commands**
```bash
# Development workflow
uv run ruff check .          # Lint
uv run ruff check . --fix    # Auto-fix
uv run ruff format .         # Format
uv run pytest               # Test
endorctl scan               # Security
```

### **Common Linting Fixes**
- **E501**: Break long lines with parentheses/backslashes
- **F401**: Remove unused imports
- **W291/W293**: Remove trailing/blank line whitespace
- **F541**: Remove `f` prefix from strings without placeholders
- **I001**: Sort import blocks

---

## 🔒 **Security-First Development**

### **Security Scanning**
```bash
# Required before any code changes
endorctl scan

# For dependency changes
endorctl scan --dependencies

# For first-party code changes
endorctl scan --sast
```

### **Data Protection**
- **No PII in logs**: This project handles no PII data
- **Secure logging filters**: Ensure no sensitive data leaks through logging
- **Environment variables**: Use secure credential management

---

## 📚 **Documentation Navigation**

### **Persona-Specific Guides**
- **[Developer](./docs/personas/developer/README.md)**: SDK development, testing, contributing
- **[Operations](./docs/personas/operations/README.md)**: Namespace admin, integrations, troubleshooting
- **[Security](./docs/personas/security/README.md)**: Policy authoring, findings, compliance

### **Knowledge Base**
- **[API Corrections](./docs/SPECIFICATION.md)**: Known discrepancies between OpenAPI spec and actual API
- **[Endor Data Model](./docs/knowledge/endor-data-model/)**: Resource schemas and relationships
- **[Examples](./docs/knowledge/examples/)**: Common workflows and patterns

### **Historical Context**
- **[Changelog](./docs/history/CHANGELOG.md)**: Project evolution and breaking changes
- **[API Evolution](./docs/history/api-evolution.md)**: How the Endor API has changed over time

---

## 🎯 **Success Indicators**

### **Development Success**
- ✅ All tests passing
- ✅ No linting errors
- ✅ Security scan clean
- ✅ Namespace operations working
- ✅ Error handling graceful

### **Documentation Success**
- ✅ Semantic chunking applied consistently
- ✅ Persona routing clear and accurate
- ✅ API patterns documented with examples
- ✅ Vector DB retrievals relevant and complete

---

## 📁 **Workspace Folder**

For local testing and development, use the `workspace/` folder which is excluded from version control:
- Integration test results and configurations
- Temporary policy configurations
- Development scripts and utilities
- Test-specific documentation
- User-specific API configurations
- **Agent notes and task documentation**

**Note for AI Agents**: When creating documentation, notes, or task-specific files, place them in the `workspace/` folder rather than the root directory to keep the repository clean and organized.

### Long-Living Task Tracking for AI Agents

For multi-session tasks or complex workflows that span multiple interactions:

1. Create task tracking files in `workspace/` directory
2. Use markdown checklist format for easy tracking
3. File naming: `workspace/tasks-<description>.md` or `workspace/current-tasks.md`
4. Update checklists as tasks progress
5. Archive completed task files to `workspace/archive/` when done

**Format:**
```markdown
# Task: [Description]
Started: YYYY-MM-DD
Last Updated: YYYY-MM-DD

## Objectives
- [ ] Objective 1
- [ ] Objective 2

## Current Status
- [x] Completed step
- [ ] In progress step
- [ ] Pending step

## Notes
- Important context or decisions
```

**When to use:**
- Multi-session workflows
- Complex refactoring or feature development
- Research and analysis tasks
- Documentation overhauls
- Any task requiring > 30 minutes of context

**When NOT to use:**
- Single-session tasks (use ephemeral notes)
- Quick fixes or simple edits
- Tasks tracked by TODO tool in codebase

### Operational Context
For current operational context including environment setup, GitHub CLI configuration, and development workflow, see `workspace/OPERATIONAL_CONTEXT.md`.

---

## 📝 **Knowledge Capture & Promotion Protocol**

### **Ephemeral Learning Capture**

**CRITICAL**: For every technical issue encountered during SDK development, API debugging, or endorctl usage, document a log entry in `.workspace/logbook.md` using the template format.

**Required Information**:
- **Task**: What was being attempted
- **Context**: Resource types, related files, RAG queries, terminal output
- **Attempted Approach**: Specific function calls, API endpoints, commands
- **Unexpected Behavior**: Expected vs actual behavior, error messages
- **Resolution**: Working solution with exact function signatures
- **Key Learning**: One-sentence summary of core insight
- **Relevant Documentation**: SDK references, test files, API endpoints
- **Miscellaneous Notes**: Additional context and follow-up items
- **Tags**: Appropriate categorization (resource type, operation type, context)
- **Reviewed for Promotion**: Checkbox when ready for archive consideration

### **Template Compliance**

Use `_LOGBOOK_TEMPLATE.md` format exactly:
- Include all required sections
- Provide specific function calls and error messages
- Include working code examples in resolution
- Tag entries with relevant resource types and operation types

### **Promotion Workflow**

**Pre-Commit Process**:
1. **Check for entries** marked "Reviewed for Promotion"
2. **Request user approval** for valuable learnings
3. **If approved**: AI reviews entry and identifies relevant documentation files
4. **Integration**: AI adds learnings to appropriate documentation with timestamp and logbook reference
5. **Vector DB**: Rebuild vector database with new content
6. **Mark promoted**: Update entry status to [PROMOTED - YYYY-MM-DD]

**Target Documentation Files**:
- **Resource-Specific Issues**: `docs/endor-data-model/[resource].md` (Troubleshooting section)
- **API Quirks**: `docs/SPECIFICATION.md` (API Corrections section)
- **Architectural Learnings**: `docs/agents/[relevant-guide].md`
- **Testing Patterns**: Test file comments or `tests/README.md`

### **Chunking Strategy Updates**

The vector database uses enhanced metadata extraction:
- **H1 titles** for main topics
- **Resource types** for resource-specific queries
- **Section names** for targeted content retrieval
- **Subsection names** for granular information

**Metadata Fields**:
- `h1_title`: Main topic title
- `resource_type`: Resource type (project, finding, policy, namespace)
- `section_name`: H2 section name
- `subsection_name`: H3 section name
- `header_level`: Header level (h1, h2, h3)

### **Protocol Benefits**

1. **Systematic Learning Capture**: No knowledge lost during development
2. **Quality Control**: User approval gate ensures value
3. **Traceability**: Link from docs back to original discovery
4. **Consistency**: Template ensures uniform format
5. **Scalability**: Protocol guides all future agents
6. **Efficiency**: Agents can query protocols for maintenance guidance
7. **Maintainability**: Clear processes for information lifecycle
8. **RAG Optimization**: Structured content for vector database indexing

---

*This guide serves as the universal anchor for all AI agents working with Endor Cockpit. For persona-specific guidance, follow the routing links above.*
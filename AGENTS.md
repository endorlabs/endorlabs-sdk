# Endor Cockpit: AI Agent Integration Guide

> **Universal Anchor for All AI Agents**

## 🚀 **Quick Start (30 seconds)**

### **Agent Type Selection**
- **🤖 SDK Developer**: [Development Guide](./docs/personas/developer/README.md) → [Architecture](./docs/personas/developer/architecture.md)
- **🔧 SDK User**: [Usage Guide](./docs/personas/developer/README.md) → [API Quirks](./docs/personas/developer/api-quirks.md)
- **🔍 Security Scanner**: [Security Guide](./docs/personas/security/README.md) → [Findings Guide](./docs/personas/security/findings-guide.md)
- **⚙️ Operations Admin**: [Operations Guide](./docs/personas/operations/README.md) → [Namespace Admin](./docs/personas/operations/namespace-admin.md)

### **Critical Requirements**
- **Security**: Always run `endorctl scan` before code changes
- **Linting**: Max 88 chars/line, sorted imports, no trailing whitespace
- **Dependencies**: Pin exact versions, avoid `latest`
- **Environment**: Set `ENDOR_API`, `ENDOR_API_CREDENTIALS_KEY`, `ENDOR_API_CREDENTIALS_SECRET`

---

## 📋 **Project Context**

**Endor Cockpit** is a production-ready foundational service:
- **Purpose**: Administer, operate and scan with Endor Labs tooling through REST APIs
- **Data Classification**: Public (no PII handling)
- **Deployment**: Production environment, global region
- **Security**: SOC2 and ISO27001 compliant
- **Architecture**: Resource-oriented SDK pattern

> 📋 **For detailed project context, see [catalog-info.yaml](./catalog-info.yaml)**

---

## 🎯 **Documentation Style Guide**

### **Semantic Chunking Strategy**
All documentation follows semantic chunking principles for optimal vector DB retrieval:

#### **Header Hierarchy**
```markdown
# Main Topic (H1) - Always chunk boundary
## Section (H2) - Primary chunk boundary  
### Subsection (H3) - Secondary chunk boundary
#### Detail (H4) - Rarely used, keep with parent
```

#### **Chunking Rules**
- **Max chunk size**: 1000 tokens
- **Overlap**: 200 tokens between chunks
- **Split on**: `##`, `###`, `\n\n` (double newlines)
- **Preserve structure**: Always maintain header context

#### **Content Patterns**
```markdown
## Section Title

**Purpose**: Brief description of what this section covers
**Audience**: Which persona(s) this applies to
**Prerequisites**: What to read first

### Subsection

**Pattern**: Show the correct way first
**Anti-pattern**: Show common mistakes
**Example**: Real code examples
**Reference**: Link to related sections
```

### **Unicode & Character Encoding Guidelines**
- **Avoid Unicode Emojis**: Use ASCII characters only in scripts and documentation to prevent encoding issues on Windows.
- **Windows Compatibility**: Use `#`, `*`, `-`, `+` instead of Unicode symbols (🚀, ✅, ❌, 📊, etc.).
- **Script Output**: Use plain text status indicators: `[OK]`, `[ERROR]`, `[INFO]`, `[WARNING]`.
- **File Encoding**: Always use UTF-8 encoding for source files, but avoid Unicode characters in output.
- **Cross-Platform**: Ensure scripts work on Windows, Linux, and macOS without encoding issues.

---

## 🔑 **Critical API Patterns**

### **Namespace Operations: Canonical Naming**
**CRITICAL**: Endor Labs API requires canonical naming, not UUIDs.

#### **✅ CORRECT Pattern**
```python
# Use canonical hierarchical names for parent-child relationships
canonical_parent = f"{tenant_namespace}.{parent_name}"
# Example: "endor-solutions-tgowan.cockpit.integration-test-parent"

# Create child namespace
child_result = namespaces.create_namespace(client, canonical_parent, child_payload)
```

#### **❌ INCORRECT Pattern**
```python
# DON'T use UUIDs as parents - this will fail with 403 Forbidden
parent_namespace.uuid  # "68f3b2956795a2693a0f5bec" - FAILS!
```

#### **API Endpoint Reference**
- **POST `/namespaces`**: `parent_namespace` parameter requires canonical name format
- **GET `/namespaces/{uuid}`**: Requires `parent_namespace` parameter (canonical name)
- **PUT `/namespaces/{uuid}`**: Requires `parent_namespace` parameter (canonical name)

### **Permission Model**
- **Tenant-level operations**: Use tenant name (`endor-solutions-tgowan.cockpit`)
- **Hierarchy operations**: Use canonical parent names (`tenant.namespace.child`)
- **Cross-tenant operations**: Forbidden (403 Forbidden)

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

*This guide serves as the universal anchor for all AI agents working with Endor Cockpit. For persona-specific guidance, follow the routing links above.*
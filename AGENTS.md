# Endor Cockpit: AI Agent Integration Guide

> **Endor Cockpit**: Navigate the Endor Labs platform with tactical precision. This guide provides Rules of Engagement for AI agents piloting the SDK.

## 🚀 **Quick Start (30 seconds)**

### **IDE Integration Ready**
**CRITICAL**: This toolkit is designed for seamless integration with AI-powered development environments. The SDK provides:
- Type-safe API operations with comprehensive error handling
- Built-in security scanning capabilities
- Resource-oriented patterns for consistent operations
- Production-ready authentication and rate limiting

```python
# Initialize client (auto-authenticates via environment variables)
from endor_cockpit.api_client import APIClient
client = APIClient()

# List namespaces
from endor_cockpit.resources import namespace
namespaces = namespace.list_namespaces(client, "tenant.namespace")
```

**Workflow**: Initialize → Authenticate → Operate → Handle Errors

### **Critical Requirements**
- **Security**: Always run `endorctl scan` before code changes
- **API Understanding**: Check OpenAPI spec → Review docs → Validate implementation
- **Linting**: Max 88 chars/line, sorted imports, no trailing whitespace
- **Dependencies**: Pin exact versions, avoid `latest`
- **Environment**: Set `ENDOR_API`, `ENDOR_API_CREDENTIALS_KEY`, `ENDOR_API_CREDENTIALS_SECRET`
- **Python**: 3.11-3.13, test on 3.13
- **Return Types**: All functions return `Optional[Resource]` for consistency
- **Canonical Naming**: Use `tenant.namespace.child` format, never UUIDs in paths

---

## 📋 **Project Context**

**Endor Cockpit** is a production-ready Python SDK for AI-powered IDEs:
- **Purpose**: Integrate Endor Labs security platform with AI development tools
- **Data Classification**: Public (no PII handling)
- **Deployment**: Production environment, global region
- **Security**: Paramount importance
- **Architecture**: Resource-oriented SDK pattern

---

## 🔍 **API Understanding Workflow**
**CRITICAL**: Before making any model changes or API modifications, follow this workflow:

1. **Check Canonical OpenAPI Spec** (`external_docs/openapi-swagger.json`)
   - Verify field requirements and types
   - Understand which fields are required vs optional
   - Check for read-only fields and their behavior
   - Validate field masking implications

2. **Review External Documentation** (`external_docs/user-docs/`)
   - Understand business context and use cases
   - Learn about field masking and API behavior
   - Check for edge cases and special handling

3. **Validate Against Current Implementation**
   - Compare Pydantic models with OpenAPI spec
   - Test with both masked and unmasked API responses
   - Ensure backward compatibility

**Example Workflow**:
```bash
# 1. Check OpenAPI spec for field requirements
grep -A 20 "v1Meta" external_docs/openapi-swagger.json

# 2. Review user documentation for context
ls external_docs/user-docs/ | grep -i policy

# 3. Test current implementation
uv run python maneuvers/cleanup_test_policies.py --dry-run
```

**Automated Workflow**: Documentation and schema drift detection are automated via the [Unified Documentation & Schema Drift Workflow](docs/rules-of-engagement/docs-drift-workflow.md). This workflow:
- Automatically updates OpenAPI spec and user docs weekly
- Detects schema drift between API responses and Pydantic models
- Creates GitHub issues for new drifts
- Ensures documentation is fresh before drift detection

Run manually: `python scripts/unified_docs_workflow.py --all`

---

## 🏗️ **Development**

### **Project Structure**
```
endor_cockpit/
├── api_client.py          # Core API client
├── resources/            # Resource modules (namespaces, policies, etc.)
└── models/               # Pydantic data models
```

### **Code Standards**
- **Python**: 3.11-3.13, test on 3.13
- **Dependencies**: `requests==2.32.5`, `pydantic==2.12.3`
- **Tools**: `ruff`, `pytest`, `endorctl`

### **Function Pattern**
```python
def create_resource(
    client: APIClient,
    parent_namespace: str,
    payload: CreateResourcePayload
) -> Optional[Resource]:
    """Create resource with proper error handling."""
```

---

## 🚨 **Linting & CI Prevention**

### **Pre-Development Checklist**
- [ ] Line length ≤ 88 characters
- [ ] Imports sorted and unused removed
- [ ] No trailing whitespace or blank line whitespace
- [ ] F-strings only with placeholders
- [ ] Dependencies pinned (no `latest`)

### **Quick Linting Commands**
```bash
uv run ruff check .          # Check all issues
uv run ruff check . --fix    # Auto-fix issues
uv run ruff format .         # Format code
uv run pytest               # Test functionality
```

### **Common Fixes**
- **E501**: Break long lines with parentheses/backslashes
- **F401**: Remove unused imports
- **W291/W293**: Remove trailing/blank line whitespace

---

## 🔧 **Usage**

### **Client Initialization**
```python
from endor_cockpit.api_client import APIClient
client = APIClient()  # Auto-authenticates via env vars
```

### **Namespace Operations**
```python
from endor_cockpit.resources import namespace
from endor_cockpit.resources.namespace import CreateNamespacePayload

# List namespaces
all_namespaces = namespace.list_namespaces(client, "tenant-namespace")

# Create namespace (CRITICAL: Use canonical naming)
canonical_parent = f"{tenant_namespace}.{parent_name}"
payload = CreateNamespacePayload(meta=NamespaceMetaCreate(name="test", description="Agent created"))
created = namespace.create_namespace(client, canonical_parent, payload)
```

### **Namespace Traversal (Tenant-Wide Queries)**
**CRITICAL**: Use `traverse=True` for efficient tenant-wide queries across all namespaces.

```python
from endor_cockpit.resources import dependency_metadata, package_version, finding
from endor_cockpit.types import ListParameters

# Query all dependencies across entire tenant (single API call)
list_params = ListParameters(traverse=True)
all_deps = dependency_metadata.list_dependency_metadata(
    client, "tenant-namespace", list_params
)

# Query all package versions across tenant
packages = package_version.list_package_versions(
    client, "tenant-namespace", ListParameters(traverse=True)
)

# Query with filtering
private_deps = dependency_metadata.list_dependency_metadata(
    client, "tenant-namespace",
    ListParameters(traverse=True, filter="spec.dependency_data.public==false")
)
```

**Why traverse?**: Automatically queries all child namespaces recursively in a single API call. Much faster than manually iterating through namespaces. See [Namespace Traversal Guide](docs/rules-of-engagement/namespace-traversal.md) for details.

### **Critical Patterns**
- **✅ CORRECT**: Use canonical naming (`tenant.namespace.child`)
- **❌ WRONG**: Don't use UUIDs as parents (403 Forbidden)
- **Required**: `parent_namespace` parameter for all operations
- **Payloads**: Use Pydantic models for type safety
- **API Understanding**: Check OpenAPI spec → Review docs → Validate implementation

---

## 📊 **Resource Implementation Status**

### **Implementation Checklist**

#### ✅ **COMPLETED RESOURCES**
- **Project** - Implementation: ✅ | Documentation: ✅ | Tests: ✅
- **Finding** - Implementation: ✅ | Documentation: ✅ | Tests: ✅
- **Policy** - Implementation: ✅ | Documentation: ✅ | Tests: ✅
- **Namespace** - Implementation: ✅ | Documentation: ✅ | Tests: ✅
- **Repository** - Implementation: ✅ | Documentation: ✅ | Tests: ✅
- **RepositoryVersion** - Implementation: ✅ | Documentation: ✅ | Tests: ✅
- **PackageVersion** - Implementation: ✅ | Documentation: ✅ | Tests: ✅
- **ScanResult** - Implementation: ✅ | Documentation: ✅ | Tests: ✅

#### 🚧 **IMPLEMENTED (Tests Pending)**
- **DependencyMetadata** - Implementation: ✅ | Documentation: ✅ | Tests: ❌
- **LinterResult** - Implementation: ✅ | Documentation: ✅ | Tests: ❌
- **Metric** - Implementation: ✅ | Documentation: ✅ | Tests: ❌
- **User** - Implementation: ✅ | Documentation: ✅ | Tests: ❌ (API: GET only)
- **Installation** - Implementation: ✅ | Documentation: ✅ | Tests: ❌ (API: GET only)

### **Completion Criteria**
- **Implementation**: CRUD operations validated, model validated and a handful of attributes modeled correctly
- **Documentation**: Statements verified to match implementation and tests  
- **Tests**: Passes linter, unit tests provided and incorporated into CI

### **Status Legend**
- ✅ **COMPLETE**: All criteria met
- 🚧 **IN PROGRESS**: Implementation started
- ❌ **NOT STARTED**: No work begun
- 🚫 **BLOCKED**: Blocked by dependencies

---

## 🛠️ **LLM Tool Integration**

### **Available Resource Operations**

#### **Fully Supported (CRUD)**
- **Namespace**: `list_namespaces`, `create_namespace`, `get_namespace`, `update_namespace`, `delete_namespace`
- **Project**: `list_projects`, `create_project`, `get_project`, `update_project`, `delete_project`
- **Finding**: `list_findings`, `get_finding`, `create_finding`, `update_finding`, `delete_finding`
- **Policy**: `list_policies`, `create_policy`, `get_policy`, `update_policy`, `delete_policy`
- **Repository**: `list_repositories`, `get_repository` (CREATE/UPDATE/DELETE: API-limited, read-only)
- **RepositoryVersion**: `list_repository_versions`, `get_repository_version` (CREATE/UPDATE/DELETE: API-limited)
- **PackageVersion**: `list_package_versions`, `get_package_version`, `create_package_version`, `update_package_version`, `delete_package_version`
- **ScanResult**: `list_scan_results`, `get_scan_result`, `create_scan_result`, `update_scan_result`, `delete_scan_result`
- **DependencyMetadata**: `list_dependency_metadata`, `get_dependency_metadata`, `create_dependency_metadata`, `update_dependency_metadata`, `delete_dependency_metadata`
- **LinterResult**: `list_linter_results`, `get_linter_result`, `create_linter_result`, `update_linter_result`, `delete_linter_result`
- **Metric**: `list_metrics`, `get_metric`, `create_metric`, `update_metric`, `delete_metric`

#### **Read-Only (GET Only)**
- **User**: `list_users`, `get_user` (CREATE/UPDATE/DELETE: Managed by identity provider)
- **Installation**: `list_installations`, `get_installation` (CREATE/UPDATE/DELETE: Managed by platform integrations)

---

## 📚 **Reference Guides & Rules of Engagement**

### **Specialized Guides**
- **Namespace Traversal**: [docs/rules-of-engagement/namespace-traversal.md](docs/rules-of-engagement/namespace-traversal.md) - **Canonical pattern for tenant-wide queries**
- **Rego Policy Development**: [docs/rego_guide.md](docs/rego_guide.md) - Complete Rego reference
- **API Validation**: [docs/rules-of-engagement/api-validation.md](docs/rules-of-engagement/api-validation.md) - Pre-implementation validation
- **Troubleshooting**: [docs/rules-of-engagement/troubleshooting.md](docs/rules-of-engagement/troubleshooting.md) - Issue resolution patterns
- **Resource Implementation**: [docs/rules-of-engagement/resource-implementation.md](docs/rules-of-engagement/resource-implementation.md) - Implementation patterns

### **Operational Maneuvers**
Example scripts in `maneuvers/` directory demonstrate practical SDK usage patterns.

---

## 🔒 **Security**

### **Security-First Development**
- **Always scan**: `endorctl scan` before any code changes
- **Scan scenarios**: Package changes, first-party code, dependency updates
- **No PII**: This project handles no PII data
- **Secure logging**: Filter sensitive data from logs

### **API Security & Validation**
- **Canonical Spec First**: Always check `external_docs/openapi-swagger.json` before model changes
- **Field Masking Security**: Understand how field masking affects data validation
- **Input Validation**: Ensure Pydantic models match API specifications exactly
- **Backward Compatibility**: Changes must not break existing functionality

### **Environment Security**
- **Credentials**: Use environment variables ONLY
- **No hardcoded secrets**: All secrets via env vars
- **Secure logging**: No sensitive data in logs
- **Input validation**: Validate all inputs

---

## 🎯 **Quick Reference**

### **Essential Commands**
```bash (or powershell equivalent)
# Development workflow
uv run ruff check .          # Lint
uv run ruff format .         # Format  
uv run pytest               # Test
endorctl scan               # Security

# Environment setup
export ENDOR_API="https://api.endorlabs.com"
export ENDOR_API_CREDENTIALS_KEY="your-key"
export ENDOR_API_CREDENTIALS_SECRET="your-secret"
```

### **Essential Patterns**
- **Canonical naming**: `tenant.namespace.child` (not UUIDs)
- **Line length**: 88 characters max
- **Imports**: Sorted, no unused
- **Security**: Always scan before changes
- **Dependencies**: Pin exact versions

---

*This guide serves as the universal anchor for all AI agents working with Endor Cockpit.*

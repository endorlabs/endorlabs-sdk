# Finding Resource Deep-Dive

> **Comprehensive guide to Finding resources in Endor Labs platform**

<!-- RAG METADATA
resource_type: finding
sdk_module: src/endor_cockpit/resources/finding.py
last_reviewed: 2025-10-19
-->

## Architecture

<!-- ~500 tokens | Query: "What is finding architecture?" -->

### Resource Structure

Findings in Endor Labs represent security issues discovered in projects:

```
Namespace (tenant.namespace)
├── Project (repository-1)
│   ├── Finding (vulnerability-1) - SCA
│   ├── Finding (vulnerability-2) - SAST
│   └── Finding (secret-1) - SECRET
└── Project (repository-2)
    ├── Finding (compliance-1) - COMPLIANCE
    └── Finding (vulnerability-3) - SCA
```

### Core Concepts

- **Scan-generated**: Findings are created by security scans (SCA, SAST, SECRET, COMPLIANCE)
- **Project-scoped**: Findings belong to a specific project
- **Severity-based**: Findings have severity levels (CRITICAL, HIGH, MEDIUM, LOW)
- **Lifecycle management**: Findings can be dismissed, remediated, or ignored
- **Multi-category**: Findings can have multiple categories (vulnerability, security, CI/CD, etc.)
- **Ecosystem-aware**: Findings are associated with specific package ecosystems (NPM, PyPI, Maven, etc.)

### Lifecycle

```
Project → Scan → Finding → Remediation → Resolution
```

**Lifecycle States**:
- **Discovered**: Finding created by scan
- **Open**: Finding requires attention
- **Dismissed**: Finding marked as false positive
- **Remediated**: Finding fixed and verified
- **Resolved**: Finding no longer exists

---

## Data Model

<!-- ~800 tokens | Query: "What are finding data structures?" -->

### SDK Implementation

**Location**: `src/endor_cockpit/resources/finding.py:117-173`

```python
# Direct reference - see SDK for full definition
class Finding(BaseModel):
    uuid: str = Field(..., description="Unique identifier for the finding")
    meta: FindingMeta = Field(..., description="Finding metadata")
    spec: FindingSpec = Field(..., description="Finding specification")
    context: Optional[FindingContext] = Field(None, description="Finding context")
    tenant_meta: TenantMeta = Field(..., description="Tenant metadata")
```

### Core Properties

**FindingMeta** (`src/endor_cockpit/resources/finding.py:175-200`):
- `name`: Finding name/title
- `description`: Detailed finding description
- `tags`: General resource tags
- `create_time`, `created_by`: Creation metadata
- `update_time`, `updated_by`: Auto-managed timestamps

**FindingSpec** (`src/endor_cockpit/resources/finding.py:202-280`):
- `project_uuid`: Associated project UUID
- `level`: Severity level (CRITICAL, HIGH, MEDIUM, LOW)
- `finding_tags`: Finding-specific tags
- `dismiss`: Dismissal status
- `remediation`: Remediation guidance
- `finding_metadata`: Scan-discovered metadata

**FindingContext** (`src/endor_cockpit/resources/finding.py:282-320`):
- `tags`: Contextual tags
- `annotations`: Additional context data

### Finding Types

**SCA (Software Composition Analysis)**:
- **Purpose**: Dependency vulnerability detection
- **Scope**: Third-party libraries and packages
- **Examples**: Known CVEs in dependencies

**SAST (Static Application Security Testing)**:
- **Purpose**: Code analysis for vulnerabilities
- **Scope**: Source code analysis
- **Examples**: SQL injection, XSS vulnerabilities

**Secrets Detection**:
- **Purpose**: Hardcoded credentials and keys
- **Scope**: Code and configuration files
- **Examples**: API keys, passwords, tokens

**Compliance Findings**:
- **Purpose**: Regulatory compliance violations
- **Scope**: Policy and configuration compliance
- **Examples**: GDPR violations, security policy violations

### Finding Categories

**Location**: `src/endor_cockpit/resources/finding.py:117-173`

```python
class FindingCategory(FlexibleEnum):
    UNSPECIFIED = "FINDING_CATEGORY_UNSPECIFIED"
    VULNERABILITY = "FINDING_CATEGORY_VULNERABILITY"
    SUPPLY_CHAIN = "FINDING_CATEGORY_SUPPLY_CHAIN"
    LICENSE_RISK = "FINDING_CATEGORY_LICENSE_RISK"
    SCPM = "FINDING_CATEGORY_SCPM"
    SECURITY = "FINDING_CATEGORY_SECURITY"
    OPERATIONAL = "FINDING_CATEGORY_OPERATIONAL"
    SECRETS = "FINDING_CATEGORY_SECRETS"
    MALWARE = "FINDING_CATEGORY_MALWARE"
    CICD = "FINDING_CATEGORY_CICD"
    TOOLS = "FINDING_CATEGORY_TOOLS"
    GHACTIONS = "FINDING_CATEGORY_GHACTIONS"
    CONTAINER = "FINDING_CATEGORY_CONTAINER"
    SAST = "FINDING_CATEGORY_SAST"
    SCA = "FINDING_CATEGORY_SCA"
    AI_MODELS = "FINDING_CATEGORY_AI_MODELS"
```

**Key Insights**:
- **Multi-category**: Findings can have multiple categories
- **Security Focus**: Most categories relate to security concerns
- **Tool Integration**: Categories reflect different analysis tools
- **Lifecycle Coverage**: Categories cover entire development lifecycle

### Analysis Methods

**Location**: `src/endor_cockpit/resources/finding.py:117-173`

```python
class AnalysisMethod(FlexibleEnum):
    UNSPECIFIED = "SYSTEM_EVALUATION_METHOD_UNSPECIFIED"
    DEFINITION_VULNERABILITIES = "SYSTEM_EVALUATION_METHOD_DEFINITION_VULNERABILITIES"
    DEFINITION_POLICIES = "SYSTEM_EVALUATION_METHOD_DEFINITION_POLICIES"
    SAST = "SYSTEM_EVALUATION_METHOD_SAST"
    SCA = "SYSTEM_EVALUATION_METHOD_SCA"
    SECRETS = "SYSTEM_EVALUATION_METHOD_SECRETS"
    CONTAINER = "SYSTEM_EVALUATION_METHOD_CONTAINER"
    INFRASTRUCTURE = "SYSTEM_EVALUATION_METHOD_INFRASTRUCTURE"
```

**Key Insights**:
- **Method Tracking**: How the finding was discovered
- **Tool Attribution**: Which analysis tool found the issue
- **Analysis Type**: Different types of security analysis

### Ecosystems

**Location**: `src/endor_cockpit/resources/finding.py:117-173`

```python
class Ecosystem(FlexibleEnum):
    UNSPECIFIED = "ECOSYSTEM_UNSPECIFIED"
    NPM = "ECOSYSTEM_NPM"
    PYPI = "ECOSYSTEM_PYPI"
    MAVEN = "ECOSYSTEM_MAVEN"
    NUGET = "ECOSYSTEM_NUGET"
    RUBYGEMS = "ECOSYSTEM_RUBYGEMS"
    GO = "ECOSYSTEM_GO"
    RUST = "ECOSYSTEM_RUST"
    DOCKER = "ECOSYSTEM_DOCKER"
    DEBIAN = "ECOSYSTEM_DEBIAN"
    UBUNTU = "ECOSYSTEM_UBUNTU"
    ALPINE = "ECOSYSTEM_ALPINE"
    REDHAT = "ECOSYSTEM_REDHAT"
```

**Key Insights**:
- **Package Ecosystem**: Which package ecosystem the finding relates to
- **Language Support**: Coverage of major programming languages
- **Platform Coverage**: Operating system and container ecosystems

---

## Operations

<!-- ~600 tokens | Query: "How to work with findings?" -->

### CRUD Operations

**Location**: `src/endor_cockpit/resources/finding.py:400-628`

#### List Findings
```python
from endor_cockpit.resources import finding

# List all findings in namespace
findings = finding.list_findings(client, namespace)

# List findings for specific project
findings = finding.list_findings(client, namespace, project_uuid="project-123")
```

#### Get Finding
```python
# Get specific finding
finding_obj = finding.get_finding(client, namespace, finding_uuid)
```

#### Update Finding
```python
from endor_cockpit.resources.finding import UpdateFindingPayload, FindingSpec

# Update finding tags
payload = UpdateFindingPayload(
    spec=FindingSpec(finding_tags=["reviewed", "false-positive"])
)
updated_finding = finding.update_finding(
    client, namespace, finding_uuid, payload, "spec.finding_tags"
)

# Dismiss finding
payload = UpdateFindingPayload(
    spec=FindingSpec(dismiss=True)
)
updated_finding = finding.update_finding(
    client, namespace, finding_uuid, payload, "spec.dismiss"
)
```

### Mutable vs Immutable Fields

**MUTABLE FIELDS** (can be updated via PATCH):
- `meta.tags`: General resource tags
- `spec.finding_tags`: Finding-specific tags
- `spec.dismiss`: Dismissal status
- `spec.remediation`: Remediation guidance
- `context.tags`: Contextual tags

**IMMUTABLE FIELDS** (read-only, managed by API):
- `uuid`: Unique identifier (set at creation)
- `meta.name`: Finding name (set by scan)
- `spec.level`: Severity level (set by scan)
- `spec.project_uuid`: Associated project (set at creation)
- `spec.finding_metadata`: Scan-discovered metadata
- `tenant_meta.namespace`: Namespace assignment

---

## Relationships

<!-- ~400 tokens | Query: "How do findings relate to other resources?" -->

### Project Relationship
- **One-to-Many**: Project → Findings
- **Required**: Every finding must belong to a project
- **Access**: Findings are accessed through project context

### Namespace Relationship
- **Hierarchical**: Namespace → Projects → Findings
- **Scoped**: Findings inherit namespace context
- **Isolation**: Findings are isolated by namespace

### Scan Relationship
- **Generated by**: Findings are created by security scans
- **Scan types**: SCA, SAST, SECRET, COMPLIANCE scans
- **Metadata**: Scan information stored in `finding_metadata`

---

## Common Issues

<!-- ~500 tokens | Query: "What are common finding issues?" -->

### API Payload Structure
- **Issue**: `UpdateFindingPayload` requires `meta` and `context` fields, not just `spec`
- **Solution**: Include complete payload structure with current finding data
- **Reference**: `src/endor_cockpit/resources/finding.py:571-596`

### Field Validation
- **Issue**: `FindingSpec` model requires `project_uuid` and `level` fields which are immutable
- **Solution**: Use current finding data to create valid update payloads
- **Reference**: `src/endor_cockpit/resources/finding.py:202-280`

### Schema Drift
- **Issue**: API responses may contain unknown fields
- **Solution**: Schema drift detection logs warnings for unknown fields
- **Reference**: `src/endor_cockpit/resources/finding.py:36-50`

---

## Testing Patterns

<!-- ~300 tokens | Query: "How to test findings?" -->

### Unit Testing
```python
def test_finding_operations():
    # Test finding retrieval
    finding = finding.get_finding(client, namespace, finding_uuid)
    assert finding is not None
    
    # Test finding updates
    payload = UpdateFindingPayload(
        spec=FindingSpec(finding_tags=["test-tag"])
    )
    updated = finding.update_finding(
        client, namespace, finding_uuid, payload, "spec.finding_tags"
    )
    assert updated.spec.finding_tags == ["test-tag"]
```

### Integration Testing
```python
def test_finding_lifecycle():
    # List findings
    findings = finding.list_findings(client, namespace)
    assert len(findings) > 0
    
    # Update finding
    test_finding = findings[0]
    payload = UpdateFindingPayload(
        spec=FindingSpec(dismiss=True)
    )
    updated = finding.update_finding(
        client, namespace, test_finding.uuid, payload, "spec.dismiss"
    )
    assert updated.spec.dismiss == True
```

---

## Troubleshooting

<!-- ~400 tokens | Query: "How to troubleshoot finding issues?" -->

### Issue: Finding Not Found (404 Errors)

**Date Discovered**: 2025-10-19  

**Symptoms**: 
- 404 errors when accessing findings
- Finding UUID incorrect or finding deleted
- Cross-namespace finding access fails

**Root Cause**: 
- Finding UUID incorrect or finding deleted
- Attempting cross-namespace operations
- Finding moved to different namespace

**Solution**: 
```python
# ❌ INCORRECT - Wrong UUID or namespace
finding = finding.get_finding(client, "wrong-namespace", finding_uuid)

# ✅ CORRECT - Verify UUID and namespace
finding = finding.get_finding(client, "correct-namespace", finding_uuid)
```

**Prevention**: Always verify finding UUID and namespace before operations.

---

### Issue: Update Failures (Validation Errors)

**Date Discovered**: 2025-10-19  

**Symptoms**: 
- Validation errors when updating findings
- "Missing required fields" errors
- PATCH requests fail with 400 Bad Request

**Root Cause**: 
- Missing required fields in `UpdateFindingPayload`
- Incomplete payload structure
- Missing `meta` and `context` fields

**Solution**: 
```python
# ❌ INCORRECT - Missing required fields
payload = UpdateFindingPayload(
    spec=FindingSpec(dismiss=True)
)

# ✅ CORRECT - Include complete payload structure
payload = UpdateFindingPayload(
    meta=FindingMeta(
        name=current_finding.meta.name,
        description=current_finding.meta.description
    ),
    context=FindingContext(
        project_uuid=current_finding.context.project_uuid,
        level=current_finding.context.level
    ),
    spec=FindingSpec(dismiss=True)
)
```

**Prevention**: Always include complete payload structure with current finding data.

---

### Issue: Field Mutability Violations

**Date Discovered**: 2025-10-19  

**Symptoms**: 
- Attempts to update immutable fields fail
- "Field is read-only" errors
- Update operations rejected

**Root Cause**: 
- Trying to update fields marked as immutable
- Attempting to change system-managed fields
- Violating field mutability rules

**Solution**: 
```python
# ❌ INCORRECT - Trying to update immutable fields
payload = UpdateFindingPayload(
    spec=FindingSpec(
        project_uuid="new-project-uuid",  # IMMUTABLE
        level="CRITICAL"                 # IMMUTABLE
    )
)

# ✅ CORRECT - Only update mutable fields
payload = UpdateFindingPayload(
    spec=FindingSpec(
        finding_tags=["new-tag"],       # MUTABLE
        dismiss=True,                    # MUTABLE
        remediation="Fixed issue"        # MUTABLE
    )
)
```

**Prevention**: Only update mutable fields: `finding_tags`, `dismiss`, `remediation`, `tags`.

---

### Issue: Schema Drift Warnings

**Date Discovered**: 2025-10-19  

**Symptoms**: 
- Warnings about unknown fields in API responses
- "Unknown field detected" log messages
- Schema validation warnings

**Root Cause**: 
- API evolution adding new fields
- Model fields not updated to match API
- New finding metadata fields

**Solution**: 
```python
# Schema drift detection automatically logs warnings
# Update models to include new fields or ignore warnings
# Check logs for specific unknown fields
```

**Prevention**: Monitor schema drift warnings and update models when needed.

---

### Issue: Finding List Empty Despite Existing Findings

**Date Discovered**: 2025-10-19  

**Symptoms**: 
- `list_findings()` returns empty list
- `endorctl api list -r Finding` shows findings exist
- SDK vs CLI discrepancy

**Root Cause**: 
- Different endpoint usage between SDK and CLI
- Authentication scope differences
- Response parsing differences

**Solution**: 
```python
# Verify endpoint and authentication
findings = finding.list_findings(client, namespace)
if not findings:
    # Check authentication and namespace
    print("No findings found - check namespace and authentication")
```

**Prevention**: Verify namespace and authentication before operations.

---

## Related Resources

- **[Project Resource](./project.md)**: Finding source projects
- **[Namespace Resource](./namespaces.md)**: Finding parent namespaces
- **[Policy Resource](./policies.md)**: Finding-related policies
- **[SDK Reference](../agents/AGENT_GUIDE.md)**: Complete SDK usage guide
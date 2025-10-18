# Finding Resource Deep-Dive

> **Comprehensive guide to security findings in Endor Labs platform**

## 🔍 **Finding Types**

### **SCA (Software Composition Analysis)**
- **Purpose**: Dependency vulnerability detection
- **Scope**: Third-party libraries and packages
- **Examples**: Known CVEs in dependencies

### **SAST (Static Application Security Testing)**
- **Purpose**: Code analysis for vulnerabilities
- **Scope**: Source code analysis
- **Examples**: SQL injection, XSS vulnerabilities

### **Secrets Detection**
- **Purpose**: Hardcoded credentials and keys
- **Scope**: Code and configuration files
- **Examples**: API keys, passwords, tokens

### **Compliance Findings**
- **Purpose**: Regulatory compliance violations
- **Scope**: Policy and configuration compliance
- **Examples**: GDPR violations, security policy violations

---

## 📊 **Finding Data Model**

### **Core Properties**
```python
class Finding(BaseModel):
    uuid: str                    # Unique identifier
    type: FindingType           # SCA, SAST, SECRET, COMPLIANCE
    severity: Severity          # CRITICAL, HIGH, MEDIUM, LOW
    status: Status              # OPEN, RESOLVED, IGNORED
    project_uuid: str          # Source project UUID
    namespace_uuid: str        # Parent namespace UUID
    created_at: datetime        # Creation timestamp
    updated_at: datetime        # Last update timestamp
```

### **Finding Details**
```python
class FindingDetails(BaseModel):
    title: str                  # Finding title
    description: str           # Detailed description
    file_path: str             # File where finding was found
    line_number: int           # Line number in file
    code_snippet: str          # Relevant code snippet
    remediation: str           # Remediation guidance
```

### **Severity Levels**
```python
class Severity(str, Enum):
    CRITICAL = "CRITICAL"      # Immediate action required
    HIGH = "HIGH"              # High priority
    MEDIUM = "MEDIUM"          # Medium priority
    LOW = "LOW"                # Low priority
```

### **Status Types**
```python
class Status(str, Enum):
    OPEN = "OPEN"              # New finding
    RESOLVED = "RESOLVED"      # Fixed
    IGNORED = "IGNORED"        # Intentionally ignored
    FALSE_POSITIVE = "FALSE_POSITIVE"  # Incorrect detection
```

---

## 🔧 **Finding Operations**

### **List Findings**
```python
def list_findings(
    client: APIClient, 
    namespace_uuid: str,
    severity: Optional[Severity] = None,
    status: Optional[Status] = None,
    finding_type: Optional[FindingType] = None
) -> List[Finding]:
    """List findings with optional filters."""
    # Implementation details
```

### **Get Finding**
```python
def get_finding(client: APIClient, finding_uuid: str) -> Optional[Finding]:
    """Get a specific finding by UUID."""
    # Implementation details
```

### **Update Finding Status**
```python
def update_finding_status(
    client: APIClient, 
    finding_uuid: str, 
    status: Status,
    comment: Optional[str] = None
) -> Optional[Finding]:
    """Update finding status."""
    # Implementation details
```

### **Bulk Update Findings**
```python
def bulk_update_findings(
    client: APIClient, 
    finding_uuids: List[str], 
    status: Status,
    comment: Optional[str] = None
) -> List[Finding]:
    """Bulk update multiple findings."""
    # Implementation details
```

---

## 🔍 **Finding Analysis**

### **Risk Assessment**
```python
def assess_finding_risk(finding: Finding) -> RiskLevel:
    """Assess risk level of a finding."""
    risk_factors = {
        "severity": finding.severity,
        "exploitability": assess_exploitability(finding),
        "business_impact": assess_business_impact(finding),
        "remediation_effort": assess_remediation_effort(finding)
    }
    
    return calculate_risk_score(risk_factors)
```

### **Finding Correlation**
```python
def correlate_findings(findings: List[Finding]) -> List[FindingGroup]:
    """Correlate related findings."""
    groups = []
    
    for finding in findings:
        # Find similar findings
        similar = find_similar_findings(finding, findings)
        if similar:
            groups.append(FindingGroup(
                primary_finding=finding,
                related_findings=similar,
                correlation_type=determine_correlation_type(finding, similar)
            ))
    
    return groups
```

### **Trend Analysis**
```python
def analyze_finding_trends(
    findings: List[Finding], 
    time_period: TimePeriod
) -> FindingTrends:
    """Analyze finding trends over time."""
    trends = FindingTrends()
    
    # Group by time period
    time_groups = group_findings_by_time(findings, time_period)
    
    # Calculate trends
    trends.severity_distribution = calculate_severity_distribution(time_groups)
    trends.finding_types = calculate_type_distribution(time_groups)
    trends.remediation_rate = calculate_remediation_rate(time_groups)
    
    return trends
```

---

## 🚨 **Common Issues**

### **False Positives**
**Cause**: Incorrect detection by security tools
**Solution**: Mark as false positive and document reason

```python
# Mark finding as false positive
finding = update_finding_status(
    client, 
    finding_uuid, 
    Status.FALSE_POSITIVE,
    comment="False positive: Code is not reachable in production"
)
```

### **Duplicate Findings**
**Cause**: Same vulnerability detected multiple times
**Solution**: Correlate and group duplicate findings

```python
# Find and group duplicate findings
duplicates = find_duplicate_findings(findings)
for group in duplicates:
    # Keep primary finding, mark others as duplicates
    primary = group[0]
    for duplicate in group[1:]:
        update_finding_status(
            client, 
            duplicate.uuid, 
            Status.IGNORED,
            comment=f"Duplicate of {primary.uuid}"
        )
```

### **Remediation Tracking**
**Cause**: Difficulty tracking remediation progress
**Solution**: Use status updates and comments

```python
# Track remediation progress
finding = update_finding_status(
    client, 
    finding_uuid, 
    Status.OPEN,
    comment="Remediation in progress: PR #123 submitted"
)
```

---

## 🧪 **Testing Patterns**

### **Finding Creation Testing**
```python
def test_finding_creation(api_client, project_uuid):
    """Test finding creation."""
    finding = create_finding(api_client, {
        "type": "SAST",
        "severity": "HIGH",
        "title": "SQL Injection Vulnerability",
        "description": "Potential SQL injection in user input",
        "file_path": "src/api/users.py",
        "line_number": 42
    })
    
    assert finding is not None
    assert finding.type == "SAST"
    assert finding.severity == "HIGH"
```

### **Finding Filtering Testing**
```python
def test_finding_filtering(api_client, namespace_uuid):
    """Test finding filtering."""
    # Test severity filtering
    high_findings = list_findings(
        api_client, 
        namespace_uuid, 
        severity=Severity.HIGH
    )
    assert all(f.severity == Severity.HIGH for f in high_findings)
    
    # Test status filtering
    open_findings = list_findings(
        api_client, 
        namespace_uuid, 
        status=Status.OPEN
    )
    assert all(f.status == Status.OPEN for f in open_findings)
```

### **Finding Correlation Testing**
```python
def test_finding_correlation(api_client, namespace_uuid):
    """Test finding correlation."""
    findings = list_findings(api_client, namespace_uuid)
    correlated = correlate_findings(findings)
    
    assert len(correlated) > 0
    for group in correlated:
        assert len(group.related_findings) > 0
        assert group.correlation_type is not None
```

---

## 📚 **Related Resources**

- **[Projects](./projects.md)** - Project resource deep-dive
- **[Scans](./scans.md)** - Scan resource deep-dive
- **[Policies](./policies.md)** - Policy resource deep-dive
- **[Relationships](./relationships.md)** - Resource relationships

---

*This resource guide provides comprehensive information about security findings in the Endor Labs platform.*

# Endor Data Model Architecture

> **Deep-dive into Endor Labs data model and resource relationships**

## 🏗️ **Endor Data Model Overview**

### **Core Resources**
- **Namespaces**: Hierarchical containers for organizing resources
- **Projects**: Code repositories and applications
- **Findings**: Security vulnerabilities and compliance issues
- **Policies**: Security rules and compliance requirements
- **Scans**: Security analysis runs and results

### **Resource Hierarchy**
```
Tenant (endor-solutions-tgowan.cockpit)
├── Namespace (tenant.namespace)
│   ├── Project (repository)
│   │   ├── Finding (vulnerability)
│   │   └── Scan (analysis run)
│   ├── Policy (security rule)
│   └── Secret (credential)
└── Namespace (tenant.other-namespace)
    └── ...
```

---

## 📁 **Namespace Architecture**

### **Canonical Naming System**
**CRITICAL**: Endor Labs uses canonical hierarchical naming, not UUIDs.

#### **Naming Convention**
```
{tenant}.{namespace}.{child}.{grandchild}
```

#### **Examples**
```
endor-solutions-tgowan.cockpit                    # Tenant
endor-solutions-tgowan.cockpit.integration-test  # Namespace
endor-solutions-tgowan.cockpit.integration-test.child  # Child namespace
```

#### **Permission Model**
- **Tenant-level**: Full access to tenant resources
- **Namespace-level**: Access to namespace and children
- **Cross-tenant**: Forbidden (403 Forbidden)

### **Namespace Operations**
```python
# All operations require parent_namespace parameter
def list_namespaces(client: APIClient, parent_namespace: str) -> List[Namespace]
def get_namespace(client: APIClient, parent_namespace: str, namespace_uuid: str) -> Optional[Namespace]
def create_namespace(client: APIClient, parent_namespace: str, payload: CreateNamespacePayload) -> Optional[Namespace]
def update_namespace(client: APIClient, parent_namespace: str, namespace_uuid: str, payload: UpdateNamespacePayload) -> Optional[Namespace]
def delete_namespace(client: APIClient, parent_namespace: str, namespace_uuid: str) -> bool
```

### **Namespace Data Model**
```python
class NamespaceMeta(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field("")  # Empty descriptions allowed
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class Namespace(BaseModel):
    uuid: str
    meta: NamespaceMeta
```

---

## 🔍 **Findings Architecture**

### **Finding Types**
- **SCA (Software Composition Analysis)**: Dependency vulnerabilities
- **SAST (Static Application Security Testing)**: Code analysis
- **Secrets**: Hardcoded credentials and keys
- **Compliance**: Policy violations

### **Finding Lifecycle**
```
Scan → Finding → Triage → Remediation → Verification
```

### **Finding Data Model**
```python
class Finding(BaseModel):
    uuid: str
    type: FindingType  # SCA, SAST, SECRET, COMPLIANCE
    severity: Severity  # CRITICAL, HIGH, MEDIUM, LOW
    status: Status      # OPEN, RESOLVED, IGNORED
    project_uuid: str
    namespace_uuid: str
    created_at: datetime
    updated_at: datetime
```

---

## 🛡️ **Policy Architecture**

### **Policy Types**
- **Security**: Vulnerability detection rules
- **Compliance**: Regulatory requirement rules
- **Access**: Permission and authorization rules

### **Policy Structure**
```python
class Policy(BaseModel):
    uuid: str
    name: str
    description: str
    type: PolicyType
    rules: List[PolicyRule]
    namespace_uuid: str
    created_at: datetime
    updated_at: datetime

class PolicyRule(BaseModel):
    action: str        # ALLOW, DENY, WARN
    condition: str     # Rule condition
    effect: str        # Rule effect
```

### **Policy Application**
- **Namespace-scoped**: Applied to specific namespace and children
- **Hierarchical**: Child namespaces inherit parent policies
- **Override**: Child policies can override parent policies

---

## 🔐 **Security Architecture**

### **Authentication**
- **API Keys**: Primary authentication method
- **Service Accounts**: Automated access with expiration
- **SSO Integration**: Enterprise authentication support

### **Authorization**
- **Permission-based**: Granular permissions per resource type
- **Namespace-scoped**: Access limited to allowed namespaces
- **Hierarchical**: Parent namespace access includes children

### **Security Scanning**
- **Pre-commit**: Automated scanning before code changes
- **CI/CD Integration**: Continuous security monitoring
- **Dependency Scanning**: Third-party vulnerability detection

---

## 📊 **Scan Architecture**

### **Scan Types**
- **Full Scan**: Comprehensive security analysis
- **Incremental**: Changes since last scan
- **Targeted**: Specific vulnerability types

### **Scan Lifecycle**
```
Trigger → Scan → Analysis → Findings → Reporting
```

### **Scan Data Model**
```python
class Scan(BaseModel):
    uuid: str
    type: ScanType
    target_namespace: str
    status: ScanStatus  # PENDING, RUNNING, COMPLETED, FAILED
    findings: List[Finding]
    created_at: datetime
    completed_at: Optional[datetime]
```

---

## 🔄 **Integration Architecture**

### **SCM Integration**
- **GitHub**: Repository access and webhook integration
- **GitLab**: Repository access and webhook integration
- **Bitbucket**: Repository access and webhook integration

### **CI/CD Integration**
- **GitHub Actions**: Automated security scanning
- **GitLab CI**: Pipeline integration
- **Jenkins**: Build system integration

### **API Integration**
- **REST API**: Primary integration method
- **Webhooks**: Real-time event notifications
- **GraphQL**: Advanced querying capabilities

---

## 📈 **Performance Architecture**

### **Rate Limiting**
- **API Limits**: Requests per minute/hour
- **Retry Logic**: Exponential backoff for rate limits
- **Caching**: Response caching for frequently accessed data

### **Scalability**
- **Horizontal Scaling**: Multiple API instances
- **Load Balancing**: Request distribution
- **Caching**: Redis for session and data caching

### **Monitoring**
- **Metrics**: Performance and usage metrics
- **Logging**: Structured logging for debugging
- **Alerting**: Automated issue detection

---

## 🎯 **Best Practices**

### **Resource Design**
- **Idempotent Operations**: Safe to retry operations
- **Declarative Configuration**: Infrastructure as code
- **Immutable Resources**: Version-controlled changes

### **Security Design**
- **Least Privilege**: Minimal required permissions
- **Defense in Depth**: Multiple security layers
- **Audit Logging**: Comprehensive activity tracking

### **Performance Design**
- **Efficient Queries**: Optimized API calls
- **Caching Strategy**: Appropriate data caching
- **Error Handling**: Graceful failure handling

---

## 📚 **Related Documentation**

- **[API Quirks](./api-quirks.md)**: Known API discrepancies
- **[Testing Guide](./testing-guide.md)**: Architecture testing patterns
- **[Contributing Guide](./contributing.md)**: Extending the architecture

---

*This architecture guide provides the foundation for understanding Endor Labs data model and building effective integrations.*

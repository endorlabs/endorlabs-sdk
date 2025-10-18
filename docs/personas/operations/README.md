# Operations Persona Guide

> **Namespace Administration, Integrations, and System Management**

## 🚀 **Quick Start**

### **5-Minute Setup**
1. **Environment**: Set `ENDOR_API`, `ENDOR_API_CREDENTIALS_KEY`, `ENDOR_API_CREDENTIALS_SECRET`
2. **Verify Access**: `endorctl scan --path . --namespace "your-namespace"`
3. **Test Connection**: Create a test namespace to verify permissions
4. **Review Hierarchy**: List existing namespaces to understand structure

### **Common Operations**
```bash
# List all namespaces
endorctl namespaces list --namespace "your-tenant"

# Create namespace hierarchy
endorctl namespaces create --parent "tenant.namespace" --name "new-namespace"

# Configure integration
endorctl integrations configure --type github --namespace "tenant.namespace"
```

---

## 📋 **Primary Responsibilities**

### **Namespace Management**
- **Hierarchy Administration**: Create and manage namespace hierarchies
- **Permission Management**: Configure access controls and permissions
- **Resource Organization**: Organize projects and resources within namespaces
- **Lifecycle Management**: Handle namespace creation, updates, and deletion

### **Integration Configuration**
- **SCM Integration**: Configure GitHub, GitLab, Bitbucket connections
- **CI/CD Integration**: Set up automated security scanning
- **Webhook Configuration**: Configure real-time event notifications
- **API Token Management**: Manage service accounts and API tokens

### **System Administration**
- **User Management**: Configure SSO and user access
- **Monitoring**: Set up system monitoring and alerting
- **Troubleshooting**: Diagnose and resolve system issues
- **Automation**: Create scripts and workflows for common tasks

---

## 📚 **Documentation Map**

### **Core Operations**
- **[Namespace Administration](./namespace-admin.md)** - 📋 SCAFFOLD
- **[Integrations](./integrations.md)** - 📋 SCAFFOLD
- **[Troubleshooting](./troubleshooting.md)** - 📋 SCAFFOLD

### **Authentication & Security**
- **[SSO Configuration](./sso-auth.md)** - 📋 SCAFFOLD
- **[Token Management](./token-management.md)** - 📋 SCAFFOLD

### **Automation & Scaling**
- **[Automation Patterns](./automation.md)** - 📋 SCAFFOLD

---

## 🎯 **Common Tasks**

### **1. Create New Namespace Hierarchy**
**Scenario**: Setting up a new project with multiple environments

**Steps**:
1. **Plan Structure**: Design namespace hierarchy (dev, staging, prod)
2. **Create Namespaces**: Use canonical naming for parent-child relationships
3. **Configure Permissions**: Set up appropriate access controls
4. **Test Access**: Verify namespace operations work correctly

**Example**:
```bash
# Create development namespace
endorctl namespaces create --parent "tenant.projects" --name "myapp-dev"

# Create staging namespace
endorctl namespaces create --parent "tenant.projects" --name "myapp-staging"

# Create production namespace
endorctl namespaces create --parent "tenant.projects" --name "myapp-prod"
```

### **2. Configure GitHub Integration**
**Scenario**: Connecting a GitHub repository for automated security scanning

**Steps**:
1. **Repository Access**: Configure GitHub app or personal access token
2. **Webhook Setup**: Configure repository webhooks for real-time scanning
3. **Namespace Mapping**: Map repository to appropriate namespace
4. **Test Integration**: Verify webhook delivery and scanning

**Example**:
```bash
# Configure GitHub integration
endorctl integrations configure \
  --type github \
  --namespace "tenant.projects.myapp-dev" \
  --repository "owner/repo" \
  --webhook-url "https://api.endorlabs.com/webhooks/github"
```

### **3. Troubleshoot Failed Scans**
**Scenario**: Security scans are failing or not running

**Steps**:
1. **Check Logs**: Review scan logs for error messages
2. **Verify Permissions**: Ensure API key has required permissions
3. **Test Connectivity**: Verify network connectivity to Endor Labs API
4. **Check Configuration**: Validate integration settings

**Example**:
```bash
# Check scan status
endorctl scans list --namespace "tenant.projects.myapp-dev"

# View scan logs
endorctl scans logs --scan-id "scan-uuid"

# Test connectivity
endorctl test-connection --namespace "tenant.projects.myapp-dev"
```

---

## 🔧 **Administrative Tools**

### **Namespace Management**
- **Hierarchy Visualization**: View namespace tree structure
- **Permission Auditing**: Review access controls and permissions
- **Resource Inventory**: List all resources within namespaces
- **Cleanup Operations**: Remove unused or obsolete resources

### **Integration Management**
- **Connection Testing**: Verify integration connectivity
- **Configuration Backup**: Backup integration settings
- **Monitoring**: Track integration health and performance
- **Troubleshooting**: Diagnose integration issues

### **User Management**
- **SSO Configuration**: Set up single sign-on authentication
- **Permission Assignment**: Assign roles and permissions
- **Access Auditing**: Review user access and activity
- **Account Lifecycle**: Handle user onboarding and offboarding

---

## 🚨 **Troubleshooting Guide**

### **Common Issues**

#### **Namespace Creation Failures**
- **403 Forbidden**: Check if using canonical naming instead of UUIDs
- **Permission Denied**: Verify API key has required permissions
- **Invalid Parent**: Ensure parent namespace exists and is accessible

#### **Integration Failures**
- **Webhook Delivery**: Check webhook URL and authentication
- **Repository Access**: Verify repository permissions and visibility
- **Network Connectivity**: Test network connectivity to Endor Labs API

#### **Authentication Issues**
- **SSO Configuration**: Verify SSO provider settings
- **Token Expiration**: Check API token expiration and renewal
- **Permission Scope**: Ensure tokens have required permissions

### **Debugging Tools**
- **Log Analysis**: Review system logs for error messages
- **Connection Testing**: Test API connectivity and authentication
- **Permission Verification**: Check user and service account permissions
- **Integration Testing**: Verify integration configuration and connectivity

---

## 📊 **Monitoring & Alerting**

### **System Health**
- **API Availability**: Monitor Endor Labs API availability
- **Integration Health**: Track integration status and performance
- **Resource Usage**: Monitor namespace and resource utilization
- **Error Rates**: Track and alert on error rates and failures

### **Security Monitoring**
- **Scan Results**: Monitor security scan results and findings
- **Policy Violations**: Track policy violations and compliance issues
- **Access Patterns**: Monitor user access and activity patterns
- **Anomaly Detection**: Identify unusual or suspicious activity

---

## 🎯 **Best Practices**

### **Namespace Design**
- **Hierarchical Structure**: Use logical hierarchy for organization
- **Naming Conventions**: Follow consistent naming patterns
- **Permission Boundaries**: Align namespaces with permission boundaries
- **Lifecycle Management**: Plan for namespace lifecycle and cleanup

### **Integration Management**
- **Security First**: Prioritize security in integration configuration
- **Monitoring**: Set up comprehensive monitoring and alerting
- **Documentation**: Document integration configurations and procedures
- **Testing**: Regularly test integration functionality

### **User Management**
- **Least Privilege**: Grant minimal required permissions
- **Regular Auditing**: Regularly review and audit user access
- **Lifecycle Management**: Handle user onboarding and offboarding
- **Security Awareness**: Educate users on security best practices

---

## 📚 **Related Documentation**

- **[Namespace Administration](./namespace-admin.md)** - Detailed namespace management
- **[Integrations](./integrations.md)** - Integration configuration and management
- **[Troubleshooting](./troubleshooting.md)** - Common issues and solutions
- **[SSO Configuration](./sso-auth.md)** - Single sign-on setup
- **[Token Management](./token-management.md)** - API token lifecycle
- **[Automation](./automation.md)** - Scripting and workflow automation

---

## 🆘 **Urgent Support**

### **Critical Issues**
- **System Outage**: Contact [Emergency Contact]
- **Security Incident**: Contact [Security Contact]
- **Data Loss**: Contact [Data Recovery Contact]

### **General Support**
- **Documentation**: Check [Troubleshooting Guide](./troubleshooting.md)
- **API Issues**: Review [API Quirks](../developer/api-quirks.md)
- **Integration Problems**: See [Integrations Guide](./integrations.md)
- **Contact**: [Support Channel]

---

*This operations guide provides comprehensive guidance for administering and managing Endor Cockpit systems.*

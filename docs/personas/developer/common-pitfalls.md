# Common Development Pitfalls & Solutions

> **Critical Issues Encountered During Development and Their Solutions**

## 🚨 **Critical Pitfalls**

### **1. Unicode Encoding Issues on Windows**
**Problem**: `UnicodeEncodeError: 'charmap' codec can't encode character '\u2705'`
**Root Cause**: Windows PowerShell/CMD uses cp1252 encoding, can't handle Unicode emojis
**Solution**: Use ASCII characters only
```python
# WRONG: print(f"✅ Success")
# CORRECT: print(f"[SUCCESS] Success")
```
**Prevention**: Always use ASCII characters for cross-platform compatibility

### **2. Import Path Issues**
**Problem**: `ModuleNotFoundError: No module named 'endor_cockpit'`
**Root Cause**: Imports happening before `sys.path.insert()`
**Solution**: Set up paths before imports
```python
# CORRECT order:
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from endor_cockpit.api_client import APIClient
```
**Prevention**: Always set up paths before any imports

### **3. Virtual Environment Issues**
**Problem**: Python not finding installed packages
**Root Cause**: No virtual environment activated
**Solution**: Use `uv run python` instead of direct `python`
```bash
# WRONG: python .workspace/workspace.py
# CORRECT: uv run python .workspace/workspace.py
```
**Prevention**: Always use `uv run` for Python execution

### **4. API Response Structure Confusion**
**Problem**: Expecting direct arrays, getting empty results
**Root Cause**: API returns `{"list": {"objects": [...]}}` structure
**Solution**: Parse response correctly
```python
# WRONG: data = res.json().get("projects", [])
# CORRECT: data = res.json().get("list", {}).get("objects", [])
```
**Prevention**: Always check API response structure first

### **5. Wrong Path Parameters**
**Problem**: Using `namespace_uuid` instead of canonical namespace
**Root Cause**: Assuming UUID-based paths
**Solution**: Use canonical namespace format
```python
# WRONG: f"v1/namespaces/{namespace_uuid}/projects"
# CORRECT: f"v1/namespaces/{tenant_meta_namespace}/projects"
```
**Prevention**: Use canonical namespace format like `endor-solutions-tgowan.cockpit`

### **6. Direct API Calls Instead of Resource Modules**
**Problem**: APIClient.get() returning None
**Root Cause**: Bypassing resource modules and authentication
**Solution**: Use resource modules
```python
# WRONG: response = client.get("v1/namespaces/...")
# CORRECT: projects = list_projects(client, namespace)
```
**Prevention**: Always use resource modules, not direct API calls

### **7. Authentication Conflicts**
**Problem**: `Error: more than one authentication method provided`
**Root Cause**: Environment variables conflicting with endorctl
**Solution**: Use SDK's built-in authentication
**Prevention**: Use the SDK's resource modules, not endorctl for testing

### **8. Child Namespace Permission Issues**
**Problem**: `403 Client Error: Forbidden`
**Root Cause**: Child namespaces don't inherit parent permissions
**Solution**: Use parent namespace for operations
**Prevention**: Understand namespace hierarchy and permission inheritance

## 🔧 **Development Environment Setup**

### **Required Setup Steps**
1. **Create Virtual Environment**:
   ```bash
   uv venv
   source .venv/bin/activate  # Linux/Mac
   # or
   .venv\Scripts\activate    # Windows
   ```

2. **Initialize Knowledge Base**:
   ```bash
   uv run python workflow/init_vector_db.py
   ```

3. **Set Environment Variables**:
   ```bash
   export ENDOR_API="your-api-url"
   export ENDOR_API_CREDENTIALS_KEY="your-key"
   export ENDOR_API_CREDENTIALS_SECRET="your-secret"
   export ENDOR_NAMESPACE="your-namespace"
   ```

4. **Install Dependencies**:
   ```bash
   uv pip install -e .
   ```

### **Critical Commands**
- **Always use**: `uv run python` instead of `python`
- **Always use**: Resource modules instead of direct API calls
- **Always use**: ASCII characters, no Unicode emojis
- **Always use**: Canonical namespace format

## 🧪 **Testing Strategy**

### **Incremental Testing Approach**
1. **Start with GET operations** to understand structure
2. **Test with existing data** before creating new data
3. **Use collaborative workspace.py** for experimentation
4. **Trust SDK logging** for verbose output
5. **Document API discrepancies** when endorctl and SDK differ

### **Workspace Management**
- **Single file**: Use `.workspace/workspace.py` for all experimentation
- **Function-based**: Define test functions instead of one-off scripts
- **Version control**: Commit working versions with descriptive messages
- **Clean up**: Remove one-off scripts, keep only workspace.py

## 📚 **Knowledge Base Integration**

### **Research Workflow**
1. **Query RAG knowledge base** for existing patterns
2. **Analyze OpenAPI spec** for `{Resource}Service` endpoints
3. **Use endorctl** for live data structure reference
4. **Test with APIClient** for actual implementation
5. **Document learnings** in .workspace/log.md

### **Update Knowledge Base**
1. **Propagate learnings** to relevant documentation
2. **Avoid duplicates** by checking existing content
3. **Re-index knowledge base** after updates
4. **Update workspace.py** with new patterns

## 🎯 **Success Patterns**

### **Correct Development Flow**
```python
# 1. Set up environment
import sys
sys.path.insert(0, '..')
from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import projects

# 2. Use resource modules
client = APIClient()
namespace = "endor-solutions-tgowan.cockpit"
projects_list = projects.list_projects(client, namespace)

# 3. Handle response structure
for project in projects_list:
    print(f"[INFO] Project: {project.meta.name}")
```

### **Avoid These Patterns**
```python
# WRONG: Direct API calls
response = client.get("v1/namespaces/uuid/projects")

# WRONG: Unicode characters
print("✅ Success")

# WRONG: Direct python execution
python .workspace/workspace.py
```

## 🔍 **Troubleshooting Checklist**

- [ ] Using `uv run python` instead of `python`
- [ ] Path setup before imports
- [ ] ASCII characters only (no Unicode)
- [ ] Using resource modules, not direct API calls
- [ ] Following existing patterns from namespaces.py
- [ ] Testing with parent namespace, not child namespaces
- [ ] Virtual environment activated
- [ ] Knowledge base initialized
- [ ] Environment variables set correctly

---

*This guide prevents common development pitfalls and ensures smooth development experience.*

# Agent From-Scratch Guide

> **Complete workflow for agents starting fresh with Endor Cockpit**

## 🚀 **Phase 1: Initial Setup (5 minutes)**

### **Step 1: Environment Setup**
```bash
# 1. Verify Python environment
python --version  # Should be 3.11-3.14

# 2. Set up virtual environment
uv venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows

# 3. Install dependencies
uv pip install -e .

# 4. Verify installation
python -c "import endor_cockpit; print('SDK installed successfully')"
```

### **Step 2: Environment Variables**
```bash
# Required environment variables
export ENDOR_API="https://api.endorlabs.com"
export ENDOR_API_CREDENTIALS_KEY="your-api-key"
export ENDOR_API_CREDENTIALS_SECRET="your-api-secret"
export ENDOR_NAMESPACE="your-namespace"

# Optional for RAG functionality
export OPENAI_API_KEY="your-openai-key"
```

### **Step 3: Verify API Connectivity**
```bash
# Test API connection
endorctl api list -r Namespace

# Expected output: List of namespaces or error message
```

## 🧠 **Phase 2: Knowledge Base Initialization (2 minutes)**

### **Step 1: Initialize Vector Database**
```bash
# Initialize the knowledge base
uv run python workflow/init_vector_db.py

# Expected output: "Vector database initialized successfully"
```

### **Step 2: Test RAG Functionality**
```python
# Test RAG query
from endor_cockpit.rag import query_vector_db

results = query_vector_db("How do I create a namespace?")
print(f"Found {len(results)} relevant documents")
```

## 🔍 **Phase 3: First Operations (10 minutes)**

### **Step 1: Basic API Operations**
```python
# Test basic operations
from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import namespace

# Initialize client
client = APIClient()

# List namespaces
namespaces = namespace.list_namespaces(client, "your-namespace")
print(f"Found {len(namespaces)} namespaces")
```

### **Step 2: Resource Operations**
```python
# Test resource operations
from endor_cockpit.resources import project

# List projects
projects = project.list_projects(client, "your-namespace")
print(f"Found {len(projects)} projects")

# Get specific project
if projects:
    project_detail = project.get_project(client, "your-namespace", projects[0].uuid)
    print(f"Project: {project_detail.meta.name}")
```

## 🧪 **Phase 4: Testing & Validation (5 minutes)**

### **Step 1: Run Tests**
```bash
# Run all tests
uv run pytest tests/ -v

# Expected: All tests should pass
```

### **Step 2: Security Scan**
```bash
# Run security scan
endorctl scan

# Expected: No security issues found
```

### **Step 3: Linting**
```bash
# Check linting
uv run ruff check .

# Fix any issues
uv run ruff check . --fix
```

## 📚 **Phase 5: Learning & Documentation (15 minutes)**

### **Step 1: Explore Knowledge Base**
```python
# Query different topics
topics = [
    "How do I create a namespace?",
    "What are the common API pitfalls?",
    "How do I implement a new resource?",
    "What are the security requirements?"
]

for topic in topics:
    results = query_vector_db(topic)
    print(f"Topic: {topic}")
    print(f"Results: {len(results)} documents")
    print("---")
```

### **Step 2: Read Key Documentation**
1. **AGENT_GUIDE.md**: Comprehensive agent instructions
2. **Resource Documentation**: Understanding data models
3. **API Patterns**: Common usage patterns
4. **Troubleshooting**: Common issues and solutions

### **Step 3: Practice Operations**
```python
# Practice common operations
# 1. Create a test namespace
# 2. List resources
# 3. Update resource tags
# 4. Handle errors gracefully
```

## 🚨 **Phase 6: Error Recovery (5 minutes)**

### **Common Issues & Solutions**

#### **Issue 1: API Connection Failed**
```bash
# Check environment variables
echo $ENDOR_API
echo $ENDOR_API_CREDENTIALS_KEY

# Test connectivity
endorctl api list -r Namespace
```

#### **Issue 2: Import Errors**
```bash
# Reinstall dependencies
uv pip install -e .

# Check Python path
python -c "import sys; print(sys.path)"
```

#### **Issue 3: RAG Not Working**
```bash
# Reinitialize vector database
uv run python workflow/init_vector_db.py

# Test RAG query
python -c "from endor_cockpit.rag import query_vector_db; print(query_vector_db('test'))"
```

#### **Issue 4: Tests Failing**
```bash
# Check environment
uv run pytest tests/ -v --tb=short

# Fix specific issues
uv run ruff check . --fix
```

## ✅ **Phase 7: Validation Checklist**

### **Pre-Development Checklist**
- [ ] Environment variables set correctly
- [ ] API credentials valid and tested
- [ ] Knowledge base initialized
- [ ] Security scan completed
- [ ] Linting rules configured
- [ ] Tests passing
- [ ] RAG functionality working

### **Development Readiness**
- [ ] Can list namespaces
- [ ] Can list projects
- [ ] Can query knowledge base
- [ ] Can handle API errors
- [ ] Can run tests
- [ ] Can run security scan

## 🎯 **Success Metrics**

### **Time to First Success**
- **Environment Setup**: < 5 minutes
- **First API Call**: < 2 minutes
- **Knowledge Base Query**: < 1 minute
- **First Resource Operation**: < 3 minutes

### **Error Recovery**
- **Common Issues**: < 2 minutes to resolve
- **API Errors**: < 1 minute to identify
- **Import Errors**: < 1 minute to fix
- **Test Failures**: < 3 minutes to resolve

## 📈 **Next Steps**

### **Beginner Path**
1. **Read AGENT_GUIDE.md**: Comprehensive guidance
2. **Practice Basic Operations**: Namespace, project, finding operations
3. **Explore Knowledge Base**: Query different topics
4. **Follow Examples**: Implement simple workflows

### **Intermediate Path**
1. **Implement New Resource**: Follow resource implementation workflow
2. **Debug API Issues**: Use troubleshooting guides
3. **Contribute Learnings**: Update knowledge base
4. **Optimize Workflows**: Improve efficiency

### **Expert Path**
1. **Deep Architecture Understanding**: Study system design
2. **Advanced Patterns**: Implement complex workflows
3. **Performance Optimization**: Improve efficiency
4. **Knowledge Base Maintenance**: Keep documentation current

---

*This guide ensures agents can start from scratch and become productive within 30 minutes.*

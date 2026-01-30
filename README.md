# 🚀 Endor Cockpit

[![Python CI](https://github.com/<your-org>/<your-repo>/actions/workflows/ci.yml/badge.svg)](https://github.com/<your-org>/<your-repo>/actions/workflows/ci.yml)

> **Starfighter Ready**: Navigate the Endor Labs security platform with tactical precision. This cockpit is designed for AI agents, human pilots, and autonomous security operations.

A production-ready Python SDK for integrating Endor Labs security platform with AI-powered IDEs and development tools. Provides comprehensive REST API client capabilities for administering, operating, and scanning with Endor Labs tooling.

## 🤖 **AI Agents Welcome**

This cockpit is specifically engineered for AI-powered development environments. Whether you're an autonomous security agent, a development assistant, or a human pilot, the Endor Cockpit provides the tools you need to navigate the security landscape with confidence.

## 🚀 Agentic Usage (Quick Start)

**For AI Agents in IDEs**: This toolkit is designed to be seamlessly integrated into AI-powered development environments. See [AGENTS.md](./AGENTS.md) for comprehensive integration guidance.

```python
from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import namespace

# Initialize client (auto-authenticates via environment variables)
client = APIClient()

# List namespaces
namespaces = namespace.list_namespaces(client, "tenant.namespace")
for ns in namespaces:
    print(f"Namespace: {ns.meta.name}")
```

## ⚡ **Tactical Features**

- **🎯 AI Agent Integration**: Seamlessly integrated with AI-powered development environments
- **🛡️ Security-First Design**: Built-in security scanning with `endorctl` integration
- **🔧 Comprehensive API Coverage**: Full REST API client for Endor Labs platform operations
- **⚙️ Modern Python Arsenal**: `uv` dependency management, `ruff` linting, `pytest` testing
- **🎪 Type-Safe Operations**: Pydantic-powered data structures with field mutability tracking
- **🏗️ Resource-Oriented Architecture**: Intuitive modules for specific API resources
- **🚀 Production-Ready**: Robust error handling, authentication, rate limiting, and retry mechanisms
- **📚 External Documentation Sync**: Automated helpers to pull API specs and user docs
- **🎭 Maneuvers & Protocols**: Pre-built tactical scripts for common security operations
- **🔍 Schema Drift Detection**: Advanced monitoring for API specification changes

## 🛠️ **Installation & Setup**

### Quick Setup (Recommended)

```bash
# Clone the repository
git clone https://github.com/endor-solutions-architecture/endor-cockpit.git
cd endor-cockpit

# Create virtual environment
uv venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate    # Windows

# Install dependencies
uv pip install -e .

# Optional: Install dependencies for documentation sync scripts
uv pip install -e ".[docs]"
```

### External Documentation Sync

Pull the latest API specifications and user documentation:

```bash
# Download user documentation from Endor Labs (CI-only, use unified workflow instead)
# Note: download_user_docs.py has been moved to .github/scripts/ for CI use
# For manual use, use: python .github/scripts/unified_docs_workflow.py --update-docs-only --download-user-docs

# The OpenAPI specification is already included in external_docs/openapi-swagger.json
```

## 🔐 **Environment Configuration**

### Configuration Precedence

The SDK uses environment variables only (no config file loading). Precedence is:

1. **Constructor Parameters** - Explicit values passed to `APIClient()`
2. **Environment Variables** - System/process environment variables
3. **Defaults** - Built-in SDK defaults

This follows 12-factor app principles: deployment-specific settings via environment variables.

### Required Environment Variables

The SDK requires the following environment variables to be set:

```bash
export ENDOR_API="https://api.endorlabs.com"
export ENDOR_API_CREDENTIALS_KEY="your-api-key"
export ENDOR_API_CREDENTIALS_SECRET="your-api-secret"
export ENDOR_NAMESPACE="your-tenant-namespace"  # Required for operations
export ENDOR_LOG_LEVEL="INFO"  # Optional: DEBUG, INFO, WARNING, ERROR, CRITICAL
export ENDOR_MAX_RETRIES="5"  # Optional: Maximum number of retries (default: 5)
```

### Configuration Sources

**Environment Variables** (used by the SDK):
- Highest precedence after constructor parameters
- Secure for CI/CD and production environments
- The SDK does not read from `.endorctl/config.yaml`; use environment variables or constructor parameters.

### Local Development Setup

For local development, use environment variables or the setup/validation scripts:

```bash
# Validate environment (ENDOR_API, credentials, namespace)
uv run python scripts/validate_environment.py

# Interactive setup (optional)
uv run python scripts/setup_environment.py
```

### Configuration Management

**Local Development**:
- Set environment variables (e.g. in shell or `.env` with `python-dotenv`)
- Or pass credentials to `APIClient()` constructor

**CI/CD**: 
Environment variables are configured in GitHub repository settings:
- `ENDOR_API` - Repository variable
- `ENDOR_NAMESPACE` - Repository variable  
- `ENDOR_API_CREDENTIALS_KEY` - Repository secret
- `ENDOR_API_CREDENTIALS_SECRET` - Repository secret
- `ENDOR_LOG_LEVEL` - Optional repository variable (default: INFO)
- `ENDOR_MAX_RETRIES` - Optional repository variable (default: 5)

## Quick Start

### For Human Pilots

```python
from endor_cockpit.api_client import APIClient
from endor_cockpit.resources import namespace

# Initialize the client (uses environment variables for auth)
client = APIClient()

# List namespaces
tenant_namespace = "your-tenant-namespace"
all_namespaces = namespace.list_namespaces(client, tenant_namespace)

for ns in all_namespaces:
    print(f"Namespace: {ns.meta.name}, UUID: {ns.uuid}")
```

### For AI Agents & Autonomous Systems

This cockpit is specifically engineered for AI-powered development environments. See [AGENTS.md](./AGENTS.md) for comprehensive guidance on:

- **🤖 Agent Roles**: Developer, Security, and Operations agent definitions
- **🔧 Tool Integration**: LLM tool schemas and function definitions
- **🛡️ Security Protocols**: Built-in security scanning and compliance
- **📋 Best Practices**: Patterns for reliable agent operations
- **🎭 Maneuvers**: Pre-built tactical scripts for common operations
- **📚 External Docs**: Automated sync with API specifications and user documentation

## 🛠️ **Development & Operations**

### Testing Arsenal

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=endor_cockpit --cov-report=html

# Run integration tests (requires valid credentials)
pytest -m integration -v
```

### Code Quality & Linting

```bash
# Linting & Formatting
ruff check .

# Type checking
mypy src/
```

### Security Scanning

```bash
# Run endorctl security scan
endorctl scan --path . --namespace "your-namespace"
```

### Maneuvers & Tactical Scripts

Execute pre-built tactical operations:

```bash
# Create notification policies
uv run python maneuvers/create_notification_policy.py --help

# Tag findings for triage
uv run python maneuvers/tag_findings.py --help

# Create exception policies
uv run python maneuvers/create_exception_policy.py --help

# See all available maneuvers
ls maneuvers/
```

## 📊 **Resource Implementation Status**

> **Mission Control**: Comprehensive tracking of Endor Labs resource types and their implementation status

### Implementation Checklist

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
- **Installation** - Implementation: ✅ | Documentation: ✅ | Tests: ❌ (API: GET only)

### Completion Criteria

**Implementation**: CRUD operations validated, model validated and a handful of attributes modeled correctly
**Documentation**: Statements verified to match implementation and tests  
**Tests**: Passes linter, unit tests provided and incorporated into CI

### Status Legend
- ✅ **COMPLETE**: All criteria met
- 🚧 **IN PROGRESS**: Implementation started
- ❌ **NOT STARTED**: No work begun
- 🚫 **BLOCKED**: Blocked by dependencies

---

## 📚 **Documentation & Intelligence**

- **[AI Agent Integration Guide](./AGENTS.md)** - Primary reference for AI agent integration
- **[Documentation index](./docs/README.md)** - SDK docs (conventions, reference, guides, rules of engagement); non-SDK content in `.tmp/docs-revamp/`
- **[Rules of Engagement](./docs/rules-of-engagement/)** - Specialized tactical workflows
- **[Rego (SDK usage)](./docs/guides/rego-policies.md)** - How the SDK is used with policies; link to official Rego docs
- **[SDK Docstrings](./src/endor_cockpit/)** - Inline documentation for all resources
- **[External Documentation](./external_docs/)** - Endor Labs API and user documentation

## 🗂️ **Workspace & Mission Files**

For local testing and development, use the `.workspace/` folder which is excluded from version control. This folder is **unique to each pilot** and contains:
- Integration test results and configurations
- Temporary policy configurations
- Development scripts and utilities
- Test-specific documentation
- User-specific API configurations
- **Operational context and environment setup guides**

Each pilot's workspace is isolated and not shared across the squadron.

For current operational context including environment setup, GitHub CLI configuration, and development workflow, see `.workspace/OPERATIONAL_CONTEXT.md`.

## 🤝 **Contributing to the Squadron**

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 **Support & Mission Control**

For questions and support:
- **📚 Documentation**: See the [AI Agent Integration Guide](./AGENTS.md)
- **🐛 Issues**: Create an issue in the repository
- **🛡️ Security**: Follow the security guidelines in the documentation
- **🎭 Maneuvers**: Check the `maneuvers/` directory for tactical scripts
- **📋 Protocols**: Review `protocols/` for operational procedures

---

> **May the Force be with you, pilot. The Endor Cockpit is ready for your mission.** 🚀

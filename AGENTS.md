# Endor Cockpit: AI Agent Integration Guide

## 🚀 **Quick Start for AI Agents**

> **For comprehensive, token-efficient guidance, see: [AGENT_GUIDE.md](./docs/agents/AGENT_GUIDE.md)**

### **Agent Type Selection**
- **🤖 SDK Developer**: [Development Guide](./docs/agents/AGENT_GUIDE.md#development) → [Linting Guide](./docs/agents/AGENT_GUIDE.md#linting--ci-prevention)
- **🔧 SDK User**: [Usage Guide](./docs/agents/AGENT_GUIDE.md#usage) → [Tools Guide](./docs/agents/AGENT_GUIDE.md#tools)
- **🔍 Security Scanner**: [Security Guide](./docs/agents/AGENT_GUIDE.md#security) → [Scanning Guide](./docs/agents/AGENT_GUIDE.md#scanning)

### **Critical Requirements**
- **Security**: Always run `endorctl scan` before code changes
- **Linting**: Max 88 chars/line, sorted imports, no trailing whitespace
- **Dependencies**: Pin exact versions, avoid `latest`
- **Environment**: Set `ENDOR_API`, `ENDOR_API_CREDENTIALS_KEY`, `ENDOR_API_CREDENTIALS_SECRET`

## 📋 **Project Context**

**Endor Cockpit** is a production-ready foundational service:
- **Purpose**: Administer, operate and scan with Endor Labs tooling through REST APIs
- **Data Classification**: Public (no PII handling)
- **Deployment**: Production environment, global region
- **Security**: SOC2 and ISO27001 compliant
- **Architecture**: Resource-oriented SDK pattern

> 📋 **For detailed project context, see [catalog-info.yaml](./catalog-info.yaml)**

## 📚 **Legacy Documentation (Reference Only)**

*The following files contain detailed information but are now consolidated in [AGENT_GUIDE.md](./docs/agents/AGENT_GUIDE.md) for token efficiency:*

- **[Core Principles](./docs/agents/core-principles.md)** - Fundamental guidelines
- **[Development Guidelines](./docs/agents/development.md)** - Development best practices  
- **[Usage Patterns](./docs/agents/usage-patterns.md)** - Common patterns and examples
- **[Resource Guides](./docs/agents/resource-guides.md)** - Resource-specific API documentation
- **[Security Guidelines](./docs/agents/security.md)** - Security-first practices
- **[Tool Definitions](./docs/agents/tool-definitions.md)** - LLM tool schemas
- **[Agent Insights](./docs/agents/insights.md)** - Critical discoveries and patterns
- **[Quick Reference](./docs/agents/quick-reference.md)** - Essential patterns and fixes

## 🎯 **Next Steps**

1. **Read the consolidated guide**: [AGENT_GUIDE.md](./docs/agents/AGENT_GUIDE.md)
2. **Set up environment**: Configure required environment variables
3. **Run security scan**: `endorctl scan` before any changes
4. **Follow linting standards**: Use the pre-development checklist
5. **Test your changes**: Run `uv run pytest` to verify functionality

## 📁 **Workspace Folder**

For local testing and development, use the `workspace/` folder which is excluded from version control:
- Integration test results and configurations
- Temporary policy configurations  
- Development scripts and utilities
- Test-specific documentation
- User-specific API configurations
- **Agent notes and task documentation**

**Note for AI Agents**: When creating documentation, notes, or task-specific files, place them in the `workspace/` folder rather than the root directory to keep the repository clean and organized.

### Operational Context
For current operational context including environment setup, GitHub CLI configuration, and development workflow, see `workspace/OPERATIONAL_CONTEXT.md`.
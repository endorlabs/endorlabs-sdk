# AI Agent Integration Guide

This directory contains comprehensive documentation for AI agents working with the Endor Cockpit project.

## Quick Navigation

- **[Core Principles](./core-principles.md)** - Fundamental guidelines for agent behavior
- **[Development Guidelines](./development.md)** - Best practices for developing the SDK
- **[Usage Patterns](./usage-patterns.md)** - Common patterns and examples
- **[Resource Guides](./resource-guides.md)** - Resource-specific API documentation
- **[Security Guidelines](./security.md)** - Security-first development practices
- **[Tool Definitions](./tool-definitions.md)** - LLM tool schemas and examples
- **[Agent Insights](./insights.md)** - Critical discoveries and patterns

## For Different Agent Types

### 🤖 Agents Developing the SDK
Start with [Development Guidelines](./development.md) and [Core Principles](./core-principles.md)

### 🔧 Agents Using the SDK
Start with [Usage Patterns](./usage-patterns.md) and [Tool Definitions](./tool-definitions.md)

### 🔍 Agents Scanning/Auditing the SDK
Start with [Security Guidelines](./security.md) and review [catalog-info.yaml](../../catalog-info.yaml)

## Project Context

This is a **foundational workspace** for Endor Labs platform administration and operations. The project:

- **Purpose**: Administer, operate and scan with Endor Labs tooling through REST APIs
- **Data Classification**: Public (no PII handling)
- **Deployment**: Production-ready foundational service
- **Security**: SOC2 and ISO27001 compliant
- **Architecture**: Resource-oriented SDK pattern

## Quick Start for Agents

1. **Read the catalog-info.yaml** for deployment context
2. **Review core principles** for your agent type
3. **Follow security guidelines** for all operations
4. **Use provided tool definitions** for LLM integration

## Contributing to Agent Documentation

When adding new agent guidance:
- Place in appropriate subdirectory
- Update this README with navigation
- Ensure consistency with core principles
- Include practical examples

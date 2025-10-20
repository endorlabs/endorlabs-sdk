# Canonical Sources Mapping

> **Single source of truth for all concepts in Endor Cockpit documentation**

## Core Concepts

### Environment Setup
- **Canonical**: `docs/ESSENTIAL_CONTEXT.md#operational-protocols`
- **Essential references**: `docs/agents/README.md` (3 bullets)
- **Links only**: `docs/agents/AGENT_GUIDE.md`, `docs/personas/developer/README.md`

### API Authentication
- **Canonical**: `docs/ESSENTIAL_CONTEXT.md#operational-protocols`
- **Essential references**: `docs/agents/README.md` (2 bullets)
- **Links only**: `docs/personas/developer/README.md`

### Security Scanning
- **Canonical**: `docs/ESSENTIAL_CONTEXT.md#operational-protocols`
- **Essential references**: `docs/agents/README.md` (1 bullet)
- **Links only**: `docs/agents/AGENT_GUIDE.md`

## Resource Documentation

### Project Resource
- **Canonical**: `docs/endor-data-model/project.md`
- **Essential references**: `docs/agents/README.md` (3 bullets)
- **Links only**: `docs/agents/AGENT_GUIDE.md`, `docs/personas/developer/README.md`

### Finding Resource
- **Canonical**: `docs/endor-data-model/finding.md`
- **Essential references**: `docs/agents/README.md` (3 bullets)
- **Links only**: `docs/agents/AGENT_GUIDE.md`, `docs/personas/security/README.md`

### Policy Resource
- **Canonical**: `docs/endor-data-model/policy.md`
- **Essential references**: `docs/agents/README.md` (3 bullets)
- **Links only**: `docs/agents/AGENT_GUIDE.md`, `docs/personas/security/README.md`

### Namespace Resource
- **Canonical**: `docs/endor-data-model/namespace.md`
- **Essential references**: `docs/agents/README.md` (3 bullets)
- **Links only**: `docs/agents/AGENT_GUIDE.md`, `docs/personas/operations/README.md`

## API Patterns

### PATCH Operations
- **Canonical**: `docs/endor-data-model/project.md#update-operations`
- **Essential references**: `docs/ESSENTIAL_CONTEXT.md` (1 bullet)
- **Links only**: `docs/agents/AGENT_GUIDE.md`, `docs/personas/developer/README.md`

### Canonical Naming
- **Canonical**: `docs/endor-data-model/namespace.md#canonical-naming`
- **Essential references**: `docs/ESSENTIAL_CONTEXT.md` (1 bullet)
- **Links only**: `docs/agents/AGENT_GUIDE.md`, `docs/personas/operations/README.md`

### Response Structure
- **Canonical**: `docs/ESSENTIAL_CONTEXT.md#operational-protocols`
- **Essential references**: `docs/agents/README.md` (1 bullet)
- **Links only**: `docs/agents/AGENT_GUIDE.md`

## Workflow Documentation

### Knowledge Capture Workflow
- **Canonical**: `docs/protocols/knowledge-capture-workflow.md`
- **Essential references**: `docs/ESSENTIAL_CONTEXT.md` (1 bullet)
- **Links only**: `docs/agents/AGENT_GUIDE.md`

### Holocron Setup
- **Canonical**: `docs/protocols/holocron-setup.md`
- **Essential references**: `docs/ESSENTIAL_CONTEXT.md` (1 bullet)
- **Links only**: `docs/agents/README.md`

### Environment Validation
- **Canonical**: `scripts/validate_environment.py`
- **Essential references**: `docs/ESSENTIAL_CONTEXT.md` (1 bullet)
- **Links only**: `docs/agents/README.md`

## Troubleshooting

### Common API Errors
- **Canonical**: `docs/endor-data-model/*.md#troubleshooting`
- **Essential references**: `docs/ESSENTIAL_CONTEXT.md` (1 bullet)
- **Links only**: `docs/agents/AGENT_GUIDE.md`

### Environment Issues
- **Canonical**: `scripts/validate_environment.py`
- **Essential references**: `docs/ESSENTIAL_CONTEXT.md` (1 bullet)
- **Links only**: `docs/agents/README.md`

## Protocol Levels

### L1 (Essential - Always Required)
- Environment validation checklist
- RAG knowledge base maintenance and query
- Security scan requirement
- Error recovery basics
- Knowledge capture workflow (for maintaining database)

### L2 (Detailed - Context-Specific)
- Resource implementation workflow (for new features)
- Schema drift detection (for API changes)
- Tag management patterns (for specific operations)

### L3 (Comprehensive - Advanced)
- Architecture deep dives
- Performance optimization
- Advanced integration patterns
- Expert-level troubleshooting

---

*This mapping ensures single source of truth while allowing essential context in multiple locations. All references should link to canonical sources.*

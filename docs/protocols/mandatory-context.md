# Mandatory Context Protocol

> **L1 (Essential - Always Required) - Core operational requirements for all agent operations**

## Overview

This protocol defines the essential context that must be available to all agents before any operation. These are the "safety rails" that prevent common failures and ensure consistent operation.

## Required Context

### 1. Environment Validation
**Command**: `python scripts/validate_environment.py`
**Purpose**: Ensure all required components are properly configured
**Output**: Actionable error messages with fix commands
**When**: Before starting any operation

### 2. RAG Knowledge Base Query
**Command**: `python -m holocron query "your question"`
**Purpose**: Retrieve relevant context before coding
**Pattern**: Query first, then implement
**When**: Before implementing any feature

### 3. Security Scan Requirement
**Command**: `endorctl scan`
**Purpose**: Ensure code changes meet security standards
**When**: Before any commit
**Failure**: Block commit if security issues found

### 4. Error Recovery Basics
**Source**: `.workspace/validation.log`
**Purpose**: Understand and resolve common issues
**Pattern**: Check logs → Apply fixes → Retry operation
**When**: When operations fail

## Implementation

### For Agents
1. **Always run validation** before starting work
2. **Query holocron first** for any unknown concepts
3. **Check security scan** before committing changes
4. **Review error logs** when operations fail

### For Documentation
1. **Reference this protocol** in all entry points
2. **Link to validation script** in error messages
3. **Include RAG workflow** in all guides
4. **Document security requirements** clearly

## Success Criteria

- ✅ Environment validation passes
- ✅ Knowledge base query returns relevant context
- ✅ Security scan passes
- ✅ Error recovery procedures documented

## Related Protocols

- [Knowledge Capture Workflow](knowledge-capture-workflow.md) - L1
- [Holocron Setup Protocol](holocron-setup.md) - L2
- [Documentation Standards](documentation-standards.md) - L2

---

*This protocol is mandatory for all agent operations. It provides the essential context needed for safe and effective operation.*

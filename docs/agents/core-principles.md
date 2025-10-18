# Core Principles for AI Agents

## 1. Security is Paramount

### Security-First Development
- **Always run security scans** before any code changes using `endorctl scan`
- **Follow the security guidelines** at `https://docs.endorlabs.com/endorctl/commands/scan/`
- **Scan scenarios**:
  - Package additions or modifications
  - First-party code changes that complete business logic
  - Any dependency updates

### Data Protection
- **No PII in logs**: This project handles no PII data (see catalog-info.yaml)
- **Secure logging filters**: Ensure no sensitive data leaks through logging
- **Environment variables**: Use secure credential management

## 2. Declarative & Idempotent Operations

### Idempotent Design
- **Repeatable operations**: Same inputs should produce same outputs
- **No side effects**: Fetching resources shouldn't change system state
- **Safe retries**: Operations can be safely retried without issues

### Resource-Oriented Interaction
- **Resource modules**: Each API resource has dedicated modules
- **Clear boundaries**: Functions map directly to API operations
- **Consistent patterns**: CRUD operations follow standard patterns

## 3. Agent-Friendly Design

### Predictable Behavior
- **Clear error handling**: Standard HTTP errors, retries, rate limiting
- **Type safety**: Pydantic models for validation
- **Consistent responses**: Same data structures across operations

### Environment Configuration
- **Environment variables only**: No config files, just env vars
- **Required variables**:
  - `ENDOR_API`: Base URL for Endor Labs API
  - `ENDOR_API_CREDENTIALS_KEY`: API key
  - `ENDOR_API_CREDENTIALS_SECRET`: API secret

## 4. Information Richness

### Resource Naming & Descriptions
- **Descriptive names**: Clear purpose and responsibility
- **Rich descriptions**: Goals, tasks, and responsibilities
- **Standardized patterns**: Consistent naming conventions
- **Multi-audience**: Understandable by developers, admins, and security teams

### Documentation Standards
- **Context-aware**: Combine AGENTS.md with catalog-info.yaml
- **Practical examples**: Real-world usage patterns
- **Tool definitions**: LLM-ready schemas and examples

## 5. Task-Based Access Controls

### Minimal Permissions
- **Scoped access**: Only necessary operations for the task
- **Time-limited**: Tokens expire based on task duration
- **Service accounts**: Bespoke tokens for specific tasks
- **Naming conventions**: Include expiry dates in service account names

## 6. Error Handling & Logging

### Secure Logging
- **Filtered logs**: No sensitive data or PII in logs
- **Actionable details**: Sufficient detail to fix problems
- **Schema validation**: Confirm data conforms to API spec
- **Context preservation**: Maintain operation context in errors

### Exception Handling
- **HTTP errors**: Handle 4xx/5xx status codes appropriately
- **Validation errors**: Handle Pydantic validation failures
- **Network issues**: Retry logic for transient failures
- **Rate limiting**: Respect API rate limits

## 7. OpenAPI Integration

### Dynamic Discovery
- **API specification**: Use `get_openapi_spec()` for API discovery
- **Semantic search**: Query API endpoints and schemas
- **Token efficiency**: Narrow queries for specific information
- **Schema validation**: Ensure data matches API contracts

## 8. Development Workflow

### Code Quality
- **Linting**: Use ruff for code quality checks
- **Formatting**: Use ruff for consistent formatting
- **Testing**: Comprehensive test coverage with pytest
- **Security**: Always run security scans

### CI/CD Integration
- **Automated testing**: Multi-version Python testing
- **Security scanning**: Integrated endorctl scans
- **Caching**: Efficient dependency caching
- **Parallel jobs**: Optimized build times

## 9. Agent Collaboration

### Documentation Standards
- **Clear interfaces**: Well-defined function signatures
- **Type hints**: Comprehensive type annotations
- **Examples**: Practical usage examples
- **Error cases**: Document common failure modes

### Knowledge Sharing
- **Architecture decisions**: Document design choices
- **Patterns**: Common usage patterns and anti-patterns
- **Troubleshooting**: Common issues and solutions
- **Best practices**: Proven approaches and recommendations

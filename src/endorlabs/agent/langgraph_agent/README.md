# LangGraph Agent for Endor Labs

**Experimental:** This feature may change; it is not covered by the same stability guarantees as the rest of the SDK.

A LangGraph-based agent that enables natural language interaction with the Endor Labs API.

## Installation

Install with the agent dependencies:

```bash
pip install endor-cockpit[agent]
```

Or with uv:

```bash
uv add endor-cockpit --extra agent
```

## Quick Start

```python
from langchain_openai import ChatOpenAI
from endorlabs import Client
from endorlabs.agent.langgraph_agent import create_endor_graph

# Initialize the Endor Labs client
client = Client(tenant="my.namespace")

# Create an LLM (any LangChain-compatible chat model works)
llm = ChatOpenAI(model="gpt-4o")

# Create the agent graph
graph = create_endor_graph(client, llm)

# Run a query
result = graph.invoke({
    "messages": [("user", "List all projects in my namespace")]
})

# Get the response
print(result["messages"][-1].content)
```

## Available Tools

The agent has access to **56 tools** covering all SDK resources. Tools are generated dynamically from the SDK registry.

### Core Resources

| Tool | Description |
|------|-------------|
| `list_namespaces` | List namespaces (organizational units) |
| `get_namespace` | Get a namespace by UUID |
| `list_projects` | List projects (repositories being scanned) |
| `get_project` | Get a project by UUID |
| `list_findings` | List security findings with optional severity filter (CRITICAL, HIGH, MEDIUM, LOW) |
| `get_finding` | Get a finding by UUID |
| `list_policies` | List policies (security rules and checks) |
| `get_policy` | Get a policy by UUID |
| `list_repositories` | List repositories |
| `get_repository` | Get a repository by UUID |

> **Tip:** All tenant-scoped `list_*` tools support `traverse=True` to include results from child namespaces.

### Scan & Results

| Tool | Description |
|------|-------------|
| `list_scan_results` | List scan results (supports parent_uuid filter) |
| `get_scan_result` | Get a scan result by UUID |
| `list_scan_profiles` | List scan profiles (scan configurations) |
| `get_scan_profile` | Get a scan profile by UUID |
| `list_scan_workflows` | List scan workflows |
| `get_scan_workflow` | Get a scan workflow by UUID |
| `list_scan_workflow_results` | List scan workflow results |
| `get_scan_workflow_result` | Get a scan workflow result by UUID |
| `list_linter_results` | List linter results (code quality findings) |
| `get_linter_result` | Get a linter result by UUID |

### Dependencies & Packages

| Tool | Description |
|------|-------------|
| `list_package_versions` | List package versions (dependencies) |
| `get_package_version` | Get a package version by UUID |
| `list_package_licenses` | List package licenses (OSS scope) |
| `get_package_license` | Get a package license by UUID |
| `list_dependency_metadata` | List dependency metadata (OSS scope) |
| `get_dependency_metadata` | Get dependency metadata by UUID |
| `list_version_upgrades` | List version upgrades (recommended updates) |
| `get_version_upgrade` | Get a version upgrade by UUID |
| `list_repository_versions` | List repository versions (supports parent_uuid filter) |
| `get_repository_version` | Get a repository version by UUID |

### Access Control & Policies

| Tool | Description |
|------|-------------|
| `list_authorization_policies` | List authorization policies (access control rules) |
| `get_authorization_policy` | Get an authorization policy by UUID |
| `list_policy_templates` | List policy templates (system scope) |
| `get_policy_template` | Get a policy template by UUID |
| `list_api_keys` | List API keys |
| `get_api_key` | Get an API key by UUID |
| `list_invitations` | List invitations (pending user invites) |
| `get_invitation` | Get an invitation by UUID |

### Integrations & Notifications

| Tool | Description |
|------|-------------|
| `list_installations` | List installations (GitHub/GitLab app installations) |
| `get_installation` | Get an installation by UUID |
| `list_notification_targets` | List notification targets (Slack, email, etc.) |
| `get_notification_target` | Get a notification target by UUID |

### Logging & Audit

| Tool | Description |
|------|-------------|
| `list_audit_logs` | List audit logs |
| `get_audit_log` | Get an audit log by UUID |
| `list_finding_logs` | List finding logs (historical finding changes) |
| `get_finding_log` | Get a finding log by UUID |
| `list_authentication_logs` | List authentication logs (system scope) |
| `get_authentication_log` | Get an authentication log by UUID |

### Other Resources

| Tool | Description |
|------|-------------|
| `list_semgrep_rules` | List Semgrep rules (custom SAST rules) |
| `get_semgrep_rule` | Get a Semgrep rule by UUID |
| `list_metrics` | List metrics |
| `get_metric` | Get a metric by UUID |
| `list_code_owners` | List code owners |
| `get_code_owners` | Get code owners by UUID |
| `list_endor_licenses` | List Endor licenses (system scope) |
| `get_endor_license` | Get an Endor license by UUID |

### Common Parameters

Most `list_*` tools accept these parameters:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `namespace` | Namespace to query (uses client default if not provided) | Client default |
| `max_results` | Maximum number of results to return | 100 |
| `max_pages` | Maximum pages to fetch for pagination | 10 |
| `filter_expr` | Filter expression (see syntax below) | None |
| `traverse` | Include results from child namespaces recursively | False |
| `parent_uuid` | Filter by parent UUID (for scan_results, repository_versions) | None |

**Note:** The `traverse` parameter works on **all tenant-scoped resources** (projects, findings, policies, etc.). Only system-scoped resources (authentication_logs, endor_licenses, policy_templates) and OSS-scoped resources (package_licenses, dependency_metadata) do not support namespace traversal.

### Filter Expression Syntax

Filter expressions allow you to narrow down results. The syntax supports:

```
# Equality
meta.name == "my-project"
spec.level == FINDING_LEVEL_CRITICAL

# Contains (substring match)
meta.name contains "api"
meta.description contains "security"

# Compound filters (AND)
(meta.name contains "api") and (spec.level == FINDING_LEVEL_HIGH)

# Filter by UUID
spec.project_uuid == "69802e08c48a597dd5bfa9b3"
```

**Common filter fields by resource:**

| Resource | Common Filter Fields |
|----------|---------------------|
| Projects | `meta.name`, `spec.platform_source` |
| Findings | `spec.level`, `spec.project_uuid`, `spec.finding_categories` |
| Policies | `meta.name`, `spec.disabled` |
| Scan Results | `spec.project_uuid`, `spec.status` |

**Severity levels for findings:** `FINDING_LEVEL_CRITICAL`, `FINDING_LEVEL_HIGH`, `FINDING_LEVEL_MEDIUM`, `FINDING_LEVEL_LOW`

## Using Different LLM Providers

The agent works with any LangChain-compatible chat model:

### OpenAI

```python
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(model="gpt-4o")
```

### Anthropic

```python
from langchain_anthropic import ChatAnthropic
llm = ChatAnthropic(model="claude-3-5-sonnet-20241022")
```

### Azure OpenAI

```python
from langchain_openai import AzureChatOpenAI
llm = AzureChatOpenAI(
    azure_deployment="gpt-4o",
    api_version="2024-02-15-preview",
)
```

## Example Queries

```python
# List all projects across all child namespaces
result = graph.invoke({
    "messages": [("user", "List all projects across all namespaces recursively")]
})

# List projects with critical findings
result = graph.invoke({
    "messages": [("user", "Show me projects that have critical security findings")]
})

# Get details about a specific finding
result = graph.invoke({
    "messages": [("user", "Tell me more about finding abc123")]
})

# Check policy status
result = graph.invoke({
    "messages": [("user", "What policies are currently enabled?")]
})

# Find findings in child namespaces with specific severity
result = graph.invoke({
    "messages": [("user", "List all HIGH severity findings across all namespaces")]
})
```

## Streaming Responses

LangGraph supports streaming for real-time output:

```python
for chunk in graph.stream({"messages": [("user", "List my projects")]}):
    if "agent" in chunk:
        print(chunk["agent"]["messages"][-1].content, end="", flush=True)
```

## Using Tools Directly

If you need more control, you can use the tools without the full agent:

```python
from endorlabs import Client
from endorlabs.agent.langgraph_agent import create_tools

client = Client(tenant="my.namespace")
tools = create_tools(client)

# Find the list_projects tool
list_projects_tool = next(t for t in tools if t.name == "list_projects")

# List projects in current namespace only
result = list_projects_tool.invoke({"max_results": 10})
print(result)

# List all projects across child namespaces with traverse
result = list_projects_tool.invoke({"traverse": True, "max_results": 50})
print(result)

# Use filter expression
list_findings_tool = next(t for t in tools if t.name == "list_findings")
result = list_findings_tool.invoke({
    "severity": "CRITICAL",
    "traverse": True,
    "max_results": 20
})
print(result)
```

## Architecture

The agent uses LangGraph's StateGraph with a **Plan-Execute-Reflect** pattern for multi-step reasoning:

```
┌─────────┐     ┌─────────┐     ┌───────┐     ┌───────────┐
│  START  │────▶│ Planner │────▶│ Agent │────▶│Synthesize │────▶ END
└─────────┘     └─────────┘     └───┬───┘     └───────────┘
                                    │               ▲
                                    │ (tool calls)  │
                                    ▼               │
                                ┌───────┐          │
                                │ Tools │          │
                                └───┬───┘          │
                                    │              │
                                    ▼              │
                              ┌────────────┐       │
                              │ Accumulate │       │
                              └─────┬──────┘       │
                                    │              │
                                    ▼              │
                               ┌─────────┐         │
                               │ Reflect │─────────┘
                               └────┬────┘   (done)
                                    │
                                    └────▶ (continue to Agent)
```

### Nodes

1. **Planner**: Analyzes the user request and generates a step-by-step plan before execution
2. **Agent**: Calls the LLM with tools bound, injecting plan context and collected data
3. **Tools**: Executes the requested tool calls
4. **Accumulate**: Extracts structured JSON from tool results and stores in `collected_data`
5. **Reflect**: Evaluates progress toward the goal and decides whether to continue or synthesize
6. **Synthesize**: Composes a final comprehensive answer from all collected data

### State

The agent maintains extended state for multi-step reasoning:

```python
class AgentState(TypedDict):
    messages: list          # Conversation messages
    plan: list[str]         # Step-by-step plan from planner
    current_step: int       # Current step index
    collected_data: dict    # Structured data from tool results
    scratchpad: str         # LLM's intermediate reasoning notes
```

### Benefits

- **Complex queries**: Handles multi-step tasks like "compare the last two scan results"
- **Data accumulation**: Preserves structured data across tool invocations for reasoning
- **Self-reflection**: Evaluates progress and adjusts approach dynamically
- **Better synthesis**: Composes comprehensive answers from multiple data sources

---
url: https://docs.endorlabs.com/releasenotes/previous-releases/june-2025/
title: June 2025 | Endor Labs Docs
downloaded: 2025-12-11 11:34:39
---

June 2025 | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/releasenotes/previous-releases/june-2025/_print.html)



# June 2025

We are excited to introduce the latest features and enhancements in Endor Labs.

### Endor Labs MCP server for IDE Alpha New

Endor Labs MCP server is now available in alpha for Cursor and Visual Studio Code.

The Endor Labs MCP server integrates directly into your IDE to scan code in real-time, and catch security issues before they reach production. This workflow secures both human and AI-generated code from the moment it’s written. For more information, see [Endor Labs MCP Server](../../../deployment/mcp/).

### Grant support access to your tenant New

You can now grant the Endor Labs support team read-only access to your tenant for a limited time. This feature enables our support team to assist you more efficiently while ensuring your data remains secure and private.

For more information, see [Grant support access](../../../administration/access-endorlabs/authorization-policies/#grant-support-access).

### Finding policies for AI models Enhancement

You can now configure two new finding policies and manage the use of AI models more effectively in your organization.

* **Restricted AI models**: Raise a finding when a repository uses an AI model that your organization has marked as restricted or allowed only in specific contexts.
* **Restricted AI model providers**: Raise a finding when a repository uses an AI model from a provider that is restricted based on your organization’s policy.

For more information, see [Detect AI models](../../../ai/ai-llm/#detect-ai-models).

### Manually upgrade finding policies Enhancement

You can now upgrade a finding policy when a new version is available. Policy upgrades may include changes such as updated Rego code, new fields, parameters, or tags. After upgrading, you cannot revert the policy to its previous version.

For more information, see [Upgrade a finding policy](../../../managing-policies/finding-policies/#upgrade-a-finding-policy).

### Resolving package names from prop files Enhancement

endorctl now evaluates MSBuild properties from files like `Directory.Build.props`, enabling resolution of package names and versions defined using variables.

For more information, see [Resolving package names from props files](../../../scan-with-endorlabs/language-scanning/dotnet/#resolving-package-names-from-props-files).

### Group findings by dependency Enhancement

Findings in the **SCA**, **Vulnerability**, and **Container** categories are now grouped by **Dependency** by default, making it easier to review your scans.

For more information, see [View findings](../../../managing-projects/view-findings/).

### AI model discovery in Endor Labs monitoring scans Enhancement

Endor Labs now automatically detects AI models during SCA scans when using the GitHub App, Bitbucket App, Azure DevOps App, and GitLab App. You can view AI models from the **AI Inventory**.

For more information, see [View AI model findings using Endor Labs GitHub App](../../../ai/ai-llm/#view-AI-model-findings-through-monitoring-scans).

### Components field support for Jira tickets Enhancement

You can now configure the Jira integration in Endor Labs to automatically populate the **Components** field in Jira tickets for both company-managed and team-managed Jira projects.

For more information, see [Integrate Jira with Endor Labs](../../../integrations/jira-integration/#configure-jira-integration-on-endor-labs).

### Exclude all child namespaces Enhancement

By default, the Endor Labs dashboard includes data from all child namespaces. Use the **All child namespaces excluded** toggle to exclude child namespaces and view data and metrics for only the selected namespace.

For more information, see [Namespaces in Endor Labs](../../../administration/namespaces/#namespaces-in-an-organization).

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

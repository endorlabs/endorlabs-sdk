---
url: https://docs.endorlabs.com/deployment/mcp/
title: Endor Labs MCP server | Endor Labs Docs
downloaded: 2026-02-03 00:49:59
---

Endor Labs MCP server | Endor Labs Docs



* Type to search...

[Print entire section](/deployment/mcp/_print.html)



# Endor Labs MCP server

Learn how to deploy and run the Endor Labs MCP server in your AI generated coding workflows.

Beta

MCP (Model Context Protocol) is an open standard that defines a consistent way for applications to share relevant context and information with Large Language Models (LLMs). MCP servers expose specific capabilities through the standardized Model Context Protocol. For more information on MCP, refer to the [MCP documentation](https://modelcontextprotocol.io/introduction).

The Endor Labs MCP server integrates seamlessly into your development workflow, scanning your code as you write. You can catch issues long before they’re a problem in production. It plugs directly into your IDE, tightening the feedback loop for both human and AI-generated code. Thus, you can quickly secure your code from the start. With Endor Labs, you’re bringing security all the way left, getting real-time, proactive insights and automated fixes in your editor, while you build, minimizing last-minute security scrambles.

## How Endor Labs MCP server helps your development workflow

Endor Labs MCP server helps your developers and AI agents in their development workflows in the following ways:

* **Provide guardrails for agents before code review**: Reduce the number of known vulnerabilities entering your code and save developers time by checking AI agent suggestions in real time. Integrate security before an issue is discovered in CI or in production.
* **Improve the speed of remediating security risks**: Agents uses vulnerability context from Endor Labs to help implement secure changes, from writing more secure code to upgrading dependencies.

## How to use the Endor Labs MCP server

The Endor Labs MCP server has two editions.

* **Developer Edition**: A free edition that requires no configuration. A browser window opens on first use for authentication via GitHub, GitLab, or Google. The Developer Edition provides access to default security policies from Endor Labs.
* **Enterprise Edition**: A paid edition that enforces your organization’s specific security policies. Authenticate using Google, GitHub, GitLab, or SSO. You must specify your namespace to access your organization’s policies.

Additionally, if you already have Endor Labs configured locally (for example, from a previous `endorctl init` command), the MCP server can use your pre-existing configuration.

## Tools in the Endor Labs MCP server

The Endor Labs MCP server provides the following tools:

* `check_dependency_for_vulnerabilities`: Check if the dependencies in your project are vulnerable.
* `get_endor_vulnerability`: Get the details of a specific vulnerability from the Endor Labs vulnerability database.
* `get_resource`: Add additional context from commonly used Endor Labs resources about your software such as findings, vulnerabilities, and projects.
* `scan`: Run an Endor Labs security scan to detect risks in your open source dependencies, find common security issues, and spot any credentials accidentally exposed in your Git repository.

After you set up the MCP server, you can choose to disable the tools that you do not want to use.

## Choose your IDE or platform to get started

[### Cursor

Deploy and configure the Endor Labs MCP server in Cursor for AI-powered development workflows.](/deployment/mcp/cursor/)
[### Visual Studio Code

Integrate the Endor Labs MCP server with Visual Studio Code and GitHub Copilot.](/deployment/mcp/vscode/)
[### IntelliJ IDEA

Configure the Endor Labs MCP server in IntelliJ IDEA with GitHub Copilot.](/deployment/mcp/intellij/)
[### Gemini Extension

Configure the Endor Labs MCP server as a Gemini extension for enhanced AI development.](/deployment/mcp/gemini/)

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

---
url: https://docs.endorlabs.com/deployment/mcp/gemini/
title: Endor Labs MCP server as a Gemini Extension | Endor Labs Docs
downloaded: 2026-01-16 09:49:16
---

Endor Labs MCP server as a Gemini Extension | Endor Labs Docs



* Type to search...

[Print entire section](/deployment/mcp/gemini/_print.html)



# Endor Labs MCP server as a Gemini Extension

Learn how to deploy and run the Endor Labs MCP as a Gemini Extension

Beta

The Endor Labs Model Context Protocol (MCP) server integrates seamlessly into your AI-native development workflows to help you keep your code secure and fix security risks faster. You can catch issues long before they’re a problem in production and fix them faster when they already are.

Endor Labs MCP server is available as a Gemini extension. After you install the extension, you can use natural language commands to interact with the MCP server. You can find the extension [on GitHub](https://github.com/endorlabs/gemini-extension).

This guide details how to integrate Endor Labs security capabilities directly into your Gemini development workflows using MCP.

## How Endor Labs MCP server helps your Gemini workflow

Endor Labs MCP server helps your developers and AI agents in their development workflows in the following ways:

* **Provide guardrails for agents before code review**: Reduce the number of known vulnerabilities entering your code and save developers time by checking AI agent suggestions in real time. Integrate security before an issue is discovered in CI or in production.
* **Improve the speed of remediating security risks**: Agents uses vulnerability context from Endor Labs to help implement secure changes, from writing more secure code to upgrading dependencies.

## How to use the Endor Labs MCP server

The Endor Labs MCP server has two editions.

* **Developer Edition**: A free edition that requires no configuration. A browser window opens on first use for authentication via GitHub, GitLab, or Google. The Developer Edition provides access to default security policies from Endor Labs.
* **Enterprise Edition**: A paid edition that enforces your organization’s specific security policies. Authenticate using Google, GitHub, GitLab, or SSO. You must specify your namespace to access your organization’s policies.

Additionally, if you already have Endor Labs configured locally (for example, from a previous `endorctl init` command), the MCP server can use your pre-existing configuration.

## Integrate Endor Labs MCP server into Gemini

Complete the following tasks to integrate Endor Labs MCP Server into Gemini.

* Install the Endor Labs MCP server as a Gemini extension. See [Install the Endor Labs MCP server as a Gemini extension](#install-the-endor-labs-mcp-server-as-a-gemini-extension) for more details. No configuration is required to get started with the Developer Edition.
* Configure permissions for your developers (optional): If you’re using the Enterprise Edition with a specific namespace, ensure that your developers have `Read-Only` permissions to Endor Labs. See [Endor Lab’s Authorization policies](../../../administration/access-endorlabs/authorization-policies/) for more details.

### Set up Endor Labs MCP server on Windows

On Windows, ensure the following prerequisites are met:

* [Node.js is installed](#install-nodejs)
* [npm global bin directory is in your PATH](#configure-the-path-environment-variable)

#### Install Node.js

If Node.js is not installed, download and install the **LTS version** from [nodejs.org](https://nodejs.org/). During installation, ensure the option to add Node.js to PATH is selected.

#### Configure the PATH environment variable

After installing Node.js, verify that the npm global bin directory is in your PATH:

1. Run the following command in the command line.

   ```
   npm config get prefix
   ```

   This returns the npm global directory path, typically `C:\Users\<YourUsername>\AppData\Roaming\npm`.
2. Add the npm global directory path to the **Path** variable under **User variables** in your system’s environment variables settings.
3. Restart for the PATH changes to take effect.

#### Verify the setup

Run the following command in your terminal.

```
npx --version
```

If this returns a version number, your Windows setup is complete and the MCP server can use `npx` to run endorctl.

## Tools in the Endor Labs MCP server

The Endor Labs MCP server provides the following tools:

* `check_dependency_for_vulnerabilities`: Check if the dependencies in your project are vulnerable.
* `get_endor_vulnerability`: Get the details of a specific vulnerability from the Endor Labs vulnerability database.
* `get_resource`: Add additional context from commonly used Endor Labs resources about your software such as findings, vulnerabilities, and projects.
* `scan`: Run an Endor Labs security scan to detect risks in your open source dependencies, find common security issues, and spot any credentials accidentally exposed in your Git repository.

After you set up the MCP server, you can choose to disable the tools that you do not want to use.

## Install the Endor Labs MCP server as a Gemini extension

Run the following command to install the Endor Labs MCP server as a Gemini extension.

```
gemini extensions install https://github.com/endorlabs/gemini-extension.git
```

## Verify the Endor Labs MCP server installation

Run the following command in the Gemini CLI to verify the Endor Labs MCP server installation.

```
gemini> /mcp list
```

The following output appears if the Endor Labs MCP server is installed.

![Verify the Endor Labs MCP server Gemini installation](../../../images/mcp-server-installed-gemini.png)

## Initialize the Endor Labs MCP server in Gemini CLI

After you install the Endor Labs MCP server as a Gemini extension, you can optionally initialize the MCP server in Gemini CLI.

### Developer Edition

The Endor Labs MCP server works out of the box with the Developer Edition. When you use the MCP server for the first time, a browser window opens, and you can authenticate with GitHub, GitLab, or Google. After authentication, the MCP server provides access to the free Developer Edition with default security policies.

You can use the MCP server without initialization. When you first use a tool, a browser window will open allowing you to authenticate with GitHub, GitLab, or Google. The MCP server will automatically use the Developer Edition with default security policies.

### Use pre-existing configuration

If you already have Endor Labs configured locally (from a previous [endorctl initialization](/endorctl/commands/init/)), the MCP server uses your local configuration. The configuration already contains the namespace information, so you don’t need to specify it separately.

### Enterprise Edition

If you want to use the Enterprise Edition with your organization’s specific policies, you can use natural language commands to initiate an authentication flow. Run `endorctl init` and your browser window will open automatically. Select your authentication provider from the available options and complete the authentication process.

You can also specify your supported authentication provider manually.

```
gemini> Initialize Endor Labs with Google authentication using the command `endorctl init --auth-mode=google`
```

You can use any supported authentication mode: `google`, `github`, `gitlab`, or `sso`. If you choose `sso`, you must also provide your tenant name. Existing users with read-only permissions on a namespace can authenticate to their namespace through the browser.

## Use Endor Labs MCP server in Gemini CLI

After you initialize the MCP server, you can converse with the MCP server using natural language commands to get information about your projects, vulnerabilities, and dependencies.

The following examples show how to use the Endor Labs MCP server in Gemini CLI. Always navigate to the project directory before using the MCP server.

### Example: Scan for security vulnerabilities in your project

```
gemini> Scan my project for security vulnerabilities
```

### Example: Check dependencies for known CVEs

```
gemini> Check dependencies for known CVEs
```

### Example: Generate a security report for this repository

```
gemini> Generate a security report for this repository
```

## Gemini context file

The Endor Labs MCP server provides a context file that you can use to add additional context to the MCP server. The context file, `ENDORLABS_CONTEXT.md` is located in the `~/.gemini/extensions/Endor-Labs-Code-Security/` directory.

You can use the context file to add additional context to the MCP server. For example, you can add additional rules and context for your project in the context file.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

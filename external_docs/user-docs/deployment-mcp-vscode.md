---
url: https://docs.endorlabs.com/deployment/mcp/vscode/
title: Endor Labs MCP server in Visual Studio Code | Endor Labs Docs
downloaded: 2026-01-29 22:21:17
---

Endor Labs MCP server in Visual Studio Code | Endor Labs Docs



* Type to search...

[Print entire section](/deployment/mcp/vscode/_print.html)



# Endor Labs MCP server in Visual Studio Code

Learn how to deploy and run the Endor Labs MCP server in Visual Studio Code.

Beta

The Endor Labs Model Context Protocol (MCP) server integrates seamlessly into your AI-native development workflows to help you keep your code secure and fix security risks faster. You can catch issues long before they’re a problem in production and fix them faster when they already are.

This guide details how to integrate Endor Labs security capabilities directly into your Visual Studio Code development workflows using MCP.

## How Endor Labs MCP server helps your Visual Studio Code workflow

Endor Labs MCP server helps your developers and AI agents in their development workflows in the following ways:

* **Provide guardrails for agents before code review**: Reduce the number of known vulnerabilities entering your code and save developers time by checking AI agent suggestions in real time. Integrate security before an issue is discovered in CI or in production.
* **Improve the speed of remediating security risks**: Agents uses vulnerability context from Endor Labs to help implement secure changes, from writing more secure code to upgrading dependencies.

## How to use the Endor Labs MCP server

The Endor Labs MCP server has two editions.

* **Developer Edition**: A free edition that requires no configuration. A browser window opens on first use for authentication via GitHub, GitLab, or Google. The Developer Edition provides access to default security policies from Endor Labs.
* **Enterprise Edition**: A paid edition that enforces your organization’s specific security policies. Authenticate using Google, GitHub, GitLab, or SSO. You must specify your namespace to access your organization’s policies.

Additionally, if you already have Endor Labs configured locally (for example, from a previous `endorctl init` command), the MCP server can use your pre-existing configuration.

## Integrate Endor Labs MCP server into Visual Studio Code

Complete the following tasks to integrate Endor Labs MCP Server into Visual Studio Code.

* Configure the MCP server: Configure the MCP server in Visual Studio Code. You can use the interactive configuration tool or manually configure the MCP server. See [Configure the MCP server in Visual Studio Code](#configure-the-mcp-server-in-visual-studio-code) for more details. No configuration is required to get started with the Developer Edition.
* Configure permissions for your developers (optional): If you’re using the Enterprise Edition with a specific namespace, ensure that your developers have `Read-Only` permissions to Endor Labs. See [Endor Lab’s Authorization policies](../../../administration/access-endorlabs/authorization-policies/) for more details.

### Configure the MCP server in Visual Studio Code

**Prerequisites for Visual Studio Code**

Before running the Endor Labs MCP server, ensure that you have Visual Studio Code version 1.99 or later and enable MCP support by setting `chat.mcp.enabled` to `true` in your [Visual Studio Code settings](vscode://settings/chat.mcp.enabled).

Visual Studio Code allows you to set MCP configurations at the project and the user level.

You can manually configure the MCP server or use the interactive configuration tool to generate a one-click installation link for Visual Studio Code.

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

### Developer Edition

The Endor Labs MCP server works out of the box with the Developer Edition. When you use the MCP server for the first time, a browser window opens, and you can authenticate with GitHub, GitLab, or Google. After authentication, the MCP server provides access to the free Developer Edition with default security policies.

Add the following configuration to the `.vscode/mcp.json` file to use the Endor Labs MCP server with the Developer Edition.

```
{
  "servers": {
    "endor-cli-tools": {
      "command": "npx",
      "args": [
        "-y",
        "endorctl",
        "ai-tools",
        "mcp-server"
      ]
    }
  }
}
```

### Interactive MCP server configuration

Use our interactive configuration tool to generate a one-click installation link for Visual Studio Code. You can configure all the necessary parameters and generate a Visual Studio Code link that you can click to automatically install the MCP server.

### Endor Labs MCP Server Installation

Configure your MCP server parameters and generate a json configuration.

Edition

Developer Edition
Enterprise Edition (Google)
Enterprise Edition (GitHub)
Enterprise Edition (GitLab)
Enterprise Edition (SSO)

Choose your edition.

Developer Edition is free with default policies. Enterprise Edition uses your organization's policies.

Tenant \*


Tenant name for SSO authentication.

Required when using SSO. Enter your organization's tenant name.

Namespace \*


Your Endor Labs namespace.

Required for Enterprise Edition. Only alphanumeric characters, dots, hyphens, and underscores
are allowed.

Use pre-existing configuration

Check this if you already have Endor Labs configured locally (from `endorctl init`). Your local configuration will be used.

Reset

Generate

Fill in your configuration above and click **Generate** to create a JSON configuration.

MCP server configuration for mcp.json

Copy

### Manual MCP server configuration at the repository level

1. Navigate to the root of your repository.
2. Create a `.vscode` directory if it doesn’t exist and create an `mcp.json` file in the `.vscode` directory.

   ```
   mkdir -p .vscode && touch .vscode/mcp.json
   ```
3. Add the following configuration to the `.vscode/mcp.json` file.

   **Developer Edition**

   ```
   {
     "servers": {
       "endor-cli-tools": {
         "command": "npx",
         "args": [
           "-y",
           "endorctl",
           "ai-tools",
           "mcp-server"
         ]
       }
     }
   }
   ```

   **Use pre-existing configuration**

   ```
   {
     "servers": {
       "endor-cli-tools": {
         "command": "npx",
         "args": [
           "-y",
           "endorctl",
           "ai-tools",
           "mcp-server"
         ],
         "env": {
           "ENDOR_TOKEN": "automatic"
         }
       }
     }
   }
   ```

   Your local configuration already contains the namespace information, so you don’t need to specify `ENDOR_NAMESPACE` separately.

   **Enterprise Edition**

   ```
   {
     "servers": {
       "endor-cli-tools": {
         "command": "npx",
         "args": [
           "-y",
           "endorctl",
           "ai-tools",
           "mcp-server"
         ],
         "env": {
           "ENDOR_NAMESPACE": "<namespace>",
           "ENDOR_MCP_SERVER_AUTH_MODE": "<google|github|gitlab|sso>",
           "ENDOR_TOKEN": "automatic"
         }
       }
     }
   }
   ```

   For Enterprise Edition, specify your namespace and choose an authentication mode. If you choose `sso`, you must also add `ENDOR_MCP_SERVER_AUTH_TENANT` to the `env` section.

   The following parameters are used to configure the MCP server. All parameters are optional. If no parameters are provided, the MCP server defaults to the Developer Edition with browser authentication.

   * `ENDOR_MCP_SERVER_AUTH_MODE`: (Optional) The authentication mode to use for the MCP server. You can use the following authentication modes: `github`, `gitlab`, `google`, `sso`. If you choose `sso`, you must add `ENDOR_MCP_SERVER_AUTH_TENANT` as an additional parameter. If not specified, the MCP server defaults to browser authentication for the Developer Edition.
   * `ENDOR_NAMESPACE`: (Optional) The namespace to use for the MCP server. Required for Enterprise Edition to access your organization’s specific policies. Not needed for Developer Edition.
   * `ENDOR_TOKEN`: (Optional) The token to use for the MCP server. Do not set this value manually. It will be set automatically by the MCP server during authentication.
   * `ENDOR_MCP_SERVER_AUTH_TENANT`: (Optional) The tenant name for SSO authentication. Required when `ENDOR_MCP_SERVER_AUTH_MODE` is set to `sso` for Enterprise Edition access.

### Manage Endor Labs MCP server tools in Visual Studio Code

1. Open the **Chat** view by pressing **Cmd+Option+I**.
2. Switch to the **Agent** mode.
3. Click the **Settings** icon.
4. Select the tools that you want to enable or disable under **MCP Server: endor-cli-tools**.

### Use the MCP server with GitHub Copilot

To use the Endor Labs MCP server with GitHub Copilot in Visual Studio Code:

1. Open the **Chat** view by pressing **Cmd+Option+I**.
2. Switch to the **Agent** mode.
3. Click the **Settings** icon.
4. Select **MCP Server: endor-cli-tools** from the dropdown menu.
5. Set up Copilot rules in `.github/instructions/*.md` to use the Endor Labs MCP server throughout the development process. See Copilot rules examples to learn more.

You can now use Endor Labs tools in your chat prompts to scan for vulnerabilities.

## Example Copilot rules

Copilot instructions define the guidelines that Copilot should follow throughout the development process. The following examples demonstrate how to use the Endor Labs MCP server within Copilot rules.

* SCA Rule Example
* Secrets Rule Example
* SAST Rule Example

```
---
description: "Ensure newly added dependencies are checked for vulnerabilities and project stays clean"
applyTo: '**/package.json, **/package-lock.json, **/yarn.lock, **/pnpm-lock.yaml, **/requirements.txt, **/Pipfile, **/Pipfile.lock, **/pyproject.toml, **/poetry.lock, **/go.mod, **/go.sum, **/Cargo.toml, **/Cargo.lock, **/pom.xml, **/build.gradle, **/build.gradle.kts, **/gradle.lockfile, **/composer.json, **/composer.lock'
alwaysApply: true
---

# Software Composition Analysis (SCA) Rule (Endor Labs via MCP)
This project uses Endor Labs for automated dependency (SCA) scanning, integrated through the MCP server as configured in `.vscode/mcp.json`.

## Workflow

Every time a manifest or lockfile listed above is created or modified in any way immediately do the following prior to performing your next task.

**Important**: Do not proceed after creating or modifying a manifest file without running this first. Do not write any other code or continue with your existing prompt. This is top priority whenever a manifest file is created or updated.

- Run `endor-cli-tools` using the `check_dependency_for_vulnerabilities` tool via the MCP server.
- Provide the **ecosystem**, **dependency name**, and **version** always when making this tool call. Do not forget to provide a version.
- If a vulnerability or error is identified:
  - Upgrade to the suggested safe version, or
  - Replace the dependency with a non-vulnerable alternative.
  - The AI agent must attempt to automatically correct all detected errors and vulnerabilities before session completion.
- Re-run the check using `endor-cli-tools` to confirm the issue is resolved.
- If an error occurs in any MCP server tool call (such as missing required parameters like version, invalid arguments, or tool invocation failures):
  - The AI agent must review the error, determine the cause, and automatically correct the tool call or input parameters.
  - Re-attempt the tool call with the corrected parameters.
  - Continue this process until the tool call succeeds or it is determined that remediation is not possible, in which case the issue and reason must be reported.

## Notes
- All scans must be performed using the MCP server integration (`endor-cli-tools`) as configured in `.vscode/mcp.json`. Do not invoke `endorctl` directly.
- For troubleshooting, ensure the MCP server is running and `endorctl` is installed and accessible in your environment.

This rule ensures that all dependency changes are evaluated for risk at the time of introduction, and that the project remains clean and secure after each coding session. The scan may be performed at the end of an agent session, provided all modifications are checked and remediated before session completion.
```

```
---
description: "Scan for leaked secrets on file modification"
applyTo: '**/*'
alwaysApply: true
---

# Leaked Secrets Detection Rule (Endor Labs via MCP)
This project uses @Endor Labs for automated security scanning, integrated through the MCP server as configured in `.vscode/mcp.json`.

## Workflow
Whenever a file is modified in the repository, and before the end of an agent session:
- Run `endor-cli-tools` using the `scan` tool via the MCP server to check for leaked secrets.
- Ensure the scan includes all file types and respects `.gitignore` unless otherwise configured.
- If any secrets or errors are detected:
  - Remove the exposed secret or correct the error immediately.
  - The AI agent must attempt to automatically correct all detected secrets and errors before session completion.
  - Re-run the scan to verify the secret or error has been properly removed or resolved.
- If an error occurs in any MCP server tool call (such as missing required parameters like version, invalid arguments, or tool invocation failures):
  - The AI agent must review the error, determine the cause, and automatically correct the tool call or input parameters.
  - Re-attempt the tool call with the corrected parameters.
  - Continue this process until the tool call succeeds or it is determined that remediation is not possible, in which case the issue and reason must be reported.
- Save scan results and remediation steps in a security log or as comments for audit purposes.

## Notes
- All scans must be performed using the MCP server integration (`endor-cli-tools`) as configured in `.vscode/mcp.json`. Do not invoke `endorctl` directly.
- For troubleshooting, ensure the MCP server is running and `endorctl` is installed and accessible in your environment.
- **Important**: This scan must use the path of the directory from which the changed files are in. Do not attempt to set the path directly to a file as it must be a directory. Use absolute paths like /Users/username/mcp-server-demo/backend rather than relative paths like 'backend'

This rule ensures no accidental credentials, tokens, API keys, or secrets are committed or remain in the project history. The scan may be performed at the end of an agent session, provided all modifications are checked and remediated before session completion.
```

```
---
description: "Run SAST scan using endor-cli-tools on source code changes"
applyTo: '**/*.c, **/*.cpp, **/*.cc, **/*.cs, **/*.go, **/*.java, **/*.js, **/*.jsx, **/*.ts, **/*.tsx, **/*.py, **/*.php, **/*.rb, **/*.rs, **/*.kt, **/*.kts, **/*.scala, **/*.swift, **/*.dart, **/*.html, **/*.yaml, **/*.yml, **/*.json, **/*.xml, **/*.sh, **/*.bash, **/*.clj, **/*.cljs, **/*.ex, **/*.exs, **/*.lua'
alwaysApply: true
---

# Static Application Security Testing (SAST) Rule (Endor Labs via MCP)

This project uses @Endor Labs for automated SAST, integrated through the MCP server as configured in `.vscode/mcp.json`.

## Workflow

Whenever a file is modified in the repository, and before the end of an agent session perform the following workflow:

- Run `endor-cli-tools` using the `scan` tool via the MCP server to perform SAST scans as described above.
- If any vulnerabilities or errors are found:
  - Present the issues to the user.
  - The AI agent must attempt to automatically correct all errors and vulnerabilities, including code errors, security issues, and best practice violations, before session completion.
  - Recommend and apply appropriate fixes (e.g., input sanitization, validation, escaping, secure APIs).
  - Continue scanning and correcting until all critical issues have been resolved or no further automated remediation is possible.
- If an error occurs in any MCP server tool call (such as missing required parameters like version, invalid arguments, or tool invocation failures):
  - The AI agent must review the error, determine the cause, and automatically correct the tool call or input parameters.
  - Re-attempt the tool call with the corrected parameters.
  - Continue this process until the tool call succeeds or it is determined that remediation is not possible, in which case the issue and reason must be reported.
- Save scan results and remediation steps in a security log or as comments for audit purposes.

## Notes
- All scans must be performed using the MCP server integration (`endor-cli-tools`) as configured in `.vscode/mcp.json`. Do not invoke `endorctl` directly.
- For troubleshooting, ensure the MCP server is running and `endorctl` is installed and accessible in your environment.
- Do not invoke Opengrep directly.
- **Important**: This scan must use the path of the directory from which the changed files are in. Do not attempt to set the path directly to a file as it must be a directory. Use absolute paths like /Users/username/mcp-server-demo/backend rather than relative paths like 'backend'

This rule ensures all code changes are automatically reviewed and remediated for common security vulnerabilities and errors using `endor-cli-tools` and the MCP server, with Opengrep as the underlying engine.
```

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

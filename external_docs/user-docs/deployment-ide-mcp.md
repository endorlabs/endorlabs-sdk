---
url: https://docs.endorlabs.com/deployment/ide/mcp/
title: Endor Labs MCP server | Endor Labs Docs
downloaded: 2025-11-20 11:49:11
---

Endor Labs MCP server | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/deployment/ide/mcp/_print.html)



# Endor Labs MCP server

Learn how to deploy and run the Endor Labs MCP server in your IDE.

Beta

MCP (Model Context Protocol) is an open standard that defines a consistent way for applications to share relevant context and information with Large Language Models (LLMs). MCP servers expose specific capabilities through the standardized Model Context Protocol. For more information on MCP, refer to the [MCP documentation](https://modelcontextprotocol.io/introduction).

The Endor Labs MCP server integrates seamlessly into your development workflow, scanning your code as you write. You can catch issues long before they’re a problem in production. It plugs directly into your IDE, tightening the feedback loop for both human and AI-generated code. Thus, you can quickly secure your code from the start. With Endor Labs, you’re bringing security all the way left, getting real-time, proactive insights and automated fixes in your editor, while you build, minimizing last-minute security scrambles.

#### Note

Endor Labs MCP server is available on macOS. Endor Labs MCP server is not currently tested or fully supported on Windows workstations.

## Tools in the Endor Labs MCP server

The Endor Labs MCP server provides the following tools:

* `check_dependency_for_vulnerabilities`: Check if the dependencies in your project are vulnerable.
* `get_endor_vulnerability`: Get the details of a specific vulnerability from the Endor Labs vulnerability database.
* `get_resource`: Add additional context from commonly used Endor Labs resources about your software such as findings, vulnerabilities, and projects.
* `scan`: Run an Endor Labs security scan to detect risks in your open source dependencies, find common security issues, and spot any credentials accidentally exposed in your Git repository.

After you set up the MCP server, you can choose to disable the tools that you do not want to use.

## Prerequisites to run the Endor Labs MCP server

Before running the Endor Labs MCP server, ensure that you [install the latest version of endorctl](../../../getting-started/quickstart/quickstart-local-system/#install-endor-labs-on-your-local-system) and [authenticate](../../../getting-started/quickstart/quickstart-local-system/#authenticate-to-endor-labs) to Endor Labs. The authenticated user must have at least `Code Scanner` and `Read-Only` permissions.

## Configure the MCP server in Cursor

We recommend that you add the MCP server to the local Cursor settings rather than the user settings to keep the configuration project-specific.

You can configure the MCP server either through the interactive configuration tool or manually.

### Interactive MCP server configuration

Use our interactive configuration tool to generate a one-click installation link for Cursor. You can configure all the necessary parameters and generate a Cursor link that you can click to automatically install the MCP server.

### Endor Labs MCP Server Installation

Configure your MCP server parameters and generate a one-click install link for Cursor.

endorctl Command Path


The full path to the endorctl executable.

Run `which endorctl` to get the path.
Enter `endorctl` if endorctl is available in your PATH

Scan Languages


Comma-separated list of languages to scan.

Available: `c#`, `go`, `java`, `javascript`, `kotlin`, `objective-c`, `php`, `python`, `ruby`, `rust`, `scala`, `swift`, `typescript`

Scan Path (Optional)


Path to the workspace root directory to scan.

Namespace (Optional)


Your Endor Labs namespace.

If left blank, the namespace configured in your machine will be used.

Reset

Generate

Fill in your configuration above and click **Generate** to create a one-click installation link for Cursor.

#### One-click MCP server installation

Click the following button to install the Endor Labs MCP server in Cursor

[Add Endor Labs MCP Server to Cursor](#)

MCP server configuration preview

After you click **Add Endor Labs MCP server**, MCP Settings opens in Cursor.

![MCP Settings](../../../images/mcp-settings.png)

You can verify the configuration and click **Install** to complete the installation.

### Manual MCP server configuration

1. Navigate to the root of your repository.
2. Create a `.cursor` directory if it doesn’t exist and create an `mcp.json` file in the `.cursor` directory.

   ```
   mkdir -p .cursor && touch .cursor/mcp.json
   ```
3. Add the following configuration to the `.cursor/mcp.json` file.

   ```
   {
     "mcpServers": {
       "endor-cli-tools": {
         "type": "stdio",
         "command": "endorctl",
         "args": [
           "ai-tools",
           "mcp-server"
         ],
         "env": {
           "MCP_ENDOR_SCAN_LANGUAGES": "<languages to scan>"
         }
       }
     }
   }
   ```

The following parameters are commonly used to optimize MCP server performance.

* `command`: The full path to the endorctl executable. Run `which endorctl` to fetch the path of the endorctl executable.
* `MCP_ENDOR_SCAN_LANGUAGES`: The programming languages to scan. You can use the following languages: `c#, go, java, javascript, kotlin, objective-c, php, python, ruby, rust, scala, swift, typescript`. Enter multiple languages separated by commas. For example, `"go,java,python"`.

#### Note

You can use any Endor Labs environment variable for the `endorctl scan` command in the MCP server configuration. However, you must prefix all Endor Labs environment variables with `MCP_`. See [Endor Labs environment variables](../../../endorctl/commands/scan/#options) for more information.

### Manage Endor Labs MCP server tools in Cursor

1. Navigate to the **Settings** > **Cursor Settings** > **MCP**.
2. Click the tool that you want to disable under **endor-cli-tools**.

   Click on a disabled tool to enable it.

### Configure Cursor rules

To enhance the MCP server integration you can add custom rules for your project. These rules are custom prompts specific to your project.

1. Navigate to the root of your repository.
2. In the `.cursor/rules` directory, create an `.mdc` file to add specific instructions.
3. Add appropriate rules for your project in the `.cursor/rules/endorlabs.mdc` file. For example, you can add a rule to check if the code is free from vulnerabilities.

#### Example Cursor rules

You can use the following Cursor rules as a quick start for the Endor Labs MCP server. Modify the rules to meet your specific organization’s needs. We recommended that you store each cursor rule in a separate file. For more information, refer to the [Cursor documentation](https://docs.cursor.com/context/rules).

* SCA Rule Example
* Secrets Rule Example
* SAST Rule Example

```
---
description: Ensure newly added dependencies are checked for vulnerabilities and project stays clean
globs: '**/package.json, **/package-lock.json, **/yarn.lock, **/pnpm-lock.yaml, **/requirements.txt, **/Pipfile, **/Pipfile.lock, **/pyproject.toml, **/poetry.lock, **/go.mod, **/go.sum, **/Cargo.toml, **/Cargo.lock, **/pom.xml, **/build.gradle, **/build.gradle.kts, **/gradle.lockfile, **/composer.json, **/composer.lock'
alwaysApply: true
---

# Software Composition Analysis (SCA) Rule (Endor Labs via MCP)
This project uses Endor Labs for automated dependency (SCA) scanning, integrated through the MCP server as configured in `.cursor/mcp.json`.

## Workflow

Every time a manifest or lockfile listed above is created or modified in any way immediantly do the following prior to performing your next task.

**Important**: Do not procceed after creating or modifying a manifest file without running this first. Do not write any other code or continue with your existing prompt. This is top priority whenever a manifest file is created or updated.

- Run `endor-cli-tools` using the `check_dependency_for_vulnerabilities` tool via the MCP server.
- Provide the **language**, **dependency name**, and **version** always when making this tool call. Do not forget to provide a version.
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
- All scans must be performed using the MCP server integration (`endor-cli-tools`) as configured in `.cursor/mcp.json`. Do not invoke `endorctl` directly.
- For troubleshooting, ensure the MCP server is running and `endorctl` is installed and accessible in your environment.

This rule ensures that all dependency changes are evaluated for risk at the time of introduction, and that the project remains clean and secure after each coding session. The scan may be performed at the end of an agent session, provided all modifications are checked and remediated before session completion.
```

```
---
description: Scan for leaked secrets on file modification
globs: '**/*'
alwaysApply: true
---

# Leaked Secrets Detection Rule (Endor Labs via MCP)
This project uses @Endor Labs for automated security scanning, integrated through the MCP server as configured in `.cursor/mcp.json`.

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
- All scans must be performed using the MCP server integration (`endor-cli-tools`) as configured in `.cursor/mcp.json`. Do not invoke `endorctl` directly.
- For troubleshooting, ensure the MCP server is running and `endorctl` is installed and accessible in your environment.
- **Important**: This scan must use the path of the directory from which the changed files are in. Do not attempt to set the path directly to a file as it must be a directory. Use absolute paths like /Users/username/mcp-server-demo/backend rather than relative paths like 'backend'

This rule ensures no accidental credentials, tokens, API keys, or secrets are committed or remain in the project history. The scan may be performed at the end of an agent session, provided all modifications are checked and remediated before session completion.
```

```
---
description: Run SAST scan using endor-cli-tools on source code changes
globs: '**/*.c, **/*.cpp, **/*.cc, **/*.cs, **/*.go, **/*.java, **/*.js, **/*.jsx, **/*.ts, **/*.tsx, **/*.py, **/*.php, **/*.rb, **/*.rs, **/*.kt, **/*.kts, **/*.scala, **/*.swift, **/*.dart, **/*.html, **/*.yaml, **/*.yml, **/*.json, **/*.xml, **/*.sh, **/*.bash, **/*.clj, **/*.cljs, **/*.ex, **/*.exs, **/*.lua'
alwaysApply: true
---

# Static Application Security Testing (SAST) Rule (Endor Labs via MCP)

This project uses Endor Labs for automated SAST, integrated through the MCP server as configured in `.cursor/mcp.json`.

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
- All scans must be performed using the MCP server integration (`endor-cli-tools`) as configured in `.cursor/mcp.json`. Do not invoke `endorctl` directly.
- For troubleshooting, ensure the MCP server is running and `endorctl` is installed and accessible in your environment.
- Do not invoke Opengrep directly.
- **Important**: This scan must use the path of the directory from which the changed files are in. Do not attempt to set the path directly to a file as it must be a directory. Use absolute paths like /Users/username/mcp-server-demo/backend rather than relative paths like 'backend'

This rule ensures all code changes are automatically reviewed and remediated for common security vulnerabilities and errors using `endor-cli-tools` and the MCP server, with Opengrep as the underlying engine.
```

## Configure the MCP server in Visual Studio Code

We recommend that you add the MCP server to the local Visual Studio Code settings rather than the user settings to keep the configuration project-specific.

#### Prerequisites for Visual Studio Code

Before running the Endor Labs MCP server, ensure that you have Visual Studio Code version 1.99 or later and enable MCP support by setting `chat.mcp.enabled` to `true` in your [Visual Studio Code settings](vscode://settings/chat.mcp.enabled).

Add the Endor Labs MCP server to local Visual Studio Code settings.

1. Navigate to the root of your repository.
2. Create a `.vscode` directory if it doesn’t exist and create an `mcp.json` file in the `.vscode` directory.
3. You can use the interactive configuration tool to generate the MCP server configuration for Visual Studio Code.

   ### Endor Labs MCP Server Installation

   Configure your MCP server parameters and generate a json configuration.

   endorctl Command Path


   The full path to the endorctl executable.

   Run `which endorctl` to get the path.
   Enter `endorctl` if endorctl is available in your PATH

   Scan Languages


   Comma-separated list of languages to scan.

   Available: `c#`, `go`, `java`, `javascript`, `kotlin`, `objective-c`, `php`, `python`, `ruby`, `rust`, `scala`, `swift`, `typescript`

   Scan Path (Optional)


   Path to the workspace root directory to scan.

   Namespace (Optional)


   Your Endor Labs namespace.

   If left blank, the namespace configured in your machine will be used.

   Reset

   Generate

   Fill in your configuration above and click **Generate** to create a JSON configuration.

   MCP server configuration for .vscode/mcp.json

   Copy

   You can also manually add the following configuration to the `.vscode/mcp.json` file.

   ```
   {
     "servers": {
       "endor-cli-tools": {
         "type": "stdio",
         "command": "endorctl",
         "args": [
           "ai-tools",
           "mcp-server"
         ],
         "env": {
           "MCP_ENDOR_SCAN_LANGUAGES": "<languages to scan>"
         }
       }
     }
   }
   ```

   The following parameters are commonly used to optimize MCP server performance.

   * `command`: The full path to the endorctl executable. Run `which endorctl` to fetch the path of the endorctl executable.
   * `MCP_ENDOR_SCAN_LANGUAGES`: The programming languages to scan. You can use the following languages: `c#, go, java, javascript, kotlin, objective-c, php, python, ruby, rust, scala, swift, typescript`. Enter multiple languages separated by commas. For example, `"go,java,python"`.

   #### Note

   You can use any Endor Labs environment variable for the `endorctl scan` command in the MCP server configuration. However, you must prefix all Endor Labs environment variables with `MCP_`. See [Endor Labs environment variables](../../../endorctl/commands/scan/#options) for more information.
4. Copy the configuration to your `.vscode/mcp.json` file and restart Visual Studio Code to complete the installation.

### Manage Endor Labs MCP server tools in Visual Studio Code

1. Open the Chat view by pressing `Cmd+Option+I`.
2. Switch to the **Agent** mode.
3. Click the **Settings** icon.
4. Select the tools that you want to enable or disable under **MCP Server: endor-cli-tools**.

### Use the MCP server with GitHub Copilot

To use the Endor Labs MCP server with GitHub Copilot in Visual Studio Code:

1. Open the Chat view by pressing `Cmd+Option+I`.
2. Switch to the **Agent** mode.
3. Click the **Settings** icon.
4. Select **MCP Server: endor-cli-tools** from the dropdown menu.
5. Set up Copilot rules in `.github/instructions/*.md` to use the Endor Labs MCP server throughout the development process. See [Copilot rules examples](#example-copilot-rules) to learn more.

You can now use Endor Labs tools in your chat prompts to scan for vulnerabilities.

## Configure the MCP server in IntelliJ IDEA with GitHub Copilot

Include the MCP server in the local IntelliJ IDEA settings so that the configuration remains project-specific instead of applying to all user settings.

#### Prerequisites for IntelliJ

Before running the Endor Labs MCP server, ensure that you have IntelliJ IDEA version 2025.2 or later, with Copilot installed.

1. Open the **GitHub Copilot Chat** from the right sidebar.
2. Switch to **Agent** mode.
3. Click **Configure Tools**.
4. Select **+ Add More Tools…** from the bottom left corner to open the `mcp.json` and configure the Copilot rules.
5. You can use the interactive configuration tool to generate the MCP server configuration.

   ### Endor Labs MCP Server Installation

   Configure your MCP server parameters and generate a json configuration.

   endorctl Command Path


   The full path to the endorctl executable.

   Run `which endorctl` to get the path.
   Enter `endorctl` if endorctl is available in your PATH

   Scan Languages


   Comma-separated list of languages to scan.

   Available: `c#`, `go`, `java`, `javascript`, `kotlin`, `objective-c`, `php`, `python`, `ruby`, `rust`, `scala`, `swift`, `typescript`

   Scan Path (Optional)


   Path to the workspace root directory to scan.

   Namespace (Optional)


   Your Endor Labs namespace.

   If left blank, the namespace configured in your machine will be used.

   Reset

   Generate

   Fill in your configuration above and click **Generate** to create a JSON configuration.

   MCP server configuration for .vscode/mcp.json

   Copy

   You can also manually add the following configuration to the `mcp.json` file.

   ```
   {
     "servers": {
       "endor-cli-tools": {
         "type": "stdio",
         "command": "endorctl",
         "args": [
           "ai-tools",
           "mcp-server"
         ],
         "env": {
           "MCP_ENDOR_SCAN_LANGUAGES": "<languages to scan>"
         }
       }
     }
   }
   ```

   The following parameters are commonly used to optimize MCP server performance.

   * `command`: The full path to the endorctl executable. Run `which endorctl` to fetch the path of the endorctl executable.
   * `MCP_ENDOR_SCAN_LANGUAGES`: The programming languages to scan. You can use the following languages: `c#, go, java, javascript, kotlin, objective-c, php, python, ruby, rust, scala, swift, typescript`. Enter multiple languages separated by commas. For example, `"go,java,python"`.

   #### Note

   You can use any Endor Labs environment variable for the `endorctl scan` command in the MCP server configuration. However, you must prefix all Endor Labs environment variables with `MCP_`. See [Endor Labs environment variables](../../../endorctl/commands/scan/#options) for more information.
6. Save and close the `mcp.json`.
7. Switch from **Agent** to **Ask** mode in the chat and then back to **Agent** mode to access the Endor Labs MCP server.
8. Click **Configure Tools** and select **endor-cli-tools**.
9. Set up Copilot rules in `.github/instructions/*.md` to use the Endor Labs MCP server throughout the development process. See [Add repository custom instructions for GitHub Copilot](https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions?tool=jetbrains#creating-custom-instructions) and [Copilot example rules](#example-copilot-rules) to learn more.

You can now use Endor Labs tools in your chat prompts to scan for vulnerabilities.

## Example Copilot rules

Copilot instructions define the guidelines that Copilot should follow throughout the development process. The following examples demonstrate how to use the Endor Labs MCP server within Copilot rules.

* SCA Rule Example
* Secrets Rule Example
* SAST Rule Example

```
---
description: "Dependency vulnerability scanning using Endor Labs via MCP server integration"
applyTo: '**/package.json, **/package-lock.json, **/yarn.lock, **/pnpm-lock.yaml, **/requirements.txt, **/Pipfile, **/Pipfile.lock, **/pyproject.toml, **/poetry.lock, **/go.mod, **/go.sum, **/Cargo.toml, **/Cargo.lock, **/pom.xml, **/build.gradle, **/build.gradle.kts, **/gradle.lockfile, **/composer.json, **/composer.lock'
---

# Software Composition Analysis (SCA) Rule (Endor Labs via MCP)
This project uses Endor Labs for automated dependency (SCA) scanning, integrated through the MCP server as configured in `.vscode/mcp.json`.

## Workflow

Every time a manifest or lockfile listed above is created or modified in any way immediantly do the following prior to performing your next task.

**Important**: Do not procceed after creating or modifying a manifest file without running this first. Do not write any other code or continue with your existing prompt. This is top priority whenever a manifest file is created or updated.

- Run `endor-cli-tools` using the `check_dependency_for_vulnerabilities` tool via the MCP server.
- Provide the **language**, **dependency name**, and **version** always when making this tool call. Do not forget to provide a version.
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
description: "Scan for leaked secrets on file modification using Endor Labs via MCP server integration"
applyTo: '**/*'
---
# Leaked Secrets Detection Rule (Endor Labs via MCP)
This project uses [Endor Labs](https://docs.endorlabs.com/) for automated security scanning, integrated through the MCP server as configured in `.vscode/mcp.json`.

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
description: "Static Application Security Testing (SAST) using Endor Labs via MCP server integration"
applyTo: '**/*.c, **/*.cpp, **/*.cc, **/*.cs, **/*.go, **/*.java, **/*.js, **/*.jsx, **/*.ts, **/*.tsx, **/*.py, **/*.php, **/*.rb, **/*.rs, **/*.kt, **/*.kts, **/*.scala, **/*.swift, **/*.dart, **/*.html, **/*.yaml, **/*.yml, **/*.json, **/*.xml, **/*.sh, **/*.bash, **/*.clj, **/*.cljs, **/*.ex, **/*.exs, **/*.lua'
---

# Static Application Security Testing (SAST) Rule (Endor Labs via MCP)

This project uses [Endor Labs](https://docs.endorlabs.com/) for automated SAST, integrated through the MCP server as configured in `.vscode/mcp.json`.

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

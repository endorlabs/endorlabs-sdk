---
url: https://docs.endorlabs.com/deployment/ide/vs-code-plugin/
title: Endor Labs Visual Studio Code extension | Endor Labs Docs
downloaded: 2026-01-29 22:20:31
---

Endor Labs Visual Studio Code extension | Endor Labs Docs



* Type to search...

[Print entire section](/deployment/ide/vs-code-plugin/_print.html)



# Endor Labs Visual Studio Code extension

Use Endor Labs to scan your code in your IDE.

The Endor Labs extension for Visual Studio Code scans your repositories and highlights issues that may exist in the open-source dependencies. You can use the extension with Endor Labs API credentials.

## Prerequisites

The following prerequisites must be fulfilled to use the Endor Labs VS Code extension:

* The minimum supported version of Visual Studio Code is 1.71 and higher.
* See the following table for supported languages, package managers, and file extensions. The extension reads the manifest files to fetch the list of dependencies and displays the results in both manifest and source code files.

| Supported Language | Manifest file | Source code file |
| --- | --- | --- |
| JavaScript | `package.json` | `.js`, `.ts`, `.jsx`, `.tsx`, `.mjs`, `.cjs` extensions |
| Python | `requirements.txt` | `.py` extension |
| Go | `go.mod` | `.go` extension |

* Generate Endor Labs API keys and have them handy. You must enter these details in the VS Code extension. See [Managing API Keys](../../../administration/api-keys/) for details.

### Install the Endor Labs extension

Developers can install the extension from the Visual Studio marketplace and configure it with Endor Labs API keys.

1. Launch Visual Studio Code and click **Extensions**.
2. Look for the **Endor Labs** using the search bar and click **Install**. See [Visual Studio Extension documentation](https://code.visualstudio.com/docs/editor/extension-marketplace) for details on managing the extension.
3. Select the Endor Labs extension, click **Settings**, and choose **Extension Settings**.
4. Enter the **API Key** and **API Secret** of the Endor Labs application.

### View scan results

The Endor Labs Visual Studio extension reads all the manifest files in your project and fetches the list of dependencies.

* Hover over a dependency to view the package version, released date, findings, and Endor Labs scores in a pop-up.
* For effective prioritization, issues with dependencies are classified into four severity levels: Critical, High, Medium, and Low.
* Click a specific version to view the same results in the Endor Labs user interface.
* The dependencies are color-coded in the following ways:
  + Red underline - Has critical findings and is also on an outdated version
  + Orange underline - Has critical findings and is on the latest version
  + Yellow underline - Has no critical findings but is an outdated version
  + No Underline - Has no critical findings and is on the latest version
* Use **Update to latest version** to update the package to its latest version.

**Note**

The manifest file is updated with the latest version; however, the package is not automatically upgraded.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

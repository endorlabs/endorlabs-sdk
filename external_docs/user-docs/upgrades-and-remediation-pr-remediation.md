---
url: https://docs.endorlabs.com/upgrades-and-remediation/pr-remediation/
title: Remediation Pull Requests in GitHub App | Endor Labs Docs
downloaded: 2026-01-26 10:07:35
---

Remediation Pull Requests in GitHub App | Endor Labs Docs



* Type to search...

[Print entire section](/upgrades-and-remediation/pr-remediation/_print.html)



# Remediation Pull Requests in GitHub App

Learn how to configure Remediation Pull Request (PR) in a GitHub environment to address issues in your code repository.

Beta

You can set up Remediation PRs in your GitHub environment if you use the [Endor Labs GitHub App (Pro)](../../deployment/monitoring-scans/github-app/github-app-pro/) or the [Endor Labs GitHub Enterprise Server App](../../deployment/monitoring-scans/github-app/github-enterprise-app/). When Remediation PRs are set up, Endor Labs creates a PR to update the manifest files with dependency version upgrades, based on a remediation policy, to address vulnerability findings.

**Warning**

You cannot have both the GitHub App and the GitHub App (Pro) simultaneously in your environment. When you migrate from one app to the other, select the same set of repositories as before to preserve the currently scanned projects and vulnerability findings after the migration.

Your tenant must have [upgrades and remediation](../../upgrades-and-remediation/) feature for Remediation PRs to function.

## Understanding Remediation PRs

If Endor Labs identifies any fixes that address vulnerability findings according to the remediation policy in the next scan, it creates a pull request in GitHub with the details of the patch. You can merge the PR after review to fix the vulnerability findings.

Endor Labs updates the PR if there is a recommendation change in [upgrade impact analysis](../upgrade-impact-analysis/). If there are any changes in the vulnerability findings, Endor Labs updates the PR description. If there is new patch version available, Endor Labs closes the existing PR with comments and opens a new PR. If you resolve the notification in Endor Labs, the PR is closed with a comment.

Endor Labs does not further update the PR in the following scenarios, if you:

* Add a commit to the PR
* Close the PR
* Delete the PR branch
* Dismiss the notification in Endor Labs

## Set up Remediation PRs

Complete the following tasks to set up automated PR.

1. Install and enable SCA scanner using either [GitHub App (Pro)](../../deployment/monitoring-scans/github-app/github-app-pro/) or [GitHub Enterprise Server App](../../deployment/monitoring-scans/github-app/github-enterprise-app/).
2. [Create a GitHub PR for remediations notification integration.](#create-a-github-pr-for-remediations-notification-integration)
3. [Create a remediation policy with the notification integration that you created in the previous step.](../../managing-policies/remediation-policies/)

   The following image shows an example of a remediation policy that targets projects with the tag `java` and automatically raises a PR when remediation is found for reachable dependencies that resolve critical and high issues with low upgrade risk.

   ![Remediation Policy 1](../../images/autoPR_remediationpolicy.png)

## Remediation PRs support

Remediation PRs are supported for Java (with Gradle or Maven), Go (version 1.18 and higher), Python, .NET, and JavaScript.

#### Remediation PRs support matrix

| Ecosystem | Package manager | Build files | Automated PR remediation |
| --- | --- | --- | --- |
| Python | pip | `pyproject.toml`, `requirements.txt` | ✓ |
|  | pip | `setup.py`, `setup.cfg` | ✗ |
|  | Poetry | `pyproject.toml`, `poetry.lock` | ✗ |
|  | PDM | `pyproject.toml`, `pdm.lock` | ✗ |
| Java | Maven / Gradle | `pom.xml`, `build.gradle`, `build.gradle.kts` | ✓ |
| Go | Go modules | `go.mod`, `go.sum` | ✓ |
| JavaScript | npm / yarn / pnpm | `package.json`, `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml` | ✓ |
| .NET | NuGet | `*.csproj`, `packages.lock.json` | ✓ |

#### Limitations of Remediation PRs

Currently, Remediation PRs have the following limitations:

* Maven projects that use `dependencyManagement` tags and rely solely on dependency information in the parent pom file are not supported.
* Gradle projects with convention files (Groovy files with `.gradle` extension with any name) are not supported.
* Gradle projects with resource catalogues (version defined in `.toml` files) are not supported.
* + Gradle projects that use Spring Framework plugins, such as the Spring Boot Gradle plugin, to manage dependency versions are not supported. These plugins handle versioning internally, so dependency versions are not explicitly declared in the Gradle manifest file.
* Go projects that use the `replace` directive in `go.mod` are not supported. `replace` directives are commonly used for local development, debugging, or patching dependencies.
* JavaScript projects using npm and Yarn workspaces are not supported.
* .NET projects using `Directory.Packages.props` (central dependency management) or `packages.config`, are not supported.
* Dependency names are case sensitive.
* Updates to .NET dependencies with wildcard characters in their names are not supported.

## Create a GitHub PR for remediations notification integration

Remediation notification integration allows Endor Labs to get a notification from GitHub regarding pull requests. The notification alerts the GitHub App to perform Remediation PRs.

1. Sign in to Endor Labs and select **Integrations** from the left sidebar.
2. Under **Notifications**, click **Add** for **GitHub PR for Remediations**.
3. Click **Add Notification Integration**.

   ![Add GitHub PR for Remediation](../../images/automatePR_createnotification.png)
4. Enter a name and description for this integration.
5. Select **Enable GitHub PR Notification Integration for Remediations**.
6. Optionally, select **Propagate this notification target to all child namespaces** so that the notification integration applies to all child namespaces.
7. Click **Add Notification Integration**.

## View remediation PRs in GitHub

Endor Labs automatically generates pull requests in GitHub repositories for dependency upgrades and security fixes. Each PR contains version changes, vulnerability details, and compatibility analysis.

To view the remediation PRs:

1. Navigate to your GitHub repository.
2. Click **Pull Requests** to view all the remediation PRs in the repository.

   ![GitHub Remediation PRs](../../images/remediation-pr.png)
3. Click on a PR to view it’s details.

   * Select **Conversation** to view the version changes, security impact, fixed vulnerabilities, and potential risks, providing context to assess the upgrade.

     ![PR description](../../images/remediation-pr-description.png)
   * Select **Files changed** to view the changes made to the manifest files.

     ![files changed in the PR](../../images/remediation-pr-files-changed.png)

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

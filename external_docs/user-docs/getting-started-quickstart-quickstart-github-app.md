---
url: https://docs.endorlabs.com/getting-started/quickstart/quickstart-github-app/
title: Quick start with GitHub App | Endor Labs Docs
downloaded: 2025-10-23 23:25:10
---

Quick start with GitHub App | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/getting-started/quickstart/quickstart-github-app/_print.html)



# Quick start with GitHub App

Get up and running quickly with Endor Labs GitHub App.

This guide provides instructions on how to get started with Endor Labs using the Endor Labs GitHub App. You can install the [GitHub App](../../../deployment/monitoring-scans/github-app/) or the [GitHub App (Pro)](../../../deployment/monitoring-scans/github-app/github-app-pro/).

#### Note

The GitHub App (Pro) facilitates PR remediation. See [PR remediation](/upgrades-and-remediation/pr-remediation/#understanding-pr-remediation/) for more information.

## Prerequisites for GitHub App

Before installing and scanning projects with Endor Labs GitHub App, make sure you have:

* A GitHub cloud account and organization. If you don’t have one, create one at [GitHub](https://www.github.com).
* Administrative permissions to your GitHub organization. Installing the Endor Labs GitHub App in your organization requires approval or permissions from your GitHub organizational administrator.
* Endor Labs GitHub App requires read permissions to Dependabot alerts, actions, administration, checks, code, commit statuses, issues, metadata, packages, pull requests, repository hooks, and security events. It does not need write access to any resources.

## Quickstart with GitHub App

1. Sign in to Endor Labs and select **Getting Started** from the left sidebar.
2. Select **SCAN WITH GitHub App** and click **Install GitHub App Pro**.

   Deselect **Enable Automated Pull Requests** to disable [automatic PR remediation](../../../upgrades-and-remediation/pr-remediation/) and to install the [GitHub App](../../../deployment/monitoring-scans/github-app/).

   #### Warning

   You can only install either the GitHub App or the GitHub App (Pro) in your environment.

   ![Scan with GitHub App landing page](../../../images/githubapp-gettingstarted.png)
3. Choose the user and the organization where you wish to install the app.
4. Select whether to install and authorize Endor Labs on all your repositories or select the specific repositories that you wish to scan.
5. Click **Install & Authorize**.

   If the button to install says **Install and Request** instead of **Install and Authorize**, you don’t have permission to install the app. Select **Install and Request** to notify your organizational administrator of your request.

   ![Choose Repositories](../../../images/authorize-githubapp.png)
6. Select the Endor Labs namespace that you want to use and click **Next**.

   ![Choose namespace](../../../images/GitHubApp_namespace.png)
7. Select the scan types to enable under **SCANNERS**.

   The following scanners are available:

   * **SCA**: Perform software composition analysis and discover AI models used in your repository.
   * **RSPM**: Scan the repository for misconfigurations.
   * **Secret**: Scan the repository for exposed secrets.
   * **CI/CD**: Scan the repository and identify all the CI/CD tools used in the repository.
   * **SAST**: Scan your source code for weakness and generate SAST findings.
8. Select **Include Archived Repositories** to scan your archived repositories. By default, the GitHub archived repositories aren’t scanned.
9. Select the **PULL REQUEST SCANS** to automatically scan the PRs submitted by users.

   ![Choose PR options](../../../images/github-app-pr.png)

   * Select **Pull Request Comments** to enable GitHub Actions to comment on PRs for policy violations.
   * In **Define Scanning Preferences**, select either:

     + **Quick Scan** to gain rapid visibility into your software composition. It performs dependency resolution but does not conduct reachability analysis to prioritize vulnerabilities. The quick scan enables users to swiftly identify potential vulnerabilities in dependencies, ensuring a smoother and more secure merge into the main branch.
     + **Full Scan** to perform dependency resolution, reachability analysis, and generate call graphs for supported languages and ecosystems. This scan enables users to get complete visibility and identifies all issues dependencies, call graph generation before merging into the main branch. Full scans may take longer to complete, potentially delaying PR merges.

     See [GitHub scan options](../../../deployment/monitoring-scans/github-app/scan-with-githubapp/) for more information on the scans that you can do with the GitHub App.
10. Click **Create**.

You will be redirected back to Endor Labs.

After installation, Endor Labs scans your repositories and generates findings. Subsequently, Endor Labs scans your repository every 24 hours. See [Findings](https://docs.endorlabs.com/managing-projects/view-findings) for more information on the findings generated by the scans.

### Review the scan results

1. Sign in to the [Endor Labs user interface](https://app.endorlabs.com) and click **Projects** on the left sidebar.
2. Select your project to view the findings page. See [Findings](https://docs.endorlabs.com/managing-projects/view-findings) for more information.

![GithubApp scanned project](../../../images/findings.png)

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

---
url: https://docs.endorlabs.com/deployment/monitoring-scans/github-app/
title: Deploy Endor Labs GitHub App | Endor Labs Docs
downloaded: 2025-10-27 12:56:53
---

Deploy Endor Labs GitHub App | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/deployment/monitoring-scans/github-app/_print.html)



# Deploy Endor Labs GitHub App

Learn how to continuously monitor your environment with the Endor Labs GitHub App.

Endor Labs provides a GitHub App that continuously monitors users’ projects for security and operational risk. You can use the GitHub App to selectively scan your repositories for SCA, secrets, RSPM, or CI/CD tools. GitHub App scans also establish baselines that are subsequently used during CI scans.

The Endor Labs GitHub App scans your repositories every 24 hours and reports new findings or changes to your code’s release versions. It also performs RSPM scans weekly on Sundays to manage your repository’s posture. See [Scan with GitHub App](../github-app/scan-with-githubapp/) for more information. You can also manually trigger scans for your repositories. See [Re-scan projects](../github-app/re-scan-projects/) for more information. After you install the GitHub App, you can make further changes to the settings. See [Manage GitHub App](../github-app/manage-github-app/) for more information. You may need to review the technical limitations of the GitHub App so that you can use the GitHub App to its full potential. See [Technical limitations of the Endor Labs GitHub App](../github-app/technical-limitations/) for more information.

If you want to use PR remediations as part of your monitoring scan or need to export your findings to GitHub Advanced Security, you need to use [GitHub App (Pro)](../github-app/github-app-pro/).

#### Warning

You cannot have both GitHub App and GitHub App (Pro) simultaneously in your environment. If you are currently using the standard GitHub App, you can migrate to GitHub App (Pro). When migrating from one app to the other, ensure you select the same set of repositories as before to preserve your currently scanned projects and findings after the migration.

### Prerequisites for GitHub App

Before installing and scanning projects with Endor Labs GitHub App, make sure you have:

* A GitHub cloud account and organization. If you don’t have one, create one at [GitHub](https://www.github.com).
* Administrative permissions to your GitHub organization. Installing the Endor Labs GitHub App in your organization requires approval or permissions from your GitHub organizational administrator. If you don’t have the permissions, use the command line utility, `endorctl`, while you wait for the approval.
* Endor Labs GitHub App requires:
  + Read permissions to Dependabot alerts, actions, administration, code, commit statuses, issues, metadata, packages, repository hooks, and security events.
  + Write permissions to checks and pull requests to check the pull requests automatically and surface policy violations to developers as pull request comments.
  + Subscribe to check run, check suite, and pull request events.

## Install the GitHub App

To automatically scan repositories using the GitHub App:

1. Sign in to Endor Labs.
2. Choose **Projects** and click **Add Project**.
3. From **GitHub**, choose **GitHub App**.
   ![Install Endor Labs GitHub App](../../../images/GitHubAppInstall.png)
4. Click **Install GitHub App**.

   You will be redirected to GitHub to install the GitHub App.
   ![Endor Labs GitHub App](../../../images/githubappendorlabs.png)
5. Click **Install**.
6. Select a user to authorize the app.
7. Select the organization in which you want to install the app.
8. Select whether to install and authorize Endor Labs on all your repositories or select the specific repositories that you wish to scan.

   ![Choose Repositories](../../../images/authorize-githubapp.png)
9. Review the permissions required for Endor Labs and click **Install and Authorize**.

   If the button to install says **Install and Request** instead of **Install and Authorize**, you don’t have permission to install the GitHub App. Use the [endorctl command line interface](../../../getting-started/quickstart/quickstart-local-system/) or select **Install and Request** to notify your organizational administrator of your request to install. If you select **Install and Request** your installation will not be active unless your organizational administrator approves the request to install GitHub App.
10. Choose a namespace and click **Next**.

    ![Choose namespace](../../../images/GitHubApp_namespace.png)
11. Based on your license, select and enable the scanners.

    * **SCA**: Perform software composition analysis and discover AI models used in your repository.
    * **RSPM**: Scan the repository for misconfigurations. RSPM scans run every week on Sundays.
    * **Secret**: Scan the repository for exposed secrets.
    * **CI/CD**: Scan the repository and identify all the CI/CD tools used in the repository.
    * **SAST**: Scan your source code for weakness and generate SAST findings.
12. Select **Include Archived Repositories** to scan your archived repositories. By default, the GitHub archived repositories aren’t scanned.
13. Select **PULL REQUEST SCANS** to set preferences for scanning pull requests submitted by users.

    ![Choose PR options](../../../images/github-app-pr.png)

    * Select **Pull Request Comments** to enable GitHub Actions to comment on PRs for policy violations.
    * In **Define Scanning Preferences**, select either:

      + **Quick Scan** to gain rapid visibility into your software composition. It performs dependency resolution but does not conduct reachability analysis to prioritize vulnerabilities. The quick scan enables users to swiftly identify potential vulnerabilities in dependencies, ensuring a smoother and more secure merge into the main branch.
      + **Full Scan** to perform dependency resolution, reachability analysis, and generate call graphs for supported languages and ecosystems. This scan enables users to get complete visibility and identifies all issues dependencies, call graph generation before merging into the main branch. Full scans may take longer to complete, potentially delaying PR merges.

      See [GitHub scan options](../github-app/scan-with-githubapp/) for more information on the scans that you can do with the GitHub App.
14. Click **Continue**.

You have successfully installed the GitHub App.

### Set up package repositories

You can improve your experience with the GitHub App by setting up package repositories. This will help you create a complete bill of materials and perform static analysis. Without setting package repositories, you may not be able to get an accurate bill of materials. See [Set up package manager integration](../../../integrations/package-manager/) for more information.

---

##### [Scan capabilities of the Endor Labs GitHub App](/deployment/monitoring-scans/github-app/scan-with-githubapp/)

Learn how to scan projects using the Endor Labs GitHub App.

##### [Rescan projects](/deployment/monitoring-scans/github-app/re-scan-projects/)

Rescan your GitHub projects with Endor Labs

##### [Manage GitHub App on Endor Labs](/deployment/monitoring-scans/github-app/manage-github-app/)

Learn how to manage your GitHub App integration in Endor Labs.

##### [Technical limitations of the Endor Labs GitHub App](/deployment/monitoring-scans/github-app/technical-limitations/)

Understand the technical limitations associated with the GitHub App.

##### [Deploy Endor Labs GitHub App (Pro)](/deployment/monitoring-scans/github-app/github-app-pro/)

Learn how to continuously monitor your environment with the Endor Labs GitHub App.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

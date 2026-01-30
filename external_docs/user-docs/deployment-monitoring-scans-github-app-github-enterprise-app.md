---
url: https://docs.endorlabs.com/deployment/monitoring-scans/github-app/github-enterprise-app/
title: Deploy Endor Labs GitHub Enterprise Server App | Endor Labs Docs
downloaded: 2026-01-26 10:08:21
---

Deploy Endor Labs GitHub Enterprise Server App | Endor Labs Docs



* Type to search...

[Print entire section](/deployment/monitoring-scans/github-app/github-enterprise-app/_print.html)



# Deploy Endor Labs GitHub Enterprise Server App

Learn how to continuously monitor your GitHub Enterprise Server environment with the Endor Labs GitHub Enterprise Server App.

Beta

Endor Labs GitHub Enterprise Server App is specifically designed for **GitHub Enterprise Server (GHES)** - the self-hosted, on-premise version of GitHub. This app allows you to continuously monitor your repositories hosted on your own GitHub Enterprise Server instance for security and operational risks.

**Availability**

Currently, the GitHub Enterprise Server App does not support the Endor Labs cloud scheduler. You need to configure Endor Outpost in your environment to use the GitHub Enterprise Server App. See [Endor Outpost](../../outpost/) for more information.

**Important**

You can create only one Endor Labs app per GitHub Enterprise Server instance for a tenant. Once you create the app, you need to uninstall it from all organizations where it is installed to delete the app.

## Default branch detection

When Endor Labs scans a repository for the first time, it detects the default branch of the repository. The findings that are created in the scan are associated with the default branch.

### Changing the default branch

When you change the default branch in your source control system (for example, from `main` to `dev`):

* Endor Labs automatically detects the new default branch and sets that as the default reference
* The previous default branch becomes a reference branch
* Scans continue on the new default branch and the reference branch

The findings associated with the previous default branch are no longer associated with the default context reference. You can view them in the reference context.

### Renaming the default branch

When you rename the default branch in your source control system:

* Endor Labs automatically switches to the renamed branch
* Scans continue without disruption

### Adding repository versions

When you add a new repository version (for example, a `dev` branch), both the default branch and the new version are scanned by the Endor Labs App.

### Control default branch detection

You can control the default branch detection by setting the `ENDOR_SCAN_TRACK_DEFAULT_BRANCH` environment variable in a scan profile. You need to configure the project to use the scan profile. See [Configure scan profiles](/scan-with-endorlabs/manage-scan-profiles/) for more information.

By default, the environment variable is set to `true`. When set to `true`, the default branch detection is enabled, and the first branch you scan is automatically considered as the default branch.

## Prerequisites for GitHub Enterprise Server App

Before installing and scanning projects with Endor Labs GitHub Enterprise Server App, make sure you have:

* **Outpost Setup**: A Kubernetes cluster to deploy the Endor scheduler, with network egress configured from the cluster to Endor Labs. See [Endor Outpost](../../outpost/) for setup instructions.
* **GitHub Enterprise Server (GHES) instance**: A running GitHub Enterprise Server instance.
* **Administrative permissions**: Administrative permissions to your organization’s GitHub Enterprise Server to install and authorize the Endor Labs GitHub Enterprise Server App.
* **Organization owner permissions**: You must be an owner of the GitHub Enterprise Server organization where you plan to install the app.
* **Administrative access in Endor Labs**: Administrative access in Endor Labs to create and manage the GitHub Enterprise Server App.

## Set up GitHub Enterprise Server App

Setting up the GitHub Enterprise Server App involves the following steps:

1. [**Set up Outpost**](#set-up-outpost)

   You can skip Outpost setup if you want your projects to be scanned in Endor Labs Cloud and if your network firewall rules allow Endor Labs to access your GitHub Enterprise Server instance directly. See [Firewall rules](../../../../troubleshooting/firewall-rules/) for more information.
2. [**Create the App in Endor Labs**](#create-application-in-endor-labs)
3. [**Install the App in your organization**](#install-the-app-in-your-organization)
4. [**Scan more repositories**](#scan-more-repositories)

### Set up Outpost

Set up Outpost to deploy the Endor scheduler to your Kubernetes cluster. See [Endor Outpost](../../outpost/) for more information.

Add the following environment variable under the `endorctl` section in your `values.yaml` file to enable communication with your GitHub Enterprise Server instance.

```
endorctl:
  additionalEnvs:
    - name: "GITHUB_USE_APP_TRANSPORT"
      value: "true"
```

The following is an example `values.yaml` file with the required configuration.

```
endorAPI: "https://api.endorlabs.com"
endorNamespace: "<Endor Labs namespace>"
auth:
  apiKey: "<apiKey>"
  apiSecret: "<apiSecret>"
scheduler:
  image:
    repository: "endorcipublic.azurecr.io/scheduler"
    tag: "latest"
    pullPolicy: "Always"
endorctl:
  image:
    repository: "endorcipublic.azurecr.io/endorctl_bare"
    tag: "latest"
    pullPolicy: "Always"
  additionalEnvs:
    - name: "GITHUB_USE_APP_TRANSPORT"
      value: "true"
```

### Create application in Endor Labs

To define the application in Endor Labs, first set up an app within your GitHub Enterprise Server organization. You can create and register the GitHub Enterprise Server App only in the root tenant namespace in Endor Labs. You can then install it to any namespace including child namespaces.

If you have already created a GitHub App for Endor Labs, skip to [register application in Endor Labs](#register-application-in-endor-labs).

1. Sign in to Endor Labs.
2. Select **Integrations** from the left sidebar.
3. Click **Create App** next to **GitHub Enterprise Server** under **Source Control Managers**.
4. Enter the **Host URL** of your GitHub Enterprise Server instance in the format `https://github.company.com`.
5. Enter the **GitHub Organization Name** that will be the owner of this app.
6. Click **Create** to launch a [GitHub app registration form](#create-an-endor-labs-github-app-in-github-enterprise-server) in a new tab.

   ![Create app in GitHub](../../../../images/create-app-in-github.png)
7. Complete the registration form and [continue the configuration](#register-application-in-endor-labs) in Endor Labs.

### Create an Endor Labs GitHub App in GitHub Enterprise Server

You need to create a GitHub App for Endor Labs in your GitHub Enterprise Server instance. Refer to [Register a GitHub app](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/registering-a-github-app/#registering-a-github-app) for more information.

**Important**

While you create the GitHub App in GitHub Enterprise Server, keep the following in mind:

* Ensure that SSL is enabled for webhooks in your GitHub app.
* Provide a **Webhook secret** during app registration to enable pull request scanning and PR comment features.
* Review the **Repository Permissions**.
* Choose **Any account** under **Where can this GitHub App be installed?** to allow installing the GitHub App on any organization or user account.

After creating the GitHub app, collect the following credentials from GitHub Enterprise to complete registration in Endor Labs:

* **GitHub App name**: The name of the GitHub app you created in your GitHub Enterprise Server instance.
* **App URL**: The URL of the GitHub app you created in your GitHub Enterprise Server instance.
* **App ID**: The ID of the GitHub app you created in your GitHub Enterprise Server instance.
* **Client ID**: The client ID of the GitHub app you created in your GitHub Enterprise Server instance.

1. Navigate to your organization in GitHub Enterprise and select **Settings** > **Developer settings** > **GitHub Apps**.
2. Select the app you created.

   Copy the **GitHub App name**, **App URL**, **App ID**, and **Client ID**.
   ![App details in GitHub to copy](../../../../images/details-of-app-ghe.png)
3. Click **Generate a new client secret** and copy the generated value.
4. Generate and download the **Private key (PEM file)**.

   Refer to [manage private keys for GitHub Apps](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/managing-private-keys-for-github-apps/#generating-private-keys) for more details.
5. Copy the **Webhook Secret** you provided during GitHub app creation to enable pull request scanning features.

   See [Validating webhook deliveries](https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries) for more details.

### Register application in Endor Labs

Once you create the app in your GitHub Enterprise instance, register it in Endor Labs to establish the connection between Endor Labs and your GitHub Enterprise Server. Enter the app details to register the app.

1. Enter the base URL of your GitHub Enterprise instance in **Host URL**.
2. Enter the **App URL**.
3. Enter the **App ID**.
4. Enter the **Client ID** and **Client Secret** from your GitHub application’s configuration page.
5. Enter the **GitHub App name**.
6. The **Webhook URL** is pre-configured. Do not modify it in your GitHub app.
7. Select **Enable Pull Request scans by setting up webhook** and enter the **Webhook Secret** to enable PR scan and PR comments features.
8. Paste or upload the **Private key (PEM file)** in **Certificate**.
9. Click **Create**.

   ![Register app in Endor Labs](../../../../images/register-app-in-endor.png)

**Note**

You can only create one Endor Labs app per GitHub Enterprise Server instance per tenant.

### Install the app in your organization

After creating and registering the app, install it in one or more organizations in your GitHub Enterprise Server instance. Installing the app grants it access to your repositories and enables scanning.

1. Select **Integrations** from the left sidebar.
2. Click **Manage** next to **GitHub Enterprise Server** under **Source Control Managers**.
3. Click **Install App** next to the app you want to install.
   You will be redirected to GitHub Enterprise Server. If the app is already installed in some organizations, you’ll see a **Configure** option instead.
4. Select the organization where you want to install the app.
5. Select whether to install and authorize Endor Labs on all your repositories or select the specific repositories that you want to scan.
6. Review the permissions required for Endor Labs and click **Install and Authorize**.

   ![Choose repositories](../../../../images/authorize-githubapp.png)

**Note**

If you don’t have permission to install the GitHub Enterprise Server App, you may need to request approval from your organizational administrator. If you select **Install and Request**, your installation will not be active unless your organizational administrator approves the request.

7. Collect the **Installation ID** and the name of the organization from your GitHub Enterprise Server and provide them to Endor Labs.

   * Navigate to your organization’s settings in GitHub and select **Application** from the left sidebar.
   * Click **Configure** next to your app.
   * Copy the browser URL. The installation ID is the number at the end of the URL. In the following example, `12345678` is the installation ID and `GHE-trial` is the organization’s name.

   ```
   https://github.com/organizations/GHE-trial/settings/installations/12345678
   ```
8. Return to the Endor Labs tab and enter the GitHub organization where you installed the app in **Name of the organization** and the **Installation ID** collected in the previous step.

   ![Scanner options](../../../../images/scanner-options-ghe.png)

**Note**

You need the Installation ID for Endor Labs to identify and communicate with your specific app installation in the GitHub Enterprise Server organization.

9. Based on your license, select and enable the scanners.

   The following scanners are available:

   * **SCA**: Perform software composition analysis and discover AI models used in your repository.
   * **RSPM**: Scan the repository for misconfigurations. RSPM scans run every week on Sundays.
   * **Secret**: Scan the repository for exposed secrets.
   * **CI/CD**: Scan the repository and identify all the CI/CD tools used in the repository.
   * **SAST**: Scan your source code for weaknesses and generate SAST findings.
10. Select **Include Archived Repositories** to scan your archived repositories. By default, the GitHub archived repositories aren’t scanned.
11. Select **PULL REQUEST SCANS** to set preferences for scanning pull requests submitted by users.

    * Select **Pull Request Comments** to enable GitHub Actions to comment on PRs for policy violations.
    * In **Define Scanning Preferences**, select either:

      + **Quick Scan** to gain rapid visibility into your software composition. It performs dependency resolution but does not conduct reachability analysis to prioritize vulnerabilities. The quick scan enables users to swiftly identify potential vulnerabilities in dependencies, ensuring a smoother and more secure merge into the main branch.
      + **Full Scan** to perform dependency resolution, reachability analysis, and generate call graphs for supported languages and ecosystems. This scan enables users to get complete visibility and identifies all issues related to dependencies and call graph generation before merging into the main branch. Full scans may take longer to complete, potentially delaying PR merges.

      See [GitHub scan options](../../github-app/scan-with-githubapp/) for more information on the scans that you can do with the GitHub Enterprise Server.

**Note**

You can perform pull request scans only if you have configured a webhook URL and webhook secret when creating your GitHub Enterprise Server app.

12. Click **Create**.

You have successfully installed Endor Labs GitHub App Enterprise on your GitHub Enterprise Server instance.

### Scan more repositories

After successfully installing the app, Endor Labs starts scanning your repositories every 24 hours and reports any new findings or changes to release versions of your code.

To add more repositories to scan:

1. Select **Projects** from the left sidebar and click **Add Project**.
2. Select **GitHub Enterprise**.
3. Select the app you want to use for scanning. If you haven’t created an app in your GitHub Enterprise account, [create an app](#create-application-in-endor-labs) and install it before you scan the repositories.
4. Click **Scan**.
5. You’ll be redirected to GitHub Enterprise Server. Select the organization where the app is installed.
6. Select the app.
7. Choose the repositories you want to include and click **Save**.
8. Return to the Endor Labs tab and select **Integrations** from the left sidebar.
9. Click **Rescan Org** to view results.

Endor Labs GitHub App Enterprise scans your repositories every 24 hours and reports any new findings or changes to release versions of your code. It can also raise a PR with a fix based on your remediation policy. Ensure that you configure automated PR scans in your environment. See [Automated PR scans](../../../../upgrades-and-remediation/pr-remediation/) for more information.

**Note**

Configure [branch protection rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches) to ensure the Endor Labs Automated Scan check runs before merging your PR.

## Set up package repositories

You can improve your experience with the GitHub App Enterprise by setting up package repositories. This will help you create a complete bill of materials and perform static analysis. Without setting package repositories, you may not be able to get an accurate bill of materials. See [Set up package manager integration](../../../../integrations/package-manager/) for more information.

## Technical limitations of the GitHub App Enterprise

The Endor Labs GitHub App Enterprise has similar limitations as the GitHub App for cloud. See [Limitations](../technical-limitations/) for more information. Additional considerations for GitHub Enterprise Server:

* GitHub Enterprise Server must support GitHub Apps functionality.
* Network connectivity between Endor Labs and GitHub Enterprise Server is required for continuous monitoring.
* Firewall rules must allow egress communication from your environment to Endor Labs.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

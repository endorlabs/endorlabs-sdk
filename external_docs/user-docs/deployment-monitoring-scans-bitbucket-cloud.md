---
url: https://docs.endorlabs.com/deployment/monitoring-scans/bitbucket-cloud/
title: Deploy Endor Labs Bitbucket App in Bitbucket Cloud | Endor Labs Docs
downloaded: 2026-01-16 09:50:05
---

Deploy Endor Labs Bitbucket App in Bitbucket Cloud | Endor Labs Docs



* Type to search...

[Print entire section](/deployment/monitoring-scans/bitbucket-cloud/_print.html)



# Deploy Endor Labs Bitbucket App in Bitbucket Cloud

Learn how to continuously monitor your environment with the Endor Labs Bitbucket App.

Endor Labs provides a Bitbucket App that continuously monitors users’ projects for security and operational risks in Bitbucket Cloud. You can use the Bitbucket App to selectively scan your repositories for SCA, secrets, SAST, and CI/CD tools.

When you use the Endor Labs Bitbucket App, it creates namespaces based on your workspace and projects in Bitbucket Cloud. The namespaces created by the Endor Labs Bitbucket App are not like regular namespaces and are called managed namespaces. You can either configure the URL to Bitbucket Cloud to import all the projects or configure the project key to import a specific project in Endor Labs.

**Note**

The following characters are allowed in Endor Labs namespaces: lowercase letters (a–z), digits (0–9), hyphens (-), and underscores (\_). Additionally, the namespace is limited to a maximum of 64 characters in length. If the Bitbucket host or your projects have a different naming convention, the corresponding namespaces will be converted to comply with the naming convention of Endor Labs namespaces.

See [Manage Bitbucket Cloud App](../bitbucket-cloud/manage-bitbucket-cloud/) to learn how to manage your Bitbucket Cloud App integration in Endor Labs.

## Managed namespaces for Bitbucket Cloud

You need to add the Bitbucket Cloud workspace or a project to an Endor Labs namespace. Bitbucket Cloud workspace and projects are mapped as managed namespaces in Endor Labs.

Managed namespaces have the following restrictions:

* You cannot delete managed namespaces.
* You cannot delete repositories within managed namespaces.
* You cannot add projects or create namespaces within managed namespaces.
* You cannot create new Endor Labs App installations within managed namespaces.

### Namespace structure when you add a Bitbucket Cloud workspace

When you add a Bitbucket Cloud workspace to an Endor Labs namespace, Endor Labs creates a child namespace for the Bitbucket Cloud workspace and creates child namespaces for each project in the workspace under the workspace namespace. The namespaces of the workspace and projects are managed namespaces. You can add multiple Bitbucket Cloud workspaces to the same Endor Labs namespace. Each workspace will have its own managed namespace.

If your workspace name is `deerinc` and you have three projects, `buck`, `doe`, and `fawn`, Endor Labs creates four managed namespaces: `deerinc`, `buck`, `doe`, and `fawn`. The namespaces `buck`, `doe`, and `fawn` are child namespaces of the `deerinc` namespace.

The following image shows the namespace structure in Endor Labs.

```
graph TD

      %% Endor Labs namespace
      EN[endor-bitbucket]

      %% Bitbucket projects
      O1[deerinc]
      P1[buck]
      P2[doe]
      P3[fawn]


      %% connections
      EN --> O1
      O1 --> P1
      O1 --> P2
      O1 --> P3

      class EN,EN2 endor
      class O1,P1,P2,P3 managed
      classDef managed fill:#5EEAD4
```

### Namespace structure when you add a Bitbucket Cloud project

When you add a Bitbucket Cloud project to an Endor Labs namespace, Endor Labs creates a child namespace for the Bitbucket Cloud project and maps all repositories in that project to this namespace. The child namespace that maps to the Bitbucket Cloud project is a managed namespace. The managed namespace has the name, `<workspace name>_<project name>`. For example, if your Bitbucket Cloud workspace name is `deerinc` and project name is `doe`, the managed namespace will have the name, `deerinc_doe`.

You can add multiple projects to the same Endor Labs namespace. Each project will have its own managed namespace. For example, your workspace name is `deerinc`, which has three projects, `buck`,`doe`, and`fawn`. You add each project to the Endor Labs namespace, `endor-bitbucket`.

The following image shows the namespace structure in Endor Labs.

```
graph TD

      %% Endor Labs namespace
      EN[endor-bitbucket]

      %% Bitbucket projects
      A1[deerinc_buck]
      A2[deerinc_doe]
      A3[deerinc_fawn]


      %% connections
      EN --> A1
      EN --> A2
      EN --> A3

      class EN,EN2 endor
      class A1,A2,A3 managed
      classDef managed fill:#5EEAD4
```

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

## Prerequisites for Bitbucket App for Bitbucket Cloud

Ensure the following prerequisites are in place before you install the Endor Labs Bitbucket App.

* Bitbucket Cloud instance with workspace and projects
* A Bitbucket access token either at the [workspace level](https://support.atlassian.com/bitbucket-cloud/docs/create-a-workspace-access-token/) to import a workspace, or the [project level](https://support.atlassian.com/bitbucket-cloud/docs/create-a-project-access-token/) to import a project. The token must have at least `Project read` permission.

**Note**

Endor Labs Bitbucket App for Bitbucket Cloud requires a Bitbucket Cloud premium plan since Bitbucket Cloud standard plan does not support project-level access tokens.

## Install the Bitbucket App

1. Sign in to Endor Labs and select **Projects** from the left sidebar.
2. Click **Add Project**.
3. From **BITBUCKET**, select **Bitbucket App**, and ensure that **Cloud** is selected.

   ![Bitbucket App](../../../images/bitbucket-cloud-scan.png)
4. Enter the Bitbucket Cloud workspace URL in the format: `https://bitbucket.org/{workspace}` to import all the projects in the workspace.

   Endor Labs creates namespaces for all projects that are available in the Bitbucket Cloud workspace.

   You can also provide the URL up to a project level to import a specific project: `https://bitbucket.org/{workspace}/{project-key}`. For example, `https://bitbucket.org/endor-labs/lab`.
5. Enter the Bitbucket access token.

   The access token must have at least the `Project read` permission.
6. Select the scan types to enable.

   * **SCA**: Perform software composition analysis and discover AI models used in your repository.
   * **Secret**: Scan Bitbucket projects for exposed secrets.
   * **CI/CD**: Scan Bitbucket projects and identify all the CI/CD tools used.
   * **SAST**: Scan Bitbucket projects to generate SAST findings.

   The available scan types depend upon your license.
7. Click **Create**.

Endor Labs Bitbucket App scans your Bitbucket projects every 24 hours and reports any new findings or changes to release versions of your code.

**Note**

Only users with admin authorization role can create and manage installations.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

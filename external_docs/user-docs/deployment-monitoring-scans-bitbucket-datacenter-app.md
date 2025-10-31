---
url: https://docs.endorlabs.com/deployment/monitoring-scans/bitbucket-datacenter-app/
title: Deploy Endor Labs Bitbucket App in Bitbucket Data Center | Endor Labs Docs
downloaded: 2025-10-27 12:58:58
---

Deploy Endor Labs Bitbucket App in Bitbucket Data Center | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/deployment/monitoring-scans/bitbucket-datacenter-app/_print.html)



# Deploy Endor Labs Bitbucket App in Bitbucket Data Center

Learn how to continuously monitor your environment with the Endor Labs Bitbucket App.

Beta

Endor Labs provides a Bitbucket App that continuously monitors users’ projects for security and operational risks in Bitbucket Data Center. You can use the Bitbucket App to selectively scan your repositories for SCA, secrets, SAST, and CI/CD tools.

When you use the Endor Labs Bitbucket App, it creates namespaces based on your projects in Bitbucket Data Center. The namespaces created by the Endor Labs Bitbucket App are not like regular namespaces and are called managed namespaces. You can either configure the URL to Bitbucket Data Center to import all the projects or configure the project key to import a specific project in Endor Labs.

#### Note

The following characters are allowed in Endor Labs namespaces: lowercase letters (a–z), digits (0–9), hyphens (-), and underscores (\_). Additionally, the namespace is limited to a maximum of 64 characters in length. If the Bitbucket host or your projects have a different naming convention, the corresponding namespaces will be converted to comply with the naming convention of Endor Labs namespaces.

See [Manage Bitbucket Data Center App](../bitbucket-datacenter-app/manage-bitbucket-datacenter-app/) to learn how to manage your Bitbucket Data Center App integration in Endor Labs.

## Managed namespaces for Bitbucket Data Center

You need to add the Bitbucket Data Center host or a project to an Endor Labs namespace. Bitbucket host and projects are mapped as managed namespaces in Endor Labs.

Managed namespaces have the following restrictions:

* You cannot delete managed namespaces.
* You cannot delete repositories within managed namespaces.
* You cannot add projects or create namespaces within managed namespaces.
* You cannot create new Endor Labs App installations within managed namespaces.

### Namespace structure when you add a Bitbucket Data Center host

When you add a Bitbucket Data Center host to an Endor Labs namespace, Endor Labs creates a child namespace for the Bitbucket host and creates child namespaces for each project in the host under the host namespace. The namespaces of the host and projects are managed namespaces. If there are periods (`.`) in the Bitbucket datacenter hostname, it is converted to a hyphen (`-`). You can add multiple Bitbucket Data Center hosts to the same Endor Labs namespace. Each host will have its own managed namespace.

If your host name is `bitbucket.deerinc.com` and you have three projects, `buck`, `doe`, and `fawn`, Endor Labs creates four managed namespaces: `bitbucket-deerinc-com`, `buck`, `doe`, and `fawn`. The namespaces `buck`, `doe`, and `fawn` are child namespaces of the `bitbucket-deerinc-com` namespace.

The following image shows the namespace structure in Endor Labs.

```
graph TD

      %% Endor Labs namespace
      EN[endor-bitbucket]

      %% Bitbucket projects
      O1[bitbucket-deerinc-com]
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
      classDef managed fill:#3FE1F3
```

### Namespace structure when you add a Bitbucket Data Center project

When you add a Bitbucket Data Center project to an Endor Labs namespace, Endor Labs creates a child namespace for the Bitbucket Data Center project and maps all repositories in that project to this namespace. The child namespace that maps to the Bitbucket Data Center project is a managed namespace. The managed namespace has the name, `<host name>_<project name>`. For example, if your Bitbucket hostname is `bitbucket.deerinc.com` and project name is `doe`, the managed namespace will have the name, `bitbucket-deerinc-com_doe`.

You can add multiple projects to the same Endor Labs namespace. Each project will have its own managed namespace. For example, your hostname is `bitbucket.deerinc.com`, which has three projects, `buck`,`doe`, and`fawn`. You add each project to the Endor Labs namespace, `endor-azure`.

The following image shows the namespace structure in Endor Labs.

```
graph TD

      %% Endor Labs namespace
      EN[endor-bitbucket]

      %% Bitbucket projects
      A1[bitbucket-deerinc-com_buck]
      A2[bitbucket-deerinc-com_doe]
      A3[bitbucket-deerinc-com_fawn]


      %% connections
      EN --> A1
      EN --> A2
      EN --> A3

      class EN,EN2 endor
      class A1,A2,A3 managed
      classDef managed fill:#3FE1F3
```

## Prerequisites for Bitbucket App for Bitbucket Data Center

Ensure the following prerequisites are in place before you install the Endor Labs Bitbucket App.

* A publicly accessible Bitbucket Data Center host set up with HTTPS.
* A [Bitbucket HTTP access token](https://confluence.atlassian.com/bitbucketserver/http-access-tokens-939515499.html) with at least `Project read` permission at the project level.

## Install the Bitbucket App

1. Sign in to Endor Labs.
2. Select **Projects** from the left sidebar and click **Add Project**.
3. From **BITBUCKET**, select **Bitbucket App**, and select **Data Center** to import projects from Bitbucket Data Center.

   ![Bitbucket App](../../../images/bitbucket-scan.png)
4. Enter the Bitbucket hostname URL in the format: `https://<host name>` to import all the projects.

   Endor Labs creates namespaces for all projects that are available in the Bitbucket Data Center host.

   You can also provide the URL up to a project level to import a specific project: `https://<host name>/projects/<project-key>`. For example, `https://endor-bitbucket.com/projects/LAB`.
5. Enter the Bitbucket Data Center HTTP access token.

   The HTTP access token must have at least the `Project read` permission at the project level.
6. Select the scan types to enable.

   * **SCA**: Perform software composition analysis and discover AI models used in your repository.
   * **Secret**: Scan Bitbucket projects for exposed secrets.
   * **CI/CD**: Scan Bitbucket projects and identify all the CI/CD tools used.
   * **SAST**: Scan Bitbucket projects to generate SAST findings.

   The available scan types depend upon your license.
7. Select **Include Archived Repositories** to scan your archived repositories.

   By default, the Bitbucket archived repositories aren’t scanned.
8. Click **Create**.

Endor Labs Bitbucket App scans your Bitbucket projects every 24 hours and reports any new findings or changes to release versions of your code.

#### Note

Only users with admin authorization role can create and manage installations.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

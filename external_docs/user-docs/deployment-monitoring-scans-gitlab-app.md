---
url: https://docs.endorlabs.com/deployment/monitoring-scans/gitlab-app/
title: Deploy Endor Labs GitLab App | Endor Labs Docs
downloaded: 2025-12-11 11:32:35
---

Deploy Endor Labs GitLab App | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/deployment/monitoring-scans/gitlab-app/_print.html)



# Deploy Endor Labs GitLab App

Learn how to continuously monitor your environment with the Endor Labs GitLab App.

Endor Labs provides a GitLab App that continuously monitors users’ projects for security and operational risk. You can use the GitLab App to selectively scan your repositories for SCA, secrets, SAST, and CI/CD tools. You can use the GitLab App with a GitLab cloud account or a self-hosted GitLab instance.

When you use Endor Labs GitLab App, Endor Labs creates namespaces based on your organization hierarchy in GitLab.

The namespaces created by the Endor Labs GitLab App are not like regular namespaces and are called managed namespaces. These namespaces are named after subgroup slugs in GitLab.

See [Manage GitLab App](../gitlab-app/manage-gitlab-app/) to learn how to manage your GitLab App integration in Endor Labs.

You can also scan your merge requests using the GitLab App. You can enable MR scans during the [installation of the GitLab App](../gitlab-app/#install-the-gitlab-app) or [by editing the GitLab App integration](../gitlab-app/manage-gitlab-app/#edit-gitlab-app-integration). See [GitLab App MR scans](../gitlab-app/gitlab-mr-scan/) for more information.

## Limitations of GitLab groups in Endor Labs namespace

Ensure that you consider the following limitations when you use the GitLab monitoring scan.

* GitLab supports up to 20 levels of subgroup nesting, while Endor Labs currently supports a maximum of 10 levels, assuming the installation is created at the tenant level. If a GitLab installation is created within a nested namespace, such as `tenant.namespace1.namespace2`, the available nesting depth for subgroups in GitLab is reduced. In this case, Endor Labs can only support up to eight levels of nested subgroups.
* Endor Labs supports GitLab groups with a maximum of 64 characters.

## Managed namespaces for GitLab

Managed namespaces are always reflective in terms of structure and content in GitLab.

Managed namespaces have the following restrictions:

* You cannot delete managed namespaces.
* You cannot delete projects present within managed namespaces.
* You cannot add projects or create namespaces within managed namespaces.
* You cannot create any new Endor Labs App installation within the managed namespaces.

  For example, you cannot create an Endor Labs GitHub App installation within a namespace that was created by the Endor Labs GitLab App.

Any modifications to the namespaces have to be in GitLab. The changes that you make to the namespaces and projects are reflected in Endor Labs after a rescan.

If your organization has the following hierarchy in GitLab:

```
graph TD
    GL((GitLab))
    HC[HappyCorp]

    %% Main divisions
    Web[Web]
    Mobile[Mobile]
    Desktop[Desktop]

    %% Web subgroups
    WA[Alpha]
    WB[Beta]
    WG[Gamma]

    %% Mobile subgroups
    MD[Delta]
    ME[Epsilon]
    MZ[Zeta]

    %% Desktop subgroups
    DP[Pi]
    DR[Rho]
    DS[Sigma]

    %% Main connections
    GL --> HC
    HC --> Web
    HC --> Mobile
    HC --> Desktop

    %% Web connections
    Web --> WA
    Web --> WB
    Web --> WG

    %% Mobile connections
    Mobile --> MD
    Mobile --> ME
    Mobile --> MZ

    %% Desktop connections
    Desktop --> DP
    Desktop --> DR
    Desktop --> DS

    class HC main
    class Web,Mobile,Desktop division
    classDef default fill:#777777
    classDef circle fill:#95A5A6
    class GL circle
```

Endor Labs creates managed namespaces that mirror your GitLab groups under an Endor Labs namespace (for example, `happyendor`). Endor Labs creates `happycorp` as the parent namespace with `web`, `mobile`, and `desktop` as the child namespaces. The namespace `happycorp` will be under the Endor Labs namespace.

Each of these child namespaces have further child namespaces as follows:

* web: alpha, beta, gamma
* mobile: delta, epsilon, zeta
* desktop: pi, rho, sigma

The following diagram shows the organization of namespaces in Endor Labs.

```
graph TD
    EN[happyendor]
    HC[happycorp]

    %% Main divisions
    Web[web]
    Mobile[mobile]
    Desktop[desktop]

    %% Web subgroups
    WA[alpha]
    WB[beta]
    WG[gamma]

    %% Mobile subgroups
    MD[delta]
    ME[epsilon]
    MZ[zeta]

    %% Desktop subgroups
    DP[pi]
    DR[rho]
    DS[sigma]

    %% Main connections
    EN --> HC
    HC --> Web
    HC --> Mobile
    HC --> Desktop

    %% Web connections
    Web --> WA
    Web --> WB
    Web --> WG

    %% Mobile connections
    Mobile --> MD
    Mobile --> ME
    Mobile --> MZ

    %% Desktop connections
    Desktop --> DP
    Desktop --> DR
    Desktop --> DS

    class HC main
    class EN endor
    class Web,Mobile,Desktop division
    class WA,WB,WG,MD,ME,MZ,DP,DR,DS group
    classDef main fill:#008B87
    classDef division fill:#008B87
    classDef group fill:#008B87
```

**Note**

In Endor Labs, namespaces are always in lowercase. If your groups have uppercase characters in their names, the corresponding namespaces will be converted to lowercase.

## Manage multiple installations of GitLab App

You cannot create multiple GitLab installations with the same root group in the host URL within the same Endor Labs namespace.

For example, if a GitLab installation exists with a host URL like `gitlab.com/group1/sg1`, you cannot create another installation with a host URL like `gitlab.com/group1/sg2` within the same Endor namespace. Instead, you must create the installation with a different root group in the host URL, such as `gitlab.com/group2/sg2`.

```
graph TD

      %% Endor Labs namespace
      EN[happyendor]

      %% GitLab groups
      G1[group1]
      G2[group2]
      SG1[sg1]
      SG2[sg2]

      %% connections
      EN --> G1
      EN --> G2
      G1 --> SG1
      G2 --> SG2

      class EN endor
      class G1,G2,SG1,SG2 managed
      classDef managed fill:#008B87
```

If you wish to create an installation with a host URL like `gitlab.com/group1/sg2`, it should be inside a different Endor Labs namespace.

```
graph TD

      %% Endor Labs namespace
      EN[happyendor]
      EN2[happyendor2]

      %% GitLab groups
      G1[group1]
      G2[group1]
      SG1[sg1]
      SG2[sg2]

      %% connections
      EN --> G1
      EN2 --> G2
      G1 --> SG1
      G2 --> SG2

      class EN,EN2 endor
      class G1,G2,SG1,SG2 managed
      classDef managed fill:#008B87
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

## Prerequisites for GitLab App

Before installing and scanning projects with Endor Labs GitLab App, make sure you have:

* A [GitLab cloud](https://www.gitlab.com) account or a self-hosted GitLab instance.
* An organization in GitLab.
* Endor Labs GitLab App requires a [GitLab personal access token](https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html#create-a-personal-access-token) with at least `read_api` permission. You need to provide the `api` permission if you want to scan your merge requests.

**Admin Authorization Role**

Only users with admin authorization role in Endor Labs can create and manage installations. See [Authorization roles](../../../administration/access-endorlabs/authorization-roles/) for more information.

**GitLab Personal Access Token**

If you have restrictions on using a regular GitLab personal access token or face issues with such a token, you can use a [personal access token for a GitLab service account](https://docs.gitlab.com/user/profile/service_accounts/#view-and-manage-personal-access-tokens-for-a-service-account) instead.

## Install the GitLab App

1. Sign in to Endor Labs.
2. Select **Projects** from the left sidebar and click **Add Project**.
3. From **GITLAB**, select **GitLab App**.
   ![GitLab App](../../../images/gitlab-scan.png)
4. Enter the GitLab organization URL in the format: `https://gitlab.com/{group}/{subgroup1}/...`.

   You need to enter at least the root group. For example, `https://gitlab.com/group1`.

   You can provide the host URL up to any subgroup level. For example, `https://gitlab.com/group1/subgroup1/subgroup2/subgroup3`.

   Endor Labs creates namespaces for groups and subgroups and maps projects to these namespaces.

   If the GitLab installation is created at the tenant level, Endor Labs supports up to 10 levels of GitLab group nesting. If the installation is created within a nested namespace under the tenant, the supported nesting depth decreases by one level for each additional level of nesting.
5. Enter the GitLab personal access token.

**Scope of the Personal Access Token**

The personal access token must have at least the `read_api` scope. If you want to scan merge requests, you need to provide the personal access token of a project developer role with the `api` scope.

6. Select the scan types to enable:

   * **SCA**: Perform software composition analysis and discover AI models used in your repository.
   * **Secret**: Scan GitLab projects for exposed secrets.
   * **CI/CD**: Scan GitLab projects and identify all the CI/CD tools used.
   * **SAST**: Scan GitLab projects to generate SAST findings.

   The available scan types depend upon your license.
7. Select **Include Archived Repositories** to scan your archived repositories. By default, the GitLab archived repositories aren’t scanned.
8. Click **Create**.

   Your GitLab App installation is created and has now started monitoring the projects in your groups. Endor Labs GitLab App scans your GitLab projects every 24 hours and reports any new findings.
9. Optionally, you can continue to [Configure GitLab App MR scans](./gitlab-mr-scan/) to scan your merge requests.

   ![GitLab App installation created](../../../images/gitlab-app-installation-next.png)

   You can also choose to [configure the webhook for MR scans](../gitlab-app/gitlab-mr-scan/#configure-webhook-for-gitlab-app-mr-scans) and apply it to specific projects through a scan profile. See [Scan profiles](../../../scan-with-endorlabs/manage-scan-profiles/) for more information. Thereby, you can ensure that MR scans are only for selected projects rather than for all the projects in the group.
10. Click **Skip** to if you don’t want to scan your merge requests.

    You can enable MR scans later in the [GitLab App integration](../gitlab-app/manage-gitlab-app/#edit-gitlab-app-integration).

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

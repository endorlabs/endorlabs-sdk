---
url: https://docs.endorlabs.com/deployment/monitoring-scans/
title: Monitoring or supervisory scans | Endor Labs Docs
downloaded: 2026-01-29 22:20:06
---

Monitoring or supervisory scans | Endor Labs Docs



* Type to search...

[Print entire section](/deployment/monitoring-scans/_print.html)



# Monitoring or supervisory scans

Learn how to deploy the Endor Labs application for monitoring or supervisory scans in our environment.

Perform monitoring scans to gain fast and broad visibility over open source risks across the application portfolio without requiring integrations into application pipelines. These scans are conducted periodically.

```
graph TB
    subgraph Customer["Customer Environment"]
        REPOS[("Source Code Repositories")]
    end

    subgraph Endor[<label style='font-size: 17px'>Endor Labs Infrastructure</label>]
        APP["Endor Labs App"]
        CLOUD["Scan Environment<br/><small>Customer data destroyed after scans</small>"]
        PLATFORM["Endor Labs Platform<br/><small>Generate findings and alerts</small>"]
    end

    APP -->|<small>1. Continuous monitoring</small>| REPOS
    APP -->|<small>2. Trigger scan every 24h or on-demand</small>| CLOUD
    CLOUD <-->|<small>3. Clone and scan repositories</small>| REPOS
    CLOUD -->|<small>4. Send results</small>| PLATFORM

    style REPOS fill:#C4B5FD
```

Endor Labs monitoring scans are available for the following source code management (SCM) platforms:

* **GitHub**: You can use the Endor Labs GitHub App to scan your GitHub organizations. It provides broad visibility over your GitHub organizations. Once installed, the GitHub App will automatically clone and scan all the repositories every 24 hours, providing continuous monitoring for open source vulnerabilities. It performs RSPM scans for posture management of your repository weekly on Sundays. These repositories are temporarily cloned and retained only during the scan. See [Scan using the GitHub App](../monitoring-scans/github-app/) for more information. Endor Labs supports GitHub cloud. GitHub App supports pull request scans and pull request comments. See [Scan pull requests using the GitHub App](../monitoring-scans/github-app/github-app-pr-scans/) for more information.
* **Azure DevOps**: You can use the Endor Labs Azure DevOps App to scan your Azure projects organizations. It provides broad visibility over your Azure organizations. Once installed, the Azure DevOps App will automatically clone and scan all Azure repos every 24 hours, providing continuous monitoring for open source vulnerabilities. These repositories are temporarily cloned and retained only during the scan. See [Deploy Endor Labs Azure DevOps App](../monitoring-scans/azure-app/) for more information. Endor Labs supports Azure DevOps cloud instances.
* **GitLab**: You can use the Endor Labs GitLab App to scan your GitLab organization. It provides broad visibility over your GitLab group and subgroups. Once installed, the GitLab App will automatically clone and scan all projects every 24 hours, providing continuous monitoring for open source vulnerabilities. These repositories are temporarily cloned and retained only during the scan. See [Deploy Endor Labs GitLab App](../monitoring-scans/gitlab-app/) for more information. Endor Labs support both GitLab cloud and self-managed instances. GitLab App supports merge request scans. See [Scan merge requests using the GitLab App](../monitoring-scans/gitlab-app/gitlab-mr-scan/) for more information.
* **GitHub Enterprise Server**: You can use the Endor Labs GitHub App Enterprise to scan your self-hosted GitHub Enterprise Server (GHES) organizations and repositories. Once installed, the app will automatically clone and scan all repositories every 24 hours, providing continuous monitoring for open source vulnerabilities. It performs RSPM scans for posture management of your repository weekly on Sundays. These repositories are temporarily cloned and retained only during the scan. The app supports pull request scans and pull request comments as well. See [Deploy Endor Labs GitHub App Enterprise](../monitoring-scans/github-app/github-enterprise-app/) for more information.
* **Bitbucket Data Center**: You can use the Endor Labs Bitbucket App to scan your Bitbucket Data Center. It provides broad visibility over your Bitbucket projects. Once installed, the Bitbucket App will automatically clone and scan all projects every 24 hours, continuously monitoring open source vulnerabilities. These repositories are temporarily cloned and retained only during the scan. See [Deploy Endor Labs Bitbucket App for Data Center](../monitoring-scans/bitbucket-datacenter-app/) for more information.
* **Bitbucket Cloud**: You can use the Endor Labs Bitbucket App to scan your Bitbucket Cloud. It provides broad visibility over your Bitbucket Cloud projects. Once installed, the Bitbucket App will automatically clone and scan all projects every 24 hours, providing continuous monitoring for open source vulnerabilities. These repositories are temporarily cloned and retained only during the scan. See [Deploy Endor Labs Bitbucket App for Bitbucket Cloud](../monitoring-scans/bitbucket-cloud/) for more information.
* **Local monitoring scan**: Perform periodic scans in your local environment. You must provide the necessary computing resources to run the scans. These scans can support any type of Git repository. See [Set up Jenkins pipeline for supervisory scans](../monitoring-scans/jenkins-supervisory-scan/).

You can use the following wizard to get a tailored plan for setting up monitoring scans for your SCM platform.

### SCM Monitoring Scans Setup Wizard

Pick your SCM and scan options. We'll generate a tailored checklist and links.

1 SCM
2 Environment
3 Options
4 Plan

Choose your SCM platform

Where should monitoring scans run?

Select scan options

Your tailored plan

Reset
Copy plan

Back
Next

## Support Matrix for monitoring scans

Endor Labs features available depends upon the type of scan and the SCM.

The following table lists the scan capabilities available for different types of SCM.

| Feature | GitHub Cloud | GitHub Enterprise Server | Azure DevOps Cloud | GitLab Cloud | GitLab Self-Managed | Bitbucket Data Center | Bitbucket Cloud |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [Reachability Analysis](../../introduction/reachability-analysis/) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| [Secrets Scan](../../secrets-leak-detection/) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| [SAST](../../sast-scans-with-endorlabs/) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| [RSPM](../../scan-with-endorlabs/scm-configuration-management/) | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| [PR Comments](../../deployment/monitoring-scans/github-app/scan-with-githubapp/#scan-prs) | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ |
| [PR Checks](../../deployment/monitoring-scans/github-app/scan-with-githubapp/#scan-prs) | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ | ✗ |
| [Container Scan](../../scan-with-endorlabs/scan-containers/) | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |

### Remediation

The following table lists the types of remediation available for different types of SCM.

| Feature | GitHub Cloud | GitHub Enterprise Server | Azure DevOps Cloud | GitLab Cloud | GitLab Self-Managed | Bitbucket Data Center | Bitbucket Cloud |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [Jira remediation](../../integrations/jira-integration/) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| [Endor Patches](../../upgrades-and-remediation/using-endor-patches/) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| [PR remediation](../../upgrades-and-remediation/pr-remediation/) | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |

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

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

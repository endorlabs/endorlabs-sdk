---
url: https://docs.endorlabs.com/deployment/monitoring-scans/
title: Monitoring or supervisory scans | Endor Labs Docs
downloaded: 2025-11-20 11:48:01
---

Monitoring or supervisory scans | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/deployment/monitoring-scans/_print.html)



# Monitoring or supervisory scans

Learn how to deploy the Endor Labs application for monitoring or supervisory scans in our environment.

Perform monitoring scans to gain fast and broad visibility over open source risks across the application portfolio without requiring integrations into application pipelines. These scans are conducted periodically.

```
graph TD
    A["Endor Labs App"]
    B["Customer Repositories"]
    C["Endor Labs Cloud<br/><small>Customer data destroyed after scans</small>"]
    D["Endor Labs Platform<br/><small>Generate findings from scan results</small>"]

    A -->|<small>Continuous monitoring</small>| B
    A -->|<small>Initiate scan every 24h or on-demand</small>| C
    C <-->|<small>Clone and scan repositories</small>| B
    C -->|<small>Pass scan data</small>| D

    subgraph "Supervisory scan workflow"
    A
    B
    C
    D
    end

    class B customer
    class A,C,D endor
    classDef customer fill:#3FE1F3
```

* **GitHub App monitoring scan**: You can use the Endor Labs GitHub App to scan your GitHub organizations. It provides broad visibility over your GitHub organizations. Once installed, the GitHub App will automatically clone and scan all the repositories every 24 hours, providing continuous monitoring for open source vulnerabilities. It performs RSPM scans for posture management of your repository weekly on Sundays. These repositories are temporarily cloned and retained only during the scan. See [Scan using the GitHub App](../monitoring-scans/github-app/) for more information.
* **Azure DevOps App monitoring scan**: You can use the Endor Labs Azure DevOps App to scan your Azure projects organizations. It provides broad visibility over your Azure organizations. Once installed, the Azure DevOps App will automatically clone and scan all Azure repos every 24 hours, providing continuous monitoring for open source vulnerabilities. These repositories are temporarily cloned and retained only during the scan. See [Deploy Endor Labs Azure DevOps App](../monitoring-scans/azure-app/) for more information.
* **GitLab App monitoring scan**: You can use the Endor Labs GitLab App to scan your GitLab organization. It provides broad visibility over your GitLab group and subgroups. Once installed, the GitLab App will automatically clone and scan all projects every 24 hours, providing continuous monitoring for open source vulnerabilities. These repositories are temporarily cloned and retained only during the scan. See [Deploy Endor Labs GitLab App](../monitoring-scans/gitlab-app/) for more information.
* **Bitbucket App for Bitbucket Data Center monitoring scan**: You can use the Endor Labs Bitbucket App to scan your Bitbucket Data Center. It provides broad visibility over your Bitbucket projects. Once installed, the Bitbucket App will automatically clone and scan all projects every 24 hours, continuously monitoring open source vulnerabilities. These repositories are temporarily cloned and retained only during the scan. See [Deploy Endor Labs Bitbucket App for Data Center](../monitoring-scans/bitbucket-datacenter-app/) for more information.
* **Bitbucket App for Bitbucket Cloud monitoring scan**: You can use the Endor Labs Bitbucket App to scan your Bitbucket Cloud. It provides broad visibility over your Bitbucket Cloud projects. Once installed, the Bitbucket App will automatically clone and scan all projects every 24 hours, providing continuous monitoring for open source vulnerabilities. These repositories are temporarily cloned and retained only during the scan. See [Deploy Endor Labs Bitbucket App for Bitbucket Cloud](../monitoring-scans/bitbucket-cloud/) for more information.
* **Local monitoring scan**: Perform periodic scans in your local environment. You must provide the necessary computing resources to run the scans. These scans can support any type of Git repository. See [Set up Jenkins pipeline for supervisory scans](../monitoring-scans/jenkins-supervisory-scan/).

## Support Matrix

Endor Labs features available depends upon the type of scan and the SCM.

### Scan capabilities

The following table lists the scan capabilities available for different types of SCM.

| Feature | GitHub Cloud | Azure DevOps Cloud | GitLab Cloud | GitLab Self-Managed | Bitbucket Data Center | Bitbucket Cloud |
| --- | --- | --- | --- | --- | --- | --- |
| [Reachability Analysis](../../introduction/reachability-analysis/) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| CI/CD Tools | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| [Secrets Scan](../../secrets-leak-detection/) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| [SAST](../../sast-scans-with-endorlabs/) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| [RSPM](../../scan-with-endorlabs/scm-configuration-management/) | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| [PR Comments](../../deployment/monitoring-scans/github-app/scan-with-githubapp/#scan-prs) | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| [PR Checks](../../deployment/monitoring-scans/github-app/scan-with-githubapp/#scan-prs) | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| [Container Scan](../../scan-with-endorlabs/scan-containers/) | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |

### Remediation

The following table lists the types of remediation available for different types of SCM.

| Feature | GitHub Cloud | Azure DevOps Cloud | GitLab Cloud | GitLab Self-Managed | Bitbucket Data Center | Bitbucket Cloud |
| --- | --- | --- | --- | --- | --- | --- |
| [Jira remediation](../../integrations/jira-integration/) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| [Endor Patches](../../upgrades-and-remediation/using-endor-patches/) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| [PR remediation](../../upgrades-and-remediation/pr-remediation/) | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |

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

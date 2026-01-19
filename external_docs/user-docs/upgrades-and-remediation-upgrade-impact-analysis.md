---
url: https://docs.endorlabs.com/upgrades-and-remediation/upgrade-impact-analysis/
title: Upgrade impact analysis | Endor Labs Docs
downloaded: 2026-01-16 09:48:10
---

Upgrade impact analysis | Endor Labs Docs



* Type to search...

[Print entire section](/upgrades-and-remediation/upgrade-impact-analysis/_print.html)



# Upgrade impact analysis

Learn how Endor Labs helps you fix issues in your dependencies with remediation guidance.

To help developers and security teams make informed decisions, Endor Labs provides a prioritized list of upgrade recommendations for each project and package.

The recommendations are made after assessing the following criteria to determine the impact and complexity of an upgrade:

* Vulnerabilities associated with a dependency’s current version and those of its transitive dependencies.
* Resolved vulnerabilities associated with a dependency’s later versions and those of its transitive dependencies.
* Heuristic factors that influence the probability of breaking changes.
* Program analysis to directly identify breaking changes.

Endor Labs provides an assessment of upgrade options for each dependency, including the potential impact and risk of each option.

The following upgrade options are available after assessment:

* The latest version of the software
* The latest vulnerable free version
* The most impactful update with moderate evidence of breaking changes
* The most impactful update with low evidence of breaking changes

**License**

Upgrade impact analysis is available with the Endor Pro license.

## Remediation risk

Endor Labs evaluates the remediation options for each recommended upgrade and assigns a remediation risk. To assign remediation risk, Endor Labs looks for [breaking changes](#breaking-changes) associated with the upgrade and conflicts between [dependency versions](#dependency-conflicts). There are three categories of remediation risk.

* **High Remediation Risk**: This risk level is assigned when Endor Labs has high confidence that a breaking change will occur.
* **Medium Remediation Risk**: This risk level is assigned when Endor Labs has identified a potential breaking change but has low to moderate confidence in its impact. It is also assigned in cases of major version conflicts that could be affected by the upgrade.
* **Low Remediation Risk**: This risk level is assigned when there is minimal or no evidence suggesting that a breaking change will occur. The absence of evidence does **NOT** guarantee that it will not break your application.

### Breaking changes

Breaking changes may necessitate refactoring your code to complete an upgrade due to newly introduced incompatibilities.
A breaking change may occur due to the following criteria:

* **API Changes**: When the public interface of a library changes, such as through renaming or removing functions, altering function signatures, or modifying expected input or output parameters.
* **Behavioral Changes**: When the underlying behavior of a function or method changes, even if the interface remains the same. This can lead to unexpected results or introduce issues.
* **Dependency Updates**: When a dependency of a dependency, that is a transitive dependency, introduces breaking changes, it can affect the higher-level dependency.
* **Deprecations and Removals**: When deprecated features are finally removed or altered significantly.
* **Configuration Changes**: When the configuration format or options for a library change.
* **Changes in Supported Platforms**: When a library drops support for certain platforms or versions of platforms, for example, an older version of Go.

### Dependency conflicts

Dependency conflicts occur when different parts of a software project require different versions of the same dependency. These conflicts can cause various issues, such as build failures, runtime errors, or unexpected behavior. When there are major or minor version conflicts in your dependency graph, the impact can vary depending on the nature of the conflicts and the specific dependencies involved.

While conflicts do not necessarily guarantee that updating will impact your application, they increase the likelihood that changes may affect it.

## View remediation recommendations

To view Endor Labs remediation recommendations:

1. Sign in to Endor Labs and select **Projects** from the left sidebar.
2. Select the project for which you want to view the remediations.
3. Select **Remediations** to view the list of remediation recommendations available for the project.

### Review recommendations

Endor Labs lists the remediations available for the project based on the main branch of the project. You can filter the remediations by **Show Only Reachable** remediations, the **Remediation Risk**, and the time period. Additionally, you can export all findings to a CSV file.

![View dependencies with remediations](../../images/uia-view-dependencies.png)

The list shows the affected package, its current version, and the number of vulnerabilities fixed by the recommended upgrade. The list also indicates if [Endor patches](../using-endor-patches/) are available for the package.

Select a dependency to view all available upgrade options.

![View remediations and dependency upgrade recommendations](../../images/uia-view-dependency-remediation.png)

Endor Labs assesses the upgrade options and identifies the optimal upgrade as the recommended choice based on the vulnerabilities fixed and the [remediation risk](#remediation-risk). You can view the remediation risk and the number of vulnerabilities resolved for each upgrade path.

### Review remediation risk

Select an upgrade option to view the details of this upgrade path on the right sidebar.

![Upgrade overview information](../../images/uia-upgrade-overview.png)

You can view the following information in **Overview**:

* An overview of the remediation including the remediation risk, version age, latest scan information, and findings fixed.
* The **Remediation Risk Drivers** with the potential conflicts and breaking changes. Remediation risk drivers also influence the breaking change confidence, which denotes how likely your project’s functionalities can be negatively impacted due to the upgrade.
* The **Details** of the package including the project, package, and version details.
* The **Fixed Findings** with the details of the vulnerabilities fixed by this upgrade.

Select **Potential Conflicts** to view the [potential conflicts](#dependency-conflicts) that may occur due to the upgrade.

![View upgrade’s potential conflicts](../../images/uia-upgrade-conflicts.png)

You can view all the major or minor version conflicts in your dependency graph if you upgrade to this version.

Select **Breaking Changes** to view the [breaking changes](#breaking-changes) that may occur due to the upgrade.

![View breaking changes introduced by upgrade](../../images/uia-upgrade-breakingchanges.png)

In a newer version, functions and interfaces may be removed or their behavior may have changed. You can view the list of functions or interfaces that are affected by this upgrade so that you can understand the impact of the upgrade.

Click **View Details** to view the list of potential conflicts and breaking changes in a single page view.

![View details of dependency](../../images/uia-remediation-view-details.png)

You can also view the remediation recommendations from **Projects** > **Findings**. See [Manage project findings](../../managing-projects/view-findings/#view-remediations) for more information.

## Limitations of upgrade impact analysis

Upgrade impact analysis has the following limitations:

* Upgrade recommendations are proposed only for OSS packages.
* Upgrade recommendations are based on the data available in the main branch of the project.
* Upgrade impact analysis never recommends version downgrades.
* Upgrade impact analysis does not propose upgrades for container dependencies, GitHub Actions dependencies, and approximate dependencies.
* Upgrade recommendations for groups of direct dependencies are not supported.
* Upgrade impact analysis for a dependency is at the project level and not across the tenant or a namespace.
* Upgrade recommendations are suggested only for the dependencies with vulnerabilities.
* Version constraints are excluded in the upgrade recommendations.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

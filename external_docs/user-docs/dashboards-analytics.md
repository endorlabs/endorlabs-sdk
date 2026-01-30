---
url: https://docs.endorlabs.com/dashboards/analytics/
title: Analytics | Endor Labs Docs
downloaded: 2026-01-26 10:07:51
---

Analytics | Endor Labs Docs



* Type to search...

[Print entire section](/dashboards/analytics/_print.html)



# Analytics

Visualize metrics on volume and efficiency of issue resolution.

Analytics dashboard offers a comprehensive view of your security metrics, and tracks finding trends and resolution times across projects. Use it to quickly assess risk levels, monitor progress, and identify areas needing improvement in your security posture.

## Set the filters

Customize the data displayed on the Analytics dashboard by applying specific filters to focus on the most relevant information, enabling better analysis and decision-making. Adjusting the filters ensures that you can track progress and identify trends that are critical to your security and development goals.

**Tip**

These are global filters and apply to all widgets on this dashboard.

* **Severity** - Filter the data based on finding severity such as Critical (C), High (H), Medium (M), or Low (L).
* **Category** - Filter the findings by category such as AI models, vulnerability, SCA, SAST, secrets, and container.
* **Attributes** - Narrow down the list based on a range of factors such as:

  + if a patch is available to fix the findings
  + if the vulnerable function is reachable
  + if the dependency is reachable
  + if the dependency originates from a current repository or a current tenant
  + if the dependency is a test dependency
  + if the dependency is a phantom dependency
  + if the finding originates from itself, direct, or a transitive dependency
  + filter the findings by the **Exploited** tag from **CISA KEV**
  + filter the findings by the **Warn** or **Break the Build** options set in the [action policy](../../managing-policies/action-policies/#create-an-action-policy-from-template)

    See [Finding attributes](../../managing-projects/view-findings/#finding-attributes) for more information.
* **When was the Finding first introduced** - Select a time period from the available options to filter the analytics data based on when the finding was first scanned. By default, the data from the last 90 days is displayed.

## Findings snapshot metrics

Get a quick overview of key metrics for the selected category, helping you monitor newly identified and resolved findings, as well as the time it takes to address them. Here’s what each metric represents:

* **Newly Discovered**: The number of findings recently identified across your projects. This count indicates areas that may need attention or remediation.
* **Resolved**: The number of findings that have been fixed or mitigated recently, reflecting progress in securing your projects.
* **Mean Time to Resolve**: The average time, in days, it takes to resolve a finding once discovered. Lowering this number can indicate faster responses to security issues.
* **Minimum Time to Resolve**: The shortest time it took to resolve a finding in the current tracking period, providing insight into how quickly issues can be addressed.
* **Maximum Time to Resolve**: The longest time it took to resolve a finding, showing the upper range for resolution times and highlighting areas where responses might need improvement.

These metrics help track security effectiveness over time and identify trends in finding resolution within your projects.

## Analytics for AI models, SCA, SAST, secrets, and container

When you select **AI models**, **SCA**, **SAST**, **secrets**, or **container** as the category filter, the dashboard displays the following sections.

![Analytics for SCA findings](../../images/analytics-charts-findings.png)

### Findings over time

The **Findings over Time** chart tracks the number of newly discovered and resolved findings across your projects over the [selected period](#set-the-filters). This view helps you analyze trends in finding discovery and resolution, showing whether security issues are increasing, decreasing, or remaining steady over time.

### Time for issues resolved

The **Time for Issues Resolved** chart displays the number of days taken to resolve issues over the selected period. This metric helps assess response efficiency, highlighting how quickly security and other issues are addressed, and can indicate improvements or delays in issue resolution processes.

### New open findings approaching SLA

The **New Open Findings Approaching SLA** section shows findings that are close to missing their resolution deadlines, with less than 24 hours remaining. This allows you to prioritize issues and take immediate action to resolve them before the SLA is missed. To define or adjust SLA durations, see [Set SLA for findings](#set-sla-for-findings).

## Analytics for vulnerabilities

When you select **Vulnerability** as the category filter, the dashboard displays all the charts and metrics described above, plus additional dependency trend charts specific to vulnerability analysis.

![Analytics charts for vulnerabilities](../../images/analytics-charts-vulnerabilities.png)

### Vulnerabilities over time

The **Vulnerabilities over Time** chart tracks the number of detected vulnerabilities across your projects over the [selected period](#set-the-filters). This view helps you analyze trends in vulnerability discovery and resolution, showing whether security issues are increasing, decreasing, or remaining steady over time.

### Time for vulnerabilities issues resolved

This chart displays the number of days taken to resolve vulnerability issues over the selected period. This metric helps assess response efficiency, highlighting how quickly vulnerabilities are addressed, and can indicate improvements or delays in issue resolution processes.

### New open vulnerabilities approaching SLA

The **New Open Vulnerabilities Approaching SLA** section shows vulnerabilities that are close to missing their resolution deadlines, with less than 24 hours remaining. This allows you to prioritize issues and take immediate action to resolve them before the SLA is missed. To define or adjust SLA for different vulnerability severities, see [Set SLA for findings](#set-sla-for-findings).

### Outdated dependencies trend

This chart tracks the number of outdated dependencies in your projects over time. It helps you monitor the progress of updating libraries and frameworks, providing insights into how many dependencies are no longer up-to-date. By identifying trends, you can prioritize updating critical dependencies, reduce security risks, and ensure your projects remain current with the latest versions.

### Unmaintained dependencies trend

This chart shows the number of dependencies in your projects that are no longer actively maintained over time. This helps you track the accumulation of unsupported libraries and frameworks, which may pose security and compatibility risks. By monitoring this trend, you can take proactive steps to replace or update unmaintained dependencies, ensuring the stability and security of your projects.

### Unused dependencies trend

This chart tracks the number of dependencies in your projects that are no longer in use over time. This helps identify redundant libraries or packages that can be safely removed, reducing the overall project size and improving performance. By monitoring this trend, you can streamline your codebase and reduce potential security risks from unnecessary dependencies.

## Set SLA for findings

A Service Level Agreement (SLA) defines the expected time frame within which security findings should be addressed, based on their severity. It sets a deadline for resolving new open findings before they are considered approaching or breaching SLA.

Follow these steps to define SLA for findings:

1. Sign in to Endor Labs and navigate to **Dashboard** on the left sidebar.
2. Select **ANALYTICS**.
3. Scroll down to **New Open Findings Approaching SLA** and select a severity level to set the SLA for it. The default SLA for severities are:

   * Critical - 30 Days
   * High - 30 Days
   * Medium - 90 Days
   * Low - 180 Days

   For example, click **SLA** duration for Critical to modify it.
4. In **SLA DURATION**, set a duration in days for the selected severity level.
5. Click **Reset** to restore the SLA to its default duration.
6. Click **Save**.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

---
url: https://docs.endorlabs.com/dashboards/oss-overview/
title: OSS overview | Endor Labs Docs
downloaded: 2025-11-20 11:48:42
---

OSS overview | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/dashboards/oss-overview/_print.html)



# OSS overview

Visualize complete software security posture of your organization.

Use the widgets in OSS overview dashboard to understand various aspects of your codebase, dependencies, vulnerabilities, and overall software security posture.

## Scanned by Endor Labs

Displays information on the following scan statistics across all ecosystems in the given tenant:

* Total number of dependencies, categorized into direct and transitive dependencies
* Total number of vulnerabilities, categorized into unreachable and other vulnerabilities
* Total number of projects
* total number of packages
* Total number of scans
* Total number of configured notifications

## Vulnerability prioritization funnel

Endor Labs’ vulnerability prioritization funnel systematically assesses and categorizes vulnerabilities based on their severity and category. The vulnerabilities are prioritized in the following order:

* **Total open vulnerabilities** - Indicates the complete list of vulnerabilities detected in all the scanned projects in this tenant.
* **Not in test** - Indicates the list of vulnerabilities that are present in the production code and not in the test code.
* **Fix available** - Indicates the list of vulnerabilities in the production code, for which a fix is available.
* **Reachable** - Indicates the list of vulnerabilities in production code, with a fix, that can be accessed or exploited. Customize the reachable findings for your organization. You choose to see the data for reachable functions or potentially reachable functions, or for both. See [Customize finding reachability](#customize-finding-reachability).
* **Exploitable likelihood** - Indicates the list of vulnerabilities in production code, with a fix, that are reachable, and with an EPSS probability score greater than 1%.

Click **Low Risk Upgrades** in the vulnerability prioritization funnel to view findings with low remediation risk, if present in your namespace.

Use the search bar to filter projects by name and view their OSS overview. The search supports partial matching. For example, when you search `repo`, the system displays all projects containing `repo` in their title along with their corresponding OSS overview data.

![Vulnerability funnel](../../images/vulnerability-funnel.png)

#### Note

You require an Endor Labs OSS Pro license to access the **Low Risk Upgrade** feature.

By applying this funnel approach, organizations can prioritize addressing the most critical, exploitable, and actionable vulnerabilities first, maximizing their security efforts.

### Customize finding reachability

Customize finding reachability for your organization. The data in the **Vulnerability Prioritization Funnel**

1. Sign in to Endor Labs and click **Dashboard**.
2. Navigate to the **Vulnerability Prioritization Funnel** and click the vertical three dots.
3. In **FINDING REACHABILITY**, define your finding reachability criteria.

   You can select **Reachable Function**, **Potentially Reachable Function**, both options, or neither.
4. Click **Save**.
5. Click **Reset** to restore finding reachability to your last set values.

![vulnerability funnel customization](../../images/vuln-funnel-customization.png)

### Development hours and cost saved

Visualize the hours and cost saved metrics information on the dashboard.

* **Dev Hours Saved** - Development hours saved is an estimate that is calculated after reducing the number of vulnerabilities that developers must prioritize. See [Customize development hours](#customize-baseline-for-development-hours).
* **Cost Saved** - Cost savings is an estimate that is made by multiplying the saved developer hours with the full-time equivalent (FTE) hourly cost for triaging vulnerabilities. See [Customize cost baseline](#customize-baseline-for-cost).

#### Customize baseline for development hours

Adjust the development baseline to meet your organization’s specific needs.

1. Sign in to Endor Labs and click **Dashboard**.
2. Navigate to the **Dev Hours Saved** and click the vertical ellipsis.
3. Choose **BASELINE** and set **DEV HOURS** for a record on the **Vulnerability Prioritization Funnel**,
   * **Total Open Vulnerabilities** - Provide approximate development hours required to triage all open vulnerabilities. By default, the development hours saved are calculated based on this baseline and displayed on the **Vulnerability Prioritization Funnel**.
   * **Not In Test** - Provide approximate development hours required to triage vulnerabilities in production code.
   * **Reachable** - Provide approximate development hours required to triage accessible and most exploitable vulnerabilities.
   * **Fix Available** - Provide approximate development hours required to triage vulnerabilities that can be addressed with a patch or an upgrade.
4. Click **Save**.

#### Customize baseline for cost

Tailor the cost baseline to reflect the Full-Time Equivalent cost of your organization.

1. Sign in to Endor Labs and click **Dashboard**.
2. Navigate to **Cost Saved** and click the vertical ellipsis.
3. Enter an **HOURLY COST** and **CURRENCY** that applies to one full-time employee following your organization’s application security program.
4. Click **Save**.

## Top projects metrics

View the top project data by all findings, all vulnerabilities, reachable vulnerabilities, outdated dependencies, and unmaintained dependencies. You can identify the numbers for critical, high, medium, and low risk severity findings. Click the bar graph to view complete details.

## Top packages metrics

View package data by all findings, all vulnerabilities, reachable vulnerabilities, outdated dependencies, and unmaintained dependencies. You can identify the numbers for critical, high, medium, and low risk severity findings. Click the bar graph to view complete details.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

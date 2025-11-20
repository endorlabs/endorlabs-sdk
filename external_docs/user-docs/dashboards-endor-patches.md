---
url: https://docs.endorlabs.com/dashboards/endor-patches/
title: Endor patches | Endor Labs Docs
downloaded: 2025-11-20 11:49:12
---

Endor patches | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/dashboards/endor-patches/_print.html)



# Endor patches

Explore the benefits of Endor patches on the dependencies identified within your organization.

Endor patches dashboard provides you with metrics to understand the impact of using Endor patches and remediating vulnerabilities.

### Set the filters

Customize the data displayed on the dashboard by applying specific filters to focus on the most relevant information, enabling better analysis and decision-making.

**critical(C)** or **high(H)** priority findings - Customize the displayed data by selecting critical or high priority findings or both.

**Reachability** - Filter the data by reachable function or reachable dependency.

* Select **Yes** to include reachable function or dependency.
* Select **No** to exclude reachable function or dependency.
* Select **Potential** to include potentially reachable functions or dependencies.

These are global filters and apply to all widgets on this dashboard.

### Use impact calculator

Use the impact calculator to see the number of critical and high findings remediated after applying the recommended Endor patches.

![Impact Calculator](../../images/impact_calculator.png)

### View impact of Endor patches

The Top impact By Endor Patches gives you the available Endor patches that you can request.

* View the list of dependencies with their current version, findings, projects impacted, and package versions impacted.
* Click the drawer on a dependency to view details about the dependency and the list of fixable findings, projects impacted, and package versions impacted.
* To export the data in the widget into a CSV file for offline analysis, click **Export All as CSV**.
* To request the Endor patches, click **Request Now**.
* To view the available patches, click **Available**.

![Impact widget](../../images/endor_patches.png)

### Request for Endor patches

After reviewing the most impactful dependencies that affect your applications, you can choose to request for Endor patches that will remediate your critical and high priority findings.

1. From the **Endor Patches** dashboard, navigate to **Top Impact By Endor Patches**.
2. Select the patch you want to request and click **Request Now**.
3. Enter a comment and click **Send Request**.

### Patch request lifecycle

The patch request lifecycle consists of four stages: Open, In Process, Done, and Won’t Do, each representing a different phase of assessment and development.

* **Open**: Endor Labs is assessing the request’s feasibility.
* **In Process**: The request is actively being developed.
* **Done**: The patch is now available.
* **Won’t Do**: Endor Labs has determined that the request is not feasible.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

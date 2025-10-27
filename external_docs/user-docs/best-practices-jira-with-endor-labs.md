---
url: https://docs.endorlabs.com/best-practices/jira-with-endor-labs/
title: Best Practices: Jira integration with Endor Labs | Endor Labs Docs
downloaded: 2025-10-27 12:59:04
---

Best Practices: Jira integration with Endor Labs | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/best-practices/jira-with-endor-labs/_print.html)



# Best Practices: Jira integration with Endor Labs

Learn how to use Jira efficiently with Endor Labs.

Explore how to effectively use Endor Labs with Jira to manage security findings within your organization’s software development workflows. Endor Labs analyzes your software dependencies, generates security findings, and automatically creates Jira tickets to track and resolve these issues. Each ticket is linked to your project and contains specific details about the detected vulnerabilities.

## Set up Jira integration in Endor Labs

Endor Labs integrates with Jira Cloud to automatically create tickets in your projects when configured policies are violated, streamlining your organization’s security workflow.

See [Jira integration with Endor Labs](../../integrations/jira-integration/) for more information.

## Track findings in Jira

A **finding** is a security vulnerability in your source code. When Endor Labs scans a project, it analyzes its **dependencies**, which are the software packages the project relies on and generates findings. A **package version** is a specific release of a dependency, identified by a version number (for example, `jwx v1.0.5`).

Endor Labs automatically creates a Jira ticket to track and address the issue when a finding is identified. The ticket includes the project URL, branch, details about findings such as:

* Finding: A link to the identified vulnerability.
* Explanation: A brief description of the issue.
* Summary: Technical details about the vulnerability, versions affected, and packages impacted.
* Remediation: Recommended actions, such as upgrading to a secure version.
* Location: Exact file, package, dependency, and repository where the vulnerability is identified.

![Findings in Jira](../../images/jira-findings-columns.png)

You can assign the ticket to an individual for remediation. Based on the selected issue type and the aggregation type, it can be one of the following:

* Task
* Sub-Task
* Bug

Findings and their associated Jira tickets are organized within a project. In Jira, a project serves as a centralized space where all related issues are managed.

To learn more about setting up a project, refer to the [Jira documentation.](https://confluence.atlassian.com/jira061/jira-administrator-s-guide/project-management/defining-a-project)

### Choose the right notification aggregation type

Choose the appropriate notification aggregation type to organize security findings in Jira effectively. See [Aggregation Types](../../managing-policies/action-policies/#aggregation-types-for-notifications) for more information.

#### Project

Use **Project** aggregation to receive a single Jira notification for all findings in a project. This groups all findings into one Jira ticket. It is ideal for teams that prefer a high-level view of issues.

For example, the back-end team relies on libraries such as `archiver` and `jwx`. All findings from these libraries are compiled into a single Jira **Task**.

This approach helps the teams:

* Avoid excessive notifications and streamline remediation efforts.
* Manage all security related issues within their designated Jira project.
* Improve tracking and collaboration.

![Project Aggregation Type](../../images/project-aggregation.png)

#### Dependency

Use **Dependency** aggregation to receive separate notifications for each affected dependency in a project. A parent Jira ticket is created, with each dependency tracked as a **Sub-Task** with its findings. This approach is ideal for teams prioritizing security management at the dependency level.

For example, the back-end team developing a `Go` application relies on libraries like `archiver` and `jwx`. When Endor Labs scans the project:

* Findings for `archiver` are present in its **Sub-Task**.
* Findings for `jwx` are present in its **Sub-Task**.

This approach ensures:

* A clear division of responsibilities for efficient vulnerability tracking.
* Focused issue resolution without overwhelming teams.
* Granular visibility into security risks for targeted management.

![Dependency Aggregation](../../images/dependency-aggregationn-example.png)

#### Dependency per package version

Use this to receive separate notifications for each affected package version. Each version has its own **Sub-Task** under a parent Jira ticket, with its findings present in the respective **Sub-Task**.

For example, a `Go` project using the `jwx` library has multiple versions in use. Endor Labs creates a parent Jira ticket, with each affected version tracked as **Sub-Tasks**:

* Findings for `jwx v2.0.13` are present in its **Sub-Task**.
* Findings for `jwx v1.0.5` are present in its **Sub-Task**.

This approach helps the teams:

* Apply security fixes precisely without triggering unnecessary updates.
* Reduce notification noise and focus on resolving issues in their specific dependencies.
* Maintain stability in machine learning workflows while managing vulnerabilities effectively.

![Dependency Per Package Version Aggregation](../../images/dependency-per-package-version-example.png)

#### Note

Ensure you have a Jira instance set up on Jira Cloud before integrating with Endor Labs.

## Jira tickets

Each Jira ticket contains specific labels, comments, and custom fields to provide context and streamline tracking.

### Labels

Endor Labs automatically assigns labels to Jira tickets to simplify the management of security issues. These labels appear in the right-hand sidebar of the Jira ticket under **Details**. The following labels are provided by Endor Labs:

`endorlabs-scan`: Assigned to every Jira ticket that is generated by Endor Labs scan.

`endor-severity`: Represents the severity of the associated finding. The value of this label can be critical, high, medium, or low.

#### Tip

For Dependency and Dependency per Package Version aggregation types, the `endor-severity` label is applied to the **Sub-Task** and not the parent ticket.

In the following example, the ticket titled “Findings with no dependencies” includes the following labels:

`endorlabs-scan`: Identifies that the ticket was created as part of an Endor Labs scan.

`endor-severity:medium`: Represents the severity of the detected finding.

![Example of Jira label ](../../images/jira-labels.png)

### Comments

During future scans, the status of the findings is updated in the form of comments in your Jira ticket.

If new findings are detected, a comment will be generated with their details.

![New findings comment](../../images/jira-comments-1.png)

If existing findings are resolved, a comment will be generated with their details.
![Update findings comment](../../images/jira-comments-2.png)

### Components

Endor Labs automatically sets the **Components** field using values from your Jira project configured during the Jira integration with Endor Labs.

* For a [team-managed Jira project](https://support.atlassian.com/jira-software-cloud/docs/what-are-team-managed-and-company-managed-projects/#Team-managed-projects), Endor Labs applies the configured component value to each ticket it creates.

  In the following example, `Test DEPR Component` is the assigned components value.
  ![Team managed project components](../../images/team-mananged-components.png)
* For a [company-managed Jira project](https://support.atlassian.com/jira-software-cloud/docs/what-are-team-managed-and-company-managed-projects/#Company-managed-projects), Endor Labs applies all configured component values to each ticket it creates.

  In the following example, `Test DEPR Component` and `Test UI Component` are the assigned components values.
  ![Company managed project components](../../images/company-managed-components.png)

### Considerations

Ensure your Jira board has a designated resolution state like **Done**, **Fixed**, etc. for Endor Labs to mark tickets as resolved. If no such state exists, the ticket remains unresolved.

Ensure that tickets can transition from a beginning state, such as **To Do**, to a resolution state like **Done** without requiring intermediate states such as **In Progress**. If the workflow restricts direct movement, Endor Labs cannot move tickets between states, and you must update the status manually on your Jira board.

### FAQs

What permissions are required for Jira integration?

Jira integration requires only the minimum project-level permissions, such as: create issues, transition issues, assign issues, resolve issues, and add comments.




What happens if a Jira ticket is manually marked as **Resolved** in Jira?

If a Jira ticket is manually marked as **Resolved** in your Jira board, Endor Labs does not scan the finding in the future scans and the finding is not displayed in the ticket.




What happens if we fix the security vulnerability?

Endor Labs marks the ticket as resolved in your Jira board after the next scan.




Can I change the project that I initially configured?

No. You must add a new Jira integration and then configure Endor Labs to the new project with a new API key.




What happens if I change the aggregation type?

Jira updates the grouping of findings in the board based on changes to the action policy’s aggregation type.

* When changing from **Project** to **Dependency**, findings are split into separate **Sub-tasks** based on the dependency type.
* When changing from **Project** to **Dependency per package version**, findings are split into **Sub-tasks** based on the package version.
* When changing from **Dependency** or **Dependency per package version** to **Project**, all findings are consolidated into a single Jira ticket.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

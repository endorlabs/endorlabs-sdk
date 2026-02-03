---
url: https://docs.endorlabs.com/integrations/jira-integration/
title: Set up Jira integration with Endor Labs | Endor Labs Docs
downloaded: 2026-02-03 00:50:10
---

Set up Jira integration with Endor Labs | Endor Labs Docs



* Type to search...

[Print entire section](/integrations/jira-integration/_print.html)



# Set up Jira integration with Endor Labs

Learn how to implement ticketing workflows for JIRA.

Integrate Endor Labs with Jira and automatically create Jira tickets in specific projects when configured policies are violated. This integration automates the process of generating Jira tickets within your organization’s existing security workflow. This integration is supported on Jira Cloud.

To integrate Endor Labs with Jira:

* [Generate Jira API token](#generate-jira-api-token)
* [Configure Jira Integration on Endor Labs](#configure-jira-integration-on-endor-labs)
  + [Manage Endor Labs Jira notifications](#manage-endor-labs-jira-notifications)
* [Associate an action policy with a Jira notification](#associate-an-action-policy-with-a-jira-notification)
  + [View ticket details in Jira](#view-ticket-details-in-jira)
  + [View Jira notification in Endor Labs](#view-jira-notification-in-endor-labs)

## Generate Jira API token

Generate Jira API credentials that you want to use to sign in to Endor Labs.

**Note**

It is recommended that the Jira account used for this integration includes only the following set of minimum required permissions.

* Create Issues
* Transition Issues
* Assign Issues
* Resolve Issues
* Add Comments

1. Sign in to your Jira account.
2. Navigate to your [Jira profile](https://id.atlassian.com/manage-profile/security).
3. Under **API tokens**, click **Create API Token**.
4. Enter a concise label to distinguish your token and click **Create**.
5. Click **Copy to clipboard**, and have the token handy to enter in the Endor Labs application.

**Note**

The token cannot be viewed after closing the form. Copy it to a secure location and have it handy. Do not share the token.

## Configure Jira Integration on Endor Labs

Set up Jira integration on the Endor Labs application.

1. Sign in to Endor Labs.
2. From the sidebar, navigate to **Integrations**.
3. Under **Notifications**, click **Manage** for Jira.
4. Click **Add Notification Integrations**.
5. Enter a name and description for the integration.
6. Enter a Jira username.

   The user account is displayed as the reporter for all the tasks or bugs created in Jira for this notification. We recommend creating a new user account for receiving Jira notifications from Endor Labs.
7. In **API Key**, enter the API token that you generated from Jira.
8. In **Jira URL**, enter the HTTPS endpoint of your Jira instance.
9. Select one of the following In **Authentication Method**:

   * **Basic Authentication**: If you are using Jira cloud, enter your Jira user name in **Username** and the API token that you generated from Jira in **API Key**.
   * **Personal Access Token [PAT]**: If you are using Jira Data Center, enter the personal access token (PAT) in **Access Token**.
10. In **PROJECT Key**, enter the project key of your Jira project in which you want to create the notifications.

    The project key is the prefix of the bug or task ID. For example, if the project key is `ENG`, the task or bug is created with ID in the format, `ENG-352`.
11. In **ISSUE TYPE**, enter the notification issue type such as `Task`, `Bug`, `Story`, `Sub-Task`, or `Epic`.

    The issue type is case-sensitive. Make sure to match with an exact issue type on your Jira board.

**Note**

Make sure the endorctl version is 1.6.547 or higher to use **ISSUE TYPE**.

12. In **RESOLVED STATUS**, specify the resolved status used in your Jira projects.

    For example, if you enter the value as `Completed`, after the findings are resolved, the Jira ticket will be updated to this status. If you don’t specify a status, Endor Labs will attempt to determine your project’s resolution status and default to one of the following statuses in the order of priority: `Done`, `Resolved`, `Closed`, or `Fixed`.

**Warning**

If you do not provide a resolved status and your project’s resolved status does not match `Done`, `Resolved`, `Closed`, or `Fixed`, you will be unable to configure the integration.

13. In **LABELS**, enter a label to associate it with your Jira notifications.
14. For [company-managed Jira project](https://support.atlassian.com/jira-software-cloud/docs/what-are-team-managed-and-company-managed-projects/#Company-managed-projects), enter one or more component values in **COMPONENTS**. These values are automatically populated in the **Components** field of the created Jira ticket.
15. Click **Add Custom Field** to add custom `KEY-VALUE` pairs in the created Jira ticket. Use this to create a **Components** field in your team managed Jira project.

    For example, you can add `Source` as **KEY** and associate it to `Endor Labs` in **VALUE**, so that every notification created will now have the information `Source = Endor Labs` associated with the ticket.

    For [team-managed Jira project](https://support.atlassian.com/jira-software-cloud/docs/what-are-team-managed-and-company-managed-projects/#Team-managed-projects), use **Add Custom Field** to create a **Components** field in your Jira ticket. In **KEY** enter `Components` and enter the component value in **VALUE**.

**Note**

Ensure that the endorctl version is 1.6.567 or higher to use **Custom Fields**. Check that the **KEY** you enter matches an existing custom field in your Jira project; otherwise, the notification cannot be saved and the **KEY-VALUE** pair will not be reflected in your Jira ticket.

16. Click **Propagate this notification target to all child namespaces** to apply this Jira notification target to all child namespaces within the hierarchy.
17. Click **Add Notification Integration**.

### Manage Endor Labs Jira notifications

You can view and manage the Endor Labs Jira notifications created for a project.

1. From the sidebar, navigate to **Integrations**.
2. Under **Notifications**, click **Manage** for Jira.
3. To edit a notification, click the vertical ellipsis and choose **Edit Notification Integration**.
4. To delete a notification, click the vertical ellipsis dots and choose **Delete Notification Integration**.

## Associate an action policy with a Jira notification

Users can create action policies to execute a recommended action when a policy is violated. For example, if there is a license compliance violation, you can create a Jira ticket and notify the required personnel.

While creating an action policy, configure the following settings:

* Select **Choose an Action** as **Send Notification**.
* From **SELECT NOTIFICATION TARGETS**, choose the Jira integration notification that you created.
* Choose an **Aggregation type** for Jira notifications.
  + Choose **None (Notify for each Finding)** to trigger a separate email for each finding. This is supported only for [SAST](../../managing-policies/action-policies/templates/#sast) and [Secrets](../../managing-policies/action-policies/templates/#secrets) action policies.
  + Choose **Project** to trigger a single notification for all findings.
  + Choose **Dependency** to trigger a notification for every dependency.
  + Choose **Dependency per package version** to trigger notifications for every unique combinations of dependency and package version.

See [Aggregation types](../../managing-policies/action-policies/#aggregation-types-for-notifications) for more details.

### View ticket details in Jira

A parent ticket is created with the selected issue type, either a Task or a Bug, and includes the project name. Each identified dependency is assigned to a dedicated sub-ticket, which includes both the project name and the dependency name. Findings without dependencies are grouped into a separate sub-ticket. During future scans, the existing sub-tickets are updated or marked as resolved. If a new dependency is detected, a new sub-ticket is created.

1. Sign into your Jira account.
2. Navigate to **Projects** drop down menu in the top bar and select your project.
3. Click on the issue to view its details.

![Jira ticket](../../images/Jiraticket.png)

The following labels are associated with a Jira ticket created by Endor Labs:

* `endorlabs-scan`: Indicates that the ticket was created by Endor Labs scan.
* `endor-severity`: The `endor-severity` label has an associated value, `critical`, `high`, `medium`, or `low`, that reflects the severity of the associated Endor Labs finding. If a ticket includes multiple findings with different severities, the label represents the highest severity among them.

**Note**

For Dependency and Dependency per package version aggregation types, the `endor-severity` label is included in the sub-task.

![Jira Parent Ticket](../../images/jiraticketwithlabel.png)

During future scans, the status of the findings is updated in the form of comments in your Jira ticket.

* If new findings are detected, a comment will be generated with their details.

![New findings Jira comment](../../images/jira-comments-1.png)

* If existing findings are resolved, a comment will be generated with their details.

![Resolved findings Jira comment](../../images/jira-comments-2.png)

### View Jira notification in Endor Labs

You can view the details of created Jira tickets in the Endor Labs application, including their status such as open or closed, associated action policy, number of violations, and other key details.

1. From the Endor Labs application, navigate to **Manage** and click **Notifications**.
2. Navigate across the **Open**, **Resolved**, or **All** tabs to view the issues listed under them.
3. You can view specific details such as created date of the ticket, the name of the policy, the name of the project, the number of violations, and any labels associated with the projects.
4. Choose a notification and click the vertical three dots on the far right side and choose:
   * **Dismiss Notification**: Clear this notification if it is no longer valid. It will be marked in grey.
   * **Show Details**: View the Jira ticket number and you can also navigate to Jira.
   * **Go to Policy**: View configuration details of the policy that created this Jira ticket.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

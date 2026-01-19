---
url: https://docs.endorlabs.com/integrations/slack-integration/
title: Set up Slack integration | Endor Labs Docs
downloaded: 2026-01-16 09:50:43
---

Set up Slack integration | Endor Labs Docs



* Type to search...

[Print entire section](/integrations/slack-integration/_print.html)



# Set up Slack integration

Learn how to integrate Slack with Endor Labs and receive finding notifications

Integrate Endor Labs with Slack and automatically receive policy violations as notifications in your Slack channels. If you are using Slack for team communication and notifications, this integration helps you to seamlessly integrate Endor Labs into your organization’s existing workflows.

* [Create incoming webhooks in Slack](#create-incoming-webhooks-in-slack)
* [Configure Slack integration](#configure-slack-integration)
  + [Associate an action policy with a Slack notification](#associate-an-action-policy-with-a-slack-notification)
  + [Manage Slack notification targets in Endor Labs](#manage-slack-notification-targets-in-endor-labs)
  + [Customize Slack notification templates](#customize-slack-notification-templates)
  + [Data model](#data-model)
* [Run a scan](#run-a-scan)
  + [View notifications in Slack](#view-notifications-in-slack)

## Create incoming webhooks in Slack

Create an incoming webhook to your Slack channel to enable Endor Labs to post notifications in the channel. The **Incoming Webhook** provides a unique URL to integrate your Slack channel in Endor Labs.

**Note**

We recommend you designate a channel in your Slack workspace for receiving Endor Labs notifications and create an incoming webhook for that channel.

To create incoming webhooks in Slack:

1. Create a [Slack app](https://api.slack.com/apps?new_app=1) for Endor Labs or use an existing app.
   * Click **Create New App**.
   * Choose **From Scratch** and Enter a name for the app, for example, **Endor Labs**.
   * Select your workspace and click **Create App**
   * You can enter basic, install, or display information for your [Endor Labs app in Slack](https://api.slack.com/apps?new_app=1).
   * In **Display Information**, you can upload a logo and customize App colours to distinguish the Endor Labs App on the Slack workspace.
   * Click **Save Changes**.
2. Navigate to **Features**, select **Incoming Webhooks**, and toggle **Activate Incoming Webhooks**.
3. Refresh the page and click **Add New Webhook to Workspace**.
4. Select a channel to receive Endor Labs findings in **Post to**, then select **Authorize**. If you need to add the incoming webhook to a private channel, you must first be in that channel.
5. From **Settings**, copy the webhook URL under **Webhook URLs for Your Workspace**. Keep this URL handy to enter in Endor Labs.

For details on creating incoming webhooks in Slack, see [Slack Integration](https://api.slack.com/messaging/webhooks).

## Configure Slack integration

To configure Slack integration, follow these steps:

1. Sign in to Endor Labs and click **Integrations** from the left sidebar.
2. Navigate to **Slack** under **Notifications** and click **Add**.
3. Click **Add Notification Integration**.
4. Specify a name and description for this integration.
5. Enter webhook URL copied from Slack in **Incoming Webhook**.
6. Click **Add Notification Integration**.

### Associate an action policy with a Slack notification

Users can create action policies to send a Slack notification when the conditions of a given policy are met. For example, if there is a critical or high vulnerability, send the findings to Slack.

While creating an action policy, configure the following settings:

* Select **Choose an Action** as **Send Notification**.
* From **SELECT NOTIFICATION TARGETS**, choose the Slack integration notification that you created.
* Choose an **Aggregation type** for notifications.

  + Choose **None (Notify for each Finding)** to trigger a separate message for each finding. This is supported only for [SAST](../../managing-policies/action-policies/templates/#sast) and [Secrets](../../managing-policies/action-policies/templates/#secrets) action policies.
  + Choose **Project** to group and send all the findings related to a project in one message.
  + Choose **Dependency** to send individual messages for every dependency.
  + Choose **Dependency per package version** to send individual messages for every unique combination of dependency and package version.

  You can see the top three findings from the highest available severity level. If fewer than three findings exist, only those are shown.
* From **Assign Scope**, include the project tags in **INCLUSIONS** to apply this policy to a project.

See [Create an action policy](../../managing-policies/action-policies/) for more details.

### Manage Slack notification targets in Endor Labs

You can view and manage the Endor Labs Slack notification targets created for a project.

1. From the sidebar, navigate to **Manage** > **Notifications**.
2. Under **Notifications**, click **Manage** for **Slack**. You can view all your created notification targets for Slack.
3. To edit a notification target, click the vertical ellipsis and choose **Edit Notification Integration**.
4. To delete a notification target, click the vertical ellipsis dots and choose **Delete Notification Integration**.

### Customize Slack notification templates

Endor Labs provides a default standard template with standard information that will be included in the Slack message. You can use the default template or you can choose to edit and customize this template to fit your organization’s specific requirements. You can also create custom templates using [Go Templates](https://pkg.go.dev/text/template).

1. Sign in to Endor Labs and navigate to **Manage**>**Integrations**.
2. Look for **Slack** under **Notifications**.
3. Click **Manage** to view the list of configured notification integrations.
4. Choose one and click the ellipsis on the right side, and click **Edit Template**.
5. Make required changes to any of the following templates and click **Save Template**.
   * **Open** - This template is used when new notifications are raised.
   * **Update** - This template is used when an existing notification is updated, such as, when some findings for the notification are changed.
6. Click **Restore to Default** to revert the changes.
7. Use the download icon on the top right corner to download this template.
8. Use the copy icon to copy the information in the template.

### Data model

To create custom templates for Slack messages, you must understand the data supplied to the template.

See the protobuf specification `NotificationData` message used for the templates.

```
syntax = "proto3";

package internal.endor.ai.endor.v1;

import "google/protobuf/wrappers.proto";
import "spec/internal/endor/v1/finding.proto";
import "spec/internal/endor/v1/notification.proto";
import "spec/internal/endor/v1/package_version.proto";
import "spec/internal/endor/v1/project.proto";
import "spec/internal/endor/v1/repository_version.proto";

option go_package = "github.com/endorlabs/monorepo/src/golang/spec/internal.endor.ai/endor/v1";
option java_package = "ai.endor.internal.spec";

// The statistics for findings in a notification.
message FindingStats {
  // The total number of findings for a notification.
  google.protobuf.UInt32Value num_total_findings = 1;
  google.protobuf.UInt32Value num_total_critical_severity_findings = 2;
  google.protobuf.UInt32Value num_total_high_severity_findings = 3;
  google.protobuf.UInt32Value num_total_medium_severity_findings = 4;
  google.protobuf.UInt32Value num_total_low_severity_findings = 5;

  // The number of new findings for a notification as compared to the previous scan.
  google.protobuf.UInt32Value num_new_findings = 6;
  google.protobuf.UInt32Value num_new_critical_severity_findings = 7;
  google.protobuf.UInt32Value num_new_high_severity_findings = 8;
  google.protobuf.UInt32Value num_new_medium_severity_findings = 9;
  google.protobuf.UInt32Value num_new_low_severity_findings = 10;

  // The number of findings for a notification that was resolved in latest scan.
  google.protobuf.UInt32Value num_resolved_findings = 11;
}

// The data supplied to notification templates while rendering.
message NotificationData {
  // The raw notification object.
  Notification raw_notification = 1;

  // The name of the project.
  google.protobuf.StringValue project_name = 2;

  // The name of the violated policy that triggered the notification.
  google.protobuf.StringValue policy_name = 3;

  // The Git reference of the project that was scanned.
  google.protobuf.StringValue ref_name = 4;

  // The project URL.
  google.protobuf.StringValue project_url = 5;

  // The map of finding UUIDs to finding objects.
  map<string, internal.endor.ai.endor.v1.Finding> findings_map = 6;

  // The map of finding UUIDs to corresponding parent package version objects.
  map<string, internal.endor.ai.endor.v1.PackageVersion> package_version_map = 7;

  // The map of finding UUIDs to corresponding parent project objects.
  // Deprecated: Findings cannot have Project as a parent. This field is kept for backward compatibility but will always be empty.
  map<string, internal.endor.ai.endor.v1.Project> project_map = 8 [deprecated = true];

  enum NotificationType {
    NOTIFICATION_TYPE_UNSPECIFIED = 0;

    // Notification type when a notification is created.
    NOTIFICATION_TYPE_CREATE = 1;

    // Notification type when a notification is updated.
    NOTIFICATION_TYPE_UPDATE = 2;

    // Notification type when a noticiation is resolved.
    NOTIFICATION_TYPE_RESOLVED = 3;
  }

  NotificationType type = 9;

  // The project to which the notification is associated.
  internal.endor.ai.endor.v1.Project project = 10;

  // The map of finding UUIDs to the correcponding parent repository version objects.
  map<string, internal.endor.ai.endor.v1.RepositoryVersion> repository_version_map = 11;

  // The project URL in Endor Labs UI.
  google.protobuf.StringValue project_app_url = 12;

  // The policy URL in Endor Labs UI.
  google.protobuf.StringValue policy_app_url = 13;

  FindingStats finding_stats = 14;

  // The map of package version UUIDs to package version names.
  map<string, string> package_version_name_map = 15;

  // The Endor context reference of the project that was scanned.
  // This is the same as ref_name except for the 'default' branch.
  google.protobuf.StringValue raw_ref_name = 16;
}
```

To understand Project, Finding, PackageVersion, and RepositoryVersion definitions used in this protobuf specification, see:

* [Project resource kind](../../rest-api/using-the-rest-api/data-model/resource-kinds/#project)
* [Finding resource kind](../../rest-api/using-the-rest-api/data-model/resource-kinds/#finding)
* [PackageVersion resource kind](../../rest-api/using-the-rest-api/data-model/resource-kinds/#packageversion)
* [RepositoryVersion resource kind](../../rest-api/using-the-rest-api/data-model/resource-kinds/#repositoryversion)

See the following specification to understand a few additional functions available to the template. You can access these functions by using their corresponding keys.

```
// FuncMap contains the additional functions that are available to notification templates.
var FuncMap = func(h *NotificationTemplate) template.FuncMap {
	return template.FuncMap{
		"now": func() string {
			now := time.Now()
			return now.Format("01-02-2006 15:04:05 MST")
		},

		// csvFileName generates the filename for the CSV attachment for Jira.
		"csvFileName": GetJiraAttachmentFilename,

		// findingURL returns the URL for the given finding.
		"findingURL": h.getFindingURL,

		// toCSV converts the given string to a CSV format.
		"toCSV": toCSV,

		// findingLevelSlackEmoji returns the slack emoji for the given finding based on severity.
		"findingLevelSlackEmoji": GetSlackEmojiForSeverity,

		// packageName returns the user facing name of the package.
		"packageName": func(p *endorpb.PackageVersion) string {
			return lib.GetUserFacingName(p.GetMeta().GetName().GetValue())
		},

		// filteredFindingsURL returns the URL to view findings with the given uuids
		"filteredFindingsURL": common.GetFilteredFindingsURL,

		// increment increments the given integer by 1.
		"increment": func(i int) int {
			return i + 1
		},

		// GetFindingLocation returns the location information for a finding based on its type.
		"GetFindingLocation": func(finding *endorpb.Finding) string {
			namespace := ""
			if h.Data != nil && h.Data.RawNotification != nil && h.Data.RawNotification.TenantMeta != nil {
				namespace = h.Data.RawNotification.TenantMeta.GetNamespace().GetValue()
			}
			return GetFindingLocation(finding, h.m, namespace, h.Data)
		},

		// Sanitize removes trailing newlines from the given string.
		"Sanitize": func(s string) string {
			return strings.TrimRight(s, "\n")
		},

		// countFindingsBySeverity returns the count of findings grouped by severity level.
		//
		// Template usage:
		//   {{- $counts := countFindingsBySeverity .FindingsMap -}}
		// - Returns a `*SeverityCounts` with fields: `Critical`, `High`, `Medium`, `Low`.
		"countFindingsBySeverity": func(findingsMap map[string]*endorpb.Finding) *SeverityCounts {
			counts := CountFindingsBySeverity(findingsMap)
			return counts
		},

		// sortedFindingsBySeverity returns findings sorted by severity (Critical -> High -> Medium -> Low).
		// Template usage:
		//   {{- range $i, $f := sortedFindingsBySeverity .FindingsMap -}}
		//     {{ increment $i }}. {{ Sanitize $f.Meta.Description.Value }}
		//     ({{ getSeverityName $f.Spec.Level }})
		//   {{- end -}}
		"sortedFindingsBySeverity": func(findingsMap map[string]*endorpb.Finding) []*endorpb.Finding {
			sorted := SortFindingsBySeverity(findingsMap)
			return sorted
		},

		// getSeverityName returns the user-facing severity name (Critical/High/Medium/Low/Unspecified).
		// Template usage:
		//   Severity: {{ getSeverityName .Spec.Level }}
		"getSeverityName": func(level endorpb.Finding_Spec_FindingLevel) string {
			name := GetSeverityName(level)
			return name
		},

		// getSeverityColor returns the hex color code for a finding severity.
		// Template usage:
		//   {color:{{ getSeverityColor .Spec.Level }}}● {{ getSeverityName .Spec.Level }}{color}
		"getSeverityColor": func(level endorpb.Finding_Spec_FindingLevel) string {
			color := GetSeverityColor(level)
			return color
		},
	}
}

type SeverityCounts struct {
	Critical int
	High     int
	Medium   int
	Low      int
}
```

## Run a scan

Run the endorctl scan on your configured projects. See [endorctl scan commands](../../endorctl/commands/scan/) for more information.

### View notifications in Slack

View Endor Labs’ findings in Slack and take remedial actions.

* Sign in to Slack and view the notifications on the configured channel.
* You can view the top 3 findings by their severity level. Click **View All** to see all the findings in Endor Labs.

![View notifications in Slack](../../images/slack_notifications.png)

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

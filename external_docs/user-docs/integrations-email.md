---
url: https://docs.endorlabs.com/integrations/email/
title: Set up email integration | Endor Labs Docs
downloaded: 2026-01-29 22:23:25
---

Set up email integration | Endor Labs Docs



* Type to search...

[Print entire section](/integrations/email/_print.html)



# Set up email integration

Learn how to integrate your email addresses with Endor Labs and receive finding notifications

Integrate your email address with Endor Labs and automatically receive policy violations as email notifications.

* [Configure email integration](#configure-email-integration)
  + [Associate an action policy with the email notification](#associate-an-action-policy-with-the-email-notification)
  + [Customize email notification templates](#customize-email-notification-templates)
  + [Data model](#data-model)
* [Run a scan](#run-a-scan)

## Configure email integration

To configure an email integration, follow these steps:

1. Sign in to Endor Labs and select **Integrations** from the left sidebar.
2. Navigate to **Email** under **Notifications** and click **Add**.
3. Click **Add Notification Integration**.
4. Specify a name and description for this integration.
5. Enter email addresses separated by commas in **EMAIL ADDRESSES**.
6. Click **Add Notification Integration**.

### Associate an action policy with the email notification

Users can create action policies to send an email notification when the conditions of a given policy are met. For example, if there is a critical or high vulnerability, send an email notification.

While creating an action policy, configure the following settings:

* Select **Choose an Action** as **Send Notification**.
* From **SELECT NOTIFICATION TARGETS**, choose the email integration notification that you created.
* Choose an **Aggregation type** for notifications.

  + Choose **None (Notify for each Finding)** to trigger a separate email for each finding. This is supported only for [SAST](../../managing-policies/action-policies/templates/#sast) and [Secrets](../../managing-policies/action-policies/templates/#secrets) action policies.
  + Choose **Project** to group and send all the findings related to a project in one email.
  + Choose **Dependency** to send individual emails for every dependency.
  + Choose **Dependency per package version** to send emails for every unique combination of dependency and package version.
* From **Assign Scope**, include the project tags in **INCLUSIONS** to apply this policy to a project.

See [Create an action policy](../../managing-policies/action-policies/) for more details.

### Customize email notification templates

Endor Labs provides a default template with standard information that will be included in the email. You can use the default template or you can choose to edit and customize this template to fit your organization’s specific requirements. You can also create custom templates using [Go Templates](https://pkg.go.dev/text/template).

1. Sign in to Endor Labs and navigate to **Manage** > **Integrations**.
2. Look for **Email** under **Notifications**.
3. Click **Manage** to view the list of configured notification integrations.
4. Choose a notification integration and click the ellipsis on the right side, and click **Edit Template**.
5. Make required changes to any of the following templates and click **Save Template**.
   * **Open** - This template is used when new notifications are raised.
   * **Update** - This template is used when an existing notification is updated, such as, when some findings for the notification are changed.
   * **Resolve** - This template is used when all the findings reported by the notification are resolved.
6. Click **Restore to Default** to revert the changes.
7. Use the download icon on the top right corner to download this template.
8. Use the copy icon to copy the information in the template.

### Data model

To create custom templates for email notifications, you must understand the data supplied to the template.

See the `EmailData` message used for **Open** and **Update** templates.

```
// EmailData contains mappings for findings and package versions that is to be published as
// an email. It also contains the NotificationData object in the payload.
type EmailData struct {
	Payload                      *endorpb.NotificationData
	PackageVersionFindingMapping map[string]map[string][]string
	PackageVersionMap            map[string]*endorpb.PackageVersion
	APIURL                       string
	APPURL                       string
	FromAddress                  string
}
```

See the `ResolvedEmailData` message used for **Resolve** template.

```
// ResolvedEmailData contains the data that's acessible in the resolved email template.
type ResolvedEmailData struct {
	APIURL      string
	APPURL      string
	Project     *endorpb.Project
	Policy      *endorpb.Policy
	ProjectName string
}
```

See the following protobuf specification for the `NotificationData` message referenced by `EmailData`.

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

To understand Project, Finding, PackageVersion and RepositoryVersion definitions that are used in this protobuf specification, see:

* [Project resource kind](../../rest-api/using-the-rest-api/data-model/resource-kinds/#project)
* [Finding resource kind](../../rest-api/using-the-rest-api/data-model/resource-kinds/#finding)
* [PackageVersion resource kind](../../rest-api/using-the-rest-api/data-model/resource-kinds/#packageversion)
* [RepositoryVersion resource kind](../../rest-api/using-the-rest-api/data-model/resource-kinds/#repositoryversion)

See the following specification to understand a few additional functions available to the template. You can access these functions by using their corresponding keys.

```
// EmailTemplateFuncs contains the functions that are available in the email template.
var EmailTemplateFuncs = template.FuncMap{
	"now": func() string {
		now := time.Now()
		return now.Format("01-02-2006 15:04:05 MST")
	},

	// findingURL returns the URL for the finding.
	"findingURL": func(f *endorpb.Finding, apiURL string) string {
		findingURL, err := common.GetFindingURL(apiURL, f)
		if err != nil {
			return ""
		}
		return findingURL
	},

	"getGitImage": func(url string) string {
		if strings.HasPrefix(url, "https://github.com") {
			return "github.png"
		}
		if strings.HasPrefix(url, "https://gitlab.com") {
			return "gitlab.png"
		}
		return "default_host.png"
	},

	"getProjectURL": func(p *endorpb.Project, apiURL string) string {
		projectURL, err := common.GetProjectURL(apiURL, p)
		if err != nil {
			return ""
		}
		return projectURL
	},

	"getPackageVersionURL": func(p *endorpb.PackageVersion, apiURL string) string {
		packageVersionURL, err := common.GetPackageVersionURL(apiURL, p)
		if err != nil {
			return ""
		}
		return packageVersionURL
	},

	"getFindingLevel": func(f *endorpb.Finding) string {
		return f.GetSpec().GetLevel().String()
	},

	"isPatchAvailable": func(f *endorpb.Finding) bool {
		return slices.Contains(f.GetSpec().GetFindingTags(), endorpb.FindingTags_FINDING_TAGS_FIX_AVAILABLE)
	},

	"getPackageEcosystem": func(p *endorpb.PackageVersion) string {
		if p == nil {
			return "unspecified"
		}

		offset := len("ECOSYSTEM_")
		ecosystem := p.GetSpec().GetEcosystem().String()[offset:]
		ecosystem = strings.ToLower(ecosystem)
		return ecosystem
	},
}
```

## Run a scan

Run the endorctl scan on your configured projects. See [endorctl scan commands](../../endorctl/commands/scan/) for more information.
You can view email notifications of policy violations in your inbox.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

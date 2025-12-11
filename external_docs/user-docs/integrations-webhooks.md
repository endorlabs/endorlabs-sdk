---
url: https://docs.endorlabs.com/integrations/webhooks/
title: Set up integrations using webhooks | Endor Labs Docs
downloaded: 2025-12-11 11:32:30
---

Set up integrations using webhooks | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/integrations/webhooks/_print.html)



# Set up integrations using webhooks

Learn how to create webhooks and enable custom integrations with Endor Labs application

Webhooks enable real-time communication between different systems or applications over the internet. They allow one application to send data to another application as soon as a specific event or a trigger occurs.

Use webhooks to integrate Endor Labs with applications such as Slack, Microsoft Teams or more, and instantly get notified about projects if your configured policies are violated.

When events are triggered, Endor Labs sends HTTPS POST requests to URLs of your configured events, with all the information you need.

## Configure a webhook integration

Set up a custom integration with Endor Labs webhooks.

1. Sign in to Endor Labs and click **Integrations** from the sidebar.
2. Navigate to Webhooks under **Notifications** and click **Add**.
3. Click **Add Notification Integration**.
4. Enter a name and description for this integration.
5. Enter the URL endpoint for the webhooks.
6. Enter the authentication method such as **API Key**, **Basic**, or **None**.
7. Enter the details for the authentication method such as **USERNAME**, **PASSWORD**, or **API KEY**. Make sure the API Key has required permissions to post messages using webhook.
8. To ensure integrity, de-select **Disable HMAC Integration Check** and enter the **HMAC Shared Key**. The Hash-Based Message Authentication Code (HMAC) ensures the authenticity of a message using a cryptographic hash function and a secret key. The HMAC signature is passed as a header in the HTTP request.
9. Click **Add Notification Integration**.

### Associate an action policy with the webhook

You can create action policies to trigger webhook notifications when policy conditions are met. For example, send a webhook notification when there is a critical or high vulnerability.

While creating an action policy, configure the following settings:

* Select **Choose an Action** as **Send Notification**.
* From **SELECT NOTIFICATION TARGETS**, choose the email integration notification that you created.
* Choose an **Aggregation type** for notifications.

  + Choose **Project** to trigger a single notification for all findings.
  + Choose **Dependency** to trigger a notification for every dependency.
  + Choose **Dependency per package version** to trigger notifications for every unique combination of dependency and package version.
* From **Assign Scope**, include the project tags in **INCLUSIONS** to apply this policy to a project.

See [Create an action policy](../../managing-policies/action-policies/) for more details.

## Endor Labs webhook payload

Endor Labs provides the following webhook payload, that you can customize for your needs.

| Name | Description |
| --- | --- |
| `data.message` | Brief message about the number of findings discovered for a project |
| `data.project_url` | Link to the scanned project in the Endor Labs application |
| `data.policy.name` | Name of the violated policy that triggered the notification |
| `data.policy.url` | Link to the violated policy in the Endor Labs application |
| `data.findings` | Complete list of findings |
| `data.findings[].uuid` | Unique identifier of the finding |
| `data.findings[].description` | Brief description of the finding |
| `data.findings[].severity` | Severity of the finding |
| `data.findings[].dependency [CONDITIONAL]` | Name of dependency that caused the policy violation. This field is only present for findings that have a dependency associated. For example, vulnerability findings |
| `data.findings[].package [CONDITIONAL]` | The version of the package in the project that imported the dependency causing the policy violation. This field is only present for findings that have a package version associated with them. For example, vulnerability findings |
| `data.findings[].repositoryVersion [CONDITIONAL]` | Repository version of the project that triggered the policy violation. This field is only present for findings that have a repository version associated with them. For example, secrets findings |
| `data.findings[].findingURL` | Link to the finding in the Endor Labs application |

You can view all possible payload information in [GetFindings REST API endpoint](https://docs.endorlabs.com/api/#tag/FindingService/operation/FindingService_GetFinding). Expand the `spec` section in the API response to view all the information.
**Example**:

See the following example for a sample notification payload.

```
{
 "data": {
  "message": "6 findings discovered for project endorlabs/monorepo",
  "projectURL": "https://localhost:8082/t/endor/projects/65e5b83466145505541d9664",
  "policy": {
   "name": "Webhook vuln",
   "url": "https://localhost:8082/t/endor/policies/actions?filter.default=Webhook+vuln"
  },
  "findings": [
   {
    "uuid": "550e8400-e29b-41d4-a716-446655440000",
    "description": "GHSA-c2qf-rxjj-qqgw: semver vulnerable to Regular Expression Denial of Service",
    "severity": "FINDING_LEVEL_MEDIUM",
    "dependency": "semver@7.5.0",
    "package": "endorlabs-vscode-extension@1.5.0",
    "findingURL": "https://localhost:8082/t/endor/findings/6614ec9141aef3ab8e90ed80"
   },
   {
    "uuid": "550e8400-e29b-41d4-a716-446655440001",
    "description": "GHSA-c2qf-rxjj-qqgw: semver vulnerable to Regular Expression Denial of Service",
    "severity": "FINDING_LEVEL_MEDIUM",
    "dependency": "semver@7.3.8",
    "package": "endorlabs-vscode-extension@1.5.0",
    "findingURL": "https://localhost:8082/t/endor/findings/6614ec9141aef3ab8e90ed81"
   },
   {
    "uuid": "550e8400-e29b-41d4-a716-446655440002",
    "description": "GHSA-c2qf-rxjj-qqgw: semver vulnerable to Regular Expression Denial of Service",
    "severity": "FINDING_LEVEL_MEDIUM",
    "dependency": "semver@5.7.1",
    "package": "endorlabs-vscode-extension@1.5.0",
    "findingURL": "https://localhost:8082/t/endor/findings/6614ec9141aef3ab8e90ed82"
   },
   {
    "uuid": "550e8400-e29b-41d4-a716-446655440003",
    "description": "GHSA-c2qf-rxjj-qqgw: semver vulnerable to Regular Expression Denial of Service",
    "severity": "FINDING_LEVEL_MEDIUM",
    "dependency": "semver@6.3.0",
    "package": "endorlabs-vscode-extension@1.5.0",
    "findingURL": "https://localhost:8082/t/endor/findings/6614ec9141aef3ab8e90ed83"
   }
  ]
 }
}
```

## Use Endor Labs webhooks to integrate with Slack

If you use Slack as a collaborative tool, integrate Slack channels using webhooks in Endor Labs to publish notifications as messages in the respective channels.

* [Configure a webhook integration](#configure-a-webhook-integration)
* [Endor Labs webhook payload](#endor-labs-webhook-payload)
* [Use Endor Labs webhooks to integrate with Slack](#use-endor-labs-webhooks-to-integrate-with-slack)
  + [Create incoming webhooks in Slack](#create-incoming-webhooks-in-slack)
  + [Customize webhook notification templates](#customize-webhook-notification-templates)
  + [Data model](#data-model)
  + [Webhook handler example for Slack](#webhook-handler-example-for-slack)

### Create incoming webhooks in Slack

Create an incoming webhook to your Slack channel to enable Endor Labs to post notifications in the channel. The webhook provides a unique URL which is used to integrate the channel in Endor Labs. To send messages into Slack using incoming webhooks, see [Slack Integration](https://api.slack.com/messaging/webhooks).

If you have already created an incoming webhook in the channel, copy the unique URL and integrate the channel in Endor Labs.

### Customize webhook notification templates

Endor Labs provides you with a default template with standard information that will be included in the webhook message. You can use the default template or you can choose to edit and customize this template to fit your organization’s specific requirements. You can also create your own custom templates using [Go Templates](https://pkg.go.dev/text/template).

1. Sign into Endor Labs and navigate to **Manage**>**Integrations**
2. Look for **Slack** under **Notifications**.
3. Click **Manage** to view the list of configured notification integrations.
4. Choose one and click the ellipsis on the right side, and click **Edit Template**.
5. Make required changes to any of the following templates and click **Save Template**.
   * **Open** - This template is used when new notifications are raised.
   * **Update** - This template is used when an existing notification is updated, such as, when some findings for the notification are changed.
   * **Resolve** - This template is used when all the findings reported by the notification are resolved.
6. Click **Restore to Default** to revert the changes.
7. Use the download icon on the top right corner to download this template.
8. Use the copy icon to copy the information in the template.

### Data model

To create custom templates for Webhook notifications, you must understand the data supplied to the template.

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

To understand Project, Finding, PackageVersion and RepositoryVersion definitions used in this protobuf specification, see:

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
			utc := now.UTC()
			return utc.Format("01-02-2006 15:04:05")
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

		"Sanitize": func(s string) string {
			return strings.TrimRight(s, "\n")
		},
	}
}
```

### Webhook handler example for Slack

Create a webhook handler or a cloud function to receive webhook requests generated by Endor Labs, authorize the request, and post messages to your Slack channel.

See the following code sample hosted as a cloud function or a webhook handler.

```
// Package p contains an HTTP Cloud Function.
package p

import (
 "encoding/json"
 "fmt"
 "html"
 "io"
 "io/ioutil"
 "bytes"
 "log"
 "net/http"
 "crypto/hmac"
    "crypto/sha256"
    "encoding/hex"
    "strings"
 wrapperspb "google.golang.org/protobuf/types/known/wrapperspb"
)

// Struct representation of default webhook payload from Endor Lab's notification.
type WebhookMessage {
 Data Payload `json:"data"`
}

type Payload struct {
 Message string  `json:"message"`
 ProjectUrl string  `json:"projectURL"`
 Policy  Policy  `json:"policy"`
 Findings []Finding `json:"findings"`
}

type Finding struct {
 Uuid string `json:"uuid"`
 Description string `json:"description"`
 Severity string `json:"severity"`
 Dependency string `json:"dependency,omitempty"`
 Package string `json:"package,omitempty"`
 RepositoryVersion string `json:"repositoryVersion,omitempty"`
 FindingUrl string `json:"findingURL"`
}

type Policy struct {
 Name string `json:"name"`
 Url string `json:"url"`
}

// HelloWorld deserializes the default webhook payload from the notification object,
// formats it into a format that Slack supports and send the message to Slack via webhook.
func HelloWorld(w http.ResponseWriter, r *http.Request) {
 var d WebhookMessage

 if err := json.NewDecoder(r.Body).Decode(&d); err != nil {
  switch err {
  case io.EOF:
   log.Printf("success")
   return
  default:
   log.Printf("json.NewDecoder: %v", err)
   http.Error(w, http.StatusText(http.StatusBadRequest), http.StatusBadRequest)
   return
  }
 }

 // Perform the HMAC sign to make sure that the request is not tampered with.
 hmacSign := ""
 for headerName, headerValues := range r.Header {
  if headerName == "X-Endor-Hmac-Signature" {
   if headerValues[0] == "" {
    http.Error(w, "hmac empty", http.StatusUnauthorized)
    return
   }
   hmacSign = headerValues[0]
  }
 }

 receivedMessage := d.Message
 // Secret configured in Endor
    secretKey := "Secret"

    // Validate the HMAC
    isValid := validateHMAC(receivedMessage, hmacSign, secretKey)

    // Process the result
    if isValid {
      fmt.Fprint(w, html.EscapeString("success"))
    } else {
       http.Error(w, "unauthorized, something changed", http.StatusUnauthorized)
  return
    }

 textToSlack := fmt.Sprintf("%s which violates policy %s", d.Data.Message, d.Data.Policy.Name)
 sendMessageToSlack(textToSlack)

}


func validateHMAC(receivedMessage, receivedHMAC, secretKey string) bool {
    // Create a new HMAC hasher using the SHA-256 hash function and the secret key
    mac := hmac.New(sha256.New, []byte(secretKey))

    // Write the received message to the HMAC hasher
    mac.Write([]byte(receivedMessage))

    // Calculate the HMAC value
    expectedHMAC := mac.Sum(nil)

    // Convert the expected HMAC to a hexadecimal string
    expectedHMACString := hex.EncodeToString(expectedHMAC)

    // Compare the expected HMAC with the received HMAC (ignoring case)
    return strings.EqualFold(receivedHMAC, expectedHMACString)
}

func sendMessageToSlack(msg string) {
    // Replace this url with the url hook from the Slack App
 url := "https://slack.webhook"

 payload := []byte(`{"text": "Hey there are findings in project https://github.com/endorlabs/python-deps.git which violates policy DemoNotification"}`)

 req, err := http.NewRequest("POST", url, bytes.NewBuffer(payload))
 if err != nil {
  fmt.Println("Error creating request:", err)
  return
 }

 req.Header.Set("Content-Type", "application/json")

 client := &http.Client{}
 resp, err := client.Do(req)
 if err != nil {
  fmt.Println("Error sending request:", err)
  return
 }
 defer resp.Body.Close()

 body, err := ioutil.ReadAll(resp.Body)
 if err != nil {
  fmt.Println("Error reading response body:", err)
  return
 }
}
```

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

---
url: https://docs.endorlabs.com/deployment/monitoring-scans/gitlab-app/gitlab-mr-scan/
title: GitLab App MR scans | Endor Labs Docs
downloaded: 2026-01-29 22:20:41
---

GitLab App MR scans | Endor Labs Docs



* Type to search...

[Print entire section](/deployment/monitoring-scans/gitlab-app/gitlab-mr-scan/_print.html)



# GitLab App MR scans

Learn how to enable MR scans using the GitLab App.

Beta

You can configure MR scans while creating a new GitLab App installation or for the existing GitLab App installations. Endor Labs uses group webhooks to scan your merge requests. For more information, refer to [GitLab webhooks](https://docs.gitlab.com/user/project/integrations/webhooks/#group-webhooks).

**Permissions for the GitLab App MR scans**

GitLab App installation requires a personal access token of the project developer role with the `api` scope. You need to configure webhooks to complete the MR scans configuration. Webhooks configuration through cURL requires the personal access token of the group owner with the `api` scope or the group owner role needs to configure the webhook on the GitLab UI.

You can also choose to receive MR comments on your merge requests. After you configure MR comments, Endor Labs posts a comment on the merge request if any issues are detected during the MR scan. See [GitLab MR comments](#gitlab-mr-comments) for more information.

## Configure MR scans during a GitLab App installation

After you complete the initial [installation of the GitLab App](../../gitlab-app/#install-the-gitlab-app) to install the GitLab App in Endor Labs, you can configure MR scans. At this point, the GitLab App will be operational.

You can also choose to [configure the webhook for MR scans](#configure-webhook-for-gitlab-app-mr-scans) and apply it to specific projects through a scan profile. See [Scan profiles](../../../../scan-with-endorlabs/manage-scan-profiles/) for more information. Thereby, you can ensure that MR scans are only for selected projects rather than all the projects in the group.

1. Select **Merge Request Scans** under **Merge Request Configuration**.

   ![GitLab App MR scan setup](../../../../images/gitlab-app-installation-next.png)
2. Optionally, select Merge Request Comments to enable MR comments.

   When you enable MR comments, Endor Labs will post a comment on the merge request if any issues are detected during the MR scan. You need to set up MR comments in Endor Labs to receive the comments. See [GitLab MR comments](#gitlab-mr-comments) for more information.

**Enable MR scans for selected projects**

If you select the options to configure MR scans in your GitLab App installation, merge requests for all the projects in the groups and subgroups are scanned. Instead, you can choose to configure MR scans and MR comments for selected projects. Choose not to select **Merge Request Scans** but continue to set up the webhook for MR scans. Set up a scan profile to configure MR scans. Ensure that you select **Pull Request Scans** and optionally select under **Developer Workflow** when you create the scan profile.

![Configure MR scans for selected projects](../../../../images/scan-profile-pr-scans.png)

See [Scan profiles](../../../../scan-with-endorlabs/manage-scan-profiles/) for more information.

3. Select **Set up the webhook now** under **Webhook Settings**.
4. You can either configure the webhook on the GitLab UI or use the cURL command to set up the webhook.

   Configure the webhook on the GitLab UI

   Ensure that you have the group owner role to configure the webhook on GitLab.

   1. Sign in to GitLab and select the group for which you want to configure the webhook.
   2. Select **Settings** > **Webhooks** from the left sidebar.
   3. Click **Add Webhook**.
   4. Configure the webhook in GitLab.

      * Name: Name for the webhook.
      * Description: Description for the webhook.
      * URL: Enter `https://api.endorlabs.com/webhooks/gitlab` as the URL to access the Endor Labs webhook API.
      * Secret Token: The secret token from Endor Labs.

      You can copy the values from the Endor Labs user interface.

      ![GitLab App MR scan setup webhook](../../../../images/gitlab-app-mr-scan-setup-gitlabui-webhook.png)
   5. Click **Add Custom Header** and enter the following values:

      * Key: `X-Endor-Installation-ID`
      * Value: The Custom Header Value from the Endor Labs user interface. It is the installation ID of the Endor Labs GitLab installation.
   6. Select **Merge request events** under the **Trigger** section.
   7. Ensure that **Enable SSL verification** is selected under the **SSL verification** section.
   8. Click **Add Webhook** to save the changes.

      You can create a webhook without SSL verification, but it is not recommended. Without SSL verification, the webhook is vulnerable to man-in-the-middle attacks.

   Configure the webhook using the cURL command

   Ensure that you have the personal access token of the group owner with the `api` scope to configure the cURL command.

   1. Select **cURL command** to configure the webhook using the cURL command.

      ![GitLab App MR scan setup curl](../../../../images/gitlab-app-mr-scan-setup-gitlabui-curl.png)
   2. Replace `PRIVATE-TOKEN` with the personal access token of the group owner with the `api` scope.
   3. Copy the cURL command and run it on your system to register the webhook with GitLab.

**Save the webhook configuration**

Ensure that you complete the webhook configuration in GitLab and save the configuration in Endor Labs. Otherwise, the MR scans will not be enabled.

5. Click **Save** to save MR scan configuration.

## Configure MR scans for existing GitLab installations

You can configure MR scans for existing GitLab installations or after the creation of a new GitLab installation.

**Scope of the Personal Access Token**

Replace the personal access token with the personal access token of a project developer (minimum) role with the `api` scope for MR scans.

1. Sign in to Endor Labs and select **Integrations** from the left sidebar.
2. Click **Manage** in **GitLab** under **Source Control Managers**.
3. Click the three dots menu next to the GitLab installation that you want to update.
4. Select **Edit Integration**.
5. Select **Merge Request Settings** in **Integration Settings**.

   ![GitLab App MR scan setup](../../../../images/edit-mr-scan-setup.png)
6. Select **Merge Request Scans**.
7. Optionally, select **Merge Request Comments** to enable MR comments.

   Ensure that you complete the MR comments configuration in Endor Labs to receive the comments. See [GitLab MR comments](#gitlab-mr-comments) for more information.
8. Select **Merge Request Scans** to enable MR scans.
9. Select **Set up the webhook now** under **Webhook Settings**.
10. You can either configure the webhook on the GitLab UI or use the cURL command to set up the webhook.

Configure the webhook on the GitLab UI

Ensure that you have the group owner role to configure the webhook on GitLab.

1. Sign in to GitLab and select the group for which you want to configure the webhook.
2. Select **Settings** > **Webhooks** from the left sidebar.
3. Click **Add Webhook**.
4. Configure the webhook in GitLab.

   * Name: Name for the webhook.
   * Description: Description for the webhook.
   * URL: Enter `https://api.endorlabs.com/webhooks/gitlab` as the URL to access the Endor Labs webhook API.
   * Secret Token: The secret token from Endor Labs.

   You can copy the values from the Endor Labs user interface.

   ![GitLab App MR scan setup webhook](../../../../images/gitlab-app-mr-scan-setup-gitlabui-webhook.png)
5. Click **Add Custom Header** and enter the following values:

   * Key: `X-Endor-Installation-ID`
   * Value: The Custom Header Value from the Endor Labs user interface. It is the installation ID of the Endor Labs GitLab installation.
6. Select **Merge request events** under the **Trigger** section.
7. Ensure that **Enable SSL verification** is selected under the **SSL verification** section.
8. Click **Add Webhook** to save the changes.

   You can create a webhook without SSL verification, but it is not recommended. Without SSL verification, the webhook is vulnerable to man-in-the-middle attacks.

Configure the webhook using the cURL command

Ensure that you have the personal access token of the group owner with the `api` scope to configure the cURL command.

1. Select **cURL command** to configure the webhook using the cURL command.

   ![GitLab App MR scan setup curl](../../../../images/gitlab-app-mr-scan-setup-gitlabui-curl.png)
2. Replace `PRIVATE-TOKEN` with the personal access token of the group owner with the `api` scope.
3. Copy the cURL command and run it on your system to register the webhook with GitLab.

11. Click **Save** to save the changes.

## Configure webhook for GitLab App MR scans

GitLab MR scans require a webhook to be configured on GitLab. You can configure the webhook on the GitLab UI or use the cURL command to configure the webhook. For more information, refer to [GitLab webhooks](https://docs.gitlab.com/user/project/integrations/webhooks/#group-webhooks).

### Configure the webhook on the GitLab UI

Ensure that you have the group owner role to configure the webhook on GitLab.

1. Sign in to GitLab and select the group for which you want to configure the webhook.
2. Select **Settings** > **Webhooks** from the left sidebar.
3. Click **Add Webhook**.
4. Configure the webhook in GitLab.

   * Name: Name for the webhook.
   * Description: Description for the webhook.
   * URL: Enter `https://api.endorlabs.com/webhooks/gitlab` as the URL to access the Endor Labs webhook API.
   * Secret Token: The secret token from Endor Labs.

   You can copy the values from the Endor Labs user interface.

   ![GitLab App MR scan setup webhook](../../../../images/gitlab-app-mr-scan-setup-gitlabui-webhook.png)
5. Click **Add Custom Header** and enter the following values:

   * Key: `X-Endor-Installation-ID`
   * Value: The Custom Header Value from the Endor Labs user interface. It is the installation ID of the Endor Labs GitLab installation.
6. Select **Merge request events** under the **Trigger** section.
7. Ensure that **Enable SSL verification** is selected under the **SSL verification** section.
8. Click **Add Webhook** to save the changes.

   You can create a webhook without SSL verification, but it is not recommended. Without SSL verification, the webhook is vulnerable to man-in-the-middle attacks.

### Configure the webhook using the cURL command

Ensure that you have the personal access token of the group owner with the `api` scope to configure the cURL command.

1. Select **cURL command** to configure the webhook using the cURL command.

   ![GitLab App MR scan setup curl](../../../../images/gitlab-app-mr-scan-setup-gitlabui-curl.png)
2. Replace `PRIVATE-TOKEN` with the personal access token of the group owner with the `api` scope.
3. Copy the cURL command and run it on your system to register the webhook with GitLab.

## GitLab MR comments

MR comments are automated comments added to merge requests when Endor Labs detects policy violations or security issues during scans. When an MR is raised or updated, Endor Labs runs scans on the proposed changes and adds a comment if any violations are detected based on the configured action policies.

After you enable MR comments, you need to set up an action policy to allow comments to be posted on merge requests.

### Configure action policy for MR comments

The action policy that you create triggers the posting of comments on your merge request after a scan is complete. See [Action policy](/managing-policies/action-policies/) for more information. You can create multiple action policies based on your requirements, which the MR scan can trigger. If you create action policy with the `Secret` template, you get an inline comment with the line number where the secret is detected.

Ensure that you configure the following important settings in the action policy:

1. Choose an appropriate action policy template or create a custom action policy.

   You can choose an action policy template like [Vulnerabilities](/managing-policies/action-policies/templates/#containers) or create a custom action policy.
2. Under **Action**, select **Enforce Policy**, then choose:

   * **Warn** to post a comment without breaking the build.
   * **Break the Build** to fail the build and block the pull request.
3. Define the scope of the policy using tags. Only projects that match the specified tags will receive MR comments.
4. Select **Propagate this policy to all child namespaces** if you want to apply the policy to all child namespaces.

**Action policy propagation in child namespaces**

If you select **Propagate this policy to all child namespaces**, and update the policy in the child namespace, the policy in the child namespace takes precedence over the policy in the parent namespace. If you select the propagate option for the child namespace, its child namespaces will also inherit the policy. Since [namespace hierarchy follows the group and subgroup hierarchy of GitLab](/deployment/monitoring-scans/gitlab-app/#managed-namespaces-for-gitlab), you can effectively use this option to control the policy for different levels of your organization.

### MR comments template

Endor Labs provides a default template for MR comments that you can use out-of-the-box. You can also create custom templates using [Go Templates](https://pkg.go.dev/text/template).

The following section shows the default template for MR comments.

```
{{- /* Do not modify the placement of the CommentHeader.
It is being used to identify the comments generated by Endor Labs. */ -}}
{{ .CommentHeader.Value }}

{{ $policiesTriggeredNumber := len .PolicyFindingsMap }}

{{/* ALERT BANNER */}}
> [!WARNING]
> Endor Labs detected {{ $policiesTriggeredNumber }} policy violations associated with this merge request.

{{ $dataMap := .DataMap }}
{{ $findingsMap := .FindingsMap }}
{{ $packageVersionsMap := .PackageVersionsMap }}
{{ $apiURL := .ApiEndpoint.Value }}

### Please review the findings that caused the policy violations.

{{ range $policyUUID, $policyName := .PoliciesMap }}
{{ $policyFindings := index $dataMap $policyUUID }}
<details>
<summary>

{{/* POLICY HEADER */}}
### :clipboard: Policy: {{ $policyName }} ({{ getFindingsCountString $policyFindings }})</summary>

{{ range $packageVersionUUID, $packageVersionFindings := $policyFindings.PackageToDependencies }}
{{ if ne getOtherFindingsPackageMarker $packageVersionUUID }}
{{ $packageVersionObject := index $packageVersionsMap $packageVersionUUID }}
{{ if $packageVersionObject }}
<details>
<summary>

{{/* PACKAGE HEADER */}}
#### :inbox_tray: Package [{{ $packageVersionObject.Meta.Name.Value }}]({{ getPackageVersionURL $apiURL $packageVersionObject }})</summary>
{{ range $dependencyName, $dependencyFindings := $packageVersionFindings.DependencyToFindings }}
<details>
<summary>

{{/* DEPENDENCY HEADER */}}
##### :arrow_heading_down: Dependency: {{ $dependencyName }}</summary>

{{ range $findingCounter, $findingUUID := $dependencyFindings.Uuids }}
<details>
{{ $findingObj := index $findingsMap $findingUUID }}

{{/* FINDING HEADER */}}
<summary> :triangular_flag_on_post: {{ $findingObj.Meta.Description.Value }}</summary>

{{/* FINDING DETAILS */}}
[Details]({{ getFindingURL $apiURL $findingObj }})
- **Severity**: ` + "`" + `{{ enumToString $findingObj.Spec.Level }}` + "` " + `
- **Tags**: {{ range $i, $t := $findingObj.Spec.FindingTags }}` + "`" + `{{ enumToString $t }}` + "` " + `{{ end }}
- **Categories**: {{ range $i, $c := $findingObj.Spec.FindingCategories }}` + "`" + `{{ enumToString $c }}` + "` " + `{{ end }}
{{- with getFirstPartyReachableFunctions $findingObj }}
- **Reachable via**: ` + "`" + `{{ . }}` + "` " + `
{{- end }}
- **Remediation**: {{ fixBackticks $findingObj.Spec.Remediation.Value }}
</details>
{{ end }} {{/*range $findingCounter, $findingUUID...*/}}
</details>
{{ end }} {{/*range $dependencyName, $depend...*/}}
</details>
{{ end }}  {{/* if $packageVersionObject */}}
{{ else }} {{/* if ne getOtherFindingsPackageMarker... */}}
{{ $depMarker := getOtherFindingsDependencyMarker }}
{{ $otherFindings := index $packageVersionFindings.DependencyToFindings $depMarker }}
{{ $otherFindingsLen := len $otherFindings.Uuids }}
{{ if ne $otherFindingsLen 0 }}
<details>
<summary>

#### :mag: Findings</summary>
{{ range $findingCounter, $findingUUID := $otherFindings.Uuids }}
<details>
{{ $findingObj := index $findingsMap $findingUUID }}
<summary>:triangular_flag_on_post: {{ $findingObj.Meta.Description.Value }}</summary>

[Link To Finding]({{ getFindingURL $apiURL $findingObj }})
- **Severity**: ` + "`" + `{{ enumToString $findingObj.Spec.Level }}` + "` " + `
- **Tags**: {{ range $i, $t := $findingObj.Spec.FindingTags }}` + "`" + `{{ enumToString $t }}` + "` " + `{{ end }}
- **Categories**: {{ range $i, $c := $findingObj.Spec.FindingCategories }}` + "`" + `{{ enumToString $c }}` + "` " + `{{ end }}
- **Summary**: {{ $findingObj.Spec.Summary.Value }}
- **Remediation**: {{ fixBackticks $findingObj.Spec.Remediation.Value }}
{{- if hasFindingCategory $findingObj "SAST" }}
- **Location**: {{ getCustomLocation $findingObj }}
{{- if isNotEmptyString (getCustomCodeSnippet $findingObj) }}
- **Code Snippet**:
` + "```" + `
{{ getCustomCodeSnippet $findingObj }}
` + "```" + `
{{- end }}
{{- end }}
</details>
{{ end }} {{/*range $findingCounter, $findingUUID...*/}}
</details>
{{ end }} {{/*{{ if ne $otherFindingsLen 0*/}}
{{ end }} {{/* if ne getOtherFindingsPackageMarker... */}}
{{ end }} {{/* range $packageVersionUUID, $packageVersionFindings := $policyFindings */}}
</details>
{{ end}}  {{/* {{ range $policyUUID, $policyObj := .PoliciesMap */}}

{{ .CommentFooter.Value }}
_Scanned @ {{ now }} UTC_
```

You can create your custom template by editing the default template and saving the changes.

The following specification shows the additional functions that you can use in your custom template. You can access these functions by using their corresponding keys.

```
// FuncMap contains additional template functions used in GitLab comment templates.
var FuncMap = template.FuncMap{
	"now":                              utils.ToTime,
	"enumToString":                     utils.EnumToString,
	"getFindingURL":                    utils.GetFindingURL,
	"getPackageVersionURL":             utils.GetPackageVersionURL,
	"getPullRequestURL":                getEndorLabsPullRequestRunURL,
	"getFindingsCountString":           utils.GetFindingsCountString,
	"hasOtherFindings":                 hasOtherFindings,
	"getOtherFindingsPackageMarker":    getOtherFindingsPackageMarker,
	"getOtherFindingsDependencyMarker": getOtherFindingsDependencyMarker,
	"fixBackticks":                     utils.FixUnclosedBackticks,
	"getFirstPartyReachableFunctions":  utils.GetFirstPartyReachableFunctions,
	"hasFindingCategory":               utils.HasFindingCategory,
	// isNotEmptyString checks if a string is not empty
	"isNotEmptyString": utils.IsNotEmptyString,
	// getCustomLocation extracts the location from Custom field
	"getCustomLocation": func(finding *endorpb.Finding) string {
		return utils.GetCustomFieldValue(finding, "location")
	},
	// getCustomCodeSnippet extracts the code snippet from Custom field
	"getCustomCodeSnippet": func(finding *endorpb.Finding) string {
		return utils.GetCustomFieldValue(finding, "code_snippet")
	},
	// add returns the sum of two integers
	"add": func(n int, incr int) int {
		return n + incr
	},
}
```

To edit the default template:

1. Select **Manage** > **Integrations** from the left sidebar.
2. Click **Edit Template** next to **GitLab** under **Template for PR Comments**.

   ![](/images/gitlab-app-mr-comment-template.png)
3. Update the template with the required changes.
4. Select **Propagate this template to all child namespaces** if you want to apply the template to all child namespaces.

**Template propagation in child namespaces**

If you select **Propagate this template to all child namespaces**, and update the template in the child namespace, the template in the child namespace takes precedence over the template in the parent namespace. If you select the propagate option for the child namespace, its child namespaces will also inherit the template. Since [namespace hierarchy follows the group and subgroup hierarchy of GitLab](/deployment/monitoring-scans/gitlab-app/#managed-namespaces-for-gitlab), you can effectively use this option to control the template for different levels of your organization.

5. Click **Save Template** to save the changes.

**Restore the default template**

You can restore the default template by clicking **Restore to Default** in the template editor to go back to the initial template.

### MR scan comments in GitLab

After you enable MR comments, Endor Labs posts a comment on the merge request if any issues are detected during the MR scan based on the action policies.

The following example shows a comment on the merge request as a result of the action policy for identifying leaked secrets.

![GitLab MR comment secret](../../../../images/gitlab-mr-comment-secret.png)

You can expand and view the details of the finding.

![GitLab MR comment secret details](../../../../images/gitlab-mr-comment-secret-details.png)

Click **Link to Finding** to view the details of the finding in Endor Labs.

For secrets, Endor Labs also generates a comment with the line number where the secret is detected.

![GitLab MR comment secret line](../../../../images/gitlab-mr-comment-secret-line.png)

## View MR scan findings

When you create a new merge request, the Endor Labs GitLab App scans the merge request. Endor Labs generates findings based on the finding policy.

1. Sign in to Endor Labs and select **Projects** from the left sidebar.
2. Select the project for which you want to view the MR scan findings.
3. Select **PR runs** to view the MR scan findings.

   ![View MR scan findings](../../../../images/mr-scan-findings.png)
4. Select the MR for which you want to view the findings.

   ![View MR scan pane](../../../../images/mr-scan-pane.png)
5. Click **View Details** to view the findings on the MR.

   ![View MR scan findings in detail](../../../../images/mr-scan-findings-detail.png)

See [View Findings](../../../../managing-projects/view-findings/) for more information on Findings in Endor Labs.

## Update the webhook secret

You might want to update the webhook secret for rotation or because you have lost the secret.

### Update the webhook secret on the Endor Labs GitLab App

1. Select **Integrations** from the left sidebar.
2. Click **Manage** in **GitLab** under **Source Control Managers**.
3. Click the three dots menu next to the GitLab installation that you want to update.
4. Select **Edit Integration**.
5. Select **Merge Request Settings**.
6. Enter the new **Secret Token** under **Webhook Settings**, and click **Save** to save the changes.

   ![GitLab App MR scan update webhook secret](../../../../images/gitlab-app-mr-scan-update-webhook-secret.png)

   The secret token can be any random string.

### Update the webhook secret in GitLab

To update the webhook secret in GitLab UI, you need to log in with the group owner role.

1. Sign in to GitLab and select the group for which you want to update the webhook secret.
2. Select **Settings** > **Webhooks** from the left sidebar.
3. Click **Edit** next to the webhook that you want to update.
4. Enter the new **Secret token**, and click **Save changes** to save the changes.

   Ensure that you use the same secret token that you used in Endor Labs.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

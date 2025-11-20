---
url: https://docs.endorlabs.com/managing-policies/action-policies/
title: Action policies | Endor Labs Docs
downloaded: 2025-11-20 11:49:45
---

Action policies | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/managing-policies/action-policies/_print.html)



# Action policies

Learn about action policies and how to use them.

Action policies define the workflows that are triggered when the application encounters a given set of criteria (a.k.a. findings).

For example, action policies can be used to:

* Configure the behavior of scan in a CI/CD based environment.
* Set up custom ticketing workflows.
* Set up custom messaging workflows.

## Manage action policies

You can view, enable, clone, disable, edit, or delete your Endor Labs action policies.

1. Sign in to Endor Labs and select **Policies & Rules** from the left sidebar.
2. Select **Action Policies**.
3. Use the search bar to search for a policy.
4. Enable or disable a policy using the toggle.
5. Select **Hide Disabled** to hide policies that are not enabled.
6. Select **Hide Warnings** to hide policies that are not blocking or notifications.
7. To delete a policy, click the vertical three dots and select **Delete Policy**.
8. To edit a policy, click on the vertical three dots and select **Edit Policy**.

## View policy details

1. Sign in to Endor Labs and select **Policies & Rules** from the left sidebar.
2. Select **Action Policies** to view the list of action policies.
3. Select a policy you want to review and click **View Details**.

   You can see the policy’s description, scope, and metadata. You can review the severity, finding categories, explanatory details, remediation steps and the Rego rules that implement the policy logic.

   ![View action policy details](../../images/view-action-policy-details.png)

## Create an action policy from template

You can create an action policy in Endor Labs to perform a given action when a given set of conditions are met.

1. Sign in to Endor Labs and select **Policies** from the left sidebar.
2. Select **Action Policies**.
3. Click **Create Action Policy** to create a new action policy.
4. First, you must **Define a Policy**.

   Choose a policy template and define the criteria for the action. See [Action policy templates](./templates) for more information.
5. Next, **Choose an Action** to take when the policy criteria are met.

   * Choose **Enforce Policy** to define the behavior of endorctl scans.
     + A **Warn** enforcement action will warn the user when the policy criteria are met by letting them know which findings violate the policy. **Warn** enforcement actions will only notify users of policy violations and will still return a 0 exit code in CI/CD environments, which won’t fail a job. However, it is possible to configure the scan to return a non-zero (129) exit code for policy warnings by setting the `--exit-on-policy-warning` flag.
     + A **Break the Build** enforcement action will return a non-zero (128) exit code, which will fail the job. This action will inform the user which findings violate the policy as part of the scan.
   * Choose **Send Notification** to create a ticket or send a custom message to an integrated notification system.
     + A **Notification Target** must be set to send a notification. A notification target may be defined as a notification integration. For more information, see [Endor Labs integrations](../../integrations/).
     + Choose an **Aggregation Type** for notifications. Choose **Project** to trigger a single notification for all findings, choose **Dependency** to trigger multiple notifications for every dependency, or choose **Dependency per package version** to trigger multiple notifications for unique combinations of dependency and package. For more information, see [Aggregation types for notifications](#aggregation-types-for-notifications).

       #### Note

       Notifications are only processed for monitored branches, not for pull requests.
6. You can **Assign Scope** to the action policy by specifying what projects the policy has to scan.

   * In **Inclusions**, enter the projects and the tags of the projects that you want to scan.
   * In **Exclusions**, enter the projects and the tags of the projects that you do not want to scan. Exclusions take precedence over the inclusions, in case of a conflict.
   * Click the link to view the projects included in the action policy scan.
   * Click **Add project tag to these projects** and enter a tag for the selected projects. Click **Save Tags** to apply it or **Reset Tags** to discard changes.
   * You can set custom tags for your projects from **Projects** > **Settings** > **Custom Tags**. See [Tagging projects](../tagging-projects/) for more information about creating project tags.
7. **Name Your Action Policy**.

   * Enter a human readable **Name** for your action policy.
   * Enter a **Description** for your action policy that describes what it does.
   * Enter any **Policy Tags** that you want to associate with your policy. Tags can have a maximum of 63 characters and can contain letters, numbers, and characters `=`, `@`, `_`, and `-`.
8. **Advanced**: When you define a policy you do so for the current namespace and all child namespaces. If you do not want the policy to be applied to any child namespaces, click **Advanced** and deselect **Propagate this policy to all child namespaces**.
9. Click **Create Action Policy**. The policy will be enabled by default.

## Create an action policy from scratch

Write an action policy from scratch using the [OPA Rego policy language](https://www.openpolicyagent.org/docs/latest/policy-language/).

1. Sign in to Endor Labs and select **Policies** from the left sidebar.
2. Select **Action Policies**.
3. Click **Create Action Policy**
4. Choose **From Scratch** to author an action policy
5. Enter the Rego rule for the policy in **Rego Definition**.

   For instance, the following Rego rule identifies all repository version findings that are not present in the baseline. Action policies should only operate on Findings. For more information about findings, see the [Finding resource kind documentation](../../rest-api/using-the-rest-api/data-model/resource-kinds/#finding)

   ```
   package examples

   match_baseline(finding) {
     some i
     data.baseline.Finding[i].meta.description == finding.meta.description
   }

   match_repo_version_finding[result] {
     some i
     data.resources.Finding[i].meta.parent_kind == "RepositoryVersion"
     not match_baseline(data.resources.Finding[i])

     result = {
       "Endor": {
         "Finding": data.resources.Finding[i].uuid
       }
     }
   }
   ```
6. Enter the OPA **Query Statement** for the rule in the following format: `data.<package-name>.<function-name>`.

   For the example above the query statement is `data.examples.match_repo_version_finding`
7. Select the **Resource Kinds** required to evaluate the policy.

   For the example above the required resource kind is `Finding`. The requested resource kind records for the current scan are made available to the Rego code under `data.resources.<ResourceKind>`. The corresponding baseline records are available under `data.baseline.<ResourceKind>`. Note: Action policies should only operate on Findings
8. Continue with steps 5-9 above under [Create an action policy from template](#create-an-action-policy-from-template)

#### Note

Rescan the project to apply the newly created action policy and update the findings.

### Expected output format

All action policies must list the matching Finding UUID under “Endor” in the following format.

```
foo[result] {
  <match conditions>

  result = {
    "Endor": {
      Finding: <finding-uuid>
    }
  }
}
```

### Validate policy

The application verifies the Rego syntax and query statement before creating the policy. However, please note that the logic cannot be fully validated without input data.

See the [endorctl validate policy](../../endorctl/commands/validate) command for details on how to validate a custom policy and inspect the matches returned for a given project.

### Baseline data

For action policies that are used to comment on, or block, PR scans you often only want to trigger the policy for findings that are not present in the baseline. The baseline data for the requested resource kinds is available under `data.baseline.<ResourceKind>`. Here are some examples of how to implement a function called `match_baseline` that returns true if a given finding also exists in the baseline. As in the [example above](#create-an-action-policy-from-scratch), you can then call `not match_baseline(data.resources.Finding[i])` to filter out findings that are not unique to the PR scan. Any additional resource kinds, for example `DependencyMetadata`, must be added to the list of requested [**Resource Kinds**](#create-an-action-policy-from-scratch).

#### Note

Baseline data is only loaded for action policies with one of the **Enforce Policy** actions (**Warn** or **Break the Build**). It is not loaded for any other policy types.

```
match_baseline(finding) {
    finding.meta.parent_kind == "PackageVersion"
    some i
    data.baseline.Finding[i].meta.description == finding.meta.description
    data.baseline.Finding[i].spec.target_dependency_package_name == finding.spec.target_dependency_package_name
}

match_baseline(finding) {
    finding.meta.parent_kind == "PackageVersion"
    some i, j
    data.baseline.DependencyMetadata[i].meta.name == finding.spec.target_dependency_package_name
    data.resources.DependencyMetadata[j].meta.name == finding.spec.target_dependency_package_name
    data.baseline.DependencyMetadata[i].spec.importer_data.package_name == data.resources.DependencyMetadata[j].spec.importer_data.package_name
    data.baseline.DependencyMetadata[i].spec.dependency_data.reachable == data.resources.DependencyMetadata[j].spec.dependency_data.reachable
}

match_baseline(finding) {
    finding.meta.parent_kind == "RepositoryVersion"
    some i
    data.baseline.Finding[i].meta.description == finding.meta.description
}

match_baseline(finding) {
    finding.meta.parent_kind == "Repository"
    some i
    data.baseline.Finding[i].meta.description == finding.meta.description
}

match_baseline(finding) {
    finding.spec.finding_categories[_] == "FINDING_CATEGORY_SECRETS"
    some i
    data.baseline.Finding[i].spec.extra_key == finding.spec.extra_key
    count(data.baseline.Finding[i].spec.finding_metadata.source_policy_info.results) == count(finding.spec.finding_metadata.source_policy_info.results)
}

match_baseline(finding) {
    finding.spec.finding_categories[_] == "FINDING_CATEGORY_SAST"
    some i
    data.baseline.Finding[i].spec.extra_key == finding.spec.extra_key
    count(data.baseline.Finding[i].spec.finding_metadata.source_policy_info.results) == count(finding.spec.finding_metadata.source_policy_info.results)
}
```

## Aggregation types for notifications

Aggregation types for notifications streamline the organization and management of findings for efficient workflow. By default, all project findings are included in a single notification. With the option to select aggregation types, notifications can be tailored to specific criteria based on dependencies. This customization simplifies developer actions and enhances productivity.

Endor Labs enables you to choose the following notification aggregation types, each offering distinct benefits.

* **Project**: (Default) Select **Project** to create a single notification for all project findings.
* **Dependency**: Select **Dependency** to create separate notifications for each dependency in a project.
* **Dependency per package version**: Select **Dependency per package version** to create separate notifications for each package in a project. Sub-tasks are created for each unique combination of dependency and package.

### Example

For Jira integration notifications, a parent ticket is created with the selected issue type, either `Task` or `Bug`. The parent ticket includes the project name. Each identified dependency is grouped under a dedicated sub-ticket. The sub-ticket includes both the project name and dependency name. Findings without any dependency are grouped in a separate sub-ticket. During future scans, the existing sub-ticket status is updated or resolved. If a new dependency is found, a new sub-ticket is created.

---

##### [Action policy templates](/managing-policies/action-policies/templates/)

Learn about the predefined action policy templates and how to customize them.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

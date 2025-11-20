---
url: https://docs.endorlabs.com/managing-policies/exception-policies/
title: Exception policies | Endor Labs Docs
downloaded: 2025-11-20 11:49:14
---

Exception policies | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/managing-policies/exception-policies/_print.html)



# Exception policies

Learn about exception policies and how to use them.

Exception policies define the conditions for applying an exception to a finding. When an exception is applied to a finding, it is tracked as an exception and action policies do not apply to it. Findings with exceptions are filtered out from Endor Labs reports by default.

For example, exception policies can be used to:

* Exclude a specific finding for a specific package from build breaking policies.
* Exclude specific vulnerabilities that are accepted across your organization.
* Mark an identified issue as a false positive.

## Manage exception policies

You can view, enable, clone, disable, edit, or delete your Endor Labs exception policies.

1. Sign in to Endor Labs, and select **Policies & Rules** from the left sidebar.
2. Select **Exception Policies**.
3. Use the search bar to search for a policy or click **Create Exception Policy**.
4. Enable or disable a policy using the toggle.
5. To delete a policy, click the vertical three dots and select **Delete Policy**.
6. To edit a policy, click on the vertical three dots and select **Edit Policy**.

## View policy details

1. Sign in to Endor Labs and select **Policies & Rules** from the left sidebar.
2. Select **Exception Policies** to view the list of exception policies.
3. Select a policy you want to review and click **View Details**.

   You can see the policy’s description, scope, and metadata. You can review the severity, finding categories, explanatory details, remediation steps and the Rego rules that implement the policy logic.

   ![View exception policy details](../../images/view-exception-policy-details.png)

## Create an exception policy from a template

You can create an exception policy in Endor Labs to apply an exception to a finding when a given set of conditions are met.

1. Sign in to Endor Labs, and select **Policies & Rules** from the left sidebar.
2. Select **Exception Policies**.
3. Click **Create Exception Policy**.
4. In **Define Exception Criteria**, choose a policy template and define the criteria for the exception.

   See [exception policy templates](./templates) to choose a template and define the criteria for the exception.
5. Next, you must **Choose a Reason** for your exception and set an expiration time for the exception.

   * Select from the following reasons why you are applying this exception:
     + **In Triage**: The finding is still being triaged for more information.
     + **False Positive**: The finding is a false positive.
     + **Risk Accepted**: The risk associated with the finding is accepted.
     + **Resolved**: The issue has been resolved.
     + **Other**: Another reason applies for this exception.
   * Select when the exception should expire. Options include `30`, `60`, `90` days, or `Never`.
6. You can **Assign Scope** to the exception policy by specifying what projects the policy has to scan.

   * In **Inclusions**, enter the projects and the tags of the projects that you want to scan.
   * In **Exclusions**, enter the projects and the tags of the projects that you do not want to scan. Exclusions take precedence over the inclusions, in case of a conflict.
   * Click the link to view the projects included in the exception policy scan.
   * Click **Add project tag to these projects** and enter a tag for the selected projects. Click **Save Tags** to apply it or **Reset Tags** to discard changes.
   * You can set custom tags for your projects from **Projects** > **Settings** > **Custom Tags**. See [Tagging projects](../tagging-projects/) for more information about creating project tags.
7. Finally, you must **Name Your Exception Policy**.

   * Enter a human-readable **Name** for your exception policy.
   * Enter a **Description** for your exception policy that explains its function.
   * Enter any **Policy Tags** that you want to associate with your policy. Tags can have a maximum of 63 characters and can contain letters, numbers, and characters = @ \_ -.
8. **Advanced**: When you define a policy, it applies to the current namespace and all its child namespaces. To prevent the policy from being applied to any child namespace, click **Advanced** and deselect **Propagate this policy to all child namespaces**.
9. Click **Create Exception Policy**. The policy is enabled by default.

#### Tip

When creating exceptions for a specific package, make sure to not include the version of the package in the package name template parameter. Adding the version to the name can result in the exception not applying to a newly released version of the package.

## Create an exception policy from scratch

Write an exception policy from scratch using the [OPA Rego policy language](https://www.openpolicyagent.org/docs/latest/policy-language/).

You can create an exception policy in Endor Labs to apply an exception to a finding when a given set of conditions are met.

1. Sign in to Endor Labs, and select **Policies** from the left sidebar.
2. Click on the **Exception Policies** tab.
3. Click **Create Exception Policy** to create a new exception policy
4. First, choose **From Scratch** to author an exception policy under **Define Exception Criteria**.
5. Next, you must **Choose a Reason** for your exception and set an expiration time for the exception.

   * Select from the following reasons why you are applying this exception:
     + **In Triage**: The finding is still being triaged for more information.
     + **False Positive**: The finding is a false positive.
     + **Risk Accepted**: The risk associated with the finding is accepted.
     + **Resolved**: The issue has been resolved.
     + **Other**: Another reason applies for this exception.
   * Select when the exception should expire. Options include 30, 60, 90 days, or Never.
6. Enter the Rego rule for the policy in **Rego Definition**. For example, the following Rego rule recognizes a set of 3 vulnerabilities acknowledged by an organization, with an organization-wide exception. For more information about findings, see the [Finding resource kind documentation](../../rest-api/using-the-rest-api/data-model/resource-kinds/#finding).

   ```
   package exceptions

   match_vuln_id(finding, ids) {
     finding.spec.finding_metadata.vulnerability.meta.name = ids[_]
   }

   match_vuln_id(finding, ids) {
     finding.spec.finding_metadata.vulnerability.spec.aliases[_] = ids[_]
   }

   match_finding[result] {
     some i
     ids := ["CVE-2020-10683", "CVE-2019-0231", "CVE-2017-0144"]
     match_vuln_id(data.resources.Finding[i], ids)
     result = {
       "Endor" : {
         "Finding" : data.resources.Finding[i].uuid
       }
     }
   }
   ```
7. Enter the OPA **Query Statement** for the rule in the following format: `data.<package-name>.<function-name>`. For the example above the query statement is `data.exceptions.match_finding`.
8. Select the **Resource Kinds** required to evaluate the policy. For the example above, the required resource kind is `Finding`. The requested resource kind records for the current scan are made available to the Rego code under `data.resources.<ResourceKind>`.
9. **Assign Scope** for which this exception policy should apply. Scopes are defined by the tags assigned to a project.

   * In **Inclusions**, enter the tags of the projects that you want to apply an exception to.
   * In **Exclusions**, enter the tags of the projects that you do not want to apply an exception to. Exclusions take precedence over the inclusions, in case of a conflict.
   * Click the link to view the projects included in the exception policy.
   * See [Tagging projects](../tagging-projects/) for more information about creating project tags.
10. Finally, you must **Name Your Exception Policy**.

    * Enter a human-readable **Name** for your exception policy.
    * Enter a **Description** for your exception policy that explains its function.
    * Enter any **Policy Tags** that you want to associate with your policy. Tags can have a maximum of 63 characters and can contain letters, numbers, and characters = @ \_ -.
11. **Advanced**: When you define a policy, it applies to the current namespace and all its child namespaces. To prevent the policy from being applied to any child namespace, click **Advanced** and deselect **Propagate this policy to all child namespaces**.
12. Click **Create Exception Policy**. The policy is enabled by default.

#### Note

Rescan the project to apply the newly created exception policy and update the findings.

### Expected output format

All exception policies must list the matching Finding UUID under “Endor” in the following format.

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

The application verifies the Rego syntax and query statement before generating the policy. However, it is important to note that the logic cannot be completely validated without input data.

See the [endorctl validate policy](../../endorctl/commands/validate) command for instructions on validating a custom policy and inspecting the matches returned for a specific project.

---

##### [Exception policy templates](/managing-policies/exception-policies/templates/)

Learn about the predefined exception policy templates and how to customize them.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

---
url: https://docs.endorlabs.com/managing-policies/remediation-policies/
title: Remediation policies | Endor Labs Docs
downloaded: 2025-11-20 11:50:34
---

Remediation policies | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/managing-policies/remediation-policies/_print.html)



# Remediation policies

Learn about remediation policies and how to use them.

Remediation policies define the conditions for applying remediation to a finding when an upgrade is available that fixes the finding.

## Manage remediation policies

You can view, enable, clone, disable, edit, or delete your Endor Labs remediation policies.

1. Sign in to Endor Labs and select **Policies & Rules** from the left sidebar.
2. Select **Remediation Policies**.
3. Use the search bar to search for a policy or click **Create Remediation Policy**.
4. Enable or disable a policy using the toggle.
5. To delete a policy, click the vertical three dots and select **Delete Policy**.
6. To edit a policy, click on the vertical three dots and select **Edit Policy**.
7. To clone a policy, click on the vertical three dots and select **Clone Policy**.

## View policy details

1. Sign in to Endor Labs and select **Policies & Rules** from the left sidebar.
2. Select **Remediation Policies** to view the list of remediation policies.
3. Select a policy you want to review and click **View Details**.

   You can see the policy’s description, scope, and metadata. You can review the severity, finding categories, explanatory details, remediation steps and the Rego rules that implement the policy logic.

   ![View remediation policy details](../../images/view-remediation-policy-details.png)

## Create a remediation policy from a template

You can create a remediation policy in Endor Labs to address a finding when specific conditions are met.

1. Sign in to Endor Labs, and select **Policies & Rules** from the left sidebar.
2. Click on the **Remediation Policies** tab.
3. Click **Create Remediation Policy** to create a new remediation policy.
4. Select a policy template.

   Currently, you can choose **Recommended Version Upgrades for Vulnerabilities**.
5. Next, choose the template parameters.

   * **Upgrade Risk**: The acceptable level of risk that a breaking change might occur with the upgrade.
   * **Severity:** Match upgrades that would fix findings with a particular severity.
   * **Exclude Test:** Select **Yes** to exclude version upgrade recommendations for fixing findings in test dependencies.
   * **Dependency Reachability:**: Match upgrades that address findings with the following level of dependency reachability.
     + Reachable dependency
     + Unreachable dependency
     + Potentially reachable dependency
   * **Function Reachability:** Match upgrades that address findings with the following level of function reachability.
     + Reachable function
     + Unreachable function
     + Potentially reachable function
   * **Minimum Number of Findings:** Only match upgrades that resolve a minimum number of findings equal to or greater than this value.
6. Select a notification target to be associated with the remediation policy.

   See [Integrations](../../integrations/) for more information on creation notification integrations.
7. You can **Assign Scope** to the remediation policy by specifying what projects the policy has to scan.

   * In **Inclusions**, enter the projects and the tags of the projects that you want to scan.
   * In **Exclusions**, enter the projects and the tags of the projects that you do not want to scan. Exclusions take precedence over the inclusions, in case of a conflict.
   * Click the link to view the projects included in the remediation policy scan.
   * Click **Add project tag to these projects** and enter a tag for the selected projects. Click **Save Tags** to apply it or **Reset Tags** to discard changes.
   * You can set custom tags for your projects from **Projects** > **Settings** > **Custom Tags**. See [Tagging projects](../tagging-projects/) for more information about creating project tags.
8. Finally, you must **Name Your Remediation Policy**.

   * Enter a human-readable **Name** for your remediation policy.
   * Enter a **Description** for your remediation policy that explains its function.
   * Enter any **Policy Tags** that you want to associate with your policy. Tags can have a maximum of 63 characters and can contain letters, numbers, and characters = @ \_ -.
9. **Advanced**: When you define a policy, it applies to the current namespace and all its child namespaces.

   To prevent the policy from being applied to any child namespace, click **Advanced** and deselect **Propagate this policy to all child namespaces**.
10. Click **Create Remediation Policy**.

    The policy is enabled by default.

#### Note

Rescan the project to apply the newly created remediation policy and update the findings.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

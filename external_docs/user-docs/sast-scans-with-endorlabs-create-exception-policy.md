---
url: https://docs.endorlabs.com/sast-scans-with-endorlabs/create-exception-policy/
title: Create Exception Policy for SAST Findings | Endor Labs Docs
downloaded: 2026-01-29 22:21:58
---

Create Exception Policy for SAST Findings | Endor Labs Docs



* Type to search...

[Print entire section](/sast-scans-with-endorlabs/create-exception-policy/_print.html)



# Create Exception Policy for SAST Findings

Exception policies define the conditions for applying an exception to a finding. When an exception is applied to a finding, it is tracked as an exception and action policies do not apply to it. Findings with exceptions are filtered out from Endor Labs reports by default.

See [Exception Policies](../../managing-policies/exception-policies/) for more information.

Instead of creating an exception policy, you can also use the following methods to avoid findings:

* Disable the rule under SAST Rules
* Use the `include-path` and `exclude-path` to scan parts of the project

You can create an exception policy so that you can mark a SAST finding as an exception.

For example, you want to mark findings with the description, `Detected Potential Open Redirect Vulnerability in Angular Application`, as exceptions.

1. From the left sidebar, select **Policies**.
2. Select **EXCEPTION POLICIES**.
3. Click **Create Exception Policy** to create a new exception policy.
4. Select **Standard Exception Find Attributes** as the **POLICY TEMPLATE**.
5. Enter `Detected Potential Open Redirect Vulnerability in Angular Application` in **Finding Name Contains**.
6. Select from the following reasons why you are applying this exception:

   * **In Triage**: The finding is still being triaged for more information.
   * **False Positive**: The finding is a false positive.
   * **Risk Accepted**: The risk associated with the finding is accepted.
   * **Other**: Another reason applies for this exception.
7. Select when the exception should expire.

   Options include 30, 60, 90 days, and Never.
8. **Assign Scope** for which this exception policy should apply. Scopes are defined by the tags assigned to a project.

   * In **Inclusions**, enter the tags of the projects that you want to apply an exception to.
   * In **Exclusions**, enter the tags of the projects that you do not want to apply an exception to. Exclusions take precedence over the inclusions, in case of a conflict.
   * Click the link to view the projects included in the finding policy.

   See [Tagging projects](https://docs.endorlabs.com/managing-policies/tagging-projects/) for more information about creating project tags.
9. Enter a human-readable **Name** for your exception policy.
10. Enter a **Description** for your exception policy that explains its function.
11. Enter any **Policy Tags** that you want to associate with your policy. Tags can have a maximum of 63 characters and can contain letters, numbers, and characters = @ \_ -
12. Click **Create Exception Policy**.

## Create exceptions from Findings page

You can also create exceptions from the Findings page.

1. Select **Projects** from the left sidebar.
2. Search for and select a project, and select **Findings**.
3. Search for findings using advanced or basic filters.
4. Select findings and click the vertical three dots.
5. Select **Add Exception**.

The **Create Exception Policy** page appears where you can add a new exception policy. The template parameters are automatically updated based on the vulnerability. See [Create exception policy](../../managing-policies/exception-policies/) for details on how to create and apply exceptions.

You can use this feature to specifically apply exception to findings with a specific hash value. For example, `Detected Potential time of check time of use vulnerability (open/fopen): ID #e81f27`. This exception policy after creation only applies to the SAST findings with this hash ID and not any others.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

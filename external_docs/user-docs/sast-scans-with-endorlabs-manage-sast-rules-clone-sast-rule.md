---
url: https://docs.endorlabs.com/sast-scans-with-endorlabs/manage-sast-rules/clone-sast-rule/
title: Clone a SAST rule | Endor Labs Docs
downloaded: 2025-10-23 23:24:44
---

Clone a SAST rule | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/sast-scans-with-endorlabs/manage-sast-rules/clone-sast-rule/_print.html)



# Clone a SAST rule

You can clone an existing SAST rule and use that as a base to build your own rule.

Cloning a rule provides the following benefits:

* You can make changes to a rule and review the results instead of directly editing an existing rule.
* You can create a clone of a rule that you do not have permission to edit and make your changes.

To clone a SAST rule:

1. From the left sidebar, navigate to **Policies and Rules** and select **SAST RULES**.
2. Click on the three dots menu next to a rule and select **Clone**.

   A copy of the rule appears in the list of rules with the rule name in the format, `<original rule name\>-\<number of the clone\>`. For example, if you clone the rule `Arbitrary Code Execution - Unsanitized inputs` for the first time, a clone rule is created with the name, `Arbitrary Code Execution - Unsanitized inputs-1`.

   ![Clone SAST rule](../../../images/SAST_clonerule.png)
3. Click edit to the cloned rule to edit the cloned rule according to your requirements.

   See [Edit a SAST Rule](../edit-a-sast-rule/) for more information.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

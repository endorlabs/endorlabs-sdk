---
url: https://docs.endorlabs.com/sast-scans-with-endorlabs/manage-sast-rules/
title: SAST Rules | Endor Labs Docs
downloaded: 2026-01-26 10:06:12
---

SAST Rules | Endor Labs Docs



* Type to search...

[Print entire section](/sast-scans-with-endorlabs/manage-sast-rules/_print.html)



# SAST Rules

Endor Labs uses Semgrep-compatible rules for SAST scans. Endor Labs includes hundreds of rules for various languages, including rules created by Endor Labs and vetted third-party rules. To this end, Endor Labs reviews existing open source rules and complements them with Endor Labs rules to cover additional technologies or vulnerability types.

You can edit existing rules in your tenant to make modifications specific to your environment. You can also create new custom rules with the rule designer based on your requirements. You can also use the rule designer to add any Semgrep rule as a custom rule.

From the left sidebar, navigate to **Policies and Rules** and select **SAST RULES** to view all SAST rules in the system.

![SAST rules](../../images/SAST_policies.png)

You can use the toggle against a rule to enable or disable the rule during the scan.

You can search for rules based on various parameters like rule name, languages, CWE, and tags.

### Rule Permissions

You can create SAST rules in your tenants, and can edit, delete, or propagate them to child namespaces. But you cannot edit rules that are marked as Endor Labs or 3rd Party. You can choose to disable the rule to not apply them during scanning or clone them to modify the rules.

The following sections provide more information on the actions you can do with SAST rules.

* [Create a SAST rule](../manage-sast-rules/create-sast-rule/)
* [Edit a SAST rule](../manage-sast-rules/edit-a-sast-rule/)
* [Clone a SAST rule](../manage-sast-rules/clone-sast-rule/)
* [Import a SAST rule](../manage-sast-rules/import-sast-rule/)
* [Add metadata to a SAST rule](../manage-sast-rules/add-metadata-sast-rule/)

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

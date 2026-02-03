---
url: https://docs.endorlabs.com/rest-api/using-the-rest-api/best-practices/
title: Best practices | Endor Labs Docs
downloaded: 2026-02-03 00:50:15
---

Best practices | Endor Labs Docs



* Type to search...

[Print entire section](/rest-api/using-the-rest-api/best-practices/_print.html)



# Best practices

Follow these best practices when using the Endor Labs REST API.

## Using endorctl

* Enable [tab-completion](../../../endorctl/commands/completion/).
* Use [interactive mode](../../../endorctl/commands/api/#endorctl-api-update-interactive-mode) for creates and updates.

## Optimize queries

* Use the [count](../getting-started/#list-parameters) flag if you only need the total number of objects matching the query.
* Use [grouping](../grouping/) if you only need the number of objects per unique value of a given field, or a set of fields.
* Use [field-masks](../masks/) to return only the fields you need.
* [Filter](../filters/) on [common fields](../data-model/common-fields/) such as `uuid` or `meta.name` before resource kind specific fields.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

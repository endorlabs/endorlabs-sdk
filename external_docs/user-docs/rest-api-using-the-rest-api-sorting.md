---
url: https://docs.endorlabs.com/rest-api/using-the-rest-api/sorting/
title: Sorting | Endor Labs Docs
downloaded: 2025-10-27 12:59:59
---

Sorting | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/rest-api/using-the-rest-api/sorting/_print.html)



# Sorting

Learn how to sort results from the Endor Labs REST API.

Sort allows you to sort objects in ascending (default) or descending order.
Similar to [filter keys](../filters/#keys), a sort-path key is used to specify the field to sort the objects by, using a dot-delimited path.

The following example shows how to sort findings based on create time, in descending order:

* endorctl
* curl
* HTTP

```
endorctl api list --resource Finding \
  --sort-path "meta.create_time" \
  --sort-order descending
```

```
curl --get \
  --header "Authorization: Bearer $ENDOR_TOKEN" \
  --url "https://api.endorlabs.com/v1/namespaces/$ENDOR_NAMESPACE/findings?list_parameters.sort.path=meta.create_time&list_parameters.sort.order=SORT_ENTRY_ORDER_DESC"
```

```
@baseUrl = https://api.endorlabs.com
@token = <insert-access-token>
@namespace = <insert-namespace>

###
GET {{baseUrl}}/v1/namespaces/{{namespace}}/findings?list_parameters.sort.path=meta.create_time7list_parameters.sort.order=SORT_ENTRY_ORDER_DESC HTTP/1.1
Authorization: Bearer {{token}}
```

### Sort order

The following sort orders are supported:

* endorctl
* curl / HTTP

| Option | Description |
| --- | --- |
| `sort-path` | Specify the field to sort the objects by. |
| `sort-order` | Specify the sort order. |

| Value | Description |
| --- | --- |
| `SORT_ENTRY_ORDER_ASC` | Ascending order (default) |
| `SORT_ENTRY_ORDER_DESC` | Descending order |

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

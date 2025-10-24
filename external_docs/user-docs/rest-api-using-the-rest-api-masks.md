---
url: https://docs.endorlabs.com/rest-api/using-the-rest-api/masks/
title: Masks | Endor Labs Docs
downloaded: 2025-10-23 23:27:00
---

Masks | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/rest-api/using-the-rest-api/masks/_print.html)



# Masks

Learn how to use field masks with the Endor Labs REST API.

Field masks allow you to specify a subset of fields to be returned for each object by a request.
Similar to [filter keys](../filters/#keys), a field-mask key is used to specify the field to return, using a dot-delimited path.

The following example shows how to get just the description and severity for all findings:

* endorctl
* curl
* HTTP

```
endorctl api list --resource Finding \
  --field-mask "meta.description,spec.level"
```

```
curl --get \
  --header "Authorization: Bearer $ENDOR_TOKEN" \
  --url "https://api.endorlabs.com/v1/namespaces/$ENDOR_NAMESPACE/findings?list_parameters.mask=meta.description,spec.level"
```

```
@baseUrl = https://api.endorlabs.com
@token = <insert-access-token>
@namespace = <insert-namespace>

###
GET {{baseUrl}}/v1/namespaces/{{namespace}}/findings?list_parameters.mask=meta.description,spec.level HTTP/1.1
Authorization: Bearer {{token}}
```

## jq

The Endor Labs REST API returns results in json format so it is often convenient to use the `jq` command-line json processor to parse or format the results.

The following example shows how to use `jq` to extract just the description value from the above request:

* endorctl
* curl

```
endorctl api list --resource Finding \
  --field-mask "meta.description,spec.level" \
  | jq '.list.objects[].meta.description'
```

```
curl --get \
  --header "Authorization: Bearer $ENDOR_TOKEN" \
  --url "https://api.endorlabs.com/v1/namespaces/$ENDOR_NAMESPACE/findings?list_parameters.mask=meta.description,spec.level"
  | jq '.list.objects[].meta.description'
```

#### Note

Lists of objects are always nested under `.list.objects[]`, but for `endorctl api get` commands a single object is returned directly.
To extract the object UUID from an object returned by an `endorctl api get` command, the `jq` command is `jq '.uuid'`, as opposed to `jq '.list.objects[].uuid'`.

For more information, see the [jq documentation](https://jqlang.github.io/jq/tutorial/).

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

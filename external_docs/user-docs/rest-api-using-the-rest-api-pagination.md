---
url: https://docs.endorlabs.com/rest-api/using-the-rest-api/pagination/
title: Pagination | Endor Labs Docs
downloaded: 2025-12-11 11:34:28
---

Pagination | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/rest-api/using-the-rest-api/pagination/_print.html)



# Pagination

Learn how to navigate through paginated responses from the Endor Labs REST API.

## About Pagination

When a response from the REST API includes many results, Endor Labs paginates the results and returns a subset of the results. For example, GET `/v1/namespaces/{tenant_meta.namespace}/findings` only returns 100 findings from the given namespace even if the namespace has more than 100 findings. This makes the response easier to handle for servers and for people.

You can use the additional data from the list response to request additional pages of data.

This article explains how to request additional pages of results for paginated responses and how to change the number of results returned on each page.

## Using page\_size

The `page_size` field allows you to control the number of elements returned. By default, this value is 100, with a maximum of 500. It should be noted that the higher this value is, the longer it will take to get a result from Endor Labs.

* endorctl
* curl

```
endorctl api list --resource Finding \
  --page-size=50
```

```
curl --get \
  --header "Authorization: Bearer $ENDOR_TOKEN" \
  --url "https://api.endorlabs.com/v1/namespaces/$ENDOR_NAMESPACE/findings?list_parameters.page_size=50"
```

## Using page\_token

When a response is paginated, the response includes a value for the field `next_page_token`. This value can then be used to fetch additional pages of results.

For example, the response to the above request contains the first 50 elements in the `objects` field along with the following values in the `response` field:

```
{
  "list": {
    "objects": [
        ...
    ],
    "response": {
      "next_page_id": "633dd86976186a89d64628c1",
      "next_page_token": 50
    }
  }
}
```

To access the next page of results, you can use the `next_page_token` value as the value of `page_token` in the next request. For example:

* endorctl
* curl

```
endorctl api list --resource Finding \
  --page-size=50 \
  --page-token=50
```

```
curl --get \
  --header "Authorization: Bearer $ENDOR_TOKEN" \
  --url "https://api.endorlabs.com/v1/namespaces/$ENDOR_NAMESPACE/findings?list_parameters.page_size=50&list_parameters.page_token=50"
```

This returns 50 elements starting from the 50th element in the list. In this case, it returns elements 50 to 100.

## Using `page_id`

The fields `page_id` and `next_page_id` provide the same capabilities as `page_token` and `next_page_token`. However, we recommend using `page_id` and `next_page_id` as they offer better performance for the request.

## endorctl and the flag list-all

The CLI `endorctl` provides the flag `--list-all` that allows you to fetch all resources. Internally, the command sends multiple requests to get all resources.

```
endorctl api list --resource Finding --list-all
```

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

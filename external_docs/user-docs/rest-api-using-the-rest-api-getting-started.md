---
url: https://docs.endorlabs.com/rest-api/using-the-rest-api/getting-started/
title: Getting started | Endor Labs Docs
downloaded: 2025-11-20 11:48:33
---

Getting started | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/rest-api/using-the-rest-api/getting-started/_print.html)



# Getting started

Learn how to use the Endor Labs REST API.

## Introduction

This article describes how to use the Endor Labs REST API. For a quickstart guide, see [Quickstart for Endor Labs REST API](../../quickstart).

The Endor Labs command line tool `endorctl` is a convenient wrapper around the Endor Labs REST API and allows you to interact with Endor Labs without having to worry about the REST protocol details.
For more information, see [Making a request](#making-a-request) below and the [Endor Labs CLI documentation](../../../endorctl/commands/api).

For a complete list of Endor Labs REST API endpoints, see the [Endor Labs OpenAPI documentation](https://docs.endorlabs.com/api/).

## About requests to the REST API

This section describes the elements that make up an API request:

* [HTTP method](#http-method)
* [Path](#path)
* [Headers](#headers)
* [Parameters](#parameters)

Every request to the REST API includes an HTTP method and a path. Depending on the REST API endpoint, you might also need to specify request headers, authentication information, list parameters, or body parameters.

The REST API reference documentation describes the HTTP method, path, and parameters for every endpoint. It also displays example requests and responses for each endpoint. For more information, see the [Endor Labs REST API documentation](..).

## HTTP method

The HTTP method of an endpoint defines the type of action it performs on a given resource. Some common HTTP methods are GET, POST, DELETE, and PATCH. The REST API reference documentation provides the HTTP method for every endpoint.

For example, the HTTP method for the [List Findings](https://docs.endorlabs.com/api/#tag/FindingService/operation/FindingService_ListFindings) endpoint is GET.

Where possible, the Endor Labs REST API strives to use an appropriate HTTP method for each action.

| Action | Description |
| --- | --- |
| GET | Used for retrieving resources. |
| POST | Used for creating resources. |
| PATCH | Used for updating properties of resources. |
| DELETE | Used for deleting resources. |

## Path

Each endpoint has a path. The [Endor Labs REST API reference documentation](https://docs.endorlabs.com/api) gives the path for every endpoint. For example, the path for the [List Findings](https://docs.endorlabs.com/api/#tag/FindingService/operation/FindingService_ListFindings) endpoint is `https://api.endorlabs.com/v1/namespaces/{tenant_meta.namespace}/findings` and the path for the [Get Finding](https://docs.endorlabs.com/api/#tag/FindingService/operation/FindingService_GetFinding) endpoint is `https://api.endorlabs.com/v1/namespaces/{tenant_meta.namespace}/findings/{uuid}`.

The curly brackets {} in a path denote path parameters that you need to specify. Path parameters modify the endpoint path and are required in your request. For example, the path parameter for the [List Findings](https://docs.endorlabs.com/api/#tag/FindingService/operation/FindingService_ListFindings) endpoint is `{tenant_meta.namespace}`. To use this path in your API request, replace `{tenant_meta.namespace}` with the name of the namespace where you want to request a list of findings. To get a specific finding object, add the object UUID to the end of the path.

## Headers

Headers provide extra information about the request and the desired response. Following are some examples of headers that you can use in your requests to the Endor Labs REST API. For an example of a request that uses headers, see [Making a request](#making-a-request).

### Authentication

All endpoints require authentication. Use the `endorctl init` command to authenticate with Endor Labs. For more information, see [Authentication](../../authentication). For examples, see [Making a request](#making-a-request).

### Accept-Encoding

You may optionally use the `Accept-Encoding` header to enable compression of HTTP responses for performance optimization. The following encodings are supported: `gzip`, `br` (`Brotli`), and `zstd`. If you specify multiple encodings, gzip takes priority. Ensure that the client can correctly handle the specified encoding. You can provide the `Accept-Encoding` header in the following format: `Accept-Encoding: gzip, br, zstd`.

### Content-Type

To improve API performance, set the `Content-Type` header to `application/jsoncompact`. This prevents Endor Labs APIs from returning null or empty values, which is the default behavior.

### Request-timeout

Use the `Request-timeout` header to specify the amount of time, in seconds, that you are willing to wait for a server response. For example: `--header "Request-Timeout: 10"`.

The corresponding option for `endorctl` requests is `-t/--timeout`, for example: `-t 10s`.

## Parameters

Many API methods require or allow you to send additional information in parameters in your request. There are a few different types of parameters: Path parameters, list parameters, and body parameters.

### Path parameters

Path parameters modify the endpoint path. These parameters are required in your request. For more information, see [Path](#path).

### List parameters

List parameters allow you to control what data is returned for a request. These parameters are usually optional. The documentation for each Endor Labs REST API endpoint describes any list parameters that it supports.

For example, all Endor Labs endpoints return one hundred objects by default. You can set `page_size=2` to return two objects instead of 100. You can set `count=true` to just return the number of objects. You can use the `filter` list parameter to only list objects that match a specified list of criteria (see [filters](../filters/)). For examples of requests that use list parameters, see [Making a request](#making-a-request) and [Use cases](../use-cases/).

| List Parameter | Description |
| --- | --- |
| `ci_run_uuid` | Only list objects from a specific PR scan. Example: `list_parameters.ci_run_uuid=ee4a914c-8d6d-4b65-8b0e-9755e8a6cb3a` |
| `count` | Get the number of items in the list. Example: `list_parameters.count=true` |
| `filter` | Specify the field names and values used to filter results. Example: `list_parameters.filter=meta.parent_kind==Project` |
| `group.aggregation_paths` | Specify one or more fields to group objects by. Example: `list_parameters.group.aggregation_paths=meta.name` |
| `group.show_aggregation_uuids` | Get the UUIDs of the objects in each group as specified by `group.aggregation_paths`. Example: `list_parameters.group.aggregation_paths=meta.name&list_parameters.group.show_aggregation_uuids=true` |
| `group.unique_count_paths` | Count the number of unique values, for these fields, in the group. Example: `list_parameters.group.aggregation_paths=meta.name&list_parameters.group.unique_count_paths=spec.ecosystem` |
| `group.unique_value_paths` | Get the unique values, for these fields, in the group. Example: `list_parameters.group.aggregation_paths=meta.name&list_parameters.group.unique_value_paths=meta.name` |
| `group_by_time.aggregation_paths` | Group the list based on this time field. Example: `list_parameters.group_by_time.aggregation_paths=meta.create_time` |
| `group_by_time.end_time` | End of the time period to group objects. Example: `list_parameters.group_by_time.end_time=2023-12-31T23:59:59Z` |
| `group_by_time.group_size` | The time interval size to group the objects by. Example: `list_parameters.group_by_time.interval=GROUP_BY_TIME_INTERVAL_WEEK&list_parameters.group_by_time.group_size=2` |
| `group_by_time.interval` | The time interval to group the objects by. Example: `list_parameters.group_by_time.interval=GROUP_BY_TIME_INTERVAL_DAY` |
| `group_by_time.show_aggregation_uuids` | Get the UUIDs of the objects in each group as specified by `group_by_time.aggregation_paths`. Example: `list_parameters.group_by_time.show_aggregation_uuids=true` |
| `group_by_time.start_time` | Beginning of the time period to group objects. Example: `list_parameters.group_by_time.start_time=2023-01-01T00:00:00Z` |
| `mask` | Set the list of fields to return with a request. If no mask is given, all fields are returned by the API. Example: `list_parameters.mask=uuid,mate.name` |
| `page_id` | Set the object UUID to start from. Example: `list_parameters.page_id=66073889a6cfeb5e24e72abf` |
| `page_size` | Set the page size to limit the number of results returned (default `100`). Example: `list_parameters.page_size=10` |
| `page_token` | Set the page token to start from (default `0`). Example: `list_parameters.page_token=5` |
| `sort.order` | Order of the sort. (default `SORT_ENTRY_ORDER_ASC`). Example: `list_parameters.sort.order=SORT_ENTRY_ORDER_DESC` |
| `sort.path` | Field to sort objects by. Example: `list_parameters.sort.path=meta.name` |
| `traverse` | Get data from any child namespaces as well. Example: `list_parameters.traverse=true` |

### Body parameters

Body parameters allow you to pass additional data to the API. These parameters can be optional or required, depending on the endpoint. The documentation for each Endor Labs REST API endpoint describes the body parameters that it supports. For more information, see the [Endor Labs OpenAPI documentation](https://docs.endorlabs.com/api/).

For example, the [Create Policy](https://docs.endorlabs.com/api/#tag/PolicyService/operation/PolicyService_CreatePolicy) endpoint requires that you specify a name, rule, query statement, and resource kinds for the new policy in your request. It also allows you to optionally specify other information, such as a description, actions, or tags to apply to the new policy. For an example of a request that uses body parameters, see [Making a request](#making-a-request).

## Making a request

The following example retrieves all findings for reachable functions. For more examples, see [Use cases](../use-cases/).

* endorctl
* curl
* HTTP

1. **Setup**

   Install the Endor Labs CLI on macOS, Windows, or Linux. For more information, see [Install Endor Labs on your local system](../../../getting-started/quickstart).
2. **Authenticate**

   Authenticate with Endor Labs using `endorctl init`. For more information, see [endorctl init](../../../endorctl/commands/init).

   `endorctl init --auth-mode google`
3. **Make a request**

   `endorctl api list --resource Finding --filter "spec.finding_tags contains FINDING_TAGS_REACHABLE_FUNCTION"`

   Note that you do not have to provide the access token or the namespace when using `endorctl` to access the Endor Labs REST API.

1. **Setup**

   1. You must have curl installed on your machine. To check if curl is already installed, run `curl --version`- on the command line.

      * If the output provides information about the version of curl, that means curl is installed.
      * If you get a message similar to command not found: curl, that means curl is not installed. Download and install curl. For more information, see the [curl download page](https://curl.se/download.html).
   2. Install the Endor Labs CLI on macOS, Windows, or Linux. For more information, see [Install Endor Labs on your local system](../../../getting-started/quickstart).
2. **Authenticate**

   1. Authenticate with Endor Labs using `endorctl init`. For more information, see [endorctl init](../../../endorctl/commands/init).

      `endorctl init --auth-mode google`
   2. Store the Endor Labs access token

      Run the following command from your terminal to get the Endor Labs access token.

      `endorctl auth --print-access-token`
3. **Choose an endpoint for your request**

   Choose an endpoint to make a request to. You can explore the Endor Labs REST API documentation to discover endpoints that you can use to interact with Endor Labs.

   Identify the HTTP method and path of the endpoint. You will send these with your request. For more information, see [HTTP method](#http-method) and [Path](#path).

   For example, the [List Findings](https://docs.endorlabs.com/api/#tag/FindingService/operation/FindingService_ListFindings) endpoint uses the HTTP method POST and the path `/v1/namespaces/{tenant_meta.namespace}/findings`.

   Identify any required path parameters. Required path parameters appear in curly brackets {} in the path of the endpoint. Replace each parameter placeholder with the desired value. For more information, see [Path](#path).

   For example, the [List Findings](https://docs.endorlabs.com/api/#tag/FindingService/operation/FindingService_ListFindings) endpoint uses the path `/v1/namespaces/{tenant_meta.namespace}/findings`, and the path parameter is `{tenant_meta.namespace}`. To use this path in your API request, replace `{tenant_meta.namespace}` with the name of the namespace where you want to list the findings.
4. **Choose options for your request**

   Use the curl command to make your request. For more information, see the [curl documentation](https://curl.se/docs/manpage.html).

   Specify the following options and values in your request:

   * `--request` or `-X` followed by the HTTP method as the value. For more information, see [HTTP method](#http-method).

     > Note: You can also use the shorthand curl options `--get` and `--post` for GET and POST requests respectively.
   * `--header` or `-H`:

     + `Authorization`: Pass your authentication token in an Authorization header. You must use `Authorization: Bearer` with the Endor Labs REST API. For more information, see [Authentication](#authentication).
     + `Accept-Encoding`: Provide the `Accept-Encoding` header in the following format: `Accept-Encoding: gzip` to avoid performance bottlenecks. For more information, see [Accept-Encoding](#accept-encoding).
     + `Content-Type`: Set the header as `Content-Type: application/jsoncompact` to prevent Endor Labs APIs from returning null or empty value. For more information, see [Content-Type](#content-type).
     + `Request-timeout`: Specify the amount of time, in seconds, that you are willing to wait for a server response. For more information, see [Request-timeout](#request-timeout).
   * `--url` followed by the full path as the value. The full path is a URL that includes the base URL for the Endor Labs REST API (`https://api.endorlabs.com`) and the path of the endpoint, like this: `https://api.endorlabs.com/{PATH}`. Replace `{PATH}` with the path of the endpoint. For more information, see [Path](#path).

     To use list parameters, add a `?` to the end of the path, then append your list parameter name and value in the form `list_parameter.parameter_name=value`. Separate multiple list parameters with `&`. For example, to count the number of “Outdated Release” findings, use `?list_parameters.filter=meta.name==outdated_release&list_parameters.count=true`. For more information, see [List parameters](#list-parameters).

     > Note: Filters with spaces must be encoded when using curl. Replace spaces with `%20` or use the `--data-urlencode` option for filters containing spaces.
   * `--data` or `-d` followed by any body parameters within a json object. If you do not need to specify any body parameters in your request, omit this option. For more information, see [Body parameters](#body-parameters).
5. **Make request**

   1. Using `--url`

      ```
      curl --request GET \
        --header "Authorization: Bearer $ENDOR_TOKEN" \
        --header "Accept-Encoding: gzip" \
        --header "Content-Type: application/jsoncompact" \
        --url "https://api.endorlabs.com/v1/namespaces/$ENDOR_NAMESPACE/findings?list_parameters.filter=spec.finding_tags%20contains%20FINDING_TAGS_REACHABLE_FUNCTION"
      ```
   2. Using `--data-urlencode`

      ```
      curl --request GET \
        --header "Authorization: Bearer $ENDOR_TOKEN" \
        --header "Accept-Encoding: gzip" \
        --header "Content-Type: application/jsoncompact" \
        --data-urlencode "spec.finding_tags contains FINDING_TAGS_REACHABLE_FUNCTION" \
        "https://api.endorlabs.com/v1/namespaces/$ENDOR_NAMESPACE/findings"
      ```

1. **Setup**

   Install the Endor Labs CLI on macOS, Windows, or Linux. For more information, see [Install Endor Labs on your local system](../../../getting-started/quickstart).
2. **Authenticate**

   1. Authenticate with Endor Labs using `endorctl init`. For more information, see [endorctl init](../../../endorctl/commands/init).

      `endorctl init --auth-mode google`
   2. Store the Endor Labs access token

      Run the following command from your terminal to get the Endor Labs access token.

      `endorctl auth --print-access-token`
3. **Choose an endpoint for your request**

   Choose an endpoint to make a request to. You can explore the Endor Labs REST API documentation to discover endpoints that you can use to interact with Endor Labs.

   Identify the HTTP method and path of the endpoint. You will send these with your request. For more information, see [HTTP method](#http-method) and [Path](#path).

   For example, the [List Findings](https://docs.endorlabs.com/api/#tag/FindingService/operation/FindingService_ListFindings) endpoint uses the HTTP method POST and the path `/v1/namespaces/{tenant_meta.namespace}/findings`.

   Identify any required path parameters. Required path parameters appear in curly brackets {} in the path of the endpoint. Replace each parameter placeholder with the desired value. For more information, see [Path](#path).

   For example, the [List Findings](https://docs.endorlabs.com/api/#tag/FindingService/operation/FindingService_ListFindings) endpoint uses the path `/v1/namespaces/{tenant_meta.namespace}/findings`, and the path parameter is `{tenant_meta.namespace}`. To use this path in your API request, replace `{tenant_meta.namespace}` with the name of the namespace where you want to list the findings.
4. **Make a request**

   ```
   @baseUrl = https://api.endorlabs.com
   @token = <insert-access-token>
   @namespace = <insert-namespace>

   ###
   GET {{baseUrl}}/v1/namespaces/{{namespace}}/findings?spec.finding_tags contains FINDING_TAGS_REACHABLE_FUNCTION HTTP/1.1
   Authorization: Bearer {{token}}
   ```

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

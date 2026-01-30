---
url: https://docs.endorlabs.com/rest-api/using-the-rest-api/troubleshooting/
title: Troubleshooting | Endor Labs Docs
downloaded: 2026-01-29 22:23:56
---

Troubleshooting | Endor Labs Docs



* Type to search...

[Print entire section](/rest-api/using-the-rest-api/troubleshooting/_print.html)



# Troubleshooting

Learn how to diagnose and resolve common problems for the Endor Labs REST API.

For a full list of error code descriptions, see [Errors](../errors).

## Invalid authorization

If Endor Labs cannot verify your access token, for example, if it is empty or if it has expired, Endor Labs will terminate the request and you will receive an invalid authorization response.

```
{
    "code": 16,
    "message": "Invalid authorization header: Bearer",
    "details": [
        {
            "@type": "type.googleapis.com/internal.endor.ai.rpc.v1.HTTPErrorInfo",
            "status_code": 401
        }
    ]
}
```

### Remediation

Try creating a new token or, if you have a valid API key and secret in your `~/.endorctl/config.yaml` file, unsetting the environment variable (`unset ENDOR_TOKEN`).

For more information, see [Authentication](../../authentication/).

## Permission Denied

If your access token does not have the required permissions to access a namespace or perform an operation, Endor Labs will terminate the request and you will receive an unauthorized request response.

```
{
  "code": 7,
  "message": "Unauthorized request for given endpoint",
  "details": [
    {
      "@type": "type.googleapis.com/internal.endor.ai.rpc.v1.HTTPErrorInfo",
      "status_code": 403
    }
  ]
}
```

### Remediation

Check the value of the `ENDOR_NAMESPACE` environment variable, the variable with the same name in the `~/.endorctl/config.yaml file`, or the API endpoint URL.

For more information, see [Authentication](../../authentication/).

## Context deadline exceeded

If it takes too long to process an API request, Endor Labs will terminate the request and you will receive a timeout response and a “context deadline exceeded” message.

```
{
    "code": 4,
    "message": "context deadline exceeded",
    "details": []
}
```

Endor Labs reserves the right to change the timeout window to protect the speed and reliability of the API.

### Remediation

You can [increase the request timeout limit](../getting-started/#request-timeout) or you can try to [simplify your request](../getting-started/#list-parameters). For instance, if you are requesting 100 items per page, try requesting fewer items.

For more information, see [Best practices](../best-practices/).

## Invalid argument

If a request is missing a required field, or includes a non-existent field, Endor Labs will return an “invalid argument” response.
The response `message` field contains details about the error, such as the field name and the specific problem with it.

For example, the following response is returned if you request all findings with the field mask `uui` instead of `uuid`:

```
{
  "code": 3,
  "message": "mask: proto: invalid path &#34;uui&#34; for message &#34;internal.endor.ai.endor.v1.Finding&#34;",
  "details": [
    {
      "@type": "type.googleapis.com/internal.endor.ai.rpc.v1.HTTPErrorInfo",
      "status_code": 400
    }
  ]
}
```

### PATCH requests

Here is an example response to an PATCH (update) request that sent a Finding as the payload instead of an [UpdateFinding](https://docs.endorlabs.com/api/#tag/FindingService/operation/FindingService_UpdateFinding):

```
{
  "code": 3,
  "message": "invalid Finding.Meta: value is required; invalid Finding.Spec: value is required",
  "details": [
    {
      "@type": "type.googleapis.com/internal.endor.ai.rpc.v1.HTTPErrorInfo",
      "status_code": 400
    }
  ]
}
```

#### Remediation

Make sure to use the right data structure as the payload for your PATCH requests. For example:

```
{
  "request" : {
    "update_mask": "meta.tags"
  },
  "object" : {
    "uuid" : "<uuid>",
    "meta" : {
      "tags": [
        "<tags>"
      ]
    }
  }
}
```

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

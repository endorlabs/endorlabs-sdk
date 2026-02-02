---
url: https://docs.endorlabs.com/rest-api/using-the-rest-api/errors/
title: Errors | Endor Labs Docs
downloaded: 2026-01-29 22:23:53
---

Errors | Endor Labs Docs



* Type to search...

[Print entire section](/rest-api/using-the-rest-api/errors/_print.html)



# Errors

Learn about the Endor Labs REST API error codes and how to handle them

Endor Labs uses conventional gRPC and HTTP response codes to indicate the success or failure of an API request.

**Note**

When making API requests, always implement proper error handling to gracefully manage these response codes.

## gRPC status codes

| Value | Code Name | Description |
| --- | --- | --- |
| 0 | OK | Not an error; returned on success. |
| 1 | CANCELLED | The operation was cancelled, typically by the caller. |
| 2 | UNKNOWN | Unknown error; typically indicates an unexpected error. |
| 3 | INVALID\_ARGUMENT | The client specified an invalid argument. |
| 4 | DEADLINE\_EXCEEDED | The deadline expired before the operation could complete. |
| 5 | NOT\_FOUND | The requested entity, such as a file or directory, was not found. |
| 6 | ALREADY\_EXISTS | The entity that a client attempted to create already exists. |
| 7 | PERMISSION\_DENIED | The caller does not have permission to execute the specified operation. |
| 8 | RESOURCE\_EXHAUSTED | Some resource has been exhausted, perhaps a per-user quota, or the entire file system is out of space. |
| 9 | FAILED\_PRECONDITION | The system is not in a state required for the operation’s execution. |
| 10 | ABORTED | The operation was aborted, typically due to a concurrency issue like a sequencer check failure. |
| 11 | OUT\_OF\_RANGE | The operation was attempted beyond the valid range, such as seeking past the end of a file. |
| 12 | UNIMPLEMENTED | The operation is not implemented or is not supported or enabled in this service. |
| 13 | INTERNAL | Internal errors; invariants expected by the underlying system are broken. |
| 14 | UNAVAILABLE | The service is currently unavailable. This is most likely a transient condition and may be corrected by retrying with a backoff. |
| 15 | DATA\_LOSS | Unrecoverable data loss or corruption. |
| 16 | UNAUTHENTICATED | The request does not have valid authentication credentials for the operation. |

Refer to the [gRPC status code documentation](https://grpc.io/docs/guides/status-codes/) for more information.

## HTTP status codes

| Value | Code Name | Description |
| --- | --- | --- |
| 200 | OK | Everything worked as expected. |
| 400 | Bad Request | The request was unacceptable, often due to missing a required parameter. |
| 401 | Unauthorized | No valid API key provided. |
| 402 | Request Failed | The parameters were valid but the request failed. |
| 403 | Forbidden | The API key doesn’t have permissions to perform the request. |
| 404 | Not Found | The requested resource doesn’t exist. |
| 409 | Conflict | The request conflicts with another request, possibly due to using the same key. |
| 429 | Too Many Requests | Too many API requests were sent to Endor Labs in a short time. We recommend using an exponential backoff strategy for your requests. |
| “500, 502, 503, 504” | Server Errors | Something went wrong on the Endor Labs side (these are rare). |

**Note**

When receiving a 429 status code, implement an exponential backoff strategy to avoid overwhelming the API.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

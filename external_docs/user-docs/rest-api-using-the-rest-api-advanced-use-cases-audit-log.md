---
url: https://docs.endorlabs.com/rest-api/using-the-rest-api/advanced-use-cases/audit-log/
title: Using Audit Log API | Endor Labs Docs
downloaded: 2025-10-27 12:58:56
---

Using Audit Log API | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/rest-api/using-the-rest-api/advanced-use-cases/audit-log/_print.html)



# Using Audit Log API

Learn how to use the audit log API in Endor Labs

Audit logs help to monitor user actions and system operations, and generate audit trails for compliance requirements.

You can use the [list AuditLog endpoint](https://docs.endorlabs.com/api/#tag/AuditLogService/operation/AuditLogService_ListAuditLogs) to retrieve audit logs.

You can retrieve audit logs for the following resources:

* Tenants and namespaces
* Projects
* Users and user telemetry
* Repositories and repository versions
* Scan results
* Authorization policies
* Action policies
* Remediation policies
* Notification policies
* Supported toolchains
* Application telemetry
* Endor Labs licenses

Run the following command to fetch the entire audit log.

```
endorctl api list -r AuditLog -n <namespace name>
```

## Operations with the audit log API

You can pass the [`meta`](#meta-fields) and [`spec`](#spec-fields) fields with the `endorctl list AuditLog` command to refine the output based on your requirements. You can combine multiple filters in the same command and use various operators. See [Filters](../../filters/) for more information on using filters and operators.

The `meta` and `spec` options listed are not exhaustive. You can build your command based on the `meta` and `spec` fields in the [API specification](https://docs.endorlabs.com/api/#tag/AuditLogService/operation/AuditLogService_ListAuditLogs).

## Operators

You can use the following operators with the filters.

| Operator | Description |
| --- | --- |
| `==` | Matches objects where a specified field is equal to a specified value. |
| `!=` | Matches objects where a specified field is NOT equal to a specified value. |
| `<` | Matches objects where a specified field is less than a specified value. |
| `<=` | Matches objects where a specified field is less than or equal to a specified value. |
| `>` | Matches objects where a specified field is greater than a specified value. |
| `>=` | Matches objects where a specified field is greater than or equal to a specified value. |
| `contains` | Matches objects where a specified list contains one or more specified values. |
| `in` | Matches objects where a specified field is equal to one or more specified values. |
| `matches` | Matches objects where a specified field matches a specified regex pattern. |
| `exists` | Matches objects where a specified field in a json payload exists. |

### Meta fields

You can use the following `meta` fields.

| Meta Field | Description |
| --- | --- |
| `meta.create_time` | Timestamp of the message creation. |
| `meta.update_time` | Timestamp of the message update. |
| `meta.upsert_time` | Timestamp of the message upsert. |
| `meta.created_by` | User that created the message. |
| `meta.updated_by` | User that updated the message. |

### Spec fields

| Spec Field | Description |
| --- | --- |
| `spec.message_kind` | Message type on which the operations are performed. For example, `internal.endor.ai.endor.v1.AuthorizationPolicy` is the value of `spec.message_kind` for authorization policy. |
| `spec.message_UUID` | The UUID of the message. |
| `spec.operation` | The type of operation. The following types are supported: - OPERATION\_CREATE - OPERATION\_UPDATE - OPERATION\_DELETE - OPERATION\_UPSERT |
| `spec.payload` | The operation payload, which contains the message that is being created or updated. |
| `spec.claims` | Authentication claims array. |
| `spec.remote_address` | The source IP address. |

### Timeout in AuditLog API

Since querying audit logs might take more time in comparison with other API operations, you may face a timeout with the error message, `ERROR deadline-exceeded: context deadline exceeded`. If you face the error, provide a timeout override along with your API command to complete the API call. You can use the `--timeout` option and provide the override in seconds: `endorctl api <command> --timeout=<n>s`. For example, `endorctl api list -r AuthenticationLog --timeout=30s`. The default timeout is 20 seconds.

## Examples of using AuditLog API

The following sections provide various scenarios of using the audit log API.

### Filter audit log by time range

Audit logs grow with time. You may want to restrict the time period to retrieve meaningful data to investigate activity during a specific timeframe.

The following example retrieves the audit log of the month of January 2025.

```
endorctl api list -r AuditLog -n demo \
  --filter="meta.create_time>=date(2025-01-01T00:00:00Z)
            and meta.create_time<=date(2025-01-31T23:59:59Z)"
```

### Filter audit log by users and time range

You can retrieve the logs of a specific user in a time period.

The following example retrieves the audit log of a user with the name `Doe` in their claims token.

```
endorctl api list -r AuditLog -n demo \
  --filter="meta.create_time>=date(2025-02-01T00:00:00Z)
            and meta.create_time<=date(2025-02-19T23:59:59Z)
            and spec.claims matches '.*firstname=Doe.*'"
```

The following example retrieves the audit log of all users with `endor.ai` as the domain in their claims token.

```
endorctl api list -r AuditLog -n demo \
  --filter="meta.create_time>=date(2025-02-01T00:00:00Z)
            and meta.create_time<=date(2025-02-19T23:59:59Z)
            and spec.claims matches '.*domain=endor.ai.*'"
```

### Filter audit log based on operation types

You can retrieve the specific audit logs based on a particular operation.

The following retrieves audit logs that pertain to create operation after August 18, 2024.

```
endorctl api list -r AuditLog -n demo \
  --filter="spec.operation=='OPERATION_CREATE'
            and meta.create_time>=date(2024-08-18T00:00:00Z)"
```

### Filter audit log based on message type

You can retrieve audit logs based on the message type.

You need to provide `internal.endor.ai.endor.v1.` followed by the message type with the `spec.message_kind` filter.

The following example retrieves updates to scan results.

```
endorctl api list -r AuditLog -n demo \
  --filter="spec.operation=='OPERATION_CREATE'
            and spec.message_kind=='internal.endor.ai.endor.v1.ScanResult'"
```

### Filter audit log based on policy updates

You can retrieve audit logs for the updates on policies.

The following example retrieves updates to action, notification, and remediation policies made after August 18, 2024.

```
endorctl api list -r AuditLog -n demo \
  --filter="spec.operation=='OPERATION_CREATE'
            and spec.message_kind=='internal.endor.ai.endor.v1.Policy'
            and meta.create_time>=date(2024-08-18T00:00:00Z)"
```

The following example retrieves changes to authorization policies made after August 18, 2024.

```
endorctl api list -r AuditLog -n demo \
  --filter="spec.operation=='OPERATION_UPDATE'
            and spec.message_kind=='internal.endor.ai.endor.v1.AuthorizationPolicy'
            and meta.create_time>=date(2024-08-18T00:00:00Z)"
```

### Filter audit log based on IP range

You can retrieve audit logs based on an IP range to investigate activities originating from a particular geography or a particular service that uses your Endor Labs instance.

The following example retrieves audit log for activities done from the IP range, `10.244.0.0` to `10.244.255.255`.

```
endorctl api list -r AuditLog -n demo \
  --filter="spec.remote_address>='10.244.0.0'
            and spec.remote_address<='10.244.255.255'"
```

### Retrieve the history of an object based on message UUID

You can retrieve the history of an object based on the message UUID.

```
endorctl api list -r AuditLog -n demo \
  --filter="spec.message_uuid=='<message_uuid>'"
```

The following example retrieves the history of an action policy with the UUID, `66axxxxxxxxxx4c15dc1`.

```
endorctl api list -r AuditLog -n demo \
  --filter="spec.message_uuid=='66axxxxxxxxxx4c15dc1'"
```

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

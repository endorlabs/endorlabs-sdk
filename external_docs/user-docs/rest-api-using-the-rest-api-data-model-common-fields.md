---
url: https://docs.endorlabs.com/rest-api/using-the-rest-api/data-model/common-fields/
title: Common fields | Endor Labs Docs
downloaded: 2026-01-16 09:47:16
---

Common fields | Endor Labs Docs



* Type to search...

[Print entire section](/rest-api/using-the-rest-api/data-model/common-fields/_print.html)



# Common fields

Learn about the common fields for all objects in the Endor Labs data model.

All objects adhere to the same high-level structure as outlined below. Object specific fields are defined in **Spec**. For more information, see [Resource kinds](../resource-kinds/).

## UUID

All objects have a unique **UUID**. You can use UUID to retrieve objects individually through the API.

## Meta

All objects include a common nested object called **Meta**.

Meta is a mandatory object that contains the common fields for each object, including the following fields.

| Field name | Description |
| --- | --- |
| `name` | The name of the object. |
| `description` | A description of the object. |
| `kind` | The resource kind of the object (for example, `RepositoryVersion`). |
| `version` | The version of the object, used to differentiate between different versions if needed. |
| `parent_uuid` | The UUID of the parent object. |
| `parent_kind` | The resource kind of the parent object (for example, `Project`). |
| `create_time` | The time the object was created. |
| `update_time` | The time the object was last updated (HTTP PATCH). |
| `upsert_time` | The time the object was last updated or created (HTTP POST). |
| `created_by` | The name and authentication source of the user who created the object. Example: `ewok@endor.ai@google@api-key` |
| `updated_by` | The name and authentication source of the last user who updated the object. Example: `vulnerabilityingestor@endor.ai@x509` |
| `tags` | A list of custom tags attached to the object. Tags can be used to organize objects and find collections of objects that satisfy certain conditions. A tag must be 63 characters or fewer. Tags may contain alphanumeric characters, `@`, `_`, `.`, and `-`. An optional prefix must be separated with `=` (for example, `my_tag=my_value`). |
| `annotations` | Map of additional metadata for the object. Annotation keys may contain alphanumeric characters, `_`, `.`, and `-`. Annotation values can be structured or unstructured and may include characters not permitted by tags. Values must be 16384 bytes or smaller. |

## TenantMeta

Most objects include a common nested object called **TenantMeta**.

TenantMeta contains the following field.

| Field name | Description |
| --- | --- |
| `namespace` | Name of the namespace the object belongs to. Organizes organizational units into virtual groupings of objects. Namespaces must be fully qualified names (for example, the child namespace of `endor.prod` called `app` is `endor.prod.app`). |

### OSS tenant

There is a common tenant for all OSS projects called `oss`, to which customers have read access.

## Spec

All objects include a common nested object called **Spec**. This mandatory object contains the specification of the object, representing its current state. For more information, see [Resource kinds](../resource-kinds/).

## Context

Most objects include a common nested object called **Context**. Contexts keep objects from different scans separated.

The context object has the following fields.

| Field name | Description |
| --- | --- |
| `type` | The [type](#context-types) of context, usually defined based on how endorctl is being used. |
| `id` | The ID of the context, such as a pull request ID or branch reference. |
| `will_be_deleted_at` | The time when the object will be automatically deleted by the system. |
| `tags` | A list of tags applied to a context. Used primarily for CI and SBOM contexts. |

### Context types

Each context has a type and an id. For example, objects created during a scan of the default branch belong to the **main** context, while objects for non-default branches have the context type **ref**.

| Context type | Description |
| --- | --- |
| `CONTEXT_TYPE_MAIN` | Objects from a scan of the default branch. All objects in the OSS namespace are in the main context. The context ID is always `default`. |
| `CONTEXT_TYPE_REF` | Objects from a scan of a specific branch. The context ID is the branch reference name. |
| `CONTEXT_TYPE_CI_RUN` | Objects from a PR scan. The context ID is the PR UUID. Objects in this context are deleted after three weeks. |
| `CONTEXT_TYPE_SBOM` | Objects from an SBOM scan. The context ID is the SBOM serial number or some other unique identifier. |
| `CONTEXT_TYPE_EXTERNAL` | Indicates that this object is a copy/temporary value of an object in another project. Used for same-tenant dependencies. In source code reference this is equivalent to “vendor” folders. Package versions in the external context are only scanned for call graphs. No other operations are performed on them. |

## Processing status

**Project** and **PackageVersion** objects include a common nested object called **ProcessingStatus**, which contains fields about the processing status of the object (when it was/will be scanned). The processing status object has the following fields:

| Field name | Description |
| --- | --- |
| `scan_state` | The [state](#scan-state) of the scan. |
| `scan_time` | The last time the object was scanned. Projects onboarded via the GitHub App are scanned every 24 hours. |
| `analytic_time` | The last time the object was analyzed. Analytics are run automatically every 24 hours. |
| `disable_automated_scan` | A boolean used to disable automatic scanning by the system. |

### Scan state

The following scan states are supported.

| Scan state | Description |
| --- | --- |
| `SCAN_STATE_NOT_PROCESSED` | The object has not yet been processed by the system. |
| `SCAN_STATE_IDLE` | The object has been scanned at least once. |
| `SCAN_STATE_INGESTING` | The object is being scanned. |
| `SCAN_STATE_ANALYTIC` | The object is being analyzed. |
| `SCAN_STATE_UNREACHABLE` | The object is not reachable from the scheduler. |
| `SCAN_STATE_REQUEST_FULL_RESCAN` | The object is marked for a complete rescan. This only applies to OSS projects. |
| `SCAN_STATE_REQUEST_INCREMENTAL_RESCAN` | The object is marked for an incremental rescan, where only new packages discovered in the scan are added. |

## Example

The following is an example of a **Project** object.

```
{
  "meta": {
    "create_time": "2023-12-05T00:04:21.853Z",
    "kind": "Project",
    "name": "https://github.com/my_organization/my_repository.git",
    "update_time": "2024-05-01T16:50:03.830911988Z",
    "version": "v1"
  },
  "processing_status": {
    "analytic_time": "2024-05-01T16:45:06.483972413Z",
    "disable_automated_scan": true,
    "scan_state": "SCAN_STATE_IDLE",
    "scan_time": "2024-03-18T14:38:31.899249002Z"
  },
  "spec": {
    "git": {
      "full_name": "endorlabs/monorepo",
      "git_clone_url": "git@github.com:my_organization/my_repository.git",
      "http_clone_url": "https://github.com/my_organization/my_repository.git",
      "organization": "endorlabs",
      "path": "monorepo",
      "web_url": "https://api.github.com/my_organization/my_repository"
    },
    "internal_reference_key": "https://github.com/my_organization/my_repository.git",
    "platform_source": "PLATFORM_SOURCE_GITHUB"
  },
  "tenant_meta": {
    "namespace": "my_namespace"
  },
  "uuid": "656e69058032bf0abaaeb681"
}
```

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

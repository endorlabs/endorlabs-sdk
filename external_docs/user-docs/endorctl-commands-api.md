---
url: https://docs.endorlabs.com/endorctl/commands/api/
title: endorctl api | Endor Labs Docs
downloaded: 2025-12-11 11:31:17
---

endorctl api | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/endorctl/commands/api/_print.html)



# endorctl api

Use the endorctl api command to interact with the Endor Labs API

The `endorctl api` command allows you to interact with the Endor Labs API directly through the command line interface.

## Usage

The syntax of the `endorctl api` command is:

```
endorctl api [subcommand] [flags]
```

The following subcommands are supported:

* `create` creates a specified object in a namespace.
* `delete` deletes a specified object in a namespace.
* `get` gets a specified object in a namespace.
* `list` lists a specified group of objects in a namespace.
* `update` updates a specified object in a namespace.

### Flags and variables

The following flags are supported for all `endorctl api` subcommands, unless specified otherwise:

| Flag | Environment Variable | Type | Description |
| --- | --- | --- | --- |
| `data` | `ENDOR_API_DATA` | json | Define the object you want to create or update in json format. |
| `field-mask` | `ENDOR_API_FIELD_MASK` | string | Specify a list of fields to return or update. |
| `header` | `ENDOR_API_HEADER` | string | Specify request header information in the following format: `key:value`. |
| `interactive` | `ENDOR_API_INTERACTIVE` | boolean (default:false) | Create or update an object interactively. Requires the environment variable `EDITOR` to be set (for example, `export EDITOR=vim`). |
| `name` | `ENDOR_API_NAME` | string | Specify the name of the resource that you want to interact with. |
| `output-type` | `ENDOR_API_OUTPUT_TYPE` | string | Specify the output format of the response. The default output type is `json`, but can also be set to `yaml` or `table`. |
| `resource` | `ENDOR_API_RESOURCE` | string | Specify the resource type that you want to interact with. See [commonly used resource types](#commonly-used-resource-types) below for a list of supported resource types. |
| `timeout` | `ENDOR_API_TIMEOUT` | string | Set the timeout limit for the command. The default is `20s`, but larger or more complex requests might need additional time, which might lead to a “context deadline exceeded” error. |
| `uuid` | `ENDOR_API_UUID` | string | Specify the UUID of the resource that you want to interact with. |

### Commonly used resource types

The following table lists resource types that are commonly used in the API. See [resource kind](../../../rest-api/using-the-rest-api/data-model/resource-kinds) for more information.

**Note**

Resource kinds are case sensitive.

| Resource Kind | Description |
| --- | --- |
| `Project` | A project represents a configuration for ingesting source control repositories. List all projects by calling `endorctl api list -r Project`. |
| `Repository` | A repository represents information about a source control repository where source code is hosted. List all repositories for a project by filtering on `meta.parent_uuid==<project-uuid>`. |
| `RepositoryVersion` | A repository version represents information about a specific version of code in source control, such as commit SHAs, tags or branches. List all repository versions for a project by filtering on `meta.parent_uuid==<project-uuid>`. |
| `PackageVersion` | A package version represents information about a named version of a package. List all package versions for a project by filtering on `spec.project_uuid==<project-uuid>`. |
| `DependencyMetadata` | A dependency metadata object represents the relationship between the root package version (importer) and a given dependency. List all dependency metadata objects for a project by filtering on `spec.importer_data.project_uuid==<project-uuid>`. |
| `Metric` | A metric object contains the output of a given analytic. List all metric objects for a project by filtering on `spec.project_uuid==<project-uuid>`. |
| `Finding` | A finding represents a result of an evaluation method used to evaluate code against a rule. List all findings for a project by filtering on `spec.project_uuid==<project-uuid>`. |
| `ScanResult` | A scan result contains metadata about a particular scan (like configuration and results). List all scan results for a project by filtering on `meta.parent_uuid==<project-uuid>`. |
| `AuthorizationPolicy` | An authorization policy represents a policy for access control. List all authorization policies by calling `endorctl api list -r AuthorizationPolicy`. |

## endorctl api create

The `endorctl api create` command creates an object of a specified resource type.

```
endorctl api create -r [resource] [flags]
```

### endorctl api create interactive mode

* Use `--interactive` or `-i` to create an object with an interactive code editor.
  + Define your editor using `export EDITOR=<editor>` where the editor is defined as the command used to edit files. For example, `export EDITOR=vi` allows you to edit in vi and `export EDITOR=code` opens the file with the code command in VS Code.

### endorctl api create examples

To create a package manager integration that uses the repository `https://example.replaceme.com` for dependency resolution in Python with the top priority for dependency resolution use the following command.

```
endorctl api create -r PackageManager \
    --data '{"meta":{"name":"pypi PackageManager"},"spec":{"pypi":{"url":"https://example.replaceme.com ","priority":0}}}'
```

## endorctl api delete

The `endorctl api delete` command deletes a given object of a specified resource type.

```
endorctl api delete -r [resource] [flags]
```

### endorctl api delete example

Use the following command to delete the project with the UUID, ‘62aa1cfadfa47d9ccb754d22’, that is no longer needed.

```
endorctl api delete -r Project --uuid 62aa1cfadfa47d9ccb754d22
```

## endorctl api get

The `endorctl api get` command retrieves a given object of a specified resource type.

```
endorctl api get -r [resource] [flags]
```

### endorctl api get examples

* Get a specific project by its UUID.

```
endorctl api get -r Project --uuid <UUID>
```

* Get a specific package version.

```
endorctl api get --resource "PackageVersion" --name "<ecosystem>://<name>@<version>"
```

## endorctl api list

The `endorctl api list` command lists all objects of a specified resource type, based on the specified filters, field-masks and/or other options.

```
endorctl api list -r [resource] [flags]
```

### endorctl api list flags and variables

The `endorctl api list` command supports the following additional flags and environment variables:

| Flag | Environment Variable | Type | Description |
| --- | --- | --- | --- |
| `count` | `ENDOR_API_COUNT` | boolean (default:false) | Get the number of items in the list. |
| `filter` | `ENDOR_API_FILTER` | json | Specify query parameters used to filter resources. |
| `group-aggregation-paths` | `ENDOR_API_GROUP_AGGREGATION_PATHS` | json | Specify one or more fields to group resources by. |
| `group-show-aggregation-uuids` | `ENDOR_API_GROUP_SHOW_AGGREGATION_UUIDS` | boolean (default:false) | Get the UUIDs of the resources in each group as specified by `--group-aggregation-paths`. |
| `group-unique-count-paths` | `ENDOR_API_GROUP_UNIQUE_COUNT_PATHS` | json | Count the number of unique values, for these fields, in the group. |
| `group-unique-value-paths` | `ENDOR_API_GROUP_UNIQUE_VALUE_PATHS` | json | Get the unique values, for these fields, in the group. |
| `list-all` | `ENDOR_API_LIST_ALL` | boolean (default:false) | List all resources (use `-t`or `--timeout` to increase timeout for big queries). |
| `page-id` | `ENDOR_API_PAGE_ID` | string | Set the page ID to start from. |
| `page-size` | `ENDOR_API_PAGE_SIZE` | integer | Set the page size to limit the number of results returned (default is 100). |
| `page-token` | `ENDOR_API_PAGE_TOKEN` | string | Set the page token to start from. |
| `pr-uuid` | `ENDOR_API_PR_UUID` | string (UUID format) | Only list resources from a specific PR scan. |
| `sort-order` | `ENDOR_API_SORT_ORDER` | string | Sort resources in the specified order, ascending or descending (default ascending). |
| `sort-path` | `ENDOR_API_SORT_PATH` | string | Specify a field to sort resources by. |
| `traverse` | `ENDOR_API_TRAVERSE` | boolean (default:false) | Get data from any child namespaces as well. |

### endorctl api list examples

Use the `--filter` flag to customize your query and the `--field-mask` flag to limit the fields returned.
For example, run the following command to list the description and the target dependency name for all findings in a given project.

```
endorctl api list \
  --resource Finding \
  --filter "spec.project_uuid==<uuid>" \
  --field-mask "meta.description,spec.target_dependency_package_name"
```

See [Filters](../../../rest-api/using-the-rest-api/filters/) and [Masks](../../../rest-api/using-the-rest-api/masks/) for more information on filters and field-masks.

Get a count of the number of projects hosted in your Endor Labs tenant.

```
endorctl api list \
  --resource Project \
  --count \
  | jq -r '.count_response.count'
```

List all projects in the namespace and only return the name of each project.

```
endorctl api list \
  --resource Project \
  --list-all \
  --field-mask meta.name \
  | jq '.list.objects[].meta.name'
```

List all package versions at a given source code Git reference.

```
endorctl api list \
  --resource "PackageVersion" \
  --output-type "yaml" \
  --filter "spec.project_uuid==<uuid> and spec.source_code_reference.version.ref==<git-reference>"
```

List all direct dependencies of a specific package given its UUID.

```
endorctl api list \
  --resource DependencyMetadata \
  --filter "spec.importer_data.package_version_uuid==<UUID> and spec.dependency_data.direct==true"
```

Return a count of findings associated with the default branch for a given project.

```
endorctl api list \
  --resource Finding \
  --filter "context.type==CONTEXT_TYPE_MAIN and spec.project_uuid==<project-uuid>" \
  --count
```

Return a count of unique vulnerabilities found in non-test dependencies where there is an upstream patch available and the function associated with the vulnerability is reachable in the context of the application for a given project.

```
endorctl api list \
  --resource Finding \
  --filter "context.type==CONTEXT_TYPE_MAIN and spec.project_uuid==<project-uuid> and spec.finding_categories contains [FINDING_CATEGORY_VULNERABILITY] and spec.finding_tags contains [FINDING_TAGS_NORMAL] and spec.finding_tags contains [FINDING_TAGS_REACHABLE_FUNCTION] and spec.finding_tags contains [FINDING_TAGS_FIX_AVAILABLE]" \
  --group-aggregation-paths "spec.finding_metadata.vulnerability.meta.name"
```

Return the count of the number of scans run on the default branch since a given point in time.

```
endorctl api list \
  --resource ScanResult \
  --filter "context.id==default and meta.create_time >= date(2023-11-14)" \
  --count
```

See [Use cases](../../../rest-api/using-the-rest-api/use-cases/) for more examples.

## endorctl api update

```
endorctl api update -r [resource] [flags]
```

### endorctl api update interactive mode

* Use `--interactive` or `-i` to update an object with an interactive code editor.
  + Define your editor using `export EDITOR=<editor>` where the editor is defined as the command used to edit files. For example, `export EDITOR=vi` allows you to edit in vi and `export EDITOR=code` opens the file with the code command in VS Code.
  + Specify which fields you want to update using the `--field-mask` parameter. If this is not set, endorctl will try to update all fields.

### endorctl api update examples

To interactively update a project with the UUID 6549886f0dd828140b4a477b.

```
endorctl api update -r Project -i --uuid 6549886f0dd828140b4a477b --field-mask meta.tags
```

To add a tag “CrownJewel” to a project named <https://github.com/endorlabs/github-action> use the following command.

```
endorctl api update -r Project \
  --name https://github.com/endorlabs/github-action \
  --data "{ \"meta\": {\"tags\": [ \"CrownJewel\" ] }}" \
  --field-mask 'meta.tags'
```

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

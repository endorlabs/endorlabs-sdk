---
url: https://docs.endorlabs.com/rest-api/using-the-rest-api/filters/
title: Filters | Endor Labs Docs
downloaded: 2026-01-26 10:07:27
---

Filters | Endor Labs Docs



* Type to search...

[Print entire section](/rest-api/using-the-rest-api/filters/_print.html)



# Filters

Learn how to use filters with the Endor Labs REST API.

Filters allow you to specify a subset of objects to be returned by a request, for example:

* endorctl
* curl
* HTTP

```
endorctl api list --resource Finding \
  --filter "meta.name==dependency_with_critical_vulnerabilities" \
  --count
```

```
curl --get \
  --header "Authorization: Bearer $ENDOR_TOKEN" \
  --data-urlencode "list_parameters.filter=meta.name==dependency_with_critical_vulnerabilities" \
  --data-urlencode "list_parameters.count=true" \
  https://api.endorlabs.com/v1/namespaces/$ENDOR_NAMESPACE/findings
```

```
@baseUrl = https://api.endorlabs.com
@token = <insert-access-token>
@namespace = <insert-namespace>

###
GET {{baseUrl}}/v1/namespaces/{{namespace}}/findings?list_parameters.filter=meta.name==dependency_with_critical_vulnerabilities&list_parameters.count=true HTTP/1.1
Authorization: Bearer {{token}}
```

## Keys

A filter key is used to specify the field of the object to match against using a dot-delimited path. For example, given an object:

```
{
  "uuid": "63ef202d090b62ecf3f6655b",
  "meta": {
    "name": "Example Object",
    "tags": ["dev"]
  },
  "spec": {
    "dependencies": [
      {
        "name": "mvn://org.slf4j:slf4j-api@2.0.0",
      },
      {
        "name": "mvn://ch.qos.logback:logback-access@1.3.0",
      }
    ],
    "version": {
      "ref": "v1.6.333",
      "timestamp": "2024-05-31TT21:04:55.799Z"
    }
  }
}
```

* `uuid` specifies the root field with the value `"63ef202d090b62ecf3f6655b"`
* `meta.name` specifies the nested field with the value `"Example Object"`
* `meta.tags` specifies the nested list field containing the values `["dev"]`
* `spec.dependencies.name` specifies the nested fields within the list with the values: `"mvn://org.slf4j:slf4j-api@2.0.0"` and `"mvn://ch.qos.logback:logback-access@1.3.0"`
* `spec.version.ref` specifies the nested field with the value `"v1.6.333"`

For more information, see [Data model](../data-model/).

## Operators

The following filter operators are supported.

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

### Contains

Use `contains` or `not contains` to filter on the content of a list field. Multiple values are treated as an OR operation, for example:

* To get all findings for vulnerabilities that have a fix available OR are in a reachable function use:

  `spec.finding_tags contains [FINDING_TAGS_FIX_AVAILABLE, FINDING_TAGS_REACHABLE_FUNCTION]`
* To get all findings for vulnerabilities that have a fix available AND are in a reachable function use:

  `spec.finding_tags contains [FINDING_TAGS_FIX_AVAILABLE] and spec.finding_tags contains [FINDING_TAGS_REACHABLE_FUNCTION]`
* To get all projects that do not have the meta tags “sanity” or “test” use:

  `meta.tags not contains [sanity, test]`

### In

Use `in` or `not in` to filter on the value of a field against one or more given values. Multiple values are treated as an OR operation, for example:

* To get all findings with a “Critical” or “High” severity level use:

  `spec.finding_level in [FINDING_LEVEL_CRITICAL, FINDING_LEVEL_HIGH]`
* To get all findings that are not from the “Maven” or “npm” ecosystems use:

  `spec.ecosystem not in [ECOSYSTEM_MAVEN, ECOSYSTEM_NPM]`

### Matches

Use `matches` to filter on a regex pattern. Due to the nature of regex evaluation, this is much slower than using for example `==` or `!=`. Also due to the nature of regex evaluation, `not matches` is not supported.

### Exists

If a field does not exist then it can’t be equal to anything, so we use `exists` and `not exists` instead of `!= null` or `== null`. This also covers `{}`, `[]`, etc.

## Values

A filter value is used in combination with the operator to match against the values at the specified field.

Use double quotes to escape string or regex values in a filter, for example:

* `uuid in ["64a3b8326dda5fb62bfcceea", "658323c91aa208f231cc7eff", "658323c963ca516ef02d1b02"]`
* `meta.name matches "validation bypass"`

**Note**

Filters are case-sensitive by default.

To filter with case-insentive values a regex modifier may be used, for example:

* `meta.description matches "(?i)django"`

### Date/Time Values

Use `date` to encode date values in a filter, for example:

* To filter for objects created after a given date, use a date value with the format `YYYY-MM-DD`:

  `meta.update_time >= date(2024-05-01)`
* To filter for objects created between specific times, use a timestamp values with the [RFC 3339](https://www.rfc-editor.org/rfc/rfc3339) format:

  `meta.create_time >= date(2024-05-01T13:30:00.000Z) and meta.create_time < date(2024-05-01T23:30:00.000Z)`

Use `now` to encode relative date values in a filter by a given duration offset, for example:

* To filter for objects created in the last 15 minutes, use:

  `meta.create_time >= now(-12h)`
* To filter for objects created in the last 72 hours, use:

  `meta.create_time >= now(-72h)`

## Combinations

Use `and` or `or` to combine multiple filters, for example:

* `spec.finding_categories contains [FINDING_CATEGORY_VULNERABILITY] and meta.create_time >= date(2024-05-31)`
* `meta.name==archived_source_code_repo or meta.name==outdated_release`

### Nesting filters

Multiple filters may also be nested together into a single filter with the use of parentheses `()`, for example:

* `(spec.finding_categories contains [FINDING_CATEGORY_VULNERABILITY] and spec.level==FINDING_LEVEL_CRITICAL) or (spec.finding_categories contains [FINDING_CATEGORY_SECRETS] and spec.level in [FINDING_LEVEL_CRITICAL, FINDING_LEVEL_HIGH])`

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

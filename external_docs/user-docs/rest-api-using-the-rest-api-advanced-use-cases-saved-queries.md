---
url: https://docs.endorlabs.com/rest-api/using-the-rest-api/advanced-use-cases/saved-queries/
title: Using saved queries | Endor Labs Docs
downloaded: 2026-01-16 09:48:53
---

Using saved queries | Endor Labs Docs



* Type to search...

[Print entire section](/rest-api/using-the-rest-api/advanced-use-cases/saved-queries/_print.html)



# Using saved queries

Learn how to use saved queries for interacting with the Endor Labs REST API.

The Endor Labs REST API provides the [Query Service](https://docs.endorlabs.com/api/#tag/QueryService) for flexible requests for resources. The Endor Labs REST API also provides the ability to save and manage queries for your own use cases through the [Saved Query Service](https://docs.endorlabs.com/api/#tag/SavedQueryService).

See [Using the Query Service](../query-service/) for examples on using the Query Service to specify and request resources from the Endor Labs REST API.

## Creating a saved query

To create a saved query, a Query object specifying the request is embedded in a SavedQuery object.

* endorctl
* curl
* HTTP

```
saved_query_data=$(cat << EOF
{
  "meta": {
    "name": "Saved Query for Recent Vulnerabilities"
  },
  "spec": {
    "query": {
      "meta": {
        "name": "Query for Recent Vulnerabilities"
      },
      "spec": {
        "query_spec": {
          "kind": "Finding",
          "list_parameters": {
            "filter": "meta.create_time > now(-24h) and spec.finding_categories contains [FINDING_CATEGORY_VULNERABILITY]",
            "mask": "uuid,meta.create_time,meta.update_time,meta.description,spec.level"
          }
        }
      },
      "tenant_meta": {
        "namespace": "$ENDOR_NAMESPACE"
      }
    }
  }
}
EOF
)

endorctl api create --resource SavedQuery \
  --data "$saved_query_data"
```

```
saved_query_data=$(cat << EOF
{
  "meta": {
    "name": "Saved Query for Recent Vulnerabilities"
  },
  "spec": {
    "query": {
      "meta": {
        "name": "Query for Recent Vulnerabilities"
      },
      "spec": {
        "query_spec": {
          "kind": "Finding",
          "list_parameters": {
            "filter": "meta.create_time > now(-24h) and spec.finding_categories contains [FINDING_CATEGORY_VULNERABILITY]",
            "mask": "uuid,meta.create_time,meta.update_time,meta.description,spec.level"
          }
        }
      },
      "tenant_meta": {
        "namespace": "$ENDOR_NAMESPACE"
      }
    }
  },
  "tenant_meta": {
    "namespace": "$ENDOR_NAMESPACE"
  }
}
EOF
)

curl "https://api.endorlabs.com/v1/namespaces/$ENDOR_NAMESPACE/saved-queries" \
  --header "Authorization: Bearer $ENDOR_TOKEN" \
  --request POST \
  --data "$saved_query_data"
```

```
@baseUrl = https://api.endorlabs.com
@token = <insert-access-token>
@namespace = <insert-namespace>

###
POST {{baseUrl}}/v1/namespaces/{{namespace}}/saved-queries HTTP/1.1
Authorization: Bearer {{token}}

{
  "meta": {
    "name": "Saved Query for Recent Vulnerabilities"
  },
  "spec": {
    "query": {
      "meta": {
        "name": "Query for Recent Vulnerabilities"
      },
      "spec": {
        "query_spec": {
          "kind": "Finding",
          "list_parameters": {
            "filter": "meta.create_time > now(-24h) and spec.finding_categories contains [FINDING_CATEGORY_VULNERABILITY]",
            "mask": "uuid,meta.create_time,meta.update_time,meta.description,spec.level"
          }
        }
      },
      "tenant_meta": {
        "namespace": "{{namespace}}"
      }
    }
  },
  "tenant_meta": {
    "namespace": "{{namespace}}"
  }
}
```

## Updating a saved query

The following example updates the Query specified in the SavedQuery to add additional [list parameters](../../getting-started/#list-parameters).

* endorctl
* curl
* HTTP

```
saved_query_uuid="<insert-uuid>"
saved_query_data=$(cat << EOF
{
  "spec": {
    "query": {
      "spec": {
        "query_spec": {
          "kind": "Finding",
          "list_parameters": {
            "filter": "meta.create_time > now(-24h) and spec.finding_categories contains [FINDING_CATEGORY_VULNERABILITY]",
            "mask": "uuid,meta.create_time,meta.update_time,meta.description,spec.level",
            "page_size": 10,
            "sort": {
              "order": "SORT_ENTRY_ORDER_DESC",
              "path": "meta.create_time"
            }
          }
        }
      }
    }
  }
}
EOF
)

endorctl api update --resource SavedQuery \
  --uuid "$saved_query_uuid" \
  --field-mask "spec.query.spec.query_spec" \
  --data "$saved_query_data"
```

```
saved_query_uuid="<insert-uuid>"
saved_query_data=$(cat << EOF
{
  "request": {
    "update_mask": "spec.query.spec.query_spec"
  },
  "object": {
    "uuid": "$saved_query_uuid",
    "spec": {
      "query": {
        "spec": {
          "query_spec": {
            "kind": "Finding",
            "list_parameters": {
              "filter": "meta.create_time > now(-24h) and spec.finding_categories contains [FINDING_CATEGORY_VULNERABILITY]",
              "mask": "uuid,meta.create_time,meta.update_time,meta.description,spec.level",
              "page_size": 10,
              "sort": {
                "order": "SORT_ENTRY_ORDER_DESC",
                "path": "meta.create_time"
              }
            }
          }
        }
      }
    }
  }
}
EOF
)

curl "https://api.endorlabs.com/v1/namespaces/$ENDOR_NAMESPACE/saved-queries" \
  --header "Authorization: Bearer $ENDOR_TOKEN" \
  --request PATCH \
  --data "$saved_query_data"
```

```
@baseUrl = https://api.endorlabs.com
@token = <insert-access-token>
@namespace = <insert-namespace>
@uuid = <insert-uuid>

###
PATCH {{baseUrl}}/v1/namespaces/{{namespace}}/saved-queries HTTP/1.1
Authorization: Bearer {{token}}

{
  "request": {
    "update_mask": "spec.query.spec.query_spec"
  },
  "object": {
    "uuid": "{{uuid}}",
    "spec": {
      "query": {
        "spec": {
          "query_spec": {
            "kind": "Finding",
            "list_parameters": {
              "filter": "meta.create_time > now(-24h) and spec.finding_categories contains [FINDING_CATEGORY_VULNERABILITY]",
              "mask": "uuid,meta.create_time,meta.update_time,meta.description,spec.level",
              "page_size": 10,
              "sort": {
                "order": "SORT_ENTRY_ORDER_DESC",
                "path": "meta.create_time"
              }
            }
          }
        }
      }
    }
  }
}
```

See also [interactive mode](../../../../endorctl/commands/api/#endorctl-api-update-interactive-mode) for managing updates to a SavedQuery with `endorctl api update`:

```
endorctl api update --interactive --resource SavedQuery \
  --name "Saved Query for Recent Vulnerabilities"
```

## Evaluating saved queries

After a Saved Query has been created, the request specified by the Query in the SavedQuery may be evaluated on demand.

* endorctl
* curl
* HTTP

```
endorctl api get --resource SavedQuery --uuid <insert-uuid>
```

```
base_url="https://api.endorlabs.com"
uuid="<insert-uuid>"

curl "$base_url/v1/namespaces/$ENDOR_NAMESPACE/saved-queries/$uuid/evaluate" \
  --header "Authorization: Bearer $ENDOR_TOKEN"
```

```
@baseUrl = https://api.endorlabs.com
@token = <insert-access-token>
@namespace = <insert-namespace>
@uuid = <insert-uuid>

###
GET {{baseUrl}}/v1/namespaces/{{namespace}}/saved-queries/{{uuid}}/evaluate HTTP/1.1
Authorization: Bearer {{token}}
```

The resulting data from evaluating the saved query will be returned in the response in a nested field under the Query specification. The `jq` command may be used to extract the nested data.

For the example queries given above, the following command will evaluate the given saved query, and extract the list of Finding objects from the Query response:

```
endorctl api get --resource SavedQuery --uuid <insert-uuid> \
  | jq '.spec.query.spec.query_response.list.objects[]'
```

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

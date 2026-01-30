---
url: https://docs.endorlabs.com/rest-api/using-the-rest-api/advanced-use-cases/query-service/
title: Using the query service | Endor Labs Docs
downloaded: 2026-01-29 22:21:00
---

Using the query service | Endor Labs Docs



* Type to search...

[Print entire section](/rest-api/using-the-rest-api/advanced-use-cases/query-service/_print.html)



# Using the query service

Learn how to use the Query Service for advanced use cases with the Endor Labs REST API.

In addition to REST API endpoints for individual [Resource Kinds](../../data-model/resource-kinds), the Endor Labs REST API exposes a generic graph API capability through the [Query Service](https://docs.endorlabs.com/api/#tag/QueryService) endpoint. This Query Service may be used to retrieve resources and their related resources in a single call.

Requests for resources through the Query Service are sent with a Query that specifies a [Resource Kind](../../data-model/resource-kinds) and optional [list parameters](../../getting-started/#list-parameters) to control the data returned from the request for that resource. The Query may also specify nested references, connecting related [Resource Kinds](../../data-model/resource-kinds/#introduction), and returning all corresponding data in the response.

## List projects with package version counts

The following Query returns the number of package versions in the default branch of each project.

1. Request a list of projects, but only return the `uuid`, `meta.name` and `processing_status` fields for each project.
2. Connect the project `uuid` to the corresponding child package version `spec.project_uuid` field.
3. Set additional parameters to filter to only resources from the project’s default branch, and to return the count of resources.©

* endorctl
* curl
* HTTP

```
endorctl api create --resource Query \
  --data '{
    "meta": {
      "name": "Projects with Package Version Counts"
    },
    "spec": {
      "query_spec": {
        "kind": "Project",
        "list_parameters": {
          "mask": "uuid,meta.name,processing_status"
        },
        "references": [
          {
            "connect_from": "uuid",
            "connect_to": "spec.project_uuid",
            "query_spec": {
              "kind": "PackageVersion",
              "list_parameters": {
                "filter": "context.type==CONTEXT_TYPE_MAIN",
                "count": true
              }
            }
          }
        ]
      }
    }
  }'
```

```
query_data=$(cat << EOF
{
  "meta": {
    "name": "Projects with Package Version Counts"
  },
  "spec": {
    "query_spec": {
      "kind": "Project",
      "list_parameters": {
        "mask": "uuid,meta.name,processing_status"
      },
      "references": [
        {
          "connect_from": "uuid",
          "connect_to": "spec.project_uuid",
          "query_spec": {
            "kind": "PackageVersion",
            "list_parameters": {
              "filter": "context.type==CONTEXT_TYPE_MAIN",
              "count": true
            }
          }
        }
      ]
    }
  },
  "tenant_meta": {
    "namespace": "$ENDOR_NAMESPACE"
  }
}
EOF
)

curl "https://api.endorlabs.com/v1/namespaces/$ENDOR_NAMESPACE/queries" \
  --header "Authorization: Bearer $ENDOR_TOKEN" \
  --request POST \
  --data "$query_data"
```

```
@baseUrl = https://api.endorlabs.com
@token = <insert-access-token>
@namespace = <insert-namespace>

###
POST {{baseUrl}}/v1/namespaces/{{namespace}}/queries HTTP/1.1
Authorization: Bearer {{token}}

{
  "meta": {
    "name": "Projects with Package Version Counts"
  },
  "spec": {
    "query_spec": {
      "kind": "Project",
      "list_parameters": {
        "mask": "uuid,meta.name,processing_status"
      },
      "references": [
        {
          "connect_from": "uuid",
          "connect_to": "spec.project_uuid",
          "query_spec": {
            "kind": "PackageVersion",
            "list_parameters": {
              "filter": "context.type==CONTEXT_TYPE_MAIN",
              "count": true
            }
          }
        }
      ]
    }
  },
  "tenant_meta": {
    "namespace": "{{namespace}}"
  }
}
```

The response for the example above includes the query request that was sent, along with the list response data added under the `spec.query_response` field.

For each project in the list response, response data for each reference is added under the `meta.references` field.

```
{
  "meta": {
    "name": "Projects with Package Version Counts"
  },
  "spec": {
    "query_spec": {
      "kind": "Project",
      "list_parameters": {
        "mask": "uuid,meta.name,processing_status"
      }
    },
    "query_response": {
      "@type": "type.googleapis.com/internal.endor.ai.endor.v1.ListProjectsResponse",
      "list": {
        "objects": [
          {
            "meta": {
              "name": "https://github.com/example/app.git",
              "references": {
                "PackageVersion": {
                  "@type": "type.googleapis.com/internal.endor.ai.endor.v1.ListPackageVersionsResponse",
                  "count_response": {
                    "count": 12
                  }
                }
              }
            },
            "processing_status": {
              "analytic_time": "2023-10-28T03:41:40.824366382Z",
              "disable_automated_scan": false,
              "scan_state": "SCAN_STATE_IDLE",
              "scan_time": "2024-06-03T17:43:33.994191285Z"
            },
            "uuid": "633cbce48c4eb448a44d717b"
          },
          {
            "meta": {
              "name": "https://github.com/example/go-uuid.git",
              "references": {
                "PackageVersion": {
                  "@type": "type.googleapis.com/internal.endor.ai.endor.v1.ListPackageVersionsResponse",
                  "count_response": {
                    "count": 8
                  }
                }
              }
            },
            "processing_status": {
              "analytic_time": "2023-06-21T02:06:43.081498151Z",
              "disable_automated_scan": false,
              "scan_state": "SCAN_STATE_IDLE",
              "scan_time": "2024-06-03T17:43:47.098976874Z"
            },
            "uuid": "633cbce48c4eb448a44d717e"
          },
          {
            "meta": {
              "name": "https://github.com/example/go-lru.git",
              "references": {
                "PackageVersion": {
                  "@type": "type.googleapis.com/internal.endor.ai.endor.v1.ListPackageVersionsResponse",
                  "count_response": {
                    "count": 28
                  }
                }
              }
            },
            "processing_status": {
              "analytic_time": "2023-06-21T02:08:44.727640782Z",
              "disable_automated_scan": false,
              "scan_state": "SCAN_STATE_IDLE",
              "scan_time": "2024-06-03T17:43:52.028934453Z"
            },
            "uuid": "633cbce48c4eb448a44d7181"
          }
        ],
        "response": {
          "next_page_token": null
        }
      }
    }
  }
}
```

## List projects, with repository versions and CI/CD tool metrics

The following query requests a list of projects, with a reference for the related RepositoryVersion resources for the default branch, and the corresponding CI/CD tool Metric resources.

1. Request a list of projects, but only return the `uuid` and `meta.name` fields for each project.
2. Connect the project `uuid` to the corresponding child RepositoryVersion `meta.parent_uuid` field.
3. Set additional parameters to filter to only resources from the project’s default branch, and an additional nested reference for Metric objects related to the RepositoryVersions, with a filter to return only Metrics for the CI/CD tools.

* endorctl
* curl
* HTTP

```
endorctl api create --resource Query \
  --data '{
    "meta": {
      "name": "Projects with RepositoryVersions and CI/CD Tool Metrics"
    },
    "spec": {
      "query_spec": {
        "kind": "Project",
        "list_parameters": {
          "mask": "uuid,meta.name"
        },
        "references": [
          {
            "connect_from": "uuid",
            "connect_to": "meta.parent_uuid",
            "query_spec": {
              "kind": "RepositoryVersion",
              "list_parameters": {
                "filter": "context.type==CONTEXT_TYPE_MAIN",
                "mask": "uuid,meta.name,scan_object"
              },
              "references": [
                {
                  "connect_from": "uuid",
                  "connect_to": "meta.parent_uuid",
                  "query_spec": {
                    "kind": "Metric",
                    "list_parameters": {
                      "filter": "spec.analytic==\"version_cicd_tools\""
                    }
                  }
                }
              ]
            }
          }
        ]
      }
    }
  }'
```

```
query_data=$(cat << EOF
{
  "meta": {
    "name": "Projects with RepositoryVersions and CI/CD Tool Metrics"
  },
  "spec": {
    "query_spec": {
      "kind": "Project",
      "list_parameters": {
        "mask": "uuid,meta.name"
      },
      "references": [
        {
          "connect_from": "uuid",
          "connect_to": "meta.parent_uuid",
          "query_spec": {
            "kind": "RepositoryVersion",
            "list_parameters": {
              "filter": "context.type==CONTEXT_TYPE_MAIN",
              "mask": "uuid,meta.name,scan_object"
            },
            "references": [
              {
                "connect_from": "uuid",
                "connect_to": "meta.parent_uuid",
                "query_spec": {
                  "kind": "Metric",
                  "list_parameters": {
                    "filter": "spec.analytic==\"version_cicd_tools\""
                  }
                }
              }
            ]
          }
        }
      ]
    }
  },
  "tenant_meta": {
    "namespace": "$ENDOR_NAMESPACE"
  }
}
EOF
)

curl "https://api.endorlabs.com/v1/namespaces/$ENDOR_NAMESPACE/queries" \
  --header "Authorization: Bearer $ENDOR_TOKEN" \
  --request POST \
  --data "$query_data"
```

```
@baseUrl = https://api.endorlabs.com
@token = <insert-access-token>
@namespace = <insert-namespace>

###
POST {{baseUrl}}/v1/namespaces/{{namespace}}/queries HTTP/1.1
Authorization: Bearer {{token}}

{
  "meta": {
    "name": "Projects with RepositoryVersions and CI/CD Tool Metrics"
  },
  "spec": {
    "query_spec": {
      "kind": "Project",
      "list_parameters": {
        "mask": "uuid,meta.name"
      },
      "references": [
        {
          "connect_from": "uuid",
          "connect_to": "meta.parent_uuid",
          "query_spec": {
            "kind": "RepositoryVersion",
            "list_parameters": {
              "filter": "context.type==CONTEXT_TYPE_MAIN",
              "mask": "uuid,meta.name,scan_object"
            },
            "references": [
              {
                "connect_from": "uuid",
                "connect_to": "meta.parent_uuid",
                "query_spec": {
                  "kind": "Metric",
                  "list_parameters": {
                    "filter": "spec.analytic==\"version_cicd_tools\""
                  }
                }
              }
            ]
          }
        }
      ]
    }
  },
  "tenant_meta": {
    "namespace": "{{namespace}}"
  }
}
```

The response for the example above includes then related repository versions and metrics as nested references under their parent resources.

```
{
  "meta": {
    "name": "Projects with RepositoryVersions and CI/CD Tool Metrics"
  },
  "spec": {
    "query_response": {
      "@type": "type.googleapis.com/internal.endor.ai.endor.v1.ListProjectsResponse",
      "list": {
        "objects": [
          {
            "meta": {
              "name": "https://github.com/OWASP-Benchmark/BenchmarkJava.git",
              "references": {
                "RepositoryVersion": {
                  "@type": "type.googleapis.com/internal.endor.ai.endor.v1.ListRepositoryVersionsResponse",
                  "list": {
                    "objects": [
                      {
                        "meta": {
                          "name": "master",
                          "references": {
                            "Metric": {
                              "@type": "type.googleapis.com/internal.endor.ai.endor.v1.ListMetricsResponse",
                              "list": {
                                "objects": [
                                  {
                                    "spec": {
                                      "analytic": "version_cicd_tools",
                                      "metric_values": {
                                        "CiCdTools": {
                                          "category": "CiCdTools",
                                          "ci_cd_tools": {
                                            "tools": [
                                              // additional content from response not shown here
                                            ]
                                          }
                                        }
                                      }
                                    },
                                    "uuid": "65b0287557d245d7a840220d"
                                  }
                                ],
                                "response": {}
                              }
                            }
                          }
                        },
                        "scan_object": {
                          "scan_time": "2024-04-15T02:17:56.541640347Z",
                          "status": "STATUS_SCANNED"
                        },
                        "uuid": "65b02837f82e0aeecbf468df"
                      }
                    ],
                    "response": {}
                  }
                }
              }
            },
            "uuid": "65b028374ab228de2903786e"
          }
        ],
        "response": {}
      }
    },

    // additional content from response not shown here
}
```

## Find a project and related Finding counts

The following query example requests the projects matching the given filter, with multiple references specified for the counts of related finding resources for the default branch.

> Note: When using multiple references of the same resource kind, the field `return_as` is provided as the key to be used in the references of the response.

* endorctl
* curl
* HTTP

```
endorctl api create --resource Query \
  --data '{
    "meta": {
      "name": "Project with Finding counts by category"
    },
    "spec": {
      "query_spec": {
        "kind": "Project",
        "list_parameters": {
          "filter": "meta.name matches \"acme-monorepo\"",
          "mask": "uuid,meta.name"
        },
        "references": [
          {
            "connect_from": "uuid",
            "connect_to": "spec.project_uuid",
            "query_spec": {
              "return_as": "VulnerabilityFindingsCount",
              "kind": "Finding",
              "list_parameters": {
                "count": true,
                "filter": "context.type==CONTEXT_TYPE_MAIN and spec.finding_categories contains [FINDING_CATEGORY_VULNERABILITY]"
              }
            }
          },
          {
            "connect_from": "uuid",
            "connect_to": "spec.project_uuid",
            "query_spec": {
              "return_as": "SecretsFindingsCount",
              "kind": "Finding",
              "list_parameters": {
                "count": true,
                "filter": "context.type==CONTEXT_TYPE_MAIN and spec.finding_categories contains [FINDING_CATEGORY_SECRETS]"
              }
            }
          },
          {
            "connect_from": "uuid",
            "connect_to": "spec.project_uuid",
            "query_spec": {
              "return_as": "MalwareFindingsCount",
              "kind": "Finding",
              "list_parameters": {
                "count": true,
                "filter": "context.type==CONTEXT_TYPE_MAIN and spec.finding_categories contains [FINDING_CATEGORY_MALWARE]"
              }
            }
          }
        ]
      }
    }
  }'
```

```
query_data=$(cat << EOF
{
  "meta": {
    "name": "Project with Finding counts by category"
  },
  "spec": {
    "query_spec": {
      "kind": "Project",
      "list_parameters": {
        "filter": "meta.name matches \"acme-monorepo\"",
        "mask": "uuid,meta.name"
      },
      "references": [
        {
          "connect_from": "uuid",
          "connect_to": "spec.project_uuid",
          "query_spec": {
            "return_as": "VulnerabilityFindingsCount",
            "kind": "Finding",
            "list_parameters": {
              "count": true,
              "filter": "context.type==CONTEXT_TYPE_MAIN and spec.finding_categories contains [FINDING_CATEGORY_VULNERABILITY]"
            }
          }
        },
        {
          "connect_from": "uuid",
          "connect_to": "spec.project_uuid",
          "query_spec": {
            "return_as": "SecretsFindingsCount",
            "kind": "Finding",
            "list_parameters": {
              "count": true,
              "filter": "context.type==CONTEXT_TYPE_MAIN and spec.finding_categories contains [FINDING_CATEGORY_SECRETS]"
            }
          }
        },
        {
          "connect_from": "uuid",
          "connect_to": "spec.project_uuid",
          "query_spec": {
            "return_as": "MalwareFindingsCount",
            "kind": "Finding",
            "list_parameters": {
              "count": true,
              "filter": "context.type==CONTEXT_TYPE_MAIN and spec.finding_categories contains [FINDING_CATEGORY_MALWARE]"
            }
          }
        }
      ]
    }
  },
  "tenant_meta": {
    "namespace": "$ENDOR_NAMESPACE"
  }
}
EOF
)

curl "https://api.endorlabs.com/v1/namespaces/$ENDOR_NAMESPACE/queries" \
  --header "Authorization: Bearer $ENDOR_TOKEN" \
  --request POST \
  --data "$query_data"
```

```
@baseUrl = https://api.endorlabs.com
@token = <insert-access-token>
@namespace = <insert-namespace>

###
POST {{baseUrl}}/v1/namespaces/{{namespace}}/queries HTTP/1.1
Authorization: Bearer {{token}}

{
  "meta": {
    "name": "Project with Finding counts by category"
  },
  "spec": {
    "query_spec": {
      "kind": "Project",
      "list_parameters": {
        "filter": "meta.name matches \"acme-monorepo\"",
        "mask": "uuid,meta.name"
      },
      "references": [
        {
          "connect_from": "uuid",
          "connect_to": "spec.project_uuid",
          "query_spec": {
            "return_as": "VulnerabilityFindingsCount",
            "kind": "Finding",
            "list_parameters": {
              "count": true,
              "filter": "context.type==CONTEXT_TYPE_MAIN and spec.finding_categories contains [FINDING_CATEGORY_VULNERABILITY]"
            }
          }
        },
        {
          "connect_from": "uuid",
          "connect_to": "spec.project_uuid",
          "query_spec": {
            "return_as": "SecretsFindingsCount",
            "kind": "Finding",
            "list_parameters": {
              "count": true,
              "filter": "context.type==CONTEXT_TYPE_MAIN and spec.finding_categories contains [FINDING_CATEGORY_SECRETS]"
            }
          }
        },
        {
          "connect_from": "uuid",
          "connect_to": "spec.project_uuid",
          "query_spec": {
            "return_as": "MalwareFindingsCount",
            "kind": "Finding",
            "list_parameters": {
              "count": true,
              "filter": "context.type==CONTEXT_TYPE_MAIN and spec.finding_categories contains [FINDING_CATEGORY_MALWARE]"
            }
          }
        }
      ]
    }
  },
  "tenant_meta": {
    "namespace": "{{namespace}}"
  }
}
```

The response for the above example includes the Finding counts as references on the project list response, using the values provided with `return_as` for the reference keys.

```
{
  "meta": {
    "name": "Project with Finding counts by category"
  },
  "spec": {
    "query_response": {
      "@type": "type.googleapis.com/internal.endor.ai.endor.v1.ListProjectsResponse",
      "list": {
        "objects": [
          {
            "meta": {
              "name": "https://github.com/example/acme-monorepo.git",
              "references": {
                "MalwareFindingsCount": {
                  "@type": "type.googleapis.com/internal.endor.ai.endor.v1.ListFindingsResponse",
                  "count_response": {
                    "count": 1
                  }
                },
                "SecretsFindingsCount": {
                  "@type": "type.googleapis.com/internal.endor.ai.endor.v1.ListFindingsResponse",
                  "count_response": {
                    "count": 8
                  }
                },
                "VulnerabilityFindingsCount": {
                  "@type": "type.googleapis.com/internal.endor.ai.endor.v1.ListFindingsResponse",
                  "count_response": {
                    "count": 74
                  }
                }
              }
            },
            "uuid": "65bbde52d70a7f64c70de4d6"
          }
        ],
        "response": {}
      }
    },

    // additional content from response not shown here
}
```

## Pagination in Query Service endpoint

The `page_size` field allows you to control the number of elements returned. By default, this value is 100, with a maximum of 500. A paginated response includes a value for the field, `next_page_token`. You can use this value to fetch additional pages of results.

For example, the following query requests for vulnerability findings.

```
endorctl api create --resource Query \
  --data '{
  "tenant_meta": {
    "namespace": "doe"
  },
  "spec": {
    "query_spec": {
      "kind": "Finding",
      "list_parameters": {
        "page_size": 50,
        "filter": "meta.name == \'vulnerability\'"
      }
    }
  }
}'
```

The response to the request contains `next_page_token`.

```
{
  "spec": {
    "query_response": {
      "@type": "type.googleapis.com/internal.endor.ai.endor.v1.ListFindingsResponse",
      "list": {
        "objects": [
          {
            "meta": {
              "name": "vulnerability",
              "description": "Example vulnerability finding"
            },
            "spec": {
              "level": "FINDING_LEVEL_CRITICAL",
              "finding_categories": ["FINDING_CATEGORY_VULNERABILITY"]
            }
          }
          // Additional findings up to page_size of 50
        ],
        "response": {
          "next_page_token": 50,
          "next_page_id": "unique-id-for-next-page"
        }
      }
    }
  }
}
```

Send the next request with the `next_page_token` to fetch the next set of results.

```
endorctl api create --resource Query \
  --data '{
  "tenant_meta": {
    "namespace": "doe"
  },
  "spec": {
    "query_spec": {
      "kind": "Finding",
      "list_parameters": {
        "page_size": 50,
        "page_token": 50,
        "filter": "meta.name == \'vulnerability\'"
      }
    }
  }
}'
```

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

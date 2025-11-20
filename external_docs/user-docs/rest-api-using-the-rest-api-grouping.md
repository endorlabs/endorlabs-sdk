---
url: https://docs.endorlabs.com/rest-api/using-the-rest-api/grouping/
title: Grouping | Endor Labs Docs
downloaded: 2025-11-20 11:51:23
---

Grouping | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/rest-api/using-the-rest-api/grouping/_print.html)



# Grouping

Learn how to group results from the Endor Labs REST API.

There are many scenarios where it is useful to group the objects returned by the Endor Labs REST API in different ways.
Like [filter keys](../filters/#keys), a group-aggregation-paths key is used to specify the field, or fields, by which to group the objects, using a dot-delimited path.
For example, the following request returns the count of findings for each severity level:

* endorctl
* curl
* HTTP

```
endorctl api list --resource Finding \
  --filter "spec.finding_categories contains FINDING_CATEGORY_VULNERABILITY" \
  --group-aggregation-paths "spec.level" \
  --timeout 60s
```

```
curl --get \
  --header "Authorization: Bearer $ENDOR_TOKEN" \
  --header "Request-Timeout: 60" \
  --data-urlencode "list_parameters.filter=spec.finding_categories contains FINDING_CATEGORY_VULNERABILITY" \
  --data-urlencode "list_parameters.group.aggregation_paths=spec.level" \
  https://api.endorlabs.com/v1/namespaces/$ENDOR_NAMESPACE/findings \
  | jq '.'
```

```
@baseUrl = https://api.endorlabs.com
@token = <insert-access-token>
@namespace = <insert-namespace>

###
GET {{baseUrl}}/v1/namespaces/{{namespace}}/findings?list_parameters.filter=spec.finding_categories contains FINDING_CATEGORY_VULNERABILITY&list_parameters.group.aggregation_paths=spec.level HTTP/1.1
Content-type: application/json
Authorization: Bearer {{token}}
Request-Timeout: 60
```

```
{
  "group_response": {
    "groups": {
      "[{\"key\":\"spec.level\",\"value\":\"FINDING_LEVEL_CRITICAL\"}]": {
        "aggregation_count": {
          "count": 49
        }
      },
      "[{\"key\":\"spec.level\",\"value\":\"FINDING_LEVEL_HIGH\"}]": {
        "aggregation_count": {
          "count": 166
        }
      },
      "[{\"key\":\"spec.level\",\"value\":\"FINDING_LEVEL_LOW\"}]": {
        "aggregation_count": {
          "count": 31
        }
      },
      "[{\"key\":\"spec.level\",\"value\":\"FINDING_LEVEL_MEDIUM\"}]": {
        "aggregation_count": {
          "count": 202
        }
      }
    }
  }
}
```

## Group by path

The following options are available to group objects based on the value of a field in a given path.

* endorctl
* curl / HTTP

| Option | Description |
| --- | --- |
| `group-aggregation-paths` | Specify one or more fields to group objects by. |
| `group-show-aggregation-uuids` | Get the UUIDs of the objects in each group as specified by `--group-aggregation-paths`. |
| `group-unique-count-paths` | Count the number of unique values, for these fields, in the group. |
| `group-unique-value-paths` | Get the unique values, for these fields, in the group. |

For the complete list of all `endorctl api list` options, see [flags and variables](../../../endorctl/commands/api/#endorctl-api-list-flags-and-variables).

| List Parameter | Description |
| --- | --- |
| `group.aggregation_paths` | Specify one or more fields to group objects by. |
| `group.show_aggregation_uuids` | Get the UUIDs of the objects in each group as specified by `group.aggregation_paths`. |
| `group.unique_count_paths` | Count the number of unique values, for these fields, in the group. |
| `group.unique_value_paths` | Get the unique values, for these fields, in the group. |

For the complete list of all HTTP list parameters, see [list parameters](../getting-started/#list-parameters).

### Group by path example

Here is an example using all options simultaneously to group package versions by call graph [resolution error](../data-model/resource-kinds/#resolution-errors), list the UUIDs of the package versions in each group, return the number of different ecosystems of the package versions in each group, and list the different ecosystems of the package versions in each group:

* endorctl
* curl
* HTTP

```
endorctl api list --resource PackageVersion \
  --filter "spec.resolution_errors.call_graph exists" \
  --group-aggregation-paths "spec.resolution_errors.call_graph.status_error" \
  --group-show-aggregation-uuids \
  --group-unique-count-paths "spec.ecosystem" \
  --group-unique-value-paths "spec.ecosystem" \
  --timeout 60s
```

```
curl --get \
  --header "Authorization: Bearer $ENDOR_TOKEN" \
  --header "Request-Timeout: 60" \
  --data-urlencode "list_parameters.filter=spec.resolution_errors.call_graph exists" \
  --data-urlencode "list_parameters.group.aggregation_paths=spec.resolution_errors.call_graph.status_error" \
  --data-urlencode "list_parameters.group.show_aggregation_uuids=true" \
  --data-urlencode "list_parameters.group.unique_value_paths=spec.ecosystem" \
  --data-urlencode "list_parameters.group.unique_count_paths=spec.ecosystem" \
  https://api.endorlabs.com/v1/namespaces/$ENDOR_NAMESPACE/package-versions \
  | jq '.'
```

```
@baseUrl = https://api.endorlabs.com
@token = <insert-access-token>
@namespace = <insert-namespace>

###
GET {{baseUrl}}/v1/namespaces/{{namespace}}/package-versions?list_parameters.filter=spec.resolution_errors.call_graph exists&list_parameters.group.aggregation_paths=spec.resolution_errors.call_graph.status_error&ist_parameters.group.show_aggregation_uuids=true&list_parameters.group.unique_value_paths=spec.ecosystem&list_parameters.group.unique_count_paths=spec.ecosystem HTTP/1.1
Content-type: application/json
Authorization: Bearer {{token}}
Request-Timeout: 60
```

```
{
  "group_response": {
    "groups": {
      "[{\"key\":\"spec.resolution_errors.call_graph.status_error\",\"value\":\"STATUS_ERROR_CALL_GRAPH\"}]": {
        "aggregation_count": {
          "count": 10
        },
        "aggregation_uuids": [
          "6494c13cdcb266d2af02804f",
          "64ace2dd05228d0041488208",
          "64ace2dc05228d00414881eb",
          "64af3a042efc155e48304bf2",
          "65b86b4a0f460309eac456b5",
          "64ace2dc832ee78dd03d85b0",
          "64c190aa17e6bfc2548f7a48",
          "64af39d2bebf530905411327",
          "64c190a817e6bfc2548f7a19",
          "64cc2b68727cd13ec36860c8"
        ],
        "unique_counts": {
          "spec.ecosystem": {
            "count": 2
          }
        },
        "unique_values": {
          "spec.ecosystem": [
            "ECOSYSTEM_MAVEN",
            "ECOSYSTEM_PYPI"
          ]
        }
      },
      "[{\"key\":\"spec.resolution_errors.call_graph.status_error\",\"value\":\"STATUS_ERROR_INTERNAL\"}]": {
        "aggregation_count": {
          "count": 2
        },
        "aggregation_uuids": [
          "6632e2d6b7765d736fac1865",
          "664ba7986fafc782b3cda1f6"
        ],
        "unique_counts": {
          "spec.ecosystem": {
            "count": 1
          }
        },
        "unique_values": {
          "spec.ecosystem": [
            "ECOSYSTEM_NPM"
          ]
        }
      },
      "[{\"key\":\"spec.resolution_errors.call_graph.status_error\",\"value\":\"STATUS_ERROR_MISSING_ARTIFACT\"}]": {
        "aggregation_count": {
          "count": 23
        },
        "aggregation_uuids": [
          "65c3e90ae2dd352a18b6f852",
          "64b99a3b3d5f8dc732555200",
          "64c190a921d68642091aa015",
          "650a2457204ab859367160a2",
          "650a245780113616f95f770e",
          "65d6840edb5cf8c9839c3d47",
          "65e8c21647aae08e2a4e5f5c",
          "64c190a921d68642091aa027",
          "64c190a958d2eff448df09e1",
          "650a2457204ab859367160a6",
          "64c190aa58d2eff448df09f0",
          "64af0879c41c606cbcef6288",
          "64c190ab17e6bfc2548f7a4d",
          "64c190aa17e6bfc2548f7a41",
          "64c190a958d2eff448df09ec",
          "64c190ab21d68642091aa033",
          "64c190ab58d2eff448df09f3",
          "64b99a3b6883c0ec1c456c3a",
          "64c190aa21d68642091aa02f",
          "64b99a3ce3b06b2f8a465bdc",
          "64c190a917e6bfc2548f7a35",
          "64b99a3b6883c0ec1c456c39",
          "650a24573e183ec1be29adc6"
        ],
        "unique_counts": {
          "spec.ecosystem": {
            "count": 1
          }
        },
        "unique_values": {
          "spec.ecosystem": [
            "ECOSYSTEM_MAVEN"
          ]
        }
      },
      "[{\"key\":\"spec.resolution_errors.call_graph.status_error\",\"value\":\"STATUS_ERROR_VENV\"}]": {
        "aggregation_count": {
          "count": 10
        },
        "aggregation_uuids": [
          "64c41863da2fbc7700d12a0e",
          "64c845aca83e181b82ef9041",
          "64dd4f61177264d779e203f3",
          "64c418647146e5738bf0af2d",
          "64c845ac41f581de1a6592d1",
          "64c845ac41f581de1a6592d0",
          "664be4bc6fafc782b363d8e3",
          "652e0bcb1d4d2ceedc87a376",
          "66311e48bf25e232ab24b68c",
          "64d6ce776e5804222a2726de"
        ],
        "unique_counts": {
          "spec.ecosystem": {
            "count": 1
          }
        },
        "unique_values": {
          "spec.ecosystem": [
            "ECOSYSTEM_PYPI"
          ]
        }
      }
    }
  }
}
```

## Group by time

The Endor Labs REST API also provides options to group objects by a given time interval. Common time fields include `meta.create_time` and `meta.update_time`, but you can sort objects based on any time field.

For example, to group objects based on create time in 2 week intervals, set the aggregation path to `meta.create_time`, the time interval to `GROUP_BY_TIME_INTERVAL_WEEK` and the group size to `2`.

The following options are available to group objects based on the value of a time field in a given path.

* curl / HTTP

| List Parameter | Description |
| --- | --- |
| `group_by_time.aggregation_paths` | Group the objects based on this time field. |
| `group_by_time.interval` | The [time interval](#time-intervals) to group the objects by. |
| `group_by_time.group_size` | The time interval size to group the objects by. |
| `group_by_time.start_time` | Beginning of the time period to group objects. |
| `group_by_time.end_time` | End of the time period to group objects. |
| `group_by_time.show_aggregation_uuids` | Get the UUIDs of the objects in each group. |

For the complete list of all HTTP list parameters, see [list parameters](../getting-started/#list-parameters).

### Time intervals

The following time intervals are supported.

* curl / HTTP

| Value | Description |
| --- | --- |
| `GROUP_BY_TIME_INTERVAL_YEAR` | Year |
| `GROUP_BY_TIME_INTERVAL_QUARTER` | Quarter |
| `GROUP_BY_TIME_INTERVAL_MONTH` | Month |
| `GROUP_BY_TIME_INTERVAL_WEEK` | Week |
| `GROUP_BY_TIME_INTERVAL_DAY` | Day |
| `GROUP_BY_TIME_INTERVAL_HOUR` | Hour |
| `GROUP_BY_TIME_INTERVAL_MINUTE` | Minute |
| `GROUP_BY_TIME_INTERVAL_SECOND` | Second |

### Group by time example

The following example requests the UUIDs of all critical findings, grouped by create time in two-week intervals:

* curl
* HTTP

```
curl --get \
  --header "Authorization: Bearer $ENDOR_TOKEN" \
  --header "Request-Timeout: 60" \
  --data-urlencode "list_parameters.filter=spec.level==FINDING_LEVEL_CRITICAL" \
  --data-urlencode "list_parameters.group_by_time.aggregation_paths=meta.create_time" \
  --data-urlencode "list_parameters.group_by_time.interval=GROUP_BY_TIME_INTERVAL_WEEK" \
  --data-urlencode "list_parameters.group_by_time.group_size=2" \
  --data-urlencode "list_parameters.group_by_time.show_aggregation_uuids=true" \
  https://api.endorlabs.com/v1/namespaces/$ENDOR_NAMESPACE/findings \
  | jq '.'
```

```
@baseUrl = https://api.endorlabs.com
@token = <insert-access-token>
@namespace = <insert-namespace>

###
GET {{baseUrl}}/v1/namespaces/{{namespace}}/findings?list_parameters.filter=spec.level==FINDING_LEVEL_CRITICAL&list_parameters.group_by_time.aggregation_paths=meta.create_time&list_parameters.group_by_time.interval=GROUP_BY_TIME_INTERVAL_WEEK&list_parameters.group_by_time.group_size=2&list_parameters.group_by_time.show_aggregation_uuids=true HTTP/1.1
Content-type: application/json
Authorization: Bearer {{token}}
Request-Timeout: 60
```

```
{
  "group_response": {
    "groups": {
      "\"2024-01-28T00:00:00Z\"": {
        "aggregation_count": {
          "count": 7
        },
        "aggregation_uuids": [
          "65c02da021a5d767fc147ec0",
          "65c02da021a5d767fc147ec3",
          "65c02da0aa4b66fa5009eaec",
          "65c02da0056f94b6129aa209",
          "65c02da021a5d767fc147eca",
          "65c02da1aa4b66fa5009eaf9",
          "65c02daa056f94b6129aa46f"
        ],
        "unique_counts": {},
        "unique_values": {}
      },
      "\"2024-03-10T00:00:00Z\"": {
        "aggregation_count": {
          "count": 2
        },
        "aggregation_uuids": [
          "65faf8ec357952c8eda2d36b",
          "65fcdcedd40334d9e0065748"
        ],
        "unique_counts": {},
        "unique_values": {}
      },
      "\"2024-03-24T00:00:00Z\"": {
        "aggregation_count": {
          "count": 2
        },
        "aggregation_uuids": [
          "660728d190fdb066027d07bb",
          "660728d8bddd7358d570ce9c"
        ],
        "unique_counts": {},
        "unique_values": {}
      },
      "\"2024-04-07T00:00:00Z\"": {
        "aggregation_count": {
          "count": 15
        },
        "aggregation_uuids": [
          "6615c531bb58b077e43cbb16",
          "6615c531e2a0c32733a7d50b",
          "6615c531e2a0c32733a7d514",
          "66216bb723ebef7ca3f4571a",
          "66216bb7c28c6f37b51cd0e8",
          "66216bb723ebef7ca3f4571d",
          "66216bc62c21fa9407eda175",
          "66216bc6c28c6f37b51cd2d4",
          "66216bc62c21fa9407eda17b",
          "66216bd72c21fa9407eda210",
          "66216bd823ebef7ca3f459a8",
          "66216bd823ebef7ca3f459ab",
          "66216bd8c28c6f37b51cd381",
          "66216be623ebef7ca3f45a8a",
          "66216be6c28c6f37b51cd465"
        ],
        "unique_counts": {},
        "unique_values": {}
      },
      "\"2024-04-21T00:00:00Z\"": {
        "aggregation_count": {
          "count": 1
        },
        "aggregation_uuids": [
          "66341d55f9aa19f4b730a74c"
        ],
        "unique_counts": {},
        "unique_values": {}
      },
      "\"2024-05-19T00:00:00Z\"": {
        "aggregation_count": {
          "count": 19
        },
        "aggregation_uuids": [
          "664be2cc6fafc782b35fdc89",
          "664be2cc6fafc782b35fdceb",
          "664be2d56fafc782b35ff0d8",
          "664be2d56fafc782b35ff0e0",
          "664be2d5f420988edd47792d",
          "664be2dd67636bf844aedcae",
          "664be2dd6fafc782b36000a8",
          "664be2dd6fafc782b36000aa",
          "664be2ddf420988edd4788eb",
          "664be2e867636bf844aef4e9",
          "664be2e8f420988edd47a140",
          "664be2e8f420988edd47a148",
          "6656ababd2d288f1981ea2ba",
          "6656ababce82b72012f10bbc",
          "6656ababce82b72012f10bbd",
          "6656abab252554c986334a6b",
          "6656ababd2d288f1981ea2bd",
          "6656abab252554c986334a6d",
          "6656abacce82b72012f10bbf"
        ],
        "unique_counts": {},
        "unique_values": {}
      },
      "\"2024-06-02T00:00:00Z\"": {
        "aggregation_count": {
          "count": 5
        },
        "aggregation_uuids": [
          "665fa482c980f9f8157e08c3",
          "6660a9f0e238ad93ad92089e",
          "6660a9f05728ef99cf0c8535",
          "6660a9f0b70974e544ccd05a",
          "6660a9f05728ef99cf0c853f"
        ],
        "unique_counts": {},
        "unique_values": {}
      }
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

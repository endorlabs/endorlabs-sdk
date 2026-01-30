---
url: https://docs.endorlabs.com/rest-api/using-the-rest-api/use-cases/
title: Use cases | Endor Labs Docs
downloaded: 2026-01-29 22:23:44
---

Use cases | Endor Labs Docs



* Type to search...

[Print entire section](/rest-api/using-the-rest-api/use-cases/_print.html)



# Use cases

Examples of common use cases for interacting with the Endor Labs REST API.

See also [Best practices](../best-practices/) for tips on how to optimize queries.

## Get list of projects

* endorctl
* curl
* HTTP

```
endorctl api list --resource Project
```

```
curl --get \
  --header "Authorization: Bearer $ENDOR_TOKEN" \
  --header "Accept-Encoding: gzip" \
  --url "https://api.endorlabs.com/v1/namespaces/$ENDOR_NAMESPACE/projects"
```

```
@baseUrl = https://api.endorlabs.com
@token = <endor-token>
@namespace = <endor-namespace>

###
GET {{baseUrl}}/v1/namespaces/{{namespace}}/projects HTTP/1.1
Authorization: Bearer {{token}}
```

Add one or more [field-masks](../masks/) to limit the fields returned for each object. For example, set the field-mask to `meta.name` to only get the name and UUID of all projects. The UUID is always returned.

* endorctl
* curl
* HTTP

```
endorctl api list --resource Project --field-mask meta.name
```

```
curl --get \
  --header "Authorization: Bearer $ENDOR_TOKEN" \
  --header "Accept-Encoding: gzip" \
  --url "https://api.endorlabs.com/v1/namespaces/$ENDOR_NAMESPACE/projects?list_parameters.mask=meta.name" \
  | jq '.list.objects[].uuid'
```

```
@baseUrl = https://api.endorlabs.com
@token = <endor-token>
@namespace = <endor-namespace>

###
GET {{baseUrl}}/v1/namespaces/{{namespace}}/projects?list_parameters.mask=meta.name HTTP/1.1
Authorization: Bearer {{token}}
```

## Get project UUID

The project UUID connects all the objects for a given project. One way to get the project UUID is to extract it from the `uuid` field in the Project object. For more information, see [Resource kinds](../data-model/resource-kinds/).

* endorctl
* curl
* HTTP

```
endorctl api get --resource Project --name <project-name> | jq '.uuid'
```

```
curl --get \
  --header "Authorization: Bearer $ENDOR_TOKEN" \
  --header "Accept-Encoding: gzip" \
  --url "https://api.endorlabs.com/v1/namespaces/$ENDOR_NAMESPACE/projects?list_parameters.filter=meta.name==<project-name>" \
  | jq '.list.objects[].uuid'
```

```
@baseUrl = https://api.endorlabs.com
@token = <endor-token>
@namespace = <endor-namespace>

###
GET {{baseUrl}}/v1/namespaces/{{namespace}}/projects?list_parameters.filter=meta.name==<project-name> HTTP/1.1
Authorization: Bearer {{token}}
```

## Get list of findings for a project

Use the following [filter](../filters/) to get a list of findings for a given project:

`spec.project_uuid==<project-uuid>`

* endorctl
* curl
* HTTP

```
endorctl api list --resource Finding --filter "spec.project_uuid==<project-uuid>"
```

```
curl --get \
  --header "Authorization: Bearer $ENDOR_TOKEN" \
  --header "Accept-Encoding: gzip" \
  --data-urlencode "list_parameters.filter=spec.project_uuid==<project-uuid>" \
  https://api.endorlabs.com/v1/namespaces/$ENDOR_NAMESPACE/findings
```

```
@baseUrl = https://api.endorlabs.com
@token = <endor-token>
@namespace = <endor-namespace>

###
GET {{baseUrl}}/v1/namespaces/{{namespace}}/findings?list_parameters.filter=spec.project_uuid==<project-uuid> HTTP/1.1
Authorization: Bearer {{token}}
```

## Get number of findings for a project

Add the `--count` flag to just get the number of findings. This is much faster than retrieving the objects.

* endorctl
* curl
* HTTP

```
endorctl api list --resource Finding --filter "spec.project_uuid==<project-uuid>" --count
```

```
curl --get \
  --header "Authorization: Bearer $ENDOR_TOKEN" \
  --header "Accept-Encoding: gzip" \
  --data-urlencode "list_parameters.filter=spec.project_uuid==<project-uuid>" \
  --data-urlencode "list_parameters.count=true" \
  https://api.endorlabs.com/v1/namespaces/$ENDOR_NAMESPACE/findings
```

```
@baseUrl = https://api.endorlabs.com
@token = <endor-token>
@namespace = <endor-namespace>

###
GET {{baseUrl}}/v1/namespaces/{{namespace}}/findings?list_parameters.filter=spec.project_uuid==<project-uuid>&list_parameters.count=true HTTP/1.1
Authorization: Bearer {{token}}
```

## Get number of findings for a project by severity

Use [grouping](../grouping/) to get the number of findings by severity.

* endorctl
* curl
* HTTP

```
endorctl api list --resource Finding \
  --filter "spec.project_uuid==<project-uuid>" \
  --group-aggregation-paths "spec.level"
```

```
curl --get \
  --header "Authorization: Bearer $ENDOR_TOKEN" \
  --data-urlencode "list_parameters.filter=spec.project_uuid==<project-uuid>" \
  --data-urlencode "list_parameters.group.aggregation_paths=spec.level" \
  https://api.endorlabs.com/v1/namespaces/$ENDOR_NAMESPACE/findings \
  | jq '.'
```

```
@baseUrl = https://api.endorlabs.com
@token = <endor-token>
@namespace = <endor-namespace>

###
GET {{baseUrl}}/v1/namespaces/{{namespace}}/findings?list_parameters.filter=spec.project_uuid==<project-uuid>&list_parameters.group.aggregation_paths=spec.level HTTP/1.1
Content-type: application/json
Authorization: Bearer {{token}}
```

## Get list of findings for reachable functions

Use the following filter to get a list of findings for reachable functions:

`spec.finding_tags contains FINDING_TAGS_REACHABLE_FUNCTION`

For a list of all finding attributes, see [Finding tags](../data-model/resource-kinds/#finding-tags).

* endorctl
* curl
* HTTP

```
endorctl api list --resource Finding \
  --filter "spec.finding_tags contains FINDING_TAGS_REACHABLE_FUNCTION"
```

```
curl --get \
  --header "Authorization: Bearer $ENDOR_TOKEN" \
  --header "Accept-Encoding: gzip" \
  --data-urlencode "list_parameters.filter=spec.finding_tags contains FINDING_TAGS_REACHABLE_FUNCTION" \
  https://api.endorlabs.com/v1/namespaces/$ENDOR_NAMESPACE/findings
```

```
@baseUrl = https://api.endorlabs.com
@token = <endor-token>
@namespace = <endor-namespace>

###
GET {{baseUrl}}/v1/namespaces/{{namespace}}/findings?list_parameters.filter=spec.finding_tags contains FINDING_TAGS_REACHABLE_FUNCTION HTTP/1.1
Authorization: Bearer {{token}}
```

## Get list of findings for reachable functions for a project

Combine the previous filters to get a list of findings for reachable functions for a given project:

`spec.project_uuid==<project-uuid> and spec.finding_tags contains FINDING_TAGS_REACHABLE_FUNCTION`

* endorctl
* curl
* HTTP

```
endorctl api list --resource Finding \
  --filter "spec.project_uuid==<project-uuid> and spec.finding_tags contains FINDING_TAGS_REACHABLE_FUNCTION"
```

```
curl --get \
  --header "Authorization: Bearer $ENDOR_TOKEN" \
  --header "Accept-Encoding: gzip" \
  --data-urlencode "list_parameters.filter=spec.project_uuid==<project-uuid> and spec.finding_tags contains FINDING_TAGS_REACHABLE_FUNCTION" \
  https://api.endorlabs.com/v1/namespaces/$ENDOR_NAMESPACE/findings
```

```
@baseUrl = https://api.endorlabs.com
@token = <endor-token>
@namespace = <endor-namespace>

###
GET {{baseUrl}}/v1/namespaces/{{namespace}}/findings?list_parameters.filter=spec.project_uuid==<project-uuid> and spec.finding_tags contains FINDING_TAGS_REACHABLE_FUNCTION HTTP/1.1
Authorization: Bearer {{token}}
```

## Get list of findings in a category

Use the following filter to get a list of findings in the RSPM category:

`spec.finding_categories contains FINDING_CATEGORY_SCPM`

For a list of all finding categories, see [Finding categories](../data-model/resource-kinds/#finding-categories).

* endorctl
* curl
* HTTP

```
endorctl api list --resource Finding \
  --filter "spec.finding_categories contains FINDING_CATEGORY_SCPM"
```

```
curl --get \
  --header "Authorization: Bearer $ENDOR_TOKEN" \
  --header "Accept-Encoding: gzip" \
  --data-urlencode "list_parameters.filter=spec.finding_categories contains FINDING_CATEGORY_SCPM" \
  https://api.endorlabs.com/v1/namespaces/$ENDOR_NAMESPACE/findings
```

```
@baseUrl = https://api.endorlabs.com
@token = <endor-token>
@namespace = <endor-namespace>

###
GET {{baseUrl}}/v1/namespaces/{{namespace}}/findings?list_parameters.filter=spec.finding_categories contains FINDING_CATEGORY_SCPM HTTP/1.1
Authorization: Bearer {{token}}
```

## Get list of findings for a vulnerability

Use the following filter to get a list of findings for a given vulnerability, for example `"CVE-2024-53677"` or `"GHSA-43mq-6xmg-29vm"`:

`spec.finding_metadata.vulnerability.spec.aliases contains CVE-2024-53677`

> Note: You can replace the CVE ID in the example with any other vulnerability ID type, such as GHSA, BIT, GO, PYSEC, or OVAL.

* endorctl
* curl
* HTTP

```
endorctl api list --resource Finding \
  --filter "spec.finding_metadata.vulnerability.spec.aliases contains CVE-2024-53677"
```

```
curl --get \
  --header "Authorization: Bearer $ENDOR_TOKEN" \
  --header "Accept-Encoding: gzip" \
  --data-urlencode "list_parameters.filter=spec.finding_metadata.vulnerability.spec.aliases contains CVE-2024-53677" \
  https://api.endorlabs.com/v1/namespaces/$ENDOR_NAMESPACE/findings
```

```
@baseUrl = https://api.endorlabs.com
@token = <endor-token>
@namespace = <endor-namespace>

###
GET {{baseUrl}}/v1/namespaces/{{namespace}}/findings?list_parameters.filter=spec.finding_metadata.vulnerability.spec.aliases contains CVE-2024-53677 HTTP/1.1
Authorization: Bearer {{token}}
```

## Get list of findings for a code owner

Use the `spec.code_owners.owners` field to filter findings based on code owner.

> Note: Code owners are automatically assigned based on the [**CodeOwners**](https://docs.endorlabs.com/api/#tag/CodeOwnersService) object for the project, which is generated from the CODEOWNERS file in the default branch of the repository. For projects without a CODEOWNERS file, the CodeOwners object can be managed through the API.

* endorctl
* curl
* HTTP

```
endorctl api list --resource Finding \
  --filter "spec.code_owners.owners contains <owner>" \
  --timeout 100s
```

```
curl --get \
  --header "Authorization: Bearer $ENDOR_TOKEN" \
  --header "Accept-Encoding: gzip" \
  --header "Request-Timeout: 100" \
  --data-urlencode "list_parameters.filter=spec.code_owners.owners contains <owner>" \
  https://api.endorlabs.com/v1/namespaces/$ENDOR_NAMESPACE/findings
```

```
@baseUrl = https://api.endorlabs.com
@token = <endor-token>
@namespace = <endor-namespace>

###
GET {{baseUrl}}/v1/namespaces/{{namespace}}/findings?list_parameters.filter=spec.code_owners.owners contains <owner> HTTP/1.1
Authorization: Bearer {{token}}
```

## Group findings by code owner

Use the `spec.code_owners.owners` field to group findings based on code owner.

> Note: Code owners are automatically assigned based on the [**CodeOwners**](https://docs.endorlabs.com/api/#tag/CodeOwnersService) object for the project, which is generated from the CODEOWNERS file in the default branch of the repository. For projects without a CODEOWNERS file, the CodeOwners object can be managed through the API.

* endorctl
* curl
* HTTP

```
endorctl api list --resource Finding \
  --group-aggregation-paths "spec.code_owners.owners" \
  --timeout 100s
```

```
curl --get \
  --header "Authorization: Bearer $ENDOR_TOKEN" \
  --header "Request-Timeout: 100" \
  --data-urlencode "list_parameters.group.aggregation_paths=spec.code_owners.owners" \
  https://api.endorlabs.com/v1/namespaces/$ENDOR_NAMESPACE/findings \
  | jq '.'
```

```
@baseUrl = https://api.endorlabs.com
@token = <endor-token>
@namespace = <endor-namespace>

###
GET {{baseUrl}}/v1/namespaces/{{namespace}}/findings?list_parameters.group.aggregation_paths=spec.code_owners.owners HTTP/1.1
Content-type: application/json
Authorization: Bearer {{token}}
```

## Get finding snooze history

Snooze updates are captured as **FindingLog** objects.

* endorctl
* curl
* HTTP

```
endorctl api list --resource FindingLog \
  --filter "spec.finding_uuid==<finding-uuid> and spec.operation==OPERATION_UPDATE" \
  --field-mask "meta.create_time,meta.created_by,spec.snooze"
```

```
curl --get \
  --header "Authorization: Bearer $ENDOR_TOKEN" \
  --header "Accept-Encoding: gzip" \
  --data-urlencode "list_parameters.filter=spec.finding_uuid==<finding-uuid> and spec.operation==OPERATION_UPDATE" \
  --data-urlencode "list_parameters.mask=meta.create_time,meta.created_by,spec.snooze" \
  https://api.endorlabs.com/v1/namespaces/$ENDOR_NAMESPACE/finding-logs
```

```
@baseUrl = https://api.endorlabs.com
@token = <endor-token>
@namespace = <endor-namespace>

###
GET {{baseUrl}}/v1/namespaces/{{namespace}}/finding-logs?list_parameters.filter=spec.finding_uuid==<finding-uuid> and spec.operation==OPERATION_UPDATE&list_parameters.mask=meta.create_time,meta.created_by,spec.snooze HTTP/1.1
Authorization: Bearer {{token}}
```

## Get Endor Labs scores for an OSS package

1. Set the namespace to `"oss"` as the data for OSS packages are stored in the OSS tenant.
2. Endor Labs scores for package versions are stored in the `"package_version_scorecard"` **Metric** object, in the `spec.metric_values.scorecard.score_card.category_scores` field, so you need to get this Metric object for the given OSS package. For more information, see the [Metric resource kind documentation](../data-model/resource-kinds/#metric).
3. To get Metric objects belonging to a given package version, get the UUID of the corresponding **PackageVersion** object. The PackageVersion object name must be in the format `<ecosystem>://<name>@<version>`, for example: `"mvn://ch.qos.logback:logback-core@1.3.3"`. For more information, see the [PackageVersion resource kind documentation](../data-model/resource-kinds/#packageversion). Once you have the PackageVersion object, use the following `jq` command to extract the UUID:

   `jq '.list.object[].uuid'`
4. Get the Metric object corresponding to the PackageVersion UUID using the following two filters:

   1. `meta.name==package_version_scorecard`
   2. `meta.parent_uuid==<package-version-uuid>`
5. Use the following `jq` command to extract just the Endor Labs scores from the Metric object:

   `jq '.list.objects[].spec.metric_values.scorecard.score_card.category_scores'`

* endorctl
* curl
* HTTP

```
# Get the PackageVersion and extract the uuid
UUID=$(endorctl api list \
  --namespace oss \
  --resource PackageVersion \
  --filter "meta.name==mvn://ch.qos.logback:logback-core@1.3.3" \
  | jq '.list.objects[].uuid')

# Get the Metric and extract the Endor Labs scores
endorctl api list \
  --namespace oss \
  --resource Metric \
  --filter "meta.name==package_version_scorecard and meta.parent_uuid==$UUID" \
  | jq '.list.objects[].spec.metric_values.scorecard.score_card.category_scores'
```

```
# Get the PackageVersion and extract the uuid
UUID=$(curl --get \
  --header "Authorization: Bearer $ENDOR_TOKEN" \
  --header "Accept-Encoding: gzip" \
  --data-urlencode "list_parameters.filter=meta.name==mvn://ch.qos.logback:logback-core@1.3.3" \
  https://api.endorlabs.com/v1/namespaces/oss/package-versions \
  | jq '.list.objects[].uuid')

# Get the Metric and extract the Endor Labs scores
curl --get \
  --header "Authorization: Bearer $ENDOR_TOKEN" \
  --header "Accept-Encoding: gzip" \
  --data-urlencode "list_parameters.filter=meta.name==package_version_scorecard and meta.parent_uuid==$UUID" \
  https://api.endorlabs.com/v1/namespaces/oss/metrics \
  | jq '.list.objects[].spec.metric_values.scorecard.score_card.category_scores'
```

```
@baseUrl = https://api.endorlabs.com
@token = <endor-token>

###
GET {{baseUrl}}/v1/namespaces/oss/package-versions?list_parameters.filter=meta.name==mvn://ch.qos.logback:logback-core@1.3.3 HTTP/1.1
Authorization: Bearer {{token}}

###
GET {{baseUrl}}/v1/namespaces/oss/metrics?list_parameters.filter=meta.name==package_version_scorecard and meta.parent_uuid==<package-version-uuid> HTTP/1.1
Authorization: Bearer {{token}}
```

Below is an example response to the request.

```
[
  {
    "category": "SCORE_CATEGORY_ACTIVITY",
    "centered_score": 6.956522,
    "description": "Captures the level of activity associated with the repository. Activity information is based on GitHub metadata. Higher levels of activity can mean that the repository is well maintained and will continue to be in the future.",
    "raw_score": 7.0212765,
    "score": 7
  },
  {
    "category": "SCORE_CATEGORY_POPULARITY",
    "centered_score": 8.076923,
    "description": "Captures how popular is the repository. Popularity information is based on GitHub metadata. Popular repositories are more likely to be maintained.",
    "raw_score": 7.368421,
    "score": 9
  },
  {
    "category": "SCORE_CATEGORY_CODE_QUALITY",
    "centered_score": 4.2105265,
    "description": "Provides a view of code quality and adherence to best practices in a repository. This information is based on from both GitHub metadata  and the source code in the repository.",
    "raw_score": 4.848485,
    "score": 4
  },
  {
    "category": "SCORE_CATEGORY_SECURITY",
    "centered_score": 4.7297297,
    "description": "Captures the level of compliance with security best practices as well as vulnerability information for the repository including currently open as well as fixed vulnerabilities.  Analysis only considers vulnerabilities associated with this repository and not its dependencies. Vulnerability information is based on OSV.dev data and Endor's vulnerability database",
    "raw_score": 8.333333,
    "score": 4
  }
]
```

## Get license text from a license finding

1. Look up a license-related **Finding** object for a dependency using the following filter:

   `spec.finding_categories contains [FINDING_CATEGORY_LICENSE_RISK] and spec.finding_tags not contains [FINDING_TAGS_SELF]`
2. Get the name of the corresponding **PackageVersion** object from the `spec.target_dependency_package_name` field. If we have a list of Finding objects, we can use the following `jq` command to get the PackageVersion name:

   `jq '.list.objects[].spec.target_dependency_package_name'`
3. Look up the PackageVersion object and store the UUID.

   > Note: If this is an OSS dependency we must use the “`oss`” namespace.
4. Look up the corresponding `pkg_version_info_for_license` **Metric** object using the following filter:

   `meta.name==pkg_version_info_for_license&meta.parent_uuid==$UUID`

   > Note: The Metric is in the same namespace as the PackageVersion.
5. Use the following `jq` command to extract the license text from the Metric object:

   `jq '.list.objects[].spec.metric_values.licenseInfoType.license_info.all_licenses[].matched_text'`

For more information, see the [Metric resource kind documentation](../data-model/resource-kinds/#metric).

* endorctl
* curl

```
# Get the target dependency PackageVersion name from a license-related finding
NAME=$(endorctl api list --resource Finding \
  --filter "spec.finding_categories contains [FINDING_CATEGORY_LICENSE_RISK] and spec.finding_tags not contains [FINDING_TAGS_SELF]" \
  --page-size 1 \
  | jq '.list.objects[].spec.target_dependency_package_name')

# Get the target dependency PackageVersion uuid
UUID=$(endorctl api list --resource PackageVersion \
  --namespace oss \
  --filter "meta.name==$NAME" \
  | jq '.list.objects[].uuid')

# Get the corresponding pkg_version_info_for_license Metric and extract the license text
endorctl api list --resource Metric \
  --namespace "oss" \
  --filter "meta.name==pkg_version_info_for_license and meta.parent_uuid==$UUID" \
  | jq '.list.objects[].spec.metric_values.licenseInfoType.license_info.all_licenses[].matched_text'
```

```
# Get the target dependency PackageVersion name from a license-related finding
NAME=$(curl --get \
  --header "Authorization: Bearer $ENDOR_TOKEN" \
  --header "Accept-Encoding: gzip" \
  --data-urlencode "list_parameters.filter=spec.finding_categories contains [FINDING_CATEGORY_LICENSE_RISK] and spec.finding_tags not contains [FINDING_TAGS_SELF]" \
  --data-urlencode "list_parameters.page_size=1" \
  https://api.endorlabs.com/v1/namespaces/$ENDOR_NAMESPACE/findings \
  | jq '.list.objects[].spec.target_dependency_package_name')

# Get the target dependency PackageVersion uuid
UUID=$(curl --get \
  --header "Authorization: Bearer $ENDOR_TOKEN" \
  --header "Accept-Encoding: gzip" \
  --data-urlencode "list_parameters.filter=meta.name==$NAME" \
  https://api.endorlabs.com/v1/namespaces/oss/package-versions \
  | jq '.list.objects[].uuid')

# Get the corresponding pkg_version_info_for_license Metric and extract the license text
curl --get \
  --header "Authorization: Bearer $ENDOR_TOKEN" \
  --header "Accept-Encoding: gzip" \
  --data-urlencode "list_parameters.filter=meta.name==pkg_version_info_for_license and meta.parent_uuid==$UUID" \
  https://api.endorlabs.com/v1/namespaces/oss/metrics \
  | jq '.list.objects[].spec.metric_values.licenseInfoType.license_info.all_licenses[].matched_text'
```

## Get list of projects using a tool

1. CI/CD tool metrics are stored in the `version_cicd_tools` **Metric** object, in the `spec.metric_values.CiCdTools.ci_cd_tools.tools` list. Use the following filter to get all such Metrics with entries for the given tool name (GitHub Actions in this example). For more information, see the [Metric resource kind documentation](../data-model/resource-kinds/#metric).

   `meta.name==version_cicd_tools and spec.metric_values.CiCdTools.ci_cd_tools.tools.name=='GitHub Actions'`
2. Use the following `jq` command to get the UUIDs of the corresponding **Project** objects:

   `.list.objects[].spec.project_uuid`
3. Remove duplicate Project UUIDs (a Project can have multiple repository versions).
4. Use the UUIDs to get the corresponding Project objects.

* endorctl
* curl

```
# Get list of Project UUIDs
PROJECT_UUIDS=$(endorctl api list --resource Metric \
  --filter "meta.name==version_cicd_tools and spec.metric_values.CiCdTools.ci_cd_tools.tools.name=='GitHub Actions'" \
  | jq -r '.list.objects[].spec.project_uuid')

# Remove duplicate UUIDs
UNIQUE_UUIDS=$(echo $PROJECT_UUIDS | sort | uniq)

# Get Project for each uuid and extract the name
for uuid in $UNIQUE_UUIDS
do
  endorctl api get --resource Project --uuid $uuid | jq '.meta.name'
done
```

```
# Get list of Project UUIDs
PROJECT_UUIDS=$(curl --get \
  --header "Authorization: Bearer $ENDOR_TOKEN" \
  --header "Accept-Encoding: gzip" \
  --data-urlencode "list_parameters.filter=meta.name==version_cicd_tools and spec.metric_values.CiCdTools.ci_cd_tools.tools.name=='GitHub Actions'" \
  https://api.endorlabs.com/v1/namespaces/$ENDOR_NAMESPACE/metrics \
  | jq -r '.list.objects[].spec.project_uuid')

# Remove duplicate UUIDs
UNIQUE_UUIDS=$(echo $PROJECT_UUIDS | sort | uniq)

# Get Project for each uuid and extract the name
for uuid in $UNIQUE_UUIDS
do
  curl --get \
    --header "Authorization: Bearer $ENDOR_TOKEN" \
    --header "Accept-Encoding: gzip" \
    --url https://api.endorlabs.com/v1/namespaces/$ENDOR_NAMESPACE/projects/$uuid \
    | jq '.meta.name'
done
```

See also [List Projects, with Repository Versions and CI/CD Tool Metrics](../advanced-use-cases/query-service/#list-projects-with-repository-versions-and-cicd-tool-metrics) for an example of how to use the Query Service to get the CI/CD tool Metric objects for a list of projects.

## Get the latest scan result

1. To get the latest object, first sort the objects in descending order, based on the `meta.create_time` field:

   `list_parameters.sort.order=SORT_ENTRY_ORDER_DESC&list_parameters.sort.path=meta.create_time`
2. Then, to get only the latest object, set the page size to 1:

   `list_parameters.page_size=1`

* endorctl
* curl
* HTTP

```
endorctl api list --resource ScanResult \
  --sort-order descending \
  --sort-path meta.create_time \
  --page-size=1
```

```
curl --get \
  --header "Authorization: Bearer $ENDOR_TOKEN" \
  --header "Accept-Encoding: gzip" \
  --url "https://api.endorlabs.com/v1/namespaces/$ENDOR_NAMESPACE/scan-results?list_parameters.sort.order=SORT_ENTRY_ORDER_DESC&list_parameters.sort.path=meta.create_time&list_parameters.page_size=1"
```

```
@baseUrl = https://api.endorlabs.com
@token = <endor-token>
@namespace = <endor-namespace>

###
GET {{baseUrl}}/v1/namespaces/{{namespace}}/scan-results?list_parameters.sort.order=SORT_ENTRY_ORDER_DESC&list_parameters.sort.path=meta.create_time&list_parameters.page_size=1 HTTP/1.1
Authorization: Bearer {{token}}
```

## Create a policy

The following example uses the [Create Policy](https://docs.endorlabs.com/api/#tag/PolicyService/operation/PolicyService_CreatePolicy) endpoint to create a new policy.

* endorctl
* curl
* HTTP

```
endorctl api create --resource Policy \
  --data '{
    "meta": {
      "description": "Disable action policies for CVE-2020-7677",
      "kind": "Policy",
      "name": "Ignore CVE-2020-7677"
    },
    "propagate": true,
    "spec": {
      "exception": {
        "reason": "EXCEPTION_REASON_RISK_ACCEPTED"
      },
      "policy_type": "POLICY_TYPE_EXCEPTION",
      "query_statements": [
        "data.exceptions.match_finding"
      ],
      "resource_kinds": [
        "Finding"
      ],
      "rule": "package exceptions\n\nmatch_finding[result] {\n\tsome i\n  data.resources.Finding[i].spec.finding_metadata.vulnerability.spec.aliases[_] = \"CVE-2020-7677\"\n  result = { \"Endor\" : { \"Finding\" : data.resources.Finding[i].uuid } }\n}"
    },
    "tenant_meta": {
      "namespace": "$ENDOR_NAMESPACE"
    }
  }'
```

```
curl --request POST \
  --header "Authorization: Bearer $ENDOR_TOKEN" \
  --header "Accept-Encoding: gzip" \
  --url "https://api.endorlabs.com/v1/namespaces/$ENDOR_NAMESPACE/policies" \
  --data '{
    "meta": {
      "description": "Disable action policies for CVE-2020-7677",
      "kind": "Policy",
      "name": "Ignore CVE-2020-7677"
    },
    "propagate": true,
    "spec": {
      "exception": {
        "reason": "EXCEPTION_REASON_RISK_ACCEPTED"
      },
      "policy_type": "POLICY_TYPE_EXCEPTION",
      "query_statements": [
        "data.exceptions.match_finding"
      ],
      "resource_kinds": [
        "Finding"
      ],
      "rule": "package exceptions\n\nmatch_finding[result] {\n\tsome i\n  data.resources.Finding[i].spec.finding_metadata.vulnerability.spec.aliases[_] = \"CVE-2020-7677\"\n  result = { \"Endor\" : { \"Finding\" : data.resources.Finding[i].uuid } }\n}"
    },
    "tenant_meta": {
      "namespace": "$ENDOR_NAMESPACE"
    }
  }' | jq '.'
```

```
@baseUrl = https://api.endorlabs.com
@token = <endor-token>
@namespace = <endor-namespace>

###
POST {{baseUrl}}/v1/namespaces/{{namespace}}/policies HTTP/1.1
Authorization: Bearer {{token}}

{
    "meta": {
        "name": "Detect Apache-2.0 License",
        "description": "Raise findings for dependencies using the Apache-2.0 license"
    },
    "spec": {
        "policy_type": "POLICY_TYPE_USER_FINDING",
        "finding_level": "FINDING_LEVEL_CRITICAL",
        "finding": {
            "explanation": "One or more of the licenses associated with this package or package dependency violates organizational license policy.",
            "external_name": "License Compliance Violation",
            "level": "FINDING_LEVEL_CRITICAL",
            "remediation": "Please consult with legal for further instructions or to request an exception.",
            "summary": "Package uses the \"Apache-2.0\" license."
        },
        "query_statements": [
            "data.license.match_license"
        ],
        "resource_kinds": [
            "Metric",
            "PackageVersion"
        ],
        "rule": "package license\n\nmatch_license[result] {\n  some i\n  data.resources.Metric[i]\n  data.resources.Metric[i].meta.name == \"pkg_version_info_for_license\"\n  data.resources.Metric[i].meta.parent_kind == \"PackageVersion\"\n  lower(data.resources.Metric[i].spec.metric_values.licenseInfoType.license_info.all_licenses[_].name) == lower(\"Apache-2.0\")\n  data.resources.PackageVersion[_].uuid == data.resources.Metric[i].meta.parent_uuid\n\n  result = {\n    \"Endor\": {\n      \"PackageVersion\": data.resources.Metric[i].meta.parent_uuid,\n    }\n  }\n}"
    },
    "tenant_meta": {
      "namespace": "{{namespace}}"
    }
}
```

## Update a policy to include a project

The following example uses the [Update Policy](https://docs.endorlabs.com/api/#tag/PolicyService/operation/PolicyService_UpdatePolicy) endpoint to apply a policy to a given project by updating the `spec.project_selector` tag list.

**Warning**

This overrides the existing `project_selector` list, so you must pass in all the project inclusion tags that you want to keep for this policy along with the new tag.

* endorctl
* curl
* HTTP

```
endorctl api update --resource Policy --uuid <policy-uuid> \
  --field-mask "spec.project_selector" \
  --data '{ "spec" : { "project_selector" : [ "$uuid=<project-uuid>" ] } }'
```

```
curl --request PATCH \
  --header "Authorization: Bearer $ENDOR_TOKEN" \
  --header "Accept-Encoding: gzip" \
  --url "https://api.endorlabs.com/v1/namespaces/$ENDOR_NAMESPACE/policies" \
  --data '{
    "request" : {
      "update_mask": "spec.project_selector"
    },
    "object" : {
      "uuid" : "<policy-uuid>",
      "spec" : {
        "project_selector": [
          "$uuid=<project-uuid>"
        ]
      }
    }
  }' | jq '.'
```

```
@baseUrl = https://api.endorlabs.com
@token = <endor-token>
@namespace = <endor-namespace>

###
PATCH {{baseUrl}}/v1/namespaces/{{namespace}}/policies HTTP/1.1
Authorization: Bearer {{token}}

{
    "request" : {
      "update_mask": "spec.project_selector"
    },
    "object" : {
      "uuid" : "<policy-uuid>",
      "spec" : {
        "project_selector": [
          "$uuid=<project-uuid>"
        ]
      }
    }
}
```

## Update a policy to exclude a project

The following example uses the [Update Policy](https://docs.endorlabs.com/api/#tag/PolicyService/operation/PolicyService_UpdatePolicy) endpoint to exclude a given project from a policy by updating the `spec.project_exceptions` tag list.

**Warning**

This overrides the existing `project_exceptions` list, so you must pass in all project exception tags that you want to keep for this policy along with the new tag.

* endorctl
* curl
* HTTP

```
endorctl api update --resource Policy --uuid <policy-uuid> \
  --field-mask "spec.project_exceptions" \
  --data '{ "spec" : { "project_exceptions" : [ "$uuid=<project-uuid>" ] } }'
```

```
curl --request PATCH \
  --header "Authorization: Bearer $ENDOR_TOKEN" \
  --header "Accept-Encoding: gzip" \
  --url "https://api.endorlabs.com/v1/namespaces/$ENDOR_NAMESPACE/policies" \
  --data '{
    "request" : {
      "update_mask": "spec.project_exceptions"
    },
    "object" : {
      "uuid" : "<policy-uuid>",
      "spec" : {
        "project_exceptions": [
          "$uuid=<project-uuid>"
        ]
      }
    }
  }' | jq '.'
```

```
@baseUrl = https://api.endorlabs.com
@token = <endor-token>
@namespace = <endor-namespace>

###
PATCH {{baseUrl}}/v1/namespaces/{{namespace}}/policies HTTP/1.1
Authorization: Bearer {{token}}

{
    "request" : {
      "update_mask": "spec.project_exceptions"
    },
    "object" : {
      "uuid" : "<policy-uuid>",
      "spec" : {
        "project_exceptions": [
          "$uuid=<project-uuid>"
        ]
      }
    }
}
```

## Update an exception policy to apply custom tags to matching findings

The following example uses the [Update Policy](https://docs.endorlabs.com/api/#tag/PolicyService/operation/PolicyService_UpdatePolicy) endpoint to specify a list of custom tags to apply to findings matching a given exception policy.

**Warning**

This overrides the existing `spec.exception.tags` list, so you must pass in all tags that you want to keep for this policy along with the new tag.

* endorctl
* curl
* HTTP

```
endorctl api update --resource Policy --uuid <policy-uuid> \
  --field-mask "spec.exception.tags" \
  --data '{ "spec" : { "exception" : { "tags" : [ <tag1>, <tag2> ] } } }'
```

```
curl --request PATCH \
  --header "Authorization: Bearer $ENDOR_TOKEN" \
  --header "Accept-Encoding: gzip" \
  --url "https://api.endorlabs.com/v1/namespaces/$ENDOR_NAMESPACE/policies" \
  --data '{
    "request" : {
      "update_mask": "spec.exception.tags"
    },
    "object" : {
      "uuid" : "<policy-uuid>",
      "spec" : {
        "exception": {
          "tags" : [
            "<tag1>",
            "<tag2>"
          ]
        }
      }
    }
  }' | jq '.'
```

```
@baseUrl = https://api.endorlabs.com
@token = <endor-token>
@namespace = <endor-namespace>

###
PATCH {{baseUrl}}/v1/namespaces/{{namespace}}/policies HTTP/1.1
Authorization: Bearer {{token}}

{
    "request" : {
      "update_mask": "spec.exception.tags"
    },
    "object" : {
      "uuid" : "<policy-uuid>",
      "spec" : {
        "exception": {
          "tags" : [
            "<tag1>",
            "<tag2>"
          ]
        }
      }
    }
}
```

## Upgrade a policy to use the latest template version

The following example uses the [Update Policy](https://docs.endorlabs.com/api/#tag/PolicyService/operation/PolicyService_UpdatePolicy) endpoint to upgrade a given policy to use the latest template version.

* endorctl
* curl
* HTTP

```
endorctl api update --resource Policy --uuid <policy-uuid> \
  --field-mask "spec.template_version" \
  --data '{ "spec" : { "template_uuid" : "<template-uuid>", "template_version" : "2.0.0" } }'
```

```
curl --request PATCH \
  --header "Authorization: Bearer $ENDOR_TOKEN" \
  --header "Accept-Encoding: gzip" \
  --url "https://api.endorlabs.com/v1/namespaces/$ENDOR_NAMESPACE/policies" \
  --data '{
    "request" : {
      "update_mask": "spec.template_version"
    },
    "object" : {
      "uuid" : "<policy-uuid>",
      "spec" : {
        "template_uuid" : "<template-uuid>",
        "template_version" : "2.0.0"
      }
    }
  }' | jq '.'
```

```
@baseUrl = https://api.endorlabs.com
@token = <endor-token>
@namespace = <endor-namespace>

###
PATCH {{baseUrl}}/v1/namespaces/{{namespace}}/policies HTTP/1.1
Authorization: Bearer {{token}}

{
    "request" : {
      "update_mask": "spec.template_version"
    },
    "object" : {
      "uuid" : "<policy-uuid>",
      "spec" : {
        "template_uuid" : "<template-uuid>",
        "template_version" : "2.0.0"
      }
    }
}
```

## Delete a policy

The following example uses the [Delete Policy](https://docs.endorlabs.com/api/#tag/PolicyService/operation/PolicyService_DeletePolicy) endpoint to delete a policy.

* endorctl
* curl
* HTTP

```
endorctl api delete --resource Policy --uuid <policy-uuid>
```

```
curl --request DELETE \
  --header "Authorization: Bearer $ENDOR_TOKEN" \
  --header "Accept-Encoding: gzip" \
  --url "https://api.endorlabs.com/v1/namespaces/$ENDOR_NAMESPACE/policies/<policy-uuid>"
```

```
@baseUrl = https://api.endorlabs.com
@token = <endor-token>
@namespace = <endor-namespace>

###
DELETE {{baseUrl}}/v1/namespaces/{{namespace}}/policies/<policy-uuid> HTTP/1.1
Authorization: Bearer {{token}}
```

## Add meta tags to an object

The following example uses the [Update Finding](https://docs.endorlabs.com/api/#tag/FindingService/operation/FindingService_UpdateFinding) endpoint to add custom tags to a finding by updating the `meta.tags` field.

**Warning**

This overrides the existing `meta.tags` list, so you must pass in all tags that you want to keep for this object along with the new tag.

* endorctl
* curl
* HTTP

```
endorctl api update --resource Finding --uuid <finding-uuid> \
  --field-mask "meta.tags" \
  --data '{ "meta" : { "tags" : [ "tag1", "tag2", "tag3" ] } }'
```

```
curl --request PATCH \
  --header "Authorization: Bearer $ENDOR_TOKEN" \
  --header "Accept-Encoding: gzip" \
  --url "https://api.endorlabs.com/v1/namespaces/$ENDOR_NAMESPACE/findings" \
  --data '{
    "request" : {
      "update_mask": "meta.tags"
    },
    "object" : {
      "uuid" : "<finding-uuid>",
      "meta" : {
        "tags": [
          "tag1",
          "tag2",
          "tag3"
        ]
      }
    }
  }' | jq '.'
```

```
@baseUrl = https://api.endorlabs.com
@token = <endor-token>
@namespace = <endor-namespace>

###
PATCH {{baseUrl}}/v1/namespaces/{{namespace}}/findings HTTP/1.1
Authorization: Bearer {{token}}

{
    "request" : {
      "update_mask": "meta.tags"
    },
    "object" : {
      "uuid" : "<finding-uuid>",
      "meta" : {
        "tags": [
          "tag1",
          "tag2",
          "tag3"
        ]
      }
    }
}
```

## Get data from child namespaces

Use the `traverse` option to include data from child namespaces as well as the parent namespace.

* endorctl
* curl
* HTTP

```
endorctl api list --resource Project --traverse
```

```
curl --get \
  --header "Authorization: Bearer $ENDOR_TOKEN" \
  --header "Accept-Encoding: gzip" \
  --url "https://api.endorlabs.com/v1/namespaces/$ENDOR_NAMESPACE/projects?list_parameters.traverse=true"
```

```
@baseUrl = https://api.endorlabs.com
@token = <endor-token>
@namespace = <endor-namespace>

###
GET {{baseUrl}}/v1/namespaces/{{namespace}}/projects?list_parameters.traverse=true HTTP/1.1
Authorization: Bearer {{token}}
```

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

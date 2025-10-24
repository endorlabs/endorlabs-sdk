---
url: https://docs.endorlabs.com/endorctl/commands/validate/
title: validate policy | Endor Labs Docs
downloaded: 2025-10-23 23:25:21
---

validate policy | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/endorctl/commands/validate/_print.html)



# validate policy

Use this command to validate policies

## Usage

Use the command `endorctl validate policy` to validate one or more policies against data from one or more projects.
If the policy is valid, the command returns all matches for the given projects, in the requested format, with the corresponding exit code.

```
endorctl validate policy [policies] [flags]
```

### Flags and variables

The `endorctl validate policy` command uses the following flags and environment variables:

| Flag | Environment Variable | Type | Description |
| --- | --- | --- | --- |
| `all-releases` | `ENDOR_VALIDATE_POLICY_ALL_RELEASES` | boolean (default:false) | Load data from all official releases of the project. |
| `filter` | `ENDOR_VALIDATE_POLICY_PROJECT_FILTER` | string | Filter projects to load data from. For example, `"meta.tags contains sanity"`. |
| `input` | `ENDOR_VALIDATE_POLICY_INPUT_FILE_PATH` | json | Path to a json file containing the input parameter values, if applicable. Input parameters are sometimes used for policy templates. |
| `output-type` | `ENDOR_VALIDATE_POLICY_SUMMARY_OUTPUT_TYPE` | string | Set output format (`json`, `yaml`, or `table`) (default `table`). |
| `policy` | `ENDOR_VALIDATE_POLICY_FILE_PATH` | string | Path to a file containing the policies to be validated. Supported formats: Text (plain Rego rules), json (one or more policies), or yaml (one or more policies or policy templates). |
| `policy-uuid` | `ENDOR_VALIDATE_POLICY_UUID` | string | UUIDs of policies to be validated. |
| `pr-baseline` | `ENDOR_VALIDATE_POLICY_PR_BASELINE` | string | Name of the baseline version from which to load data. For example, `main`. |
| `pr-uuid` | `ENDOR_VALIDATE_POLICY_PR_UUID` | string | PR scan from which to load data. |
| `query` | `ENDOR_VALIDATE_POLICY_QUERY_STATEMENTS` | string | Query statements for this policy (for example, `data.packagename.match_finding`). This option is only needed for plain text Rego rules. |
| `resource-kinds` | `ENDOR_VALIDATE_POLICY_RESOURCE_KINDS` | comma-separated string | Resource kinds required by this policy (for example, `PackageVersion,Metric`). This option is only needed for plain text Rego rules. |
| `uuid` | `ENDOR_VALIDATE_POLICY_PROJECT_UUID` | string | UUID of the project from which to load data. |

#### Specify one or more policies

Use one of the following formats to specify one or more policies:

| Input format | Description |
| --- | --- |
| Plain text Rego | Provide the file path to a file containing just the Rego rules. The query statement is provided as a separate parameter. For example, `endorctl validate policy --policy policy.txt --query data.example.match_package_version_score`. |
| json | Provide the file path to a json file containing one or more [Policy](https://docs.endorlabs.com/api/#tag/PolicyService) objects (see `Policy`, `Policies`, and `ListPoliciesResponse`). For example, `endorctl validate policy --policy policy.json`. |
| yaml | Provide the file path to a yaml file containing one or more policy or policy template definitions (see `Policies` and `PolicyTemplates`). For example, `endorctl validate policy --policy policy.yaml`. |
| UUID | Provide one or more UUIDs of existing [Policy](https://docs.endorlabs.com/api/#tag/PolicyService) objects. For example, `endorctl validate policy --policy-uuid 6418dc7a55afcfb7b0d0e025`. |

#### Specify a project or a project filter

Use one of the following formats to specify one or more projects from which to load data:

| Input format | Description |
| --- | --- |
| Filter | Load data from all projects matching a given [filter](../../../rest-api/using-the-rest-api/filters/). For example, `endorctl validate policy --policy policy.rego --query data.example.match_package_version_score --filter "meta.tags contains release"`. |
| UUID | Provide the UUID of the project from which to load data. For example, `endorctl validate policy --policy-uuid 6418dc7a55afcfb7b0d0e025 --uuid 6699c827cd89accb3a017536`. |
| PR UUID | Provide the UUID of a PR from which to load data. Add the baseline version name to match only new findings. For example, `endorctl validate policy --policy-uuid 6418dc7a55afcfb7b0d0e025 --uuid 6699c827cd89accb3a017536 --pr-uuid 43064105-1fd7-42fe-a380-bd5e36657d39 --pr-baseline main`. |

#### Specify output format

As with the other `endorctl` commands, you can specify if you prefer the output as a `table`, or in `json` or `yaml` format.
If the output format is `json` or `yaml` the matching findings are listed under `"matching_findings"` and the results for all other resource kinds are listed under `"matching_resources"`.

For example, `endorctl validate policy --policy-uuid 6418dc7a55afcfb7b0d0e025 --uuid 6699c827cd89accb3a017536 --output-type json`.

#### Exit Codes

If the policy is valid and there are no matches the command returns 0.
The following table lists the non-zero exit codes returned by the `endorctl validate policy` command:

| Value | Exit Code Name | Description |
| --- | --- | --- |
| 3 | ENDORCTL\_RC\_INVALID\_ARGS | An invalid argument was provided. |
| 18 | ENDORCTL\_RC\_POLICY\_ERROR | There was an error evaluating one or more policies. See log for details. |
| 128 | ENDORCTL\_RC\_POLICY\_VIOLATION | One or more policies had matching findings for the given projects. |

For a complete list of endorctl exit codes, see [endorctl CLI exit codes](../../../troubleshooting/endorctl-exitcodes/).

### Example

Below is an example on how to verify that a Rego policy is correctly formatted.

1. First, define a Rego policy. Let’s take the example policy below that searches for dependencies with an Endor Labs overall score of less than 7. You can save this to a file called “test\_policy.rego”.

   ```
   package example

   match_package_version_score[result] {
     some i
     data.resources.Metric[i].meta.name == "package_version_scorecard"
     data.resources.Metric[i].meta.parent_kind == "PackageVersion"
     data.resources.Metric[i].meta.parent_uuid == data.resources.PackageVersion[_].uuid
     score := data.resources.Metric[i].spec.metric_values.scorecard.score_card.overall_score
     score < 7

     result = {
       "Endor" : {
         "PackageVersion" : data.resources.Metric[i].meta.parent_uuid
       },
       "Score" : sprintf("%v", [score])
     }
   }
   ```
2. Next, validate that the policy is correctly formatted.

   ```
   endorctl validate policy \
     --policy test_policy.rego \
     --query data.example.match_package_version_score
   ```
3. Add a project UUID to validate the policy against real data.

   ```
   endorctl validate policy \
     --policy test_policy.rego \
     --query data.example.match_package_version_score \
     --uuid $PROJECT_UUID \
     --output-type json > output.json
   ```
4. Inspect the policy output.

   ```
   {
     "matching_resources": {
       "6553132357b462874261f054": {
         "Policy 1": {
           "PackageVersion": [
             {
               "resource_name": "pypi://astunparse@1.6.3",
               "resource_uuid": "63f599e177cf1f3d7f286ea1",
               "result": {
                 "None": [
                   {
                     "Score": "6"
                   }
                 ]
               }
             },
   ```

### Troubleshooting

* Set `--output-type` to `json` or `yaml` for formatted output
* Add the `--verbose` flag for detailed output
* Set `--log-level debug` for more information

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

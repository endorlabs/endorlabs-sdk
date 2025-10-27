---
url: https://docs.endorlabs.com/scan-with-endorlabs/manage-scan-profiles/configure-scan-workflow-through-api/
title: Configure scan workflow through Endor Labs API | Endor Labs Docs
downloaded: 2025-10-27 12:59:50
---

Configure scan workflow through Endor Labs API | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/scan-with-endorlabs/manage-scan-profiles/configure-scan-workflow-through-api/_print.html)



# Configure scan workflow through Endor Labs API

Learn how to configure scan workflow through Endor Labs API

Configure scan workflows through the Endor Labs API to automate how your projects are scanned. You can create, modify, and delete scan workflows. You can also define the order of scan profile execution and associate workflows with specific projects in your tenant.

### Prerequisites for creating a scan workflow

Ensure you have the following before creating a scan workflow:

* Make sure you [install and configure endorctl](../../../endorctl/install-and-configure/) in your system.
* Ensure your scan workflow includes at least one [scan profile](../../manage-scan-profiles/).
* All scan profiles you reference must already exist in your tenant.
* You can associate only one scan workflow with each project.

### Create a scan workflow

Create a scan workflow using `endorctl api` and associate it with a project in your tenant.

1. Run the endorctl scan to create a project in Endor Labs.

   ```
   endorctl scan
   ```
2. Fetch the UUID of the project. For example, to fetch the UUID of `app-java-demo` project, run:

   ```
   UUID=$(endorctl api list -r Project --filter="meta.name matches https://github.com/endorlabs/app-java-demo" --field-mask=uuid | jq -r '.list.objects[].uuid')
   ```
3. Use the following command to create a `ScanWorkflow` object and associate it with your project. Specify the title and UUID of one or more scan profiles available in your tenant. Replace the following placeholders with your actual values:

   * `demo` with name the of the scan workflow.
   * `project-uuid` with the UUID of your project from step 2.
   * `scan profile 1` and `scan profile 2` with the names of your scan profiles.
   * `uuid of scan profile 1` and `uuid of scan profile 2` with the corresponding UUIDs of the scan profiles.

   ```
   endorctl api create -r ScanWorkflow -d'{
       "meta":
       {
           "name":"demo",
           "kind": "ScanWorkflow",
           "parent_kind":"Project",
           "parent_uuid":"project-uuid"
       },
       "spec":
           {
           "steps":
           [
               {
                   "title":"scan profile 1",
                   "scan_profile_uuid":"uuid of scan profile 1"
               },
               {
                   "title":"scan profile 2",
                   "scan_profile_uuid":"uuid of scan profile 2"
               },
           ]
           }
   }'
   ```

Here is an example to create a scan workflow titled `demo-workflow` with a `Java` scan profile and `Python` scan profile.

```
endorctl api create -r ScanWorkflow -d'{
    "meta":
    {
        "name":"demo-workflow",
        "kind": "ScanWorkflow",
        "parent_kind":"Project",
        "parent_uuid":"68369123e4a717bd735c24bc"
    },
    "spec":
        {
        "steps":
        [
            {
                "title":"java",
                "scan_profile_uuid":"68450261ec0014616fa6c0c3"
            },
            {
                "title":"python",
                "scan_profile_uuid":"6845023bbe385224df4a0526"
            }
        ]
        }
}'
```

### View provision result of a scan workflow

The provision result shows the list and execution history of scan workflows in your namespace, including the scan profiles used, their order, and the outcome of each step. It verifies that prerequisites such as resources, configurations, and dependencies are ready before scanning or analytics begin. You can use it to troubleshoot failures, check that the correct scan profiles ran, and confirm workflows run as expected.

Run the following command to view the list of scan workflows in your namespace and their execution results.

```
endorctl api list -r ScanWorkflowResult
```

### Delete a scan workflow

You can delete an existing scan workflow from your tenant by using `endorctl` API and specifying its UUID.

1. Get a list of scan workflows in your namespace.

   ```
   endorctl api list -r ScanWorkflow
   ```
2. Run the following command to delete a scan workflow. Replace `abcde12345` with the UUID of the scan workflow.

   ```
   endorctl api delete -r ScanWorkflow --uuid abcde12345
   ```

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

---
url: https://docs.endorlabs.com/managing-projects/
title: Manage projects | Endor Labs Docs
downloaded: 2025-11-20 11:51:09
---

Manage projects | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/managing-projects/_print.html)



# Manage projects

Learn how to manage your Endor Labs projects.

Projects in Endor Labs represent your source code repositories. When you scan a repository, Endor Labs creates a corresponding project.

Select **Projects** from the left sidebar to view a list of all projects in your namespace.

![Projects](../images/projects.png)

You can view the following details in the Projects list:

* **Source Code Management Platform** - The icon that represents the source code management platform like GitHub, GitLab, Azure DevOps and Bitbucket.
* **Project** - The name of the project. Usually denoted as `SCM Organization/Project Name`.
* **Findings** - The condensed view of the number of critical, high, medium, and low severity findings in the project.
* **Tags** - The tags associated with the project.
* **Packages** - The number of packages in the project.
* **Dependency Resolution Status** - The percentage of packages that have been fully analyzed with no dependency resolution errors.
* **Reachability Analysis Status** - The percentage of packages eligible for reachability analysis that have been fully analyzed with no call graph errors.
* **Last Scan** - The elapsed time since the project was last analyzed by Endor Labs.

To sort projects by any column, click the column header to toggle the sort order between ascending (A–Z or oldest to newest) and descending (Z–A or newest to oldest), depending on the column type.

## View project details

Select a row to view the project details. The project details appear in the right sidebar.

![Project Details](../images/project-details.png)

In project details, you can view the project metadata, finding details, and tools associated with the project.

## View project findings

Click on **Project** to view the project findings. See [View Findings](../managing-projects/view-findings/) for more information.

You can also scan your projects for AI models. See [AI model findings](../ai/ai-llm/) for more information.

## View packages in a project

Select **Packages** under **Inventory** to view the list of all packages maintained as part of your project. See [Packages](../managing-projects/packages/) for more information.

## Review past scan details

You can view the history of scans performed on a project, which enables you to review the security posture of your project over time. See [Scan history](../managing-projects/scan-history/) for more information.

## View dependencies

You can view all the dependencies associated with all the projects in your namespace. See [Dependencies](../managing-projects/dependencies/) for more information.

## Filter projects

Filters refine the projects view by applying conditions based on project metadata and scan results. For example, you can filter projects by name, tags, scan date, or number of critical findings. You can combine multiple filters to narrow down results based on several conditions in a single query.

The following are the filters available for querying projects within the Endor Labs platform.

| Filter | Description |
| --- | --- |
| Project UUID | Filters projects by their unique identifier. |
| Name | Filters projects by the display name of the project. |
| Custom Tags | Filters projects by custom tags set during project setup or scan configuration. |
| Last Scanned | Filters projects based on the timestamp of the last successful scan. |
| Package Count | Filters projects by the total number of packages resolved in the project. |
| Package Ecosystems | Filters projects based on the language-specific package ecosystems they use. |
| Dependency Resolution Status | Filters projects by the percentage of resolved dependencies in the project. |
| Reachability Analysis Status | Filters projects based on the success rate of reachability analysis through call graph generation. |
| Critical Findings Count | Filters projects based on the number of critical-severity findings in the project. |
| High Findings Count | Filters projects based on the number of high-severity findings in the project. |
| Medium Findings Count | Filters based on the number of medium-severity findings in the project. |
| Low Findings Count | Filters projects based on the number of low-severity findings in the project. |
| Dismissed Findings Count | Filters projects based on how many findings were manually dismissed by users. Useful for reviewing triaged issues. |
| Total Findings Count | Filters projects based on the total number of findings detected in a project. |
| Platform Source | Filters projects based on source platform and helps narrow results by version control origin such as GitHub, GitLab, or Bitbucket. |

See [Working with project filters](../best-practices/project-filters/) to learn how to implement these filters effectively.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

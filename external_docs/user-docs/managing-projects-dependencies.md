---
url: https://docs.endorlabs.com/managing-projects/dependencies/
title: Dependencies | Endor Labs Docs
downloaded: 2025-11-20 11:50:27
---

Dependencies | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/managing-projects/dependencies/_print.html)



# Dependencies

View dependencies in your project with their details.

You can view project dependencies discovered in your tenant. Additionally, you can search for dependencies using specific criteria or apply predefined filters to find relevant results.

Select **Dependencies** from the left sidebar to view the list of dependencies in your current namespace, along with their Endor scores and malware status. The list also includes dependencies from all child namespaces.

![Dependencies](../../images/dependencies-table-ui.png)

## Search dependencies

You can use the search bar to enter a search string to filter the search results based on the dependency name. You can enter multiple search strings.

## Filter dependencies

You can also filter the dependencies by providing a filter criteria.

1. Click **Add Filter** and select **List Dependencies Where**.
2. Choose the filter criteria from the dropdown list and choose the filter operator.
3. Enter the filter values.
4. Click **Apply Filter** to apply the filter.

   You can choose to add multiple filters.
   The following example shows how to add a filter for reachable dependencies with the ecosystem as `Maven`.

   ![Filter dependencies](../../images/dependency-filter.png)

## View dependency details overview

Select the dependency row to view the dependency details overview on the right sidebar.

![Dependency details](../../images/dependency-detail-overview.png)

Select **OSS Scores** to view the score details for the dependency.

![Dependency scores](../../images/dependency-detail-scorecard.png)

Click **View Details** to [view](#view-dependency-details-of-the-selected-version) the details of the dependency version.

## View dependency details of the selected version

Click the dependency version from the list of dependencies to view the details of the dependency version.

![Dependency details](../../images/dependency-detailversion.png)

You can view the findings for the dependency version under **Findings**.

Select **Dependencies** under **Findings** to view findings of related dependencies.

![Related dependency findings](../../images/dependency-relateddepfindings.png)

Click **Global View** to view details of all the versions of the dependency.

![Global view](../../images/dependency-global.png)

You can select the version from the drop-down list to view the details of the selected version.

![Dependency version](../../images/dependency-versions.png)

### View dependency version overview

Select **Overview** to view the overview of the selected dependency version.

![Dependency overview](../../images/dependency-overview.png)

### View dependent projects

Select **Dependents** to view the projects that depend on the selected dependency version.

![Dependency dependents](../../images/dependency-dependents.png)

### View dependencies of the selected dependency version

Select **Dependencies** to view the dependencies of the selected dependency version.

![Dependency dependencies](../../images/dependency-dependencies.png)

### View dependency graph

Select **Dependency Graph** to view the dependency graph of the selected dependency version.

![Dependency graph](../../images/dependency-graph.png)

## Export dependencies

You can export the list of dependencies to a CSV file for offline analysis.

1. Select **Dependencies** from the left sidebar.
2. Use the search bar to enter search criteria.
3. Click **Add Filter** to filter out dependencies based on specific criteria.
4. Click **Export Dependencies** to export the list of filtered dependencies in a CSV file for offline analysis.

   You can choose the columns to include in your CSV file from the following fields.

   * UUID of the project
   * Ecosystem of the project such as Maven, npm, PyPI, Go, NuGet, or more
   * Name of the dependency
   * Version of the dependency
   * Tags associated with the dependency
   * Reachability of the dependency
   * Is Direct which indicates if the dependency is direct or transitive
   * License information such as file, name, type, URL, and license text from the source code that aligns with a known license’s text
   * Endor scores such as activity, quality, popularity, and security scores
   * Package version name that indicates the fully qualified name of the root package version
   * Package version UUID that indicates the root package’s UUID
   * Project name that indicates the qualified package name of the root package
   * Project UUID that indicates the UUID of the root package
   * Endor patch that indicates if the dependency has an Endor patch available

   ![Export dependencies](../../images/export-dependencies.png)

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

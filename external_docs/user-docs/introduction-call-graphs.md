---
url: https://docs.endorlabs.com/introduction/call-graphs/
title: Call graphs | Endor Labs Docs
downloaded: 2025-11-20 11:48:16
---

Call graphs | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/introduction/call-graphs/_print.html)



# Call graphs

Mitigate open source vulnerabilities with call graph visualizations, pinpointing and understanding the invocation of vulnerable methods for actionable developer insights.

Endor Labs has developed a systematic approach to conduct call graph analysis. Here is a structured overview:

* **Scope Expansion**: Traditional methods of static analysis are typically capable of analyzing a single project at a time. Endor Labs, however, has expanded its scope to include not only the client projects but also their dependencies, often comprising over 100 packages.
* **Enhanced Dependency Analysis**: Endor Labs employs static call graphs to conduct detailed dependency analysis, enabling a comprehensive understanding of how different external components interact within client projects. By leveraging these call graphs, Endor Labs aims to minimize false positives and more accurately identify the specific locations of problems in dependencies.
* **Multiple Data Sources**: To enrich the analysis, Endor Labs uses both source code and binary artifacts. This ensures swift results without a heavy reliance on test coverage.
* **Benchmarking for Continuous Improvement**: Endor Labs maintains accuracy and relevance by using dynamic call graphs internally to benchmark and refine static call graphs, thereby actively identifying and addressing gaps.
* **Scalability**: Addressing the challenge of scalability, Endor Labs generates call graphs not only for each project release but also for all its dependencies. This approach enables effective management of large projects with multiple versions, ensuring that the analysis is both relevant and applicable across the entire spectrum of client dependency sets.

For more information, see [Visualizing the impact of call graphs on open source security](https://www.endorlabs.com/learn/securing-code-with-beautiful-call-graph-visualizations).

Endor Labs uses static call graphs to perform dependency analysis at a fine-grained level. It is minimally intrusive to the developer workflow and provides results during development.

Endor Labs UI provides visualizations of call graphs annotated with vulnerability data and simplified into informative call paths. This empowers developers to identify and address problematic invocations of vulnerable methods efficiently.

Call paths are supported for Java, Python, Rust, JavaScript, Golang, .NET (C#), Kotlin, and Scala.

### View call paths

Endor Labs allows you to view call paths, which represent the sequences of functions invoked during program execution.

1. Select **Projects** from the left sidebar.
2. Select the project for which you want to view the call path.
3. Select **FINDINGS** and select the finding from the list view.
4. Expand a specific finding to view more details.

   ![Call Paths](../../images/call_path.png)
5. In the details section, select **CALL PATHS**.

   ![Call Paths](../../images/callpath_finding.png)

   A finding may have multiple call paths.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

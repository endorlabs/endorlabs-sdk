---
url: https://docs.endorlabs.com/introduction/scores/repository-scores/
title: Package scores | Endor Labs Docs
downloaded: 2026-01-29 22:20:12
---

Package scores | Endor Labs Docs



* Type to search...

[Print entire section](/introduction/scores/repository-scores/_print.html)



# Package scores

Understand how packages are scored in Endor Labs.

Scores provide a high-level, easy-to-understand metric of how well a package does based on factors such as security, activity, popularity, and code quality.

Endor Labs scores are categorized into:

* **Security**: Indicates the number of security-related issues a package may have such as known vulnerabilities, following security best practices when developing code, and the results of static code analysis. Packages with lower security scores can be expected to have many security-related issues when compared with packages with higher scores. See the [factors affecting the security score](../repository-scores/security-score-factors/) for more details.
* **Activity**: Indicates the level of development activity for a package as observed through the source code management system. Packages with higher activity scores will be more active and presumably better maintained when compared to packages with a lower activity score. See the [factors affecting the activity score](../repository-scores/activity-score-factors/) for more details.
* **Popularity**: Indicates how widely a package is used in its ecosystem by tracking both source code management system metrics (for example, the number of stars in GitHub), as well as counting how many other packages import it. A package with a high popularity score indicates that it is used widely. See the [factors affecting the popularity score](../repository-scores/popularity-score-factors/) for more details.
* **Code Quality**: Indicates how well the package complies with best practices for code development and includes the results of static code analysis of that package’s source code. A package with a higher quality score has fewer code issues. See the [factors affecting the code quality score](../repository-scores/code-quality-score-factors/) for more details.

## Input data for score calculation

For calculating scores of vulnerabilities, Endor Labs performs score computation for various entities such as:

* **Repository score** - A repository has a score that captures overall repository activity and properties that span multiple versions of the code.
* **Repository version score** - A repository version has a score that captures details that are specific to a version of the code.
* **Package version score** - A package version that captures the details that are specific to a package version.

The scoring algorithm considers the following input parameters while calculating the scores:

* Data from a version control system such as Git that provides information about files, versions, and their contents.
* Data from a source code management system such as GitHub that provides information about the development activities on a project like issues, pull requests, and more.
* Data from Package managers that provide information about the properties of a package, for example, license, releases, and metadata like the number of stars.
* Data from Vulnerabilities that provide information about known security issues in a package.
* Data from Static code analysis tools that provide information about specific issues in the source code of the package.

### Score range

The scores for each category range between 0 and 10.
For example, a score of 5 indicates inconclusive analysis and the package is neutral. A score higher than 5 indicates that the package mostly has positive factors while a score lower than 5 indicates negative factors.
A score of 10 indicates that the package meets all the positive conditions, while a score of 0 indicates that a package meets all negative conditions.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

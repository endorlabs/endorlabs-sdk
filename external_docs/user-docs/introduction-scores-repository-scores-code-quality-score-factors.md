---
url: https://docs.endorlabs.com/introduction/scores/repository-scores/code-quality-score-factors/
title: Code quality score factors | Endor Labs Docs
downloaded: 2025-11-20 11:50:17
---

Code quality score factors | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/introduction/scores/repository-scores/code-quality-score-factors/_print.html)



# Code quality score factors

Code quality scores provide a view of code quality and adherence to best practices in a repository. Code quality information is based on metadata gathered from a code hosting and version control system such as GitHub and from the source code in the repository.

The following factors have a positive contribution to the code quality score:

* Activity from bot accounts shows that the project is using automation for some development tasks
* The repository has reached 1.0 release status indicating the first major release milestone and is a sign of maturity
* The project includes test code
* Attaching labels to issues allows for better tracking of issue activity in the project
* The repository has multiple files that cover basic operational aspects of the project and this shows a strong emphasis on best practices
* A large fraction of the commits in this repository are verified; this shows that security best practices are followed
* Pull requests from dependency management bot accounts indicate that the project is using automation to keep its dependencies up to date
* Attaching labels to pull requests helps organize the development activity in the project
* Pull requests from bot accounts indicate that the project is using automation for development tasks
* A large faction of the commits in this repository is associated with a pull request; this shows that development best practices are followed
* The repository has released signed artifacts which is a sign of mature security operations
* The use of continuous integration is a sign of good developer practices
* Using GitHub templates to manage issues shows that the development work in the repository is well-organized
* The repository includes badges
* Displaying the Code Coverage badge means that the repository is using code coverage tools in its development process
* Displaying the Core Infra Best Practices badge means that the repository has met a number of best practices requirements
* The repository includes documentation making it easier to understand and use
* The repository has files that cover basic operational aspects of the project and this shows an emphasis on best practices
* The repository uses CI and a high fraction of commits pass the CI checks which is a sign of good code quality
* Displaying the OSSF scorecards badge means that the repository strives to meet the OSSF scorecard checks

The following factors have a negative contribution to the code quality score:

* This package has many instances of likely incorrect code that is associated with coding issues and potential bugs
* This package has many instances of questionable code warnings that are associated with coding issues and potential bugs
* This project has a high number of indirect dependencies compared to the number of direct dependencies; this additional code increases the cost of building the project and its supply chain risk.
* The repository has many major releases in a short amount of time, this is a sign of high churn and potential instability
* Packages where the package manager license information does not agree with the license information found in the code require additional review
* Packages with multiple licenses require extra effort to determine their exact license status
* Multiple unpinned dependencies can significantly increase the risk of a codebase since packages can be updated at any moment
* Many unreachable direct dependencies unnecessarily increase the size of the codebase and the cost of building it
* The project does not have an automated build system
* The repository does not have any of the files that typically explain the basic operational aspects of the project, this may be an indication that the project is not well-maintained
* Packages or source code without license information or a restrictive license can create operational risk
* This release is old and has been superseded by multiple newer releases, it should not be used
* The repository has releases that do not follow the SemVer standard, this goes against best practices
* When a repository contains binary files it is harder to analyze and assess its functionality and risks
* Lack of access to the source code of the project dramatically limits visibility in its quality and adherence to best practices
* The repository has an unusually fast first release

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

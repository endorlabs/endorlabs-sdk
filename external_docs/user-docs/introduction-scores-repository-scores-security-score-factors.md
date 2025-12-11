---
url: https://docs.endorlabs.com/introduction/scores/repository-scores/security-score-factors/
title: Security score factors | Endor Labs Docs
downloaded: 2025-12-11 11:32:40
---

Security score factors | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/introduction/scores/repository-scores/security-score-factors/_print.html)



# Security score factors

Security scores indicate the level of compliance with security best practices as well as vulnerability information for the repository that includes open and fixed vulnerabilities. Vulnerability information is based on `OSV.dev` data and Endor Lab’s vulnerability database.

The following factors have a positive contribution to the security score:

* Critical and high severity vulnerabilities were discovered in the past in the repository but have now been fixed. This indicates that the code base is properly maintained.
* A `SECURITY.md` file highlighting security-related information is a sign of repository maturity.
* A high volume of commits related to vulnerabilities may indicate that the project has many security issues but also that they are actively being addressed. A commit is considered vulnerability-related if it mentions a CVE in its commit message.
* No vulnerabilities ever discovered in a repository indicate that there are no known security issues in the codebase.
* Recently fixed vulnerabilities indicate that the repository has lower security risk and is well maintained.

The following factors have a negative contribution to the security score:

* The package has high activity from invalid accounts.
* The package calls any of the following sensitive APIs more often than an average package.
  + Access to environment information like environment variables, user and host names. Some of this information may be security sensitive, such as environment variables with API keys.
  + Read or write access to the file system. This can be dangerous in combination with user-provided input, for example, lead to path traversal vulnerabilities.
  + Start of operating system processes. This can be dangerous in combination with user-provided input, as it can lead to command or parameter injection vulnerabilities.
  + Dynamic programming techniques like introspection, reflection or dynamic code execution through `eval()` type of functions or script engines.
  + Network functions, for example, to open connections or listen for incoming connection requests. This can be dangerous in combination with user-provided input, for example, lead to data leakage or the load of data from untrusted sources.
  + Cryptographic or encoding/decoding functions. Depending on the specific functions used and the data being processed, export control regulations may apply to downstream users.
* The package contains code patterns or shows behaviors that are known to be used by malware. While this is not a guarantee that the package is malicious, a review of the related code is recommended.
* A high fraction of critical vulnerabilities among the discovered vulnerabilities indicates an elevated security risk and potentially systematic security issues with the codebase.
* A high fraction of high-fix priority vulnerabilities among the discovered vulnerabilities indicates an elevated security risk and that the repository needs immediate maintenance. A vulnerability is considered a high priority based on our analysis.
* A high fraction of high severity or critical vulnerabilities among the discovered vulnerabilities indicates an elevated security risk and potentially systematic security issues with the codebase.
* Taking more time to fix critical vulnerabilities discovered in a repository indicates a lack of regular maintenance. The analysis only considers vulnerabilities associated with this repository and not its dependencies.
* A high fraction of releases with high severity vulnerabilities indicates an elevated security risk and potentially systematic security issues with the codebase.
* The package has many unmerged vulnerability-related pull requests. This means that the project is not actively maintained and may have security issues.
* The repository includes recently discovered vulnerabilities, indicating that the repository’s security risk is increasing.
* A high number of critical or unfixed vulnerabilities discovered in a repository indicates an elevated security risk and potentially systematic security issues with the codebase.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

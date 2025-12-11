---
url: https://docs.endorlabs.com/troubleshooting/endorctl-exitcodes/
title: endorctl CLI exit codes | Endor Labs Docs
downloaded: 2025-12-11 11:31:18
---

endorctl CLI exit codes | Endor Labs Docs



* Type to search...
* ---

# endorctl CLI exit codes

Learn about the exit codes that you may encounter while using the endorctl CLI.

The endorctl exit codes provide the result of the program’s execution, indicating whether it was completed successfully or encountered an error. This page documents the possible endorctl exit code values and the recommended next steps. When contacting support, provide the error code and the error message to help us debug the issue.

To get the exit code, run `echo $?` on the command line prompt.

| Value | Exit Code Name | Description |
| --- | --- | --- |
| 2 | ENDORCTL\_RC\_ERROR | The exact reason for the error could not be determined. |
| 3 | ENDORCTL\_RC\_INVALID\_ARGS | An invalid argument was provided. This may occur due to an invalid parameter value, or an incorrect package format. |
| 4 | ENDORCTL\_RC\_ENDOR\_AUTH\_FAILURE | The user does not have the correct permissions to perform the given operation. Check the Endor Labs token or API keys to make sure they are valid and include the necessary permissions. These are provided using the `--token` flag or through the environment variables `ENDOR_TOKEN`, or `ENDOR_API_CREDENTIALS_KEY/SECRET`. Note that the environment variables are mutually exclusive, that is you cannot have both a token and API keys set at the same time. |
| 6 | ENDORCTL\_RC\_GITHUB\_AUTH\_FAILURE | The user has provided an empty or invalid GitHub token. This token is provided using the `--github-token` flag or through the environment variable `GITHUB_TOKEN`. You can skip the GitHub scan by not setting the `--github` flag. |
| 7 | ENDORCTL\_RC\_ANALYTICS\_ERROR | There was an error analyzing the dependencies. |
| 8 | ENDORCTL\_RC\_FINDINGS\_ERROR | There was an error generating findings based on the analytics output. |
| 9 | ENDORCTL\_RC\_NOTIFICATIONS\_ERROR | There was an error processing a notification triggered by a notification policy. See the error log for details and verify that the corresponding notification target is set up correctly. |
| 10 | ENDORCTL\_RC\_GITHUB\_API\_ERROR | An error was returned by the GitHub API. This can occur due to GitHub rate-limiting or context deadline exceeded. Check the log message to see what object is causing the issue. |
| 11 | ENDORCTL\_RC\_GITHUB\_PERMISSIONS\_ERROR | This error typically occurs when the user is authenticated with GitHub, but does not have the necessary permissions to perform the requested operation. It indicates that the user is forbidden from accessing the requested resource due to insufficient permissions. Check the GitHub token permissions, as well as the permissions and user accounts associated with the repository and/or organization and try again. |
| 12 | ENDORCTL\_RC\_GIT\_ERROR | A Git operation has failed. Examples of Git operations are: cloning, opening, finding the root, finding the HEAD, finding the default branch, and more. Ensure you are scanning the correct Git repository and that it is properly set up for the scan. |
| 13 | ENDORCTL\_RC\_DEPENDENCY\_RESOLUTION\_ERROR | There was an error resolving the dependencies. |
| 14 | ENDORCTL\_RC\_DEPENDENCY\_SCANNING\_ERROR | There was an error processing the resolved dependencies. |
| 15 | ENDORCTL\_RC\_CALL\_GRAPH\_ERROR | There was an error generating the call graph. |
| 16 | ENDORCTL\_RC\_LINTER\_ERROR | There was an error while running the linters used to analyze the source code. This can affect secret and vulnerability detection. |
| 17 | ENDORCTL\_RC\_BAD\_POLICY\_TYPE | An invalid policy was detected. Note that this is not a fatal error, but the policy in question was not processed. See log for details. |
| 18 | ENDORCTL\_RC\_POLICY\_ERROR | There was an error evaluating one or more policies. See log for details. |
| 20 | ENDORCTL\_RC\_INTERNAL\_ERROR | There was an internal error within endorctl. See log for details. |
| 21 | ENDORCTL\_RC\_DEADLINE\_EXCEEDED | The deadline expired before the operation could complete. |
| 22 | ENDORCTL\_RC\_NOT\_FOUND | The requested resource was not found. |
| 23 | ENDORCTL\_RC\_ALREADY\_EXISTS | An attempt to create an entity failed because a resource with the same key already exists. |
| 24 | ENDORCTL\_RC\_UNAUTHENTICATED | The request does not have valid authentication credentials for the operation. |
| 25 | ENDORCTL\_RC\_VULN\_ERROR | There was an issue ingesting and processing vulnerability data. See log for details. |
| 26 | ENDORCTL\_RC\_INITIALIZATION\_ERROR | There was an error initializing the project or the repository. This can happen if the project ingestion token is missing, the project URL is invalid, or authorization failed. See log for details. |
| 27 | ENDORCTL\_RC\_HOST\_CHECK\_FAILURE | The endorctl host-check failed. Host won’t be able to run endorctl scan successfully. See log for details. |
| 28 | ENDORCTL\_RC\_SBOM\_IMPORT\_ERROR | There was an error importing an SBOM. See log for details. |
| 29 | ENDORCTL\_RC\_PRE\_COMMIT\_CHECK\_FAILURE | The pre-commit-checks command discovered one or more leaked secrets. See log for details. |
| 30 | ENDORCTL\_RC\_GH\_ACTION\_WORKFLOW\_SCAN\_FAILURE | There was an error scanning the GitHub action dependencies. See log for details. |
| 31 | ENDORCTL\_RC\_FILE\_ANALYTICS\_ERROR | There was an error reading files for analytics processing. See log for details. |
| 32 | ENDORCTL\_RC\_SIGNATURE\_VERIFICATION\_FAILURE | Signature verification failed. See log for details. |
| 33 | ENDORCTL\_RC\_LICENSE\_ERROR | The requested operation requires additional licensing. See log for details. |
| 34 | ENDORCTL\_RC\_HUGGING\_FACE\_ERROR | There was an error running the HuggingFace scanner. |
| 35 | ENDORCTL\_RC\_SAST\_ERROR | There was an error running the SAST scanner. |
| 36 | ENDORCTL\_RC\_ARTIFACT\_OPERATION\_FAILURE | An error occurred while performing an artifact operation. |
| 37 | ENDORCTL\_RC\_SEGMENTATION\_ERROR | There was an error during file segmentation. |
| 38 | ENDORCTL\_RC\_TOOLCHAIN\_ERROR | An error occurred during the process of generating toolchains. See log for details. |
| 39 | ENDORCTL\_RC\_SANDBOX\_ERROR | An error occurred during endorctl sandbox execution, possibly due to setup or dependency issues. See log for details. |
| 40 | ENDORCTL\_RC\_RULE\_SET\_ERROR | An error occurred when importing rules. See logs for details. |
| 128 | ENDORCTL\_RC\_POLICY\_VIOLATION | One or more “blocking” admission policies were violated. See log for details. |
| 129 | ENDORCTL\_RC\_POLICY\_WARNING | One or more “warning” admission policies were violated. This error code is only returned if the `--exit-on-policy-warning` flag is set. |
| 133 | ENDORCTL\_RC\_EXPORTER\_WARNING | A warning occurred while trying to export data via the configured exporter. Please check your exporter configuration, scan profile setup, and integration status. |

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

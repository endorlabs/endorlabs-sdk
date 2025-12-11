---
url: https://docs.endorlabs.com/endorctl/environment-variables/
title: Global flags and environment variables | Endor Labs Docs
downloaded: 2025-12-11 11:34:25
---

Global flags and environment variables | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/endorctl/environment-variables/_print.html)



# Global flags and environment variables

Use global flags and environment variables to customize and configure endorctl.

Every command-line flag has a corresponding environment variable that can be set instead of the flag, either directly in your environment or in a dedicated configuration file.

See `config-path` description in [Global Flags and Variables](#global-flags-and-variables) and [Set environment variables](#set-endorctl-environment-variables) for details.

To set a command-line flag on the endorctl scan command you can specify the flag with a leading `--` for full flag names or a leading `-` for short flag aliases. If applicable, input arguments are specified after the flag and separated from it with either a blank space or a `=` character. For example, to set the `output-type` specify `--output-type json` or `-o=json`. If the input argument is a list, then the list elements are separated by a `,` character, for example `--languages=go,python`.

## Global flags and variables

The following Global flags are supported and configurable for any `endorctl` command.

| Flag | Environment Variable | Type | Description |
| --- | --- | --- | --- |
| `api` | `ENDOR_API` | string | Set the API URL for the Endor Labs Application (default `https://api.endorlabs.com`). |
| `api-key` | `ENDOR_API_CREDENTIALS_KEY` | string | Set the API key used to authenticate with Endor Labs. |
| `api-secret` | `ENDOR_API_CREDENTIALS_SECRET` | string | Set the secret corresponding to the API key used to authenticate with Endor Labs. |
| `aws-role-arn` | `ENDOR_AWS_CREDENTIALS_ROLE_ARN` | string | Set the target role ARN for AWS based authentication. AWS authentication is only enabled if this flag is set. See our [AWS Keyless Authentication Docs](../../deployment/ci-scans/keyless-authentication/) for details. |
| `bypass-host-check` | `ENDOR_BYPASS_HOST_CHECK` | boolean (default:false) | Bypass the check that verifies that the host machine is correctly set up to use endorctl. |
| `config-path` | `ENDOR_CONFIG_PATH` | string | Set the local file system path to the Endor Labs config directory containing your Endor Labs environment variables. By default, set to `$HOME/.endorctl/config.yaml`. |
| `enable-azure-managed-identity` | `ENDOR_AZURE_CREDENTIALS_MANAGED_IDENTITY_ENABLE` | boolean (default:false) | Enable keyless authentication using Azure VM managed identity system tokens. |
| `enable-github-action-token` | `ENDOR_GITHUB_ACTION_TOKEN_ENABLE` | boolean (default:false) | Enable keyless authentication using GitHub Action OIDC tokens. See the [GitHub documentation on configuring OpenID Connect in cloud providers](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-cloud-providers) for details. |
| `gcp-service-account` | `ENDOR_GCP_CREDENTIALS_SERVICE_ACCOUNT` | string | Set the target service account for GCP based authentication. GCP authentication is only enabled if this flag is set. |
| `log-level` | `ENDOR_LOG_LEVEL` | string | Set the log level. Set to `debug` for debug logs. See also the `--verbose` flag. |
| `namespace` | `ENDOR_NAMESPACE` | string | Set to the namespace of the project that you are working with. |
| `token` | `ENDOR_TOKEN` | string | Set the authentication token used to authenticate with Endor Labs. |
| `verbose` | `ENDOR_LOG_VERBOSE` | boolean (default:false) | Enable verbose logging. |
| `version` | Not applicable |  | Display the `endorctl` client version. |
| Not applicable | `ENDOR_JS_ENABLE_TSSERVER` | boolean (default:false) | Set this environment variable to true to view call graphs for JavaScript/TypeScript projects. |
| Not applicable | `ENDOR_JS_TSSERVER_TIMEOUT` | integer (default:15) | Set the timeout in seconds for `tsserver` responses when generating JavaScript/TypeScript call graphs. The default timeout is 15 seconds. Increase this value if call graph generation times out for large or complex projects. |
| Not applicable | `ENDOR_JS_PACKAGE_MANAGER` | string | Set this environment variable to `npm`, `yarn`, `pnpm`, or `lerna` to override auto detection and force `endorctl` to use a specific JavaScript package manager. |
| Not applicable | `ENDOR_SCAN_SEMGREP_PROGRAM` | string | Set the scan engine to use for SAST scans. Supported values are `semgrep` and `opengrep`. The default value is `opengrep`. You can set this value to `semgrep` to use Semgrep with Endor Labs. See [Use Semgrep with Endor Labs](../../administration/use-semgrep-with-endorlabs/) for more information. |
| Not applicable | `ENDOR_SCAN_ENABLE_PRECOMPUTED_CALLGRAPHS` | boolean (default:false) | Enable pre-computed reachability analysis to analyze your application based on analysis of how your direct dependencies interact with the software they rely on. This provides faster analysis and serves as a fallback when traditional reachability analysis fails. Supported all languages that support reachability except for Golang. |
| Not applicable | `ENDOR_MAVEN_ADDITIONAL_PARAMETERS` | Comma-separated string | Set additional JVM options for Maven dependency resolution in monitoring scans. Parameters are appended to `MAVEN_OPTS`. For example `ENDOR_MAVEN_ADDITIONAL_PARAMETERS=-Xmx4096m,-DskipTests=true`. |
| Not applicable | `ENDOR_GRADLE_ADDITIONAL_PARAMETERS` | Comma-separated string with key-value pairs | Set additional Gradle properties for dependency resolution in monitoring scans. Parameters are added to `gradle.properties`. For example `ENDOR_GRADLE_ADDITIONAL_PARAMETERS=org.gradle.jvmargs=-Xmx4096m,org.gradle.caching=true`. |
| Not applicable | `ENDOR_SCAN_MAVEN_PREPOP_CACHE` | boolean (default:false) | Enable pre-population of Maven local cache for large monorepos to speed up dependency resolution by running `mvn dependency:collect` in parallel before scanning modules. Recommended for projects with more than 100 `pom.xml` files. |

## Set `endorctl` environment variables

To set an environment variable run the following command.

```
export <environment variable>=<value>
```

For example to set the environment variable `ENDOR_TOKEN` to “mytoken” run the following command.

```
export ENDOR_TOKEN=mytoken
```

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

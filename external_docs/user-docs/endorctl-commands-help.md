---
url: https://docs.endorlabs.com/endorctl/commands/help/
title: help | Endor Labs Docs
downloaded: 2026-01-16 09:47:36
---

help | Endor Labs Docs



* Type to search...

[Print entire section](/endorctl/commands/help/_print.html)



# help

Use the help command to get command help for endorctl.

The help command lists all available commands for endorctl scan.

## Examples

```
endorctl help
```

## Usage

```
endorctl help
Endorctl is a command-line tool that allows you to scan and monitor your projects, import and export SBOMs, and interact with the API. Using endorctl you can connect to your Endor Labs tenant and integrate it into your CI pipeline.

Usage:
  endorctl [flags]
  endorctl [command]

Available Commands:
  api         Interact with the Endor Labs API
  completion  Generate the autocompletion script for the specified shell
  help        Help about any command
  host-check  Validate host machine environment and configuration
  init        Initialize or reinitialize endorctl
  recommend   Recommendations for dependency maintenance
  sbom        SBOM operations
  scan        Scan a source code repository
  sync-org    Sync GitHub repositories for a specified organization
  validate    Validate a policy

Flags:
  -a, --api string                   Set the API URL for the Endor Labs Application (default "https://api.endorlabs.com")
      --api-key string               Set the API key used to authenticate with Endor Labs
      --api-secret string            Set the secret corresponding to the API key used to authenticate with Endor Labs
      --aws-role-arn string          Set the target role ARN for AWS based authentication. AWS authentication is only enabled if this flag is set
      --bypass-host-check            Bypass the check that verifies that the host machine is correctly setup to use endorctl
      --config-path string           Set the local filesystem path to the endor config directory containing your endor environment variables
      --enable-github-action-token   Enable keyless authentication using Github action OIDC tokens
      --gcp-service-account string   Set the target service account for GCP based authentication. GCP authentication is only enabled if this flag is set
  -h, --help                         help for endorctl
      --log-level string             Set the log level (default "info")
  -n, --namespace string             Set to the namespace of the project that you are working with
      --token string                 Set the authentication token used to authenticate with Endor Labs
      --verbose                      Enable verbose logging
  -v, --version                      version for endorctl

Use "endorctl [command] --help" for more information about a command.
```

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

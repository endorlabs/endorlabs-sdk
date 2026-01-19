---
url: https://docs.endorlabs.com/secrets-leak-detection/scan-secrets/
title: Scan for secrets | Endor Labs Docs
downloaded: 2026-01-16 09:48:18
---

Scan for secrets | Endor Labs Docs



* Type to search...

[Print entire section](/secrets-leak-detection/scan-secrets/_print.html)



# Scan for secrets

Scan for secrets in your source code

Run `endorctl scan --secrets` to scan for leaked secrets in your source code. You can also scan for secrets with [monitoring scans](../../deployment/monitoring-scans/) and [CI scans](../../deployment/ci-scans/). Ensure that you select **Secrets** as a scan type when you install the Endor Labs App for your SCM to scan for secrets during monitoring scans.

The following table lists the options available with endorctl for secrets scan.

| Flag | Environment Variable | Description |
| --- | --- | --- |
| `secrets` | `ENDOR_SCAN_SECRETS` | Scan source code repository and generate findings for leaked secrets. See also `--git-logs`, `--dependencies`, and `--pre-commit-checks`. |
| `dependencies` | `ENDOR_SCAN_DEPENDENCIES` | Use the `--dependencies` option in secrets scan to perform a regular scan that detects potential secrets in the dependencies. |
| `force-rescan` | `ENDOR_SCAN_FORCE_RESCAN` | Force a full rescan of the historical Git logs for all branches in the repository. Must be used together with `--secrets.` |
| `git-logs` | `ENDOR_SCAN_GIT_LOGS` | Audit the historical Git logs of the repository for all branches in the repository. Must be used together with `--secrets`. |
| `local` | `ENDOR_SCAN_LOCAL` | Scan the local filesystem. Must be used together with `--secrets`. |
| `start-commit` | `ENDOR_SCAN_START_COMMIT` | The start commit of the Git logs of the repository to start scanning from. Must be used together with `--secrets` and `--end-commit`. |
| `end-commit` | `ENDOR_SCAN_END_COMMIT` | The end commit of the Git logs of the repository to end scanning at. Must be used together with `--secrets` and `--start-commit`. |
| `pre-commit-checks` | `ENDOR_SCAN_PRE_COMMIT_CHECKS` | Perform Git pre-commit checks on the changeset about to be committed. Must be used together with `--secrets`. |

## Scan methods

You can perform the following types of scans to detect secrets:

* [**Scan a specific code reference**](#scan-a-specific-code-reference) - Scan for secrets only on a defined path in the context of a checked-out branch, commit SHA or tag to identify secrets and raise findings. This helps you to identify secrets that are leaked in the context of what you are working on right now.
* [**Scan complete history**](#scan-complete-history) - Scan for secrets in all existing branches or tags to identify if a secret has ever been leaked in the history of the project and raise findings. This helps you to identify if any secret has ever been leaked even if it was not leaked in the context of what you are working on right now.
* [**Scan pre-commits**](#scan-pre-commits) - Scan for secrets in the code before committing the code to your repository during the automated pre-commit checks. This helps you identify and remove sensitive information from your code files early in the development life cycle.

### Scan a specific code reference

When starting a secrets scan, this default choice utilizes specified rules to search for patterns on the files located in the path where the scan is initiated.

Run the following command in the directory of the code reference to scan for secrets.

```
endorctl scan --secrets
```

Specify the `--dependencies` option in the secrets scan to perform a regular scan that also scans the dependencies.

```
endorctl scan --secrets --dependencies
```

### Scan complete history

You can scan the Git logs by using the complete history scan. The repository should be present in the scanned path. Endor Labs examines the entire repository history to search for secrets.

To perform a complete scan, include the `--git-logs` option in the command line.

```
endorctl scan --secrets --git-logs
```

Include the `--dependencies` option in the secrets scan to perform a regular dependency scan along with secret scanning.

```
endorctl scan --secrets --git-logs --dependencies
```

The `--git-logs` option scans the repository’s Git logs using the following logic:

* Perform a full scan if it is the first time the repository’s Git log history is scanned.
* Perform a full rescan if a change has been detected to any of the rules in the namespace.
* Perform an incremental scan based on the last time a scan was performed in all the other cases.

Run the following command to force a full rescan if any of the detected secrets are no longer valid, and you want to accurately reflect the state of the secrets.

```
endorctl scan --secrets --force-rescan
```

Specify the `--dependencies` option in the secrets scan to perform a regular scan that also scans the dependencies.

```
endorctl scan --secrets --force-rescan --dependencies
```

### Scan pre-commits

You can check for secrets before committing the code to the repository as part of pre-commit hooks.

You must [install and initialize endorctl](../../endorctl/install-and-configure/) before scanning the pre-commits.

1. Create a `.git/hooks/pre-commit` file at the root of your Git repository to configure the pre-commit hook. It runs automatically when you make a commit and looks for secrets in your commit.

   ```
   cd .git/hooks
   touch pre-commit
   ```
2. Edit the `.git/hooks/pre-commit` and include:

   ```
   #!/bin/bash
   #
   # Script invoked on git commit.
   #
   if ! endorctl scan --pre-commit-checks --secrets; then
      echo "Pre-commit checks failed"
      exit 1
   fi
   echo "No secrets found: Pre-commit checks succeeded"
   ```

   `--pre-commit-checks` performs a pre-commit scan and will scan only the current changes that you are committing to the repository.
3. Set the file permissions to make it executable.

   ```
   chmod +x .git/hooks/pre-commit
   ```

**Note**

You can’t push the `.git/hooks/` folder to the Git repository because it’s only recognized locally on your system. To include the pre-commit code in the Git repository, save it in a different location, like a `hooks/` directory, and then copy it into `.git/hooks/`. This way, you can easily push the hook code to your Git repository.

4. You can set up this hook on other systems in your organization by creating a script and running it on each system.

   ```
   sh setup-hooks.sh
   #!/bin/sh
   # Copy all hooks to .git/hooks
   cp hooks/* .git/hooks/
   chmod +x .git/hooks/*
   ```

**Note**

Endor Labs secret rules come packaged with the `endorctl` binary, so a local secrets scan using the `--pre-commit` flag does not need to connect to Endor Labs services over the internet, making the scan extremely fast. However, this also means the pre-commit scan does not include any custom secret rules added to your namespace.

Here’s an example output when no secrets are found.

![No secrets](../../images/secrets-not-found.png)

Here’s an example when secrets are detected and the commit fails.

![Secrets found](../../images/secrets-found.png)

## Exclude false positives from secret scan

There might be cases where certain lines of code or specific patterns are mistakenly flagged as potential secrets but are safe to include such as test values or non-sensitive information.

To handle such false positives, you can annotate the non-sensitive lines in your source code with `endorctl:allow`.

```
# These are test credentials, safe to commit
username = "test_user"  # endorctl:allow
password = "test_password"  # endorctl:allow
```

## Scan for secrets using regular expression

Endor Labs scans for secrets based on regular expressions that are designed to detect the presence of a secret. It then validates the discovered secrets against external APIs to identify if they are valid. Valid secrets actively provide access to a service or an application and can be used to gain unauthorized access.

Regular expressions are customized to match specific types of secrets, such as GitHub personal access tokens, OAuth access tokens, AWS access tokens, OpenAPI keys, Client IDs, Client Secrets, and more.

For example, you can describe a GitHub Personal Access Token with the following regular expression.

```
github_pat_[0-9a-zA-Z_]{82}
```

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

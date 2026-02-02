---
url: https://docs.endorlabs.com/endorctl/commands/host-check/
title: host-check | Endor Labs Docs
downloaded: 2026-01-29 22:20:42
---

host-check | Endor Labs Docs



* Type to search...

[Print entire section](/endorctl/commands/host-check/_print.html)



# host-check

Use the host check command to verify if your system is appropriately setup to perform a scan.

The command `endorctl host-check` allows you to quickly verify if your system is set up with the appropriate tools to perform a successful scan.

## Usage

To verify that your local host is appropriately configured to scan a given repository:

1. Clone the repository you’d like to verify system setup for. The following instructions should be updated to the repository of your selection.

   ```
   git clone https://github.com/endorlabs/app-java-demo.git
   ```
2. Navigate to the root of the repository you’ve cloned.

   ```
   cd ./app-java-demo
   ```
3. Run the host check command.

   ```
   endorctl host-check
   ```

To verify that your local host is appropriately configured with AI recommendations on how to address any issues perform the following procedure and add the `--droid-gpt` flag to the host check command.

```
endorctl host-check --droid-gpt
```

## Options

The `endorctl host-check` command uses the following flags and environment variables.

| Flag | Environment Variable | Type | Description |
| --- | --- | --- | --- |
| `auth-check-only` | `ENDOR_HOST_CHECK_AUTH_CHECK_ONLY` | boolean (default:false) | Validate authentication credentials only. |
| `droid-gpt` | `ENDOR_HOST_CHECK_DROID_GPT` | boolean (default:false) | Use DroidGPT to generate remediation advice. |
| `name` | `ENDOR_ARTIFACT_NAME` | string | The name of the artifact whose signature needs to be revoked. |
| `path` | `ENDOR_HOST_CHECK_PATH` | string | Set the path to the repository to scan on the local filesystem. For example, `--path=/Users/endorlabs/github/myrepo`. |

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

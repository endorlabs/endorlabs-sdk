---
url: https://docs.endorlabs.com/endorctl/commands/toolchains/
title: toolchains | Endor Labs Docs
downloaded: 2026-01-29 22:20:58
---

toolchains | Endor Labs Docs



* Type to search...

[Print entire section](/endorctl/commands/toolchains/_print.html)



# toolchains

Use the toolchains command to detect the tools in your repository and create a scan profile.

Use the `endorctl toolchains` command to detect the current tools used in your repository. You can also create a scan profile.

**Note**

Toolchain commands are not supported on Windows.

## Usage

* Use the `help` argument to see the options associated with toolchains command.

  ```
  endorctl toolchains --help
  ```

### Detect tools in your repository

Use `endorctl detect` to identify the tools currently used in your repository.
The following arguments can help you refine your scan:

* Use the `-p` argument to define the local filesystem path to the repository you want to scan.

  ```
  endorctl toolchains detect -p <path_to_repository>
  ```
* Use the `--exclude-path` argument to exclude specific file paths or directories.

  ```
  endorctl toolchains detect -p <path_to_repository> --exclude-path 'python/**'
  ```
* Use the `--include-path` argument to limit the scan to a specific file path or directory.

  ```
  endorctl toolchains detect -p <path_to_repository> --include-path 'developement/**'
  ```

### Create a scan profile

Use `endorctl generate` to create a scan profile. See [Configure build tools](../../../scan-with-endorlabs/manage-scan-profiles/build-tools/) for more details.

* Use the `profile-name` argument to assign a name to your profile. This command creates a `.endorctl/scanprofile.yaml` file with the tools in the repository.

  ```
  endorctl toolchains generate -p <path_to_repository>  --profile-name <profile-name>
  ```
* Use the `output-type` argument to specify the format of the output file.

  ```
  endorctl toolchains generate -p <path_to_repository> --profile-name <profile-name> --output-type <output-type>
  ```
* Use the `--output-path` argument to set the location where the output file will be saved.

  ```
  endorctl toolchains generate -p <path_to_repository> --profile-name <profile-name> --output-type json --output-path <output-path>
  ```
* Use the `--create-profile` argument to create and save the scan profile using the specified options.

  ```
  endorctl toolchains generate -p <path_to_repository> --profile-name <profile-name> --create-profile
  ```

## Options

The `endorctl toolchains` command uses the following flags and environment variables:

| Flag | Environment Variable | Type | Description |
| --- | --- | --- | --- |
| `create-profile` | `ENDOR_TOOLCHAINS_CREATE_PROFILE` | boolean (default:false) | Creates and saves the scan profile. |
| `profile-name` | `ENDOR_TOOLCHAINS_PROFILE_NAME` | string | Set the name of the scan profile, for example `development-profile`. |
| `output-type` | `ENDOR_TOOLCHAINS_OUTPUT_TYPE` | string | Set the type of output, for example, use `json` to generate a json file with tool information for your profile. |
| `output-path` | `ENDOR_TOOLCHAINS_OUTPUT_PATH` | string | Set the location to save the output file, for example, `/Desktop/output.json`. |

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

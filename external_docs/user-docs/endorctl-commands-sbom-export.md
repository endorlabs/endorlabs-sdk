---
url: https://docs.endorlabs.com/endorctl/commands/sbom/export/
title: export | Endor Labs Docs
downloaded: 2026-01-26 10:05:54
---

export | Endor Labs Docs



* Type to search...

[Print entire section](/endorctl/commands/sbom/export/_print.html)



# export

Use the sbom export command to export an SBOM for a software package from Endor Labs.

The `sbom export` command allows you to export an SBOM for a specified package from Endor Labs.

## Usage

Run the following command to export an SBOM for a specified package version named `go://github.com/Dreamacro/clash@main` in Endor Labs.

```
endorctl sbom export --package-version-name=go://github.com/Dreamacro/clash@main
```

Run the following command to export an SBOM for a specified package version given its UUID with the UUID of `653c625cd44ec559e19349dc` to a file called `sbom.json`

```
endorctl sbom export --package-version-uuid=653c625cd44ec559e19349dc >> sbom.json
```

## Options

| Flag | Environment Variable | Type | Description |
| --- | --- | --- | --- |
| `component-type` | `ENDOR_SBOM_COMPONENT_TYPE` | string | Set the SBOM component type to `application`, or `library` (default `application`). |
| `output-format` | `ENDOR_SBOM_OUTPUT_FORMAT` | string | Set the SBOM format to `json` or `xml` for CycloneDX, and `json` or `tag-value` for SPDX (`json` is the default for both). |
| `package-version-name` | `ENDOR_SBOM_PACKAGE_VERSION_NAME` | string | Name of the package version for which you want to generate an SBOM. |
| `package-version-uuid` | `ENDOR_SBOM_PACKAGE_VERSION_UUID` | string | The UUID of the package version for which you want to generate an SBOM. |
| `timeout` | `ENDOR_SBOM_TIMEOUT` | string | Set the timeout for the SBOM generation (default `30s`). Use the Go duration format, for example, 30s, 1m. |
| `with-vex` | `ENDOR_SBOM_WITH_VEX` | boolean | Generate the corresponding VEX document along with the SBOM. |
| `project-uuid` | `ENDOR_SBOM_PROJECT_UUID` | string | The UUID of the project for which you want to generate an SBOM. |
| `project-name` | `ENDOR_SBOM_PROJECT_NAME` | string | Name of the project for which you want to generate an SBOM. |
| `app-name` | `ENDOR_SBOM_APP_NAME` | string | Name of the application or the library. Required for multi-package SBOM export. |
| `package-version-uuids` | `ENDOR_SBOM_PACKAGE_VERSION_UUIDS` | string | The list of package version UUIDs to export an SBOM. |

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

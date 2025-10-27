---
url: https://docs.endorlabs.com/endorctl/commands/sbom/import/
title: import | Endor Labs Docs
downloaded: 2025-10-27 12:57:21
---

import | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/endorctl/commands/sbom/import/_print.html)



# import

Use the SBOM import command to import SBOMs to Endor Labs

The `sbom import` command allows you to import SBOMs to Endor Labs to track your third party risk.

## Usage

To import an SBOM to Endor Labs use the following command:

* CycloneDX Format
* SPDX Format

```
endorctl sbom import --sbom-file-path=/path/to/your/sbom.json
```

```
endorctl sbom import --format=spdx --sbom-file-path=/path/to/your/sbom.json
```

## Options

| Flag | Environment Variable | Type | Description |
| --- | --- | --- | --- |
| `format` | `ENDOR_SBOM_FORMAT` | string | Set the SBOM format (`cyclonedx`, or `SPDX`) (default `cyclonedx`) |
| `sbom-file-path` | `ENDOR_SBOM_FILE_PATH` | string | Set the file path to the SBOM to import. |

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

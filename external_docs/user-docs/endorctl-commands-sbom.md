---
url: https://docs.endorlabs.com/endorctl/commands/sbom/
title: sbom | Endor Labs Docs
downloaded: 2026-01-16 09:48:04
---

sbom | Endor Labs Docs



* Type to search...

[Print entire section](/endorctl/commands/sbom/_print.html)



# sbom

Use the sbom command to import or export SBOMs to or from Endor Labs

The `endorctl sbom` command allows you to import or export SBOMs to or from Endor Labs.

## Usage

The syntax of `endorctl sbom` is as follows:

`endorctl sbom [subcommand] [flags]`

The following subcommands are supported as part of `endorctl api`:

* `endorctl sbom import` imports an SBOM to be managed by Endor Labs.
* `endorctl sbom export` allows you to export an SBOM from Endor Labs.

## Options

| Flag | Environment Variable | Type | Description |
| --- | --- | --- | --- |
| `format` | `ENDOR_SBOM_FORMAT` | string | Set the SBOM format (`cyclonedx`, or `spdx`) (default`cyclonedx`). |

---

##### [export](/endorctl/commands/sbom/export/)

Use the sbom export command to export an SBOM for a software package from Endor Labs.

##### [import](/endorctl/commands/sbom/import/)

Use the SBOM import command to import SBOMs to Endor Labs

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

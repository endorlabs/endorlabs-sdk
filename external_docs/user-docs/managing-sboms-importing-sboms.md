---
url: https://docs.endorlabs.com/managing-sboms/importing-sboms/
title: Import SBOMs | Endor Labs Docs
downloaded: 2025-12-11 11:34:26
---

Import SBOMs | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/managing-sboms/importing-sboms/_print.html)



# Import SBOMs

Learn more about software transparency and the role of importing SBOMs in your organization.

Software consumers, or those who use software, need to understand their software inventory holistically. This includes both the software that they create and the software that they purchase. For the software that a software consumer procures, they can request an SBOM to get visibility into the software composition of what they deploy in their environment.

If an information security analyst on your team sends a mass email to all your vendors asking them to provide SBOMs, you are likely to get some combination of confused replies, refusals to hand over anything, and a few incredibly detailed json and XML files. An inbox full of attachments is not the correct way to manage information. Storing these SBOMs in platforms like Google Drive, Dropbox, or any other information repository without active utilization will yield minimal benefits.

Endor Labs’ SBOM hub ingests, parses, analyzes, and tracks your vendor’s SBOMs and offers a structured method to track and version control every SBOM.

## SBOM Hub

SBOM Hub is a central location for software consumers to store, search, and monitor their SBOMs. If you are building out an SBOM program you should visit our blog on [Key questions for your SBOM program](https://www.endorlabs.com/blog/sbom-vex-security-program-operations) to learn more about SBOM best practices and program management.

You can use Endor Labs finding policies to identify vulnerabilities, unmaintained open source software, license risk and outdated dependencies in the SBOMs provided to you by your third-party software vendors.

## Import an SBOM to Endor Labs

Once you have an SBOM from one of your third-party vendors, you should import the SBOM into Endor Labs to monitor and manage it.

### Import SBOMs through the Endor Labs UI

Import your project’s SBOM into the Endor Labs application to discover vulnerabilities and view findings. You can either upload the file from the user interface or through endorctl.

1. Select **SBOM Hub** on the left sidebar.
2. Select **Import SBOM** in the top right-hand corner.
3. Choose **Upload File** and select the type of SBOM you would like to upload.
   * Use CycloneDX if your vendor has provided you with a [CycloneDX format SBOM](https://cyclonedx.org/)
   * Use SPDX if your vendor has provided you with a [SPDX format SBOM](https://spdx.dev/)
4. Click **Browse** to upload your SBOM from your workstation or drag the SBOM into the Endor Labs UI.

Once you have imported your SBOM to Endor Labs, Endor Labs will schedule a scan in the background for the SBOM within the next few hours. To instantly scan the SBOM see [Importing SBOMs through the Endor Labs CLI](#import-sboms-through-the-endor-labs-cli)

**Tip**

Endor Labs supports CycloneDX or SPDX format SBOMs in XML or json format.

### Import SBOMs through the Endor Labs CLI

To import an SBOM to Endor Labs with automation or using the CLI use the following command:

* CycloneDX Format
* SPDX Format

```
endorctl sbom import --sbom-file-path=/path/to/your/sbom.json
```

```
endorctl sbom import --format=spdx --sbom-file-path=/path/to/your/sbom.json
```

See the [SBOM import command for endorctl](../../endorctl/commands/sbom/import/) for more information.

## Manage SBOMs

Manage the SBOMs on the Endor Labs application.

* **Delete SBOM** - Select one or more SBOMs, click the vertical three dots on the right side, then click **Delete SBOM**.
* **Include Tags for an SBOM** - Select one or more SBOMs and click **Edit Tags** on the top right-hand corner. Tags are labels or keywords that you can use to categorize SBOMs. They help classify and group related SBOMs, making it easier to search, filter, and manage the SBOMs. Tags can have a maximum of 63 characters and can contain letters A-Z, numbers (0-9), or any of (=@\_.-) special characters.

### Tagging strategies for SBOMs

To improve your team’s ability to search and manage SBOMs, you can tag them as they are received. Tagging SBOMs helps your team understand the applications, vendors, and their importance to your business.

---

| Use Case | Rationale | Example Tags |
| --- | --- | --- |
| Data Classification | Understand the kind of data a vendor or vendor application handles for you. | `Classification_Restricted`, `Classification_HighlySensitive`, `Classification_Public` |
| Vendor Name | Some SBOMs may lack vendor information. Be sure to label your SBOMs with vendor names for better vendor management. | `Vendor_RedHat` |
| Vendor Criticality | Tag your SBOMs according to your internal vendor tier strategy or if the vendor is considered critical. This will streamline regular SBOM reviews. | `Critical_Vendor`, `Tier1_Vendor` |

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

---
url: https://docs.endorlabs.com/administration/configure-system-settings/
title: Configure system settings | Endor Labs Docs
downloaded: 2025-10-23 23:26:16
---

Configure system settings | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/administration/configure-system-settings/_print.html)



# Configure system settings

Configure Endor Labs application system settings to define the application behavior.

Administrators can configure the following settings to customize certain interactions with Endor Labs. These interactions include:

* [Configure data privacy settings](#configure-data-privacy-settings)
* [Configure Endor patches settings](#configure-endor-patches-settings)
* [Configure policy settings](#configure-policy-settings)
* [Configure SBOM settings](#configure-sbom-settings)
* [Configure CVSS score version](#configure-cvss-score-version)

## Configure data privacy settings

Use data privacy settings to manage how your scan logs are handled to improve monitoring and visibility.

To configure data privacy settings:

1. Navigate to **Manage** > **Settings** from the left sidebar.
2. Select **SYSTEM SETTINGS** > **Data Privacy**.
3. Select **Remote Logging** to send scan logs to a centralized logging system for improved monitoring and debugging.
4. Select **Code Snippet Storage** to store and display code snippets that triggered SAST findings.
5. Select **Code Segment Embeddings and LLM Processing** to use embeddings and LLM processing to improve C/C++ and AI model detection accuracy.
6. Click **Save Data Privacy Settings** to save your changes.\*\*\*\*

![Data Privacy](../../images/enable_embeddings.png)

## Configure Endor patches settings

Use Endor Patches settings to activate auto patching for all your projects in your tenant with the supported ecosystems.

To configure Endor patches settings:

1. Select **Manage** > **Settings** from the left sidebar.
2. Select **SYSTEM SETTINGS** > **Endor Patches**.
3. Select **Auto Patch Vulnerable Dependencies** to apply vulnerability fixes to your applications without changing your code
4. Click **Save Patch Settings**.

#### Note

Changes to auto patching settings may take up to ten minutes to take effect.

![Endor Patches](../../images/settings-endor-patches.png)

## Configure policy settings

Endor Labs comes with several out-of-the-box policies that help you ensure the security posture of your code repositories, detect secret leaks, discern license risks, and make your code compliant with the CIS benchmark.
Endor Labs regularly updates its existing policies and also includes several new policies. Configure policy settings to ensure that you benefit from these regular updates.

To configure policy settings:

1. Navigate to **Manage** > **Settings** from the left sidebar.
2. Select **SYSTEM SETTINGS** > **Policies & Rules**.
3. Select **Enable Policies for New Features** to ensure that new policies released by Endor Labs are automatically enabled for your projects.

   This ensures that the policies are automatically applied and you can view the generated findings.
4. Select **Upgrade Policies to Latest Version** to ensure that any updates released by Endor Labs to the existing policies are automatically applied for your projects.
5. Click **Save Policy Settings**.

![policy settings](../../images/policy-update-settings.png)

## Configure SBOM settings

You can configure organizational settings that will be included in every one of your organization’s SBOMs. These settings allow you to meet NTIA requirements for minimum SBOM data fields which require supplier contact information for your organization.

To define your organization’s SBOM settings:

1. Navigate to **Manage** > **Settings** from the left sidebar.
2. Select **SYSTEM SETTINGS** > **SBOM**.
3. Enter the following organizational SBOM settings as appropriate for your organization under **SBOM Settings**.
   * **Organizational Name** - The organization that supplied the library or application that the SBOM describes.
   * **Contact Name** - A contact at the organization for SBOM related inquiries.
   * **Contact Email Address** - The organizational contact’s email address.
   * **Supplier URL** - The website URL of the organization supplying the SBOM.
4. Click **Save SBOM Settings**.

![SBOM settings](../../images/settings-sbom.png)

## Configure CVSS score version

Endor Labs supports choosing between CVSS v4 and v3 scoring from vulnerability providers so that organizations can standardize their security assessments.

When CVSS v4 is enabled, vulnerability severities are determined using CVSS v4.x scores.

#### Warning

Integrations with Vanta only support CVSS v3. If you are exporting vulnerability details to Vanta, only CVSS v3 data is included.

Endor Labs uses CVSS 3.x to report vulnerabilities by default.

To enable CVSS 4.x scoring:

1. Navigate to **Manage** > **Settings** from the left sidebar.
2. Select **SYSTEM SETTINGS** > **CVSS Version**.
3. Choose **CVSS 4.x**.
4. Click **Save CVSS Version Settings**.

![CVSS settings](../../images/cvss.png)

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

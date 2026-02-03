---
url: https://docs.endorlabs.com/integrations/third-party-integrations/
title: Third-party integrations | Endor Labs Docs
downloaded: 2026-02-03 00:50:14
---

Third-party integrations | Endor Labs Docs



* Type to search...

[Print entire section](/integrations/third-party-integrations/_print.html)



# Third-party integrations

Integrate Endor Labs with third-party security and vulnerability management platforms.

Endor Labs integrates with various third-party security platforms, enabling you to consolidate security data, unify vulnerability management, and streamline your security workflows. These integrations allow third-party platforms to retrieve security findings, packages, projects, and repository data from Endor Labs through the API.

Third-party integrations can retrieve the following data types from Endor Labs:

| Data Type | Description |
| --- | --- |
| Findings | Security vulnerabilities, exposed secrets, and policy violations detected by Endor Labs. |
| Finding definitions | Detailed information about vulnerability definitions, including CVE data and CVSS scores. |
| Packages | Open-source and third-party packages used in your projects. |
| Projects | Scanned applications and their configuration settings. |
| Repositories | Source code repositories linked to your projects. |

## How third-party integrations work

Third-party integrations with Endor Labs use a pull-based model where the external platform connects to the Endor Labs API to retrieve security data.

To set up an integration:

1. Create [API credentials](../../administration/api-keys/) in Endor Labs with read-only access.
2. Configure the connector in the third-party platform with your Endor Labs credentials.
3. Schedule data synchronization to keep the platforms in sync.

## Supported platforms

The following third-party platforms have integrations available with Endor Labs:

* [ArmorCode](#armorcode)
* [Brinqa](#brinqa)
* [Nucleus Security](#nucleus-security)

### ArmorCode

ArmorCode is an Application Security Posture Management (ASPM) platform that helps organizations consolidate security findings from multiple tools, prioritize vulnerabilities, and automate remediation workflows.

Integrate ArmorCode with Endor Labs to retrieve security findings, packages, projects, and repository data for centralized security management and correlation with other security tools.

For more information, refer to [ArmorCode integration](https://www.armorcode.com/blog/armorcode-endor-labs-integration).

### Brinqa

Brinqa is a unified vulnerability management (UVM) platform that helps organizations consolidate security data from multiple sources to construct a comprehensive view of their attack surface.

Integrate Brinqa with Endor Labs to import package, project, repository, and security findings data for centralized risk management and compliance reporting.

For more information, refer to [Brinqa integration](https://docs.brinqa.com/docs/connectors/endor-labs/).

### Nucleus Security

Nucleus Security is a vulnerability management platform that helps organizations aggregate, correlate, and prioritize vulnerabilities from multiple security tools.

Integrate Nucleus Security with Endor Labs to import security findings, packages, and project data for centralized vulnerability management and remediation tracking.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

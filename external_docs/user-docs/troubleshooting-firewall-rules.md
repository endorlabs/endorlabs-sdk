---
url: https://docs.endorlabs.com/troubleshooting/firewall-rules/
title: Firewall & Proxy Rules | Endor Labs Docs
downloaded: 2025-10-27 12:57:17
---

Firewall & Proxy Rules | Endor Labs Docs



* Type to search...
* ---

# Firewall & Proxy Rules

Get information about the firewall and web proxy rules that may be required to use Endor Labs

A web proxy bypass rule or firewall rule with the following information may be required in your environment to use Endor Labs successfully.

| Description | DNS | Direction / IP Address CIDR | Port |
| --- | --- | --- | --- |
| User access to Endor Labs UI | `app.endorlabs.com` | Outbound (Egress): `32.133.71.122/32`, `52.224.62.85/32` | `443` |
| CI system and user access to Endor Labs API and CLI downloads | `api.endorlabs.com` | Outbound (Egress): `34.96.123.220/32`, `52.234.140.241/32` | `443` |
| Access to The Endor Labs OSS API | `api.oss.endorlabs.com` | Outbound (Egress) `52.170.129.128/32` | `443` |
| User access to Endor Labs documentation | `docs.endorlabs.com` | Outbound (Egress): `34.123.199.118/32`, `52.224.70.63/32` | `443` |
| Access to Endor Patches | `factory.endorlabs.com` | Outbound (Egress): `52.224.70.62/32` | `443` |
| Access to Endor Patches | `elprodoss.blob.core.windows.net` | N/A | `443` |

If you have configured integrations with third-party applications like Jira, you may need to configure additional egress rules to complete that integration. Consult the documentation for those applications to add the required rules.

#### Note

For better performance, the Endor Labs client, `endorctl`, may attempt to connect to dynamically managed Endor Labs cloud resources not listed above. Egress restrictions that prevent such connections will not limit Endor Labs’ functionality.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

---
url: https://docs.endorlabs.com/administration/proxy-server-configuration/
title: Configure proxy server settings | Endor Labs Docs
downloaded: 2026-01-26 10:07:56
---

Configure proxy server settings | Endor Labs Docs



* Type to search...

[Print entire section](/administration/proxy-server-configuration/_print.html)



# Configure proxy server settings

Configure proxy settings on machines that need to connect to Endor Labs when Internet access is limited to proxy-only connections.

You must configure proxy settings on machines that need to connect to Endor Labs when Internet access is limited to proxy-only connections. These settings are required for running the endorctl client for scans, for self-hosted runners in CI/CD pipelines, and for using the Endor Labs REST API.

## Configure web proxy

Set the following environment variables as system properties if you use Windows.

```
set HTTP_PROXY=http://username:password@<proxy-host>:<proxy-port>
set HTTPS_PROXY=https://username:password@<proxy-host>:<proxy-port>
```

You can also set the variables as **User Variables** in **System > About > Advanced System Settings > Environment Variables**.

You need to set the following environment variables as system properties if you use Linux or macOS.

```
export HTTP_PROXY=http://username:password@<proxy-host>:<proxy-port>
export HTTPS_PROXY=https://username:password@<proxy-host>:<proxy-port>
```

## Configure proxy for NTLM authentication

If your proxy server uses NTLM authentication, set the following environment variables on machines that need to connect to Endor Labs when Internet access is limited to NTLM authenticated proxy-only connections.

```
export ENDOR_INSECURE_NTLM_USERNAME="your_username"
export ENDOR_INSECURE_NTLM_PASSWORD="your_password"
export ENDOR_INSECURE_NTLM_DOMAIN="your_domain"
export ENDOR_INSECURE_NTLM_PROXY_URL="<PROTOCOL>://<IP>:<PORT>"
```

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

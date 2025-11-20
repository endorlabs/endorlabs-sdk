---
url: https://docs.endorlabs.com/administration/access-endorlabs/authentication-providers/
title: Authentication providers | Endor Labs Docs
downloaded: 2025-11-20 11:48:02
---

Authentication providers | Endor Labs Docs



* Type to search...
* ---

[Print entire section](/administration/access-endorlabs/authentication-providers/_print.html)



# Authentication providers

Learn about authentication providers and their session token durations in Endor Labs.

Authentication through Endor Labs is done through an external identity provider. Some authentication mechanisms are generally designed for human users, while others are designed for machine identities.

Endor Labs supports the following authentication mechanisms for human users.

* **Google** - Authentication is provided through a user’s Google Workspace account.
* **GitHub** - Authentication is provided through a user’s GitHub account.
* **GitLab** - Authentication is provided through a user’s GitLab account.
* **Email** - Authentication is provided through an email link sent to a user.
* **Custom Identity Providers** - An enterprise identity provider such as Okta or VMware One, which uses SAML or OIDC protocol. See [Custom identity providers](../authentication-providers/custom-identity-providers/) for more information.

The following authentication mechanisms designed for machine identities, such as continuous integration or automation systems, are supported.

* **Google Cloud** - With Google Cloud workload identity federation service accounts may be used to federate identity to Endor Labs. See [Keyless authentication](../../../deployment/ci-scans/keyless-authentication/) for more information.
* **GitHub Action OIDC** - With [GitHub Action OIDC](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-cloud-providers) you can federate the identity of your workloads to Endor Labs. See [Keyless authentication](../../../deployment/ci-scans/keyless-authentication/) for more information.
* **AWS Role** - With AWS identity federation your can use the [AWS ARN](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference-arns.html) of the role acts as the identity of a machine user. See [Keyless authentication](../../../deployment/ci-scans/keyless-authentication/) for more information.

## Session duration

The duration of the session token determines how long a user stays authorized in Endor Labs. At the end of the session duration, the user authentication is invalidated and requires reauthentication.

The following table provides the session duration for various authentication providers.

| Authentication provider | Session duration |
| --- | --- |
| Google | 1 hour |
| GitHub | 4 hours |
| GitLab | 2 hours |
| Email | 4 hours |
| Custom IdP | Depends on the session duration set by the IdP |
| API Keys | 4 hours |

The default session token duration for Custom Identity Providers (IdPs) is 4 hours, provided no specific session duration is configured in your IdP. Endor Labs respects the session duration defined in your IdP, after which users must reauthenticate.

For SAML-based integrations, you can set the session duration using the `SessionNotOnOrAfter` attribute. In OIDC, the token expiration claims (`exp`) control the session duration.

The maximum allowed session duration is 4 hours. If your IdP is configured with a session duration exceeding 4 hours, the session will automatically default to a 4-hour limit.

## Feedback

Was this page helpful?

Yes
No

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

Thanks for the feedback. Write to us at support@endor.ai to tell us more.

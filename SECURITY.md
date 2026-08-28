# Security Policy

## Supported versions

Security fixes are published for the **latest PyPI release** of `endorlabs` and for
`main` while it is the active development branch. Older minor lines receive fixes
only when a supported customer or maintainer documents production dependency on that
line.

| Version | Supported |
| ------- | --------- |
| Latest PyPI release (`endorlabs`) | Yes |
| `main` (pre-release integration) | Best-effort until the next tagged release |
| Older PyPI releases | No |

## Reporting a vulnerability

If you believe you have found a security issue in this repository or the published
`endorlabs` package:

1. **Do not** open a public GitHub issue with exploit details.
2. Email **security@endorlabs.com** with a description, affected version, and
   reproduction steps if available.
3. For GitHub-native disclosure, you may also use
   [Private vulnerability reporting](https://github.com/endorlabs/endorlabs-sdk/security/advisories/new)
   on this repository.

We aim to acknowledge reports within a few business days. Coordinated disclosure
timelines depend on severity and fix complexity.

## Secure development

- Release builds use OIDC trusted publishing to PyPI (no long-lived upload tokens
  in CI).
- Pre-commit and CI run secret scanning and portable-example guards on tracked
  content.
- See [CONTRIBUTORS.md](CONTRIBUTORS.md) for local setup; never commit `.env`,
  API keys, or customer tenant identifiers.

# AuthorizationPolicy claim and namespace forms

Companion to [SKILL.md](SKILL.md). Distilled from
[Endor authorization policies](https://docs.endorlabs.com/platform-administration/rbac/authorization-policies)
and SDK model `V1AuthorizationPolicySpec`.

## `target_namespaces`

| Correct | Incorrect |
|---------|-----------|
| One path per list element: `["a.b", "a.c"]` | One CSV blob: `["a.b, a.c"]` |
| Paths use `.` separators (`tenant.child`) | Comma- or semicolon-joined multi-path string |
| Only current namespace or its children | Unrelated tenant roots (API may reject) |

**Customer footgun:** pasting a spreadsheet cell or invitation list as a single
string, e.g.

```text
example-tenant.example-github-a, example-tenant.example-github-b, example-tenant.example-github-c
```

Split on commas (trim whitespace) into separate `target_namespaces` entries.

## `clause`

- Type: `list[str]`; **all** entries must match (AND).
- Typical pattern: claim predicate(s) + IdP tag, e.g.
  `["user=jsmith@gitlab", "gitlab"]`.
- Case-sensitive; restricted character set (see generated model).

### GitHub and GitLab

| UI Key | UI Value | Notes |
|--------|----------|-------|
| `user` | Platform **username/handle** only | Not display name, not email |
| Example | `jsmith` | Becomes stored `user=jsmith@github` / `user=jsmith@gitlab` |

Do **not** enter `jsmith@gitlab` as the Value (double suffix).

### Google

| UI Key | UI Value |
|--------|----------|
| `user` | Full email (`user@company.com`) |
| `domain` | Domain only (`company.com`) |

### Email (magic link)

| UI Key | UI Value |
|--------|----------|
| `email` | Address that receives the link |

Do not use this key to “fix” GitLab/GitHub social login policies.

### Custom IdP (OIDC/SAML)

Use claim **names and values exactly as in the IdP token** (e.g. `groups=…`).
Enterprise SSO planning: sibling skill
`endor-sso-integration-validation-troubleshooting`.

## Cross-check with live identity

After a browser login, `GET /v1/auth` (or `Client.whoami()` + auth payload) shows
the principal Endor evaluated. Compare:

| IdP | Useful fields |
|-----|----------------|
| GitLab | `user.spec.user_name` (handle), `user.meta.name` (`handle@gitlab`) |
| Google | email-shaped `user` claim / identity |
| Any | `tenants[]` — missing expected tenant ⇒ claim or namespace scope mismatch |

“No authorized tenant” with Claims Information on the login page lists the
**exact** USER/EMAIL values to encode — map those through the tables above
(GitLab USER `handle@gitlab` ⇒ UI Value `handle`, not `handle@gitlab`).

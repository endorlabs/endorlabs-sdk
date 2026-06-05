---
name: sso-integration-validation-troubleshooting
description: >-
  Customer-facing workflow for planning, validating, and troubleshooting Endor
  Enterprise SSO integrations. Use when a customer is setting up SSO, validating
  namespace access behavior, or debugging claims-to-authorization mapping.
---

# SSO Integration, Validation, and Troubleshooting

Use this skill when a customer says: "I want to set up SSO."

Focus on platform behavior and configuration outcomes. Do not reference backend code paths.

## Step 1: Intake Questions (ask first)

Collect these inputs before proposing configuration changes:

1. **IdP type and flow**
   - Which IdP is used (Okta, Entra ID/Azure AD, Google Workspace, other)?
   - Which flow(s) are expected (Enterprise Login, provider button, IdP app tile)?
2. **Namespace topology**
   - Root namespace and child namespaces in scope.
   - Which namespace users should enter at login.
3. **Access model**
   - All users see all namespaces, or group-mapped namespace access.
   - Which groups/claims should map to which namespaces.
4. **Policy propagation intent**
   - Should access apply only to exact target namespaces?
   - Should access propagate to child namespaces?
5. **Validation actors**
   - 1-2 real user examples (email + expected namespace access).
   - Group claims expected in IdP assertions/tokens.

## Step 2: Explain Core Platform Behavior

- Enterprise Login and provider buttons on Endor login are SP-initiated.
- Login context is namespace-aware (entered namespace determines effective login context).
- Authentication and authorization are separate:
  - successful SSO handshake does not automatically grant all namespaces,
  - access is granted by authorization policy claim matching and namespace scope.
- Root-targeted policy with `propagate=false` is exact-match authorization only.
- Root UI context can still show aggregated child data in root-scoped views; this does not equal direct child-namespace authorization.

## Step 3: Validation Checklist

1. Confirm effective IdP configuration for intended login namespace.
2. Confirm policy clauses match actual user claims (email, groups, IdP-specific claim values).
3. Confirm `target_namespaces` and `propagate` align with intended scope.
4. Validate expected namespace-switch behavior after login:
   - allowed when claims match policies for target namespace,
   - denied when no matching policy scope exists.
5. Validate no unintended access (especially from broad root-targeted grants).

## Step 4: Spot-Check With Script

Use `sso_access_spotcheck.py` to collect evidence and produce a normalized mapping:

- claim predicates -> target namespaces -> propagation -> implied scope
- direct grants vs propagated subtree grants
- root-context aggregate visibility note

Run:

```bash
uv run --env-file .env python .cursor/skills/sso-integration-validation-troubleshooting/sso_access_spotcheck.py --tenant-hint root --output-dir .endorlabs-context/workspace/sessions/agent/exports
```

Then optionally narrow by actor:

```bash
uv run --env-file .env python .cursor/skills/sso-integration-validation-troubleshooting/sso_access_spotcheck.py --tenant-hint root --target-email user@example.com --target-group group-a --target-group group-b --output-dir .endorlabs-context/workspace/sessions/agent/exports
```

## Step 5: Troubleshooting Decision Tree

### Login succeeds, namespace access missing

- Verify claims present in auth evidence.
- Verify policy clauses are exact and case-correct.
- Verify target namespace is explicitly covered (or propagated parent is covered).

### User can see unexpected child data from root

- Determine whether this is root-context aggregated view behavior.
- Confirm whether child namespace authorization itself is present (explicit or propagated).

### User can access namespace A but not B

- Compare policy clause requirements for A vs B.
- If A and B rely on different claim/provider expectations, user may need separate auth flow that matches B.

### Root policy without propagate question

- `root` target + `propagate=false` does not directly grant child authorization.
- If child data appears in root context, explain aggregate-view behavior separately from direct namespace permissions.

## Deliverable Format for Customers

Always return:

1. Current-state mapping (claims -> namespaces).
2. Gaps between intended and observed access.
3. Minimal policy adjustment recommendation (target namespaces and propagation behavior).
4. Validation steps to confirm the fix with a named test user.

# Finding-age exception (portable Rego example)

Except vulnerability findings whose **Endor discovery age** is at least
`min_age_days` (default **90**).

Age is computed from `Finding.meta.create_time` (when Endor created the
finding), **not** from CVE / advisory `first_published`.

## Files

- [`exception.rego`](exception.rego) — drop-in `POLICY_TYPE_EXCEPTION` rule

## Create

1. Edit `min_age_days` if needed.
2. Create an exception policy with:
   - **Query:** `data.finding_age_exception.match_finding`
   - **Resource kinds:** `Finding`
   - **`disable=true`** until a dry-run looks right
3. Scope with project selectors / tags as needed; enable and rescan when ready.

## Related (not this file)

Severity SLA **admission warn** policies (Critical/High over N days, often with
reachability / EPSS gates) are a different policy type and query shape. This
example is a minimal **exception** on discovery age alone.

## Validation notes

- Policy create/update rejects invalid Rego — prefer that as the compile gate.
- Avoid embedding a `data.<package>` path in Rego comments (PolicyValidation
  may treat it as a data reference).
- Match preview may still need a live finding set; empty preview output does not
  always mean the rule is wrong.

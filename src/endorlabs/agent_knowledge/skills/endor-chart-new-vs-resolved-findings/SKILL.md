---
name: endor-chart-new-vs-resolved-findings
description: Generates cumulative weekly new vs resolved Critical/High reachable vulnerability
  trend charts from FindingLog group-by-time queries (CREATE/DELETE events via endorctl).
  Default window is the past 90 days with complete weeks only. Produces one Cursor
  canvas per namespace root with optional child traverse. Use when the user asks for
  a resolved vs new findings trend chart, FindingLog analytics, or executive vulnerability
  burndown for main-context findings—not for open Finding snapshots, PRF/PV resolution
  reports, or scan pipeline RCA.
---

# Chart new vs resolved findings

Produce **cumulative weekly** New vs Resolved vulnerability trend charts from
**FindingLog** events (`OPERATION_CREATE` = new, `OPERATION_DELETE` = resolved).
One chart (Cursor canvas) per namespace root; include child namespaces with
`--traverse`.

This is the **analytically correct** model (event ledger). It does **not** match
the Endor UI analytics **snapshot** card, which counts open `Finding` records for
"Newly Discovered" while using `FindingLog` DELETE for "Resolved".

## Scope

**In scope**

- FindingLog `group-by-time` queries with **weekly** buckets (default).
- Critical/High reachable vulnerability CREATE vs DELETE event counts.
- Client-side cumulative totals and gap (cumulative New − cumulative Resolved).
- One Cursor canvas per namespace with a cumulative line chart.

**Out of scope**

- Open Finding inventory or per-finding triage → [endor-retrieve-scan-results](../endor-retrieve-scan-results/SKILL.md)
- Tenant-wide PRF approximation / PV resolution errors → [endor-potentially-reachable-analysis](../endor-potentially-reachable-analysis/SKILL.md)
- Scan pipeline regression RCA → [endor-troubleshooting-scans](../endor-troubleshooting-scans/SKILL.md)
- Per-finding reachability proof → [endor-reachability-provenance](../endor-reachability-provenance/SKILL.md)

## When to use

- Cumulative weekly new vs resolved reachable vulnerability trends for a tenant
  namespace (and children).
- Default **rolling 90-day** executive or customer reports with **complete weeks
  only** (exclude the in-progress week and any partial week at the lookback edge).

## Default filters

| Dimension | Filter |
|-----------|--------|
| Category | `spec.finding_categories contains FINDING_CATEGORY_VULNERABILITY` |
| Severity | `spec.level in [FINDING_LEVEL_CRITICAL, FINDING_LEVEL_HIGH]` |
| Reachability | `spec.finding_tags contains [FINDING_TAGS_REACHABLE_FUNCTION, FINDING_TAGS_POTENTIALLY_REACHABLE_FUNCTION]` |
| New | `spec.operation==OPERATION_CREATE` |
| Resolved | `spec.operation==OPERATION_DELETE` |
| Scope | `--traverse` on the namespace root |
| Context | **`context.type==CONTEXT_TYPE_MAIN`** (default). Omit or broaden only when the user explicitly asks to include REF, CI, or all context types. |
| Interval | **`week`** — always use `--group-by-time-interval week`; do not use `month` |
| Window | **Past 90 days, complete weeks only** (see [Default date window](#default-date-window)) |

## Credentials

Use the same credential modes as other tenant workflows:

- `ENDOR_TOKEN`, or `ENDOR_API_CREDENTIALS_KEY` + `ENDOR_API_CREDENTIALS_SECRET`
- Prefer a single credential mode; do not print secrets.
- If API key auth returns 403, retry with token auth only (unset key/secret).

## Default date window

**Goal:** ~90 days of history using **only full weeks** — no partial week at either edge.

Week buckets from `--group-by-time-interval week` align to **UTC week start**
(Sunday 00:00:00Z). Compute bounds before querying:

1. **`windowEnd`** — start of the **current** UTC week (Sunday 00:00:00Z). This is
   the exclusive upper bound; it drops the in-progress week.
2. **`lookbackStart`** — `windowEnd` minus 90 calendar days.
3. **`windowStart`** — if `lookbackStart` is not already a UTC Sunday 00:00:00Z,
   snap **forward** to the next Sunday 00:00:00Z. This drops the partial week at
   the lookback edge.

Use explicit `date(...)` literals in the filter (ISO literals without `date()` often
return empty results):

```text
meta.create_time>=date(<windowStart>) and meta.create_time<date(<windowEnd>)
```

**Example** (today = 2026-06-24, a Wednesday):

| Bound | Value |
|-------|-------|
| `windowEnd` | `2026-06-21T00:00:00Z` (current week start — exclusive) |
| `lookbackStart` | 2026-03-23 |
| `windowStart` | `2026-03-23T00:00:00Z` (already Sunday) |

Result: complete weeks from 2026-03-23 through 2026-06-14 (~13 weeks).

When the user specifies a different range, still **exclude partial weeks** unless
they explicitly ask to include the current or edge partial week. Recompute
`windowStart` / `windowEnd` so every bucket in the chart is a full UTC week.

## Query pattern (endorctl)

Always use **`--group-by-time-interval week`**. Do not use `month`.

Use **separate** group-by-time flags (not the legacy single-string form):

```bash
BASE='meta.create_time>=date(<windowStart>) and meta.create_time<date(<windowEnd>) and context.type==CONTEXT_TYPE_MAIN and spec.finding_categories contains FINDING_CATEGORY_VULNERABILITY and spec.finding_tags contains [FINDING_TAGS_REACHABLE_FUNCTION, FINDING_TAGS_POTENTIALLY_REACHABLE_FUNCTION]'

endorctl api list -r FindingLog -n <namespace> --traverse \
  -f "${BASE} and spec.level in [FINDING_LEVEL_CRITICAL, FINDING_LEVEL_HIGH] and spec.operation==OPERATION_CREATE" \
  --group-by-time \
  --group-aggregation-paths meta.create_time \
  --group-by-time-interval week \
  --group-by-time-mode count \
  --timeout=120s -o json --log-level error
```

Repeat for `OPERATION_DELETE`.

Replace `<namespace>` with the tenant root or child namespace. Use ISO-8601 literals
inside `date(...)` (for example `2026-03-23T00:00:00Z`).

**Other context types:** When the user asks to include REF, CI, or all contexts,
remove `context.type==CONTEXT_TYPE_MAIN` from `BASE` or replace it with an explicit
`context.type in [...]` clause. State the chosen context scope in the chart subtitle
and footnote.

### Custom date windows

| Request | Window |
|---------|--------|
| Default (no range given) | Past 90 days, complete weeks only |
| Custom day or week range | Snap `windowStart` / `windowEnd` to UTC week boundaries so every bucket is a complete week |

Bucket field: `meta.create_time` (skill default). UI time chart uses
`meta.update_time` weekly — document if comparing to UI.

## Timeout fallback

If combined Critical+High query times out (~90–120s), **split by severity** and
sum client-side (four queries: CRITICAL/HIGH × CREATE/DELETE):

```bash
for op in CREATE DELETE; do for lvl in CRITICAL HIGH; do
  endorctl api list -r FindingLog -n <namespace> --traverse \
    -f "${BASE} and spec.level==FINDING_LEVEL_${lvl} and spec.operation==OPERATION_${op}" \
    --group-by-time --group-aggregation-paths meta.create_time \
    --group-by-time-interval week --group-by-time-mode count \
    --timeout=120s -o json --log-level error
done; done
```

Do not set a small `page_size` on log-style lists; cap cost with `--timeout` and
severity split instead. See shipped rule `endor-list-query-performance`.

## Parse API response

Weekly keys in `group_response.groups` look like `"2026-03-23T00:00:00Z"`.
Extract `aggregation_count.count` per bucket. Merge CRITICAL+HIGH when using the
fallback.

**Cumulative series (client-side):**

1. Sort buckets chronologically; drop any bucket outside `[windowStart, windowEnd)`.
2. Build aligned weekly arrays for CREATE and DELETE (0 for missing buckets).
3. `cumulativeNew[i] = sum(weeklyNew[0..i])`, same for Resolved.
4. `gap[i] = cumulativeNew[i] - cumulativeResolved[i]` — widening gap means New
   is outpacing Resolved; narrowing means Resolved is catching up.

## Canvas output

Use a Cursor canvas (`.canvas.tsx`) for interactive charts. Store under the Cursor
project `canvases/` folder (typically `~/.cursor/projects/<repo-slug>/canvases/` —
outside the git repo). Write artifacts under
`.endorlabs-context/workspace/sessions/<user>/exports/` only when the user asks for
a repo-local copy.

### Cumulative weekly line chart (default)

- **Component:** `LineChart` from `cursor/canvas` with `fill`, or custom SVG using
  `useHostTheme()` tokens (no hardcoded hex).
- **Series:** `{ name: "Cumulative New", data: [...], tone: "danger" }` and
  `{ name: "Cumulative Resolved", data: [...], tone: "success" }`
- **Categories:** week-start labels (for example `MM/DD` from each bucket key).
- **Title:** `Cumulative New vs Resolved Reachable Vulnerabilities`
- **Subtitle:** `{namespace} · main context (incl. child namespaces)`
- **Footnote:** FindingLog CREATE/DELETE · Critical/High reachable vulns · main
  context · `{windowStart}` – `{lastCompleteWeek}` · weekly cumulative event counts
  (not unique CVEs) · complete weeks only
- **Gap callout:** start / mid / end cumulative gap and whether the gap is widening
  or narrowing.

Use the **same structure** for every namespace in a multi-namespace request; only
change `namespace`, week labels, and count arrays.

### Filename pattern

`<namespace-slug>-cumulative-weekly-<period>.canvas.tsx`

Example: `<namespace-slug>-cumulative-weekly-past-90d.canvas.tsx`

## Workflow checklist

1. Confirm namespace root(s) and context scope (default **main only**).
2. Compute `windowStart` / `windowEnd` on UTC week boundaries — **complete weeks
   only** (default: past 90 days) unless the user specified another range.
3. Configure credentials; pick token auth if keys fail.
4. Run CREATE and DELETE queries with `--group-by-time-interval week` (or
   severity-split fallback, still `week`).
5. Parse buckets; build cumulative series; verify totals with `--count` if results
   look empty.
6. Write one cumulative weekly canvas per namespace with identical layout.
7. Summarize weekly gap trend + canvas link in chat.

## UI comparison (do not conflate)

| Metric | This skill | UI snapshot card |
|--------|------------|------------------|
| New | FindingLog CREATE events | Open `Finding` count |
| Resolved | FindingLog DELETE events | FindingLog DELETE events |
| Context | `CONTEXT_TYPE_MAIN` (default) | `CONTEXT_TYPE_MAIN` always |

With default filters, context scope aligns with the UI snapshot card. **New** counts
still diverge because the UI uses open `Finding` records, not FindingLog CREATE events.
When the user broadens context beyond MAIN, Resolved totals may also diverge from UI.

## When to use this skill vs others

| Goal | Skill |
|------|-------|
| New vs resolved FindingLog trend chart | **This skill** |
| Current open findings for one project | [endor-retrieve-scan-results](../endor-retrieve-scan-results/SKILL.md) |
| PRF approximation + PV resolution errors | [endor-potentially-reachable-analysis](../endor-potentially-reachable-analysis/SKILL.md) |
| Scan metrics/logs between runs | [endor-troubleshooting-scans](../endor-troubleshooting-scans/SKILL.md) |
| Reachability signal on one finding | [endor-reachability-provenance](../endor-reachability-provenance/SKILL.md) |

## Related skills

| Need | Skill |
| ---- | ----- |
| Finding rows and scan-scoped lists | [endor-retrieve-scan-results](../endor-retrieve-scan-results/SKILL.md) |
| PRF/PV executive report (not FindingLog trends) | [endor-potentially-reachable-analysis](../endor-potentially-reachable-analysis/SKILL.md) |
| Scan pipeline RCA | [endor-troubleshooting-scans](../endor-troubleshooting-scans/SKILL.md) |
| SDK list / group-by errors | [endor-troubleshoot-sdk](../endor-troubleshoot-sdk/SKILL.md) |

## Documentation hops

- Generated resource: [FindingLog](../../../docs/generated-reference/resources/FindingLog.md)
- List performance (log resources): shipped rule `endor-list-query-performance`

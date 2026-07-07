---
name: endor-chart-new-vs-resolved-findings
description: >-
  Generates cumulative weekly new vs resolved Critical/High reachable vulnerability
  trend charts from FindingLog group-by-time queries (CREATE/DELETE events via SDK
  FindingLog.list_groups). Default window is the past 90 days with complete weeks only.
  Produces one Cursor canvas per namespace root with optional child traverse. Use when the
  user asks for a resolved vs new findings trend chart, FindingLog analytics, or
  executive vulnerability burndown for main-context findings—not for open Finding
  snapshots, PRF/PV resolution reports, or scan pipeline RCA.
endorlabs:
  catalog:
    workflow_id: finding-log-weekly-trends
    module: endorlabs.workflows.findings.finding_log_trends
    agent_visible: true
    library_entrypoints:
      - endorlabs.workflows.findings.finding_log_trends.build_finding_log_new_vs_resolved_analysis
      - endorlabs.workflows.logs.group_by_time.group_by_time_counts
      - endorlabs.filters.reachable_vuln_log_base_filter
      - endorlabs.filters.prf_vuln_filter
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
| Scope | Tenant root + traverse by default; prefer a **child namespace** when known (high cost at tenant root) |
| Context | **`context.type==CONTEXT_TYPE_MAIN`** (default). Omit or broaden only when the user explicitly asks to include REF, CI, or all context types. |
| Interval | **`week`** — `ListParameters(group_by_time_interval="week")`; chart library uses weekly buckets only |
| Window | **`--interval week --lookback 13`** (13 complete UTC weeks ≈ past quarter); smoke with `--lookback 1` |

**Online aggregated queries:** Prefer one server-side `group_by_time` traverse query per
operation (CREATE / DELETE) — the API indexes interval buckets. That is ~2 grouped
queries for the default path. Fall back to parallel per-project shards only on
504/deadline. Do **not** paginate all FindingLog rows or run `endor-estate pull` for this chart.

**Artifact-first:** If `{namespace-slug}-new-vs-resolved-analysis.json` already exists, run `generate_canvas.py` / `run_report.py` to refresh the canvas without re-querying the API unless filters or window changed.

## Credentials

Use the same credential modes as other tenant workflows:

- `ENDOR_TOKEN`, or `ENDOR_API_CREDENTIALS_KEY` + `ENDOR_API_CREDENTIALS_SECRET`
- Prefer a single credential mode; do not print secrets.
- If API key auth returns 403, retry with token auth only (unset key/secret).

## Default date window

**Goal:** A fixed number of **complete** interval buckets — no partial bucket at either edge.

Use endorctl-style aliases for the aggregation interval and a **lookback count** (number of
complete buckets), not calendar-day integers:

| CLI / SDK | Meaning |
| --------- | ------- |
| `--interval week` | `group_by_time_interval="week"` → `GROUP_BY_TIME_INTERVAL_WEEK` on the wire |
| `--lookback 13` | 13 complete UTC weeks before the current (in-progress) week |
| `--lookback 1` | Quick smoke: one complete week |

Week buckets align to **UTC week start** (Sunday 00:00:00Z). Compute bounds before querying:

1. **`windowEnd`** — start of the **current** UTC week (Sunday 00:00:00Z). Exclusive upper bound.
2. **`windowStart`** — `windowEnd` minus `lookback` full weeks.

Filter (explicit `date(...)` literals — ISO without `date()` often returns empty rows):

```text
meta.create_time>=date(<windowStart>) and meta.create_time<date(<windowEnd>)
```

**Example** (today = 2026-06-24, a Wednesday, `--interval week --lookback 13`):

| Bound | Value |
|-------|-------|
| `windowEnd` | `2026-06-22T00:00:00Z` (current week start — exclusive) |
| `windowStart` | `2026-03-23T00:00:00Z` (13 weeks earlier) |

Result: 13 complete weeks ending the week of 2026-06-15.

## Query pattern (SDK)

Library: `endorlabs.workflows.findings.finding_log_trends.build_finding_log_new_vs_resolved_analysis`.
Generic aggregation primitive: `endorlabs.workflows.logs.group_by_time.group_by_time_counts`.
Filters: `endorlabs.filters.reachable_vuln_log_base_filter()`.

Bundled script (preferred for agents):

```bash
uv run python agent-knowledge/skills/endor-chart-new-vs-resolved-findings/scripts/run_analysis.py <namespace>
```

Uses `client.FindingLog.list_groups(..., list_params=ListParameters(group_by_time=True, ...))`
with **weekly** buckets (`group_by_time.interval=GROUP_BY_TIME_INTERVAL_WEEK` on the wire).
Pass `--no-traverse` to scope a single namespace path. Pass `--interval week --lookback 1` for a
short validation window (one complete week).
Default SDK read timeout: `--timeout 120` (seconds). On 504/deadline, the library
splits Critical+High into separate aggregate queries, then falls back to parallel
project-namespace shards (`--max-workers`, default 12).

Replace `<namespace>` with the tenant root or child namespace.

**Manual SDK example:**

```python
import endorlabs
from endorlabs.workflows.findings.finding_log_trends import (
    build_finding_log_new_vs_resolved_analysis,
)

client = endorlabs.Client(tenant="<namespace>", timeout=120.0)
analysis = build_finding_log_new_vs_resolved_analysis(client, "<namespace>", traverse=True)
```

**Other context types:** When the user asks to include REF, CI, or all contexts,
adjust the base filter (see `endorlabs.filters`) or replace
`context.type==CONTEXT_TYPE_MAIN` with an explicit `context.type in [...]` clause.
State the chosen context scope in the chart subtitle and footnote.

### Custom date windows

| Request | Window |
|---------|--------|
| Default (no range given) | Past 90 days, complete weeks only |
| Custom day or week range | Snap `windowStart` / `windowEnd` to UTC week boundaries so every bucket is a complete week |

Bucket field: `meta.create_time` (skill default). UI time chart uses
`meta.update_time` weekly — document if comparing to UI.

## Timeout fallback

If combined Critical+High query times out, the library **splits by severity** and
sums client-side (four queries: CRITICAL/HIGH × CREATE/DELETE). Do not set a small
`page_size` on log-style lists; cap cost with `--timeout` and severity split instead.
See shipped rule `endor-list-query-performance`.

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

## Analysis JSON contract (canvas input)

Producer: `endorlabs.workflows.findings.finding_log_trends.build_analysis` (via
`build_finding_log_new_vs_resolved_analysis`). Consumer:
`generate_canvas.render_canvas`.

**Artifact file:** `{namespace-slug}-new-vs-resolved-analysis.json`

**Canvas-required keys** (enforced by `validate_chart_analysis`):

| Key | Role |
|-----|------|
| `namespace` | Chart title and component name |
| `categories` | X-axis labels (`MM/DD` per week) |
| `cumulative_new` / `cumulative_resolved` | Y-axis cumulative series (equal length to `categories`) |
| `finding_criteria` | Footnote filter summary |
| `period_caption` | Human-readable inclusive date range |
| `gap_start`, `gap_mid`, `gap_end` | Cumulative gap callout values |
| `gap_mid_label`, `gap_end_label` | Week labels for mid/end gap |
| `gap_trend` | `widening` / `narrowing` / `stable` |
| `interval` | `group_by_time` alias used for buckets (chart: `week`) |
| `lookback` | Number of complete interval buckets in the window |
| `lookback_days` | Derived span in days (informational; legacy JSON may omit `interval`/`lookback`) |

**Metadata** (written by producer; canvas ignores): `window_start`, `window_end`,
`last_complete_week`, `weekly_new`, `weekly_resolved`, `weeks`, `gaps`,
`severity_split`, `context_type`, `generated_at`.

**Filename:** `chart_canvas_filename(namespace, interval=…, lookback=…)` →
`<namespace-slug>-cumulative-<interval>-past-<lookback>.canvas.tsx`

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

Example: `<namespace-slug>-cumulative-weekly-past-90d.canvas.tsx` (90 from
`lookback_days` in the analysis JSON when using the default window).

## Workflow checklist

1. Confirm namespace root(s) and context scope (default **main only**).
2. Compute `windowStart` / `windowEnd` on UTC week boundaries — **complete weeks
   only** (default: past 90 days) unless the user specified another range.
3. Configure credentials; pick token auth if keys fail.
4. Run `build_finding_log_new_vs_resolved_analysis()` (or `run_analysis.py`) for
   weekly CREATE/DELETE `FindingLog.list_groups` queries; library applies
   severity-split fallback on 504/deadline.
5. Verify bucket keys align with the UTC week grid; re-check namespace scope if
   results look empty.
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

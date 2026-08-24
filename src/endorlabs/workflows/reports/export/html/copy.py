"""Executive-facing UI copy for report packet HTML (portable, generic)."""

from __future__ import annotations

H1_ONBOARDING = "Organization onboarding"

H1_VERSION_SPRAWL = "Dependency version sprawl"

H1_SCA_BURNDOWN = "SCA burndown"

H1_FINDINGS_BURNDOWN = H1_SCA_BURNDOWN  # compat alias

H1_SAST_BURNDOWN = "SAST burndown"

H1_ENDOR_PATCHES = "Endor Patches"

PURPOSE_ENDOR_PATCHES = (
    "Highest-impact dependency families with Endor Patch coverage, ranked by "
    "severity- and reach-weighted Available risk (confirmed function-reachable "
    "boosted; potentially reachable is not treated as reachable). Families "
    "group on the vulnerable library current version. Packet Available includes "
    "any reachability; the product Patches dashboard header is RF or PRF only. "
    "Click a family for the per-version heat map and use the impact calculator "
    "for top-K closure."
)


PURPOSE_ONBOARDING = (
    "How repositories were registered over time, how MAIN (~90d) and PR (~30d) "
    "scan cadence kept up, and which project tags / projects lead by full-scan "
    "activity. Analytics-only ScanResults are excluded by default."
)

PURPOSE_VERSION_SPRAWL = "How many distinct package versions are in use, and where version sprawl concentrates."

PURPOSE_SCA_BURNDOWN = (
    "Weekly new versus resolved vulnerability (SCA) FindingLog CREATE/DELETE "
    "events by reachability selection — default RF+PRF, with RF / PRF / RD / "
    "PRD / RD+PRD and unreachable options — plus main-context scan activity. "
    "Severity defaults to High and higher; switch to Medium and higher or All "
    "severities to include Medium/Low bands."
)

PURPOSE_FINDINGS_BURNDOWN = PURPOSE_SCA_BURNDOWN  # compat alias

PURPOSE_SAST_BURNDOWN = (
    "Weekly new versus resolved OpenGrep, AI-SAST, and Secrets FindingLog "
    "CREATE/DELETE events. OpenGrep and AI-SAST share triage facets "
    "(all / true_positive / false_positive); Secrets uses valid/invalid only "
    "(no TP/FP). OpenGrep excludes FINDING_TAGS_AI; AI-SAST requires it. "
    "Severity defaults to High and higher (Critical–Low available via "
    "Medium+ / All). Same namespace and project-tag filters as SCA burndown."
)


STAT_WINDOW_NET = "Window net (CREATE−DELETE)"

PENDING_TAG_CAPTION = "Trend charts not loaded for this tag yet; project and scan counts below still apply."

MAIN_THROUGHPUT_LABEL = "Main-context scans (activity proxy)"

AVG_SCANS_PER_PROJECT_LABEL = "Avg MAIN scans / project"

TAG_HELP = "Project tags from Project.meta.tags"

GAP_DIFF_HELP = (
    "Current gap is today’s window-net (CREATE−DELETE). Period Δ is end − start "
    "over the lookback: + widens (worse), − narrows (better). Color carries the sign."
)

TAG_LEADERS_NARROWING = "Tags narrowing fastest (best period delta)"

TAG_LEADERS_WIDENING = "Tags widening fastest (worst period delta)"


GLOSSARY_HTML = """

<div class="glossary">

  <div class="glossary-title">How to read these metrics</div>

  <ul>

    <li><strong>Version sprawl</strong> counts distinct package names and resolved

      versions from DependencyMetadata. Filter by direct vs transitive

      (<code>spec.dependency_data.direct</code>) and public vs private

      (<code>spec.dependency_data.public</code>). The per-ecosystem table follows

      the same relation/visibility scope.</li>

    <li><strong>Onboarding cadence</strong> uses ScanResult counts: MAIN
      <code>TYPE_ALL_SCANS</code> (full repo scans, ~90d) and
      <code>CONTEXT_TYPE_CI_RUN</code> (PR scans, ~30d retention). Opt-out <em>Exclude analytics</em> (on by default) drops
      <code>TYPE_ANALYTICS</code> / <code>TYPE_ANALYTICS_CHECK</code> from the
      MAIN weekly series. Tag filter
      scopes registration, hierarchy, scan-count tiles, and cadence
      leaderboards; the weekly chart remains organization-wide. CI/PR appears as
      secondary bars plus a disconnected trend line over the recent ~30d only.</li>

    <li><strong>Window net (CREATE−DELETE)</strong> is cumulative FindingLog creates

      minus deletes inside the lookback window only. It can be negative when older

      findings are resolved in-window. It is not an open Finding inventory count.</li>

    <li><strong>Current gap</strong> is today’s window-net. <strong>Period Δ</strong> is end − start over the lookback (<code>+240</code> widens, <code>-420</code> narrows). Tag leaders rank by period Δ; color encodes direction.</li>

    <li><strong>Project tags</strong> come from <code>Project.meta.tags</code>

      (organization labels). They are separate from finding reachability or triage tags.</li>

    <li><strong>SCA burndown</strong> filters vulnerability FindingLog events by

      reachability selection (RF+PRF default; RF / PRF / RD / PRD /

      RD+PRD / unreachable). Severity uses cumulative

      thresholds (Critical / High and higher / Medium and higher /

      All severities).</li>

    <li><strong>SAST burndown</strong> covers OpenGrep vs AI-SAST (shared TP/FP

      triage facets) and Secrets (valid/invalid only; no TP/FP), with

      the same severity thresholds. CodeOwners filtering is not included in this

      packet (FindingLog has no code_owners field).</li>

    <li><strong>Main-context scans</strong> count ScanResult events with

      <code>CONTEXT_TYPE_MAIN</code> — a cadence proxy, not the number of main branches.

      <strong>Avg MAIN scans / project</strong> is total MAIN scans in the window

      divided by projects in scope. Scan history bounds (newest/oldest ScanResult)

      are observed from the tenant and shown as context for the window.</li>

  </ul>

</div>

"""


README_TEXT = """Endor Labs executive report packet

=================================



Open the HTML files in a browser (no Endor App login required for viewing).



Reports

-------

01-onboarding.html         Organization onboarding over time

02-version-sprawl.html     Dependency version sprawl

03-sca-burndown.html       SCA burndown (vulnerability FindingLog)

04-sast-burndown.html      OpenGrep / AI-SAST / Secrets burndown (FindingLog)

05-endor-patches.html      Endor Patches impact (Available / To Request)



Raw exports (data/)

-------------------

packet.cube.json                 Full interactive cube (source of truth)

onboarding-weekly.csv            Weekly registration counts

onboarding-hierarchy.csv         Namespace hierarchy rollups

onboarding-cadence-weekly.csv    MAIN full / with-analytics / CI weekly scans

onboarding-cadence-by-tag.csv    Tag ranks by MAIN full + CI cadence

onboarding-cadence-by-project.csv Project ranks by MAIN full + CI cadence

tag-catalog.csv                  Project.meta.tags catalog + series status

path-gap-differentials.csv       SCA path × severity × reach gap deltas

tag-gap-differentials.csv        SCA tag × path × severity × reach gap deltas

code-path-gap-differentials.csv  Code findings path × category × facet gaps

code-tag-gap-differentials.csv   Code findings tag × category × facet gaps

throughput-by-tag.csv            Main/CI scan throughput by tag

version-sprawl-top-packages.csv  Top packages by distinct version count

patches-top-families.csv         Endor Patches top families by Available risk

patches-versions.csv             Endor Patches family × version heat-map rows

patches-units-ranked.csv         Endor Patches package@version units

EXPORTS.txt                      This file list



Filters

-------

Namespace and Project tag controls appear at the top of each interactive report.

Project tags are discovered from Project.meta.tags for this tenant.

SAST burndown adds category (OpenGrep / AI-SAST / Secrets) and facet controls
(TP/FP on OpenGrep and AI-SAST; valid/invalid on Secrets).

Severity on SCA and SAST burndown uses cumulative thresholds:

Critical / High and higher (default) / Medium and higher /

All severities (Critical–Low).



Metric notes

------------

- Window net (CREATE−DELETE): cumulative new minus resolved FindingLog events

  inside the lookback window. May be negative. Not open Finding inventory.

- Current gap: today’s window-net. Period Δ: end − start (e.g. +240 /

  -420). Tag leaders rank by period Δ; color encodes direction.

- Main-context scans: ScanResult events with CONTEXT_TYPE_MAIN (activity proxy).

  Avg MAIN scans / project = window MAIN scans ÷ projects in scope.

  Packet also records observed newest/oldest ScanResult times (retention context).

- Tags marked "series pending" have project/scan counts but no FindingLog trend

  yet (cost-controlled pull; raise min-projects or wait for a fuller pull).



Generated by the Endor Labs SDK. This packet is not the live product UI.

"""

README_PATCHES_ONLY_TEXT = """Endor Labs — Endor Patches report

==================================



Open 05-endor-patches.html in a browser (no Endor App login required).



This is a --patches-only run: the onboarding, version sprawl, and burndown

pages are intentionally absent because their data was never collected. Run

`endor-reports packet -n <namespace>` without --patches-only for the full

five-page executive packet.



Reports

-------

05-endor-patches.html      Endor Patches impact (Available / To Request)



Raw exports (data/)

-------------------

packet.cube.json                 Patches cube (source of truth)

patches-top-families.csv         Top dependency families by Available risk

patches-versions.csv             Family × version heat-map rows

patches-units-ranked.csv         package@version units ranked by risk

EXPORTS.txt                      This file list



Metric notes

------------

- Scope: Critical + High vulnerability findings in main context, not

  dismissed, any reachability. The product Patches dashboard Available

  header is RF or PRF only.

- Families group on the vulnerable library current version

  (target_dependency_*), not upgrade_list / UIA bump packages.

- Available: an Endor Patch exists today. To Request: a fix or upgrade path

  exists but patch coverage is incomplete (inferred, not a platform enum).

- Risk weights severity by reachability; the formula is shown on the page.

  CSV column "reachable" is RF-only; use reachable_function and

  potentially_reachable_function for RF vs PRF.



Generated by the Endor Labs SDK. This report is not the live product UI.

"""

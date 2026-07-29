"""Executive-facing UI copy for report packet HTML (portable, generic)."""

from __future__ import annotations

H1_ONBOARDING = "Organization onboarding"

H1_VERSION_SPRAWL = "Dependency version sprawl"

H1_SCA_BURNDOWN = "SCA burndown"

H1_FINDINGS_BURNDOWN = H1_SCA_BURNDOWN  # compat alias

H1_SAST_BURNDOWN = "SAST burndown"


PURPOSE_ONBOARDING = (
    "How repositories were registered over time, how MAIN and PR scan cadence "
    "kept up (~90d), and which project tags / projects lead by full-scan activity. "
    "Analytics-only ScanResults are excluded by default."
)

PURPOSE_VERSION_SPRAWL = "How many distinct package versions are in use, and where version sprawl concentrates."

PURPOSE_SCA_BURNDOWN = (
    "Weekly new versus resolved vulnerability (SCA) FindingLog CREATE/DELETE "
    "events by reachability — default RF+PRF, with PRD and unreachable "
    "function/dependency filters — plus main-context scan activity. Severity "
    "defaults to High and higher; switch to Medium and higher or All severities "
    "to include Medium/Low bands."
)

PURPOSE_FINDINGS_BURNDOWN = PURPOSE_SCA_BURNDOWN  # compat alias

PURPOSE_SAST_BURNDOWN = (
    "Weekly new versus resolved SAST, AI-SAST, and Secrets FindingLog "
    "CREATE/DELETE events. SAST uses triage tags (true/false positive); "
    "AI-SAST is FINDING_CATEGORY_SAST + FINDING_TAGS_AI; Secrets uses "
    "valid/invalid secret tags. Severity defaults to High and higher "
    "(Critical–Low available via Medium+ / All). Same namespace and "
    "project-tag filters as SCA burndown."
)


STAT_WINDOW_NET = "Window net (CREATE−DELETE)"

PENDING_TAG_CAPTION = "Trend charts not loaded for this tag yet; project and scan counts below still apply."

MAIN_THROUGHPUT_LABEL = "Main-context scans (activity proxy)"

AVG_SCANS_PER_PROJECT_LABEL = "Avg MAIN scans / project"

TAG_HELP = "Project tags from Project.meta.tags"

GAP_DIFF_HELP = (
    "Gap differential is window-net at end of lookback minus start "
    "(CREATE−DELETE movement). Negative = narrowing; positive = widening."
)

TAG_LEADERS_NARROWING = "Tags narrowing fastest (best gap differential)"

TAG_LEADERS_WIDENING = "Tags widening fastest (worst gap differential)"


GLOSSARY_HTML = """

<div class="glossary">

  <div class="glossary-title">How to read these metrics</div>

  <ul>

    <li><strong>Version sprawl</strong> counts distinct package names and resolved

      versions from DependencyMetadata. Filter by direct vs transitive

      (<code>spec.dependency_data.direct</code>) and public vs private

      (<code>spec.dependency_data.public</code>). The per-ecosystem table follows

      the same relation/visibility scope.</li>

    <li><strong>Onboarding cadence</strong> uses ScanResult counts over ~90 days:

      MAIN <code>TYPE_ALL_SCANS</code> (full repo scans) and

      <code>CONTEXT_TYPE_CI_RUN</code> (PR scans). Toggle <em>Include analytics</em>

      to add <code>TYPE_ANALYTICS</code> / <code>TYPE_ANALYTICS_CHECK</code> into the

      MAIN weekly series. Tag filter scopes registration, hierarchy, and

      cadence leaderboards; the weekly scan chart remains organization-wide.</li>

    <li><strong>Window net (CREATE−DELETE)</strong> is cumulative FindingLog creates

      minus deletes inside the lookback window only. It can be negative when older

      findings are resolved in-window. It is not an open Finding inventory count.</li>

    <li><strong>Gap differential</strong> is end window-net minus start window-net

      for the lookback. Example: Widening (+240) / Narrowing (−420). Rankings below

      the charts use this signed delta across project tags.</li>

    <li><strong>Project tags</strong> come from <code>Project.meta.tags</code>

      (organization labels). They are separate from finding reachability or triage tags.</li>

    <li><strong>SCA burndown</strong> filters vulnerability FindingLog events by

      reachability (RF / PRF / PRD / unreachable). Severity uses cumulative

      thresholds (Critical and higher / High and higher / Medium and higher /

      All severities).</li>

    <li><strong>SAST burndown</strong> covers OpenGrep SAST (triage TP/FP), AI-SAST

      detection (<code>FINDING_TAGS_AI</code>), and Secrets (valid/invalid), with

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

04-sast-burndown.html      SAST / AI-SAST / Secrets burndown (FindingLog)



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

EXPORTS.txt                      This file list



Filters

-------

Namespace and Project tag controls appear at the top of each interactive report.

Project tags are discovered from Project.meta.tags for this tenant.

SAST burndown adds category (SAST / AI-SAST / Secrets) and facet controls.

Severity on SCA and SAST burndown uses cumulative thresholds:

Critical and higher / High and higher (default) / Medium and higher /

All severities (Critical–Low).



Metric notes

------------

- Window net (CREATE−DELETE): cumulative new minus resolved FindingLog events

  inside the lookback window. May be negative. Not open Finding inventory.

- Gap differential: end window-net minus start (e.g. Widening (+240) /

  Narrowing (−420)). Tag leaderboards rank this signed delta.

- Main-context scans: ScanResult events with CONTEXT_TYPE_MAIN (activity proxy).

  Avg MAIN scans / project = window MAIN scans ÷ projects in scope.

  Packet also records observed newest/oldest ScanResult times (retention context).

- Tags marked "series pending" have project/scan counts but no FindingLog trend

  yet (cost-controlled pull; raise min-projects or wait for a fuller pull).



Generated by the Endor Labs SDK. This packet is not the live product UI.

"""

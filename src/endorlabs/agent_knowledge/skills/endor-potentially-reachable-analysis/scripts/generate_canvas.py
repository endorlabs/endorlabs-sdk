#!/usr/bin/env python3
"""Generate PRF canvas TSX from analysis JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from paths import resolve_canvas_dir


def js_string(value: str) -> str:
    return json.dumps(value)


def render_breakdown_rows(rows: list[dict]) -> str:
    if not rows:
        return "[]"
    parts = []
    for row in rows:
        parts.append(
            "      {\n"
            f"        count: {row['count']},\n"
            f"        matching_rule: {js_string(row['matching_rule'])},\n"
            f"        explanation: {js_string(row['explanation'])},\n"
            f"        fixable_notes: {js_string(row['fixable_notes'])},\n"
            f"        fixable: {js_string(row['fixable'])},\n"
            f"        prf_vulnerabilities: {row['prf_vulnerabilities']},\n"
            f"        prd_vulnerabilities: {row['prd_vulnerabilities']},\n"
            f"        precomputed_reachability_pvs: {row['precomputed_reachability_pvs']},\n"
            "      }"
        )
    return "[\n" + ",\n".join(parts) + "\n    ]"


def render_ecosystem_errors(ecosystem_errors: dict) -> str:
    parts = []
    for eco, data in ecosystem_errors.items():
        parts.append(
            f"  {js_string(eco)}: {{\n"
            f"    dep_resolution_error_pvs: {data['dep_resolution_error_pvs']},\n"
            f"    dep_resolution_breakdown: {render_breakdown_rows(data['dep_resolution_breakdown'])},\n"
            f"    call_graph_pvs: {data['call_graph_pvs']},\n"
            f"    call_graph_breakdown: {render_breakdown_rows(data['call_graph_breakdown'])},\n"
            "  }"
        )
    return "{\n" + ",\n".join(parts) + "\n}"


def render_summary_rows(rows: list[dict]) -> str:
    parts = []
    for row in rows:
        total = ",\n    isTotal: true" if row.get("isTotal") else ""
        parts.append(
            "  {\n"
            f"    ecosystem: {js_string(row['ecosystem'])},\n"
            f"    prfVulnerabilities: {row['prfVulnerabilities']},\n"
            f"    prdVulnerabilities: {row['prdVulnerabilities']},\n"
            f"    approximatedVulns: {row['approximatedVulns']},\n"
            f"    notApproximatedVulns: {row['notApproximatedVulns']},\n"
            f"    pctApproximatedVulns: {row['pctApproximatedVulns']},\n"
            f"    uniquePvs: {row['uniquePvs']},\n"
            f"    pvsWithDepResolutionErrors: {row['pvsWithDepResolutionErrors']},\n"
            f"    pctPvsWithDepResolutionErrors: {row['pctPvsWithDepResolutionErrors']},\n"
            f"    pvsWithCallGraphErrors: {row['pvsWithCallGraphErrors']},\n"
            f"    pctPvsWithCallGraphErrors: {row['pctPvsWithCallGraphErrors']}{total},\n"
            "  }"
        )
    return "[\n" + ",\n".join(parts) + "\n]"


def render_canvas(data: dict) -> str:
    tenant = data["tenant"]
    slug = tenant.replace("_", "-")
    component = "".join(part.capitalize() for part in slug.split("-")) + "PrfApproximationMain"
    missing = data["missing_parent_pvs"]
    summary_rows = render_summary_rows(data["summary_rows"])
    ecosystem_errors = render_ecosystem_errors(data["ecosystem_errors"])

    return f"""import {{
  CollapsibleSection,
  Grid,
  H1,
  H2,
  PieChart,
  Row,
  Stack,
  Stat,
  Table,
  Text,
  useHostTheme,
}} from "cursor/canvas";

type SummaryRow = {{
  ecosystem: string;
  prfVulnerabilities: number;
  prdVulnerabilities: number;
  approximatedVulns: number;
  notApproximatedVulns: number;
  pctApproximatedVulns: number;
  uniquePvs: number;
  pvsWithDepResolutionErrors: number;
  pctPvsWithDepResolutionErrors: number;
  pvsWithCallGraphErrors: number;
  pctPvsWithCallGraphErrors: number;
  isTotal?: boolean;
}};

type ErrorBreakdownRow = {{
  count: number;
  matching_rule: string;
  explanation: string;
  fixable_notes: string;
  fixable: string;
  prf_vulnerabilities: number;
  prd_vulnerabilities: number;
  precomputed_reachability_pvs: number;
}};

type EcosystemErrors = {{
  dep_resolution_error_pvs: number;
  dep_resolution_breakdown: ErrorBreakdownRow[];
  call_graph_pvs: number;
  call_graph_breakdown: ErrorBreakdownRow[];
}};

const summaryRows: SummaryRow[] = {summary_rows};

const ecosystemErrors: Record<string, EcosystemErrors> = {ecosystem_errors};

const ECOSYSTEMS = ["NuGet", "NPM", "Maven", "PyPI"] as const;

const prfByEcosystem = summaryRows
  .filter((row) => !row.isTotal)
  .map((row) => ({{
    label: row.ecosystem,
    value: row.prfVulnerabilities,
  }}));

function formatCount(value: number): string {{
  return value.toLocaleString();
}}

function formatPct(value: number): string {{
  return `${{value.toFixed(2)}}%`;
}}

function breakdownTableRows(rows: ErrorBreakdownRow[]): React.ReactNode[][] {{
  return rows.map((row) => [
    formatCount(row.count),
    row.matching_rule,
    row.fixable || "—",
    row.explanation || "—",
    row.fixable_notes || "—",
    formatCount(row.prf_vulnerabilities),
    formatCount(row.prd_vulnerabilities),
    formatCount(row.precomputed_reachability_pvs),
  ]);
}}

function EcosystemErrorSection({{
  ecosystem,
  data,
}}: {{
  ecosystem: string;
  data: EcosystemErrors;
}}) {{
  const theme = useHostTheme();

  return (
    <CollapsibleSection
      title={{ecosystem}}
      count={{`${{formatCount(data.dep_resolution_error_pvs)}} dep · ${{formatCount(data.call_graph_pvs)}} call graph PVs`}}
      defaultOpen={{ecosystem === "NuGet"}}
    >
      <Stack gap={{16}}>
        <Stack gap={{8}}>
          <H2>Dependency resolution errors</H2>
          <Text style={{{{ color: theme.text.tertiary, fontSize: 12 }}}}>
            Main-context PRF parent PackageVersions with spec.resolution_errors.unresolved
            or .resolved · n={{formatCount(data.dep_resolution_error_pvs)}} PVs
          </Text>
          <Table
            headers={{[
              "Count",
              "matching_rule",
              "fixable",
              "explanation",
              "fixable_notes",
              "PRF vulns",
              "PRD vulns",
              "Precomputed reachability PVs",
            ]}}
            rows={{breakdownTableRows(data.dep_resolution_breakdown)}}
            columnAlign={{[
              "right",
              "left",
              "center",
              "left",
              "left",
              "right",
              "right",
              "right",
            ]}}
            striped
            stickyHeader
            style={{{{ fontSize: 12 }}}}
          />
        </Stack>

        <Stack gap={{8}}>
          <H2>Call graph errors</H2>
          <Text style={{{{ color: theme.text.tertiary, fontSize: 12 }}}}>
            Main-context PRF parent PackageVersions with spec.resolution_errors.call_graph
            exists · n={{formatCount(data.call_graph_pvs)}} PVs
          </Text>
          <Table
            headers={{[
              "Count",
              "matching_rule",
              "fixable",
              "explanation",
              "fixable_notes",
              "PRF vulns",
              "PRD vulns",
              "Precomputed reachability PVs",
            ]}}
            rows={{breakdownTableRows(data.call_graph_breakdown)}}
            columnAlign={{[
              "right",
              "left",
              "center",
              "left",
              "left",
              "right",
              "right",
              "right",
            ]}}
            striped
            stickyHeader
            style={{{{ fontSize: 12 }}}}
          />
        </Stack>
      </Stack>
    </CollapsibleSection>
  );
}}

export default function {component}() {{
  const theme = useHostTheme();
  const total = summaryRows.find((row) => row.isTotal)!;

  return (
    <Stack gap={{20}} style={{{{ padding: 28, maxWidth: 1280 }}}}>
      <Stack gap={{6}}>
        <H1>PRF vulnerability &amp; PV resolution errors — main context</H1>
        <Text style={{{{ color: theme.text.secondary }}}}>
          {tenant} (incl. child namespaces)
        </Text>
        <Text style={{{{ color: theme.text.tertiary, fontSize: 12 }}}}>
          Source: Endor Labs Finding + PackageVersion APIs · CONTEXT_TYPE_MAIN ·
          FINDING_TAGS_POTENTIALLY_REACHABLE_FUNCTION · NuGet, NPM, Maven, PyPI
        </Text>
      </Stack>

      <Stack gap={{8}} style={{{{ alignItems: "flex-start" }}}}>
        <Text style={{{{ color: theme.text.secondary, fontSize: 13, fontWeight: 600 }}}}>
          PRF vulnerabilities by ecosystem
        </Text>
        <PieChart data={{prfByEcosystem}} size={{240}} />
        <Text style={{{{ color: theme.text.tertiary, fontSize: 12 }}}}>
          Main-context potentially reachable function vulnerabilities · n=
          {{formatCount(total.prfVulnerabilities)}} across NuGet, NPM, Maven, PyPI
        </Text>
      </Stack>

      <Grid columns={{4}} gap={{12}}>
        <Stat
          label="PRF vulnerabilities"
          value={{formatCount(total.prfVulnerabilities)}}
        />
        <Stat
          label="Approximated vulns"
          value={{`${{formatCount(total.approximatedVulns)}} (${{formatPct(total.pctApproximatedVulns)}})`}}
          tone="warning"
        />
        <Stat
          label="Unique PVs"
          value={{formatCount(total.uniquePvs)}}
        />
        <Stat
          label="PVs with Dep Resolution errors"
          value={{`${{formatCount(total.pvsWithDepResolutionErrors)}} (${{formatPct(total.pctPvsWithDepResolutionErrors)}})`}}
          tone="info"
        />
      </Grid>

      <Stack gap={{8}}>
        <Row justify="space-between" align="center">
          <Text style={{{{ color: theme.text.secondary, fontSize: 13, fontWeight: 600 }}}}>
            Combined by ecosystem
          </Text>
          <Text style={{{{ color: theme.text.tertiary, fontSize: 12 }}}}>
            Dep resolution errors = resolution_errors.unresolved or .resolved · Call graph errors =
            resolution_errors.call_graph exists · PRD vulnerabilities = PRF vulns also tagged
            FINDING_TAGS_POTENTIALLY_REACHABLE_DEPENDENCY
          </Text>
        </Row>

        <Table
          headers={{[
            "Ecosystem",
            "PRF vulnerabilities",
            "PRD vulnerabilities",
            "Approximated vulns",
            "Not approximated vulns",
            "% approximated vulns",
            "Unique PVs",
            "PVs with Dep Resolution errors",
            "% PVs with Dep Resolution errors",
            "PVs with Call Graph Errors",
            "% PVs with Call Graph Errors",
          ]}}
          rows={{summaryRows.map((row) => [
            row.ecosystem,
            formatCount(row.prfVulnerabilities),
            formatCount(row.prdVulnerabilities),
            formatCount(row.approximatedVulns),
            formatCount(row.notApproximatedVulns),
            formatPct(row.pctApproximatedVulns),
            formatCount(row.uniquePvs),
            formatCount(row.pvsWithDepResolutionErrors),
            formatPct(row.pctPvsWithDepResolutionErrors),
            formatCount(row.pvsWithCallGraphErrors),
            formatPct(row.pctPvsWithCallGraphErrors),
          ])}}
          columnAlign={{[
            "left",
            "right",
            "right",
            "right",
            "right",
            "right",
            "right",
            "right",
            "right",
            "right",
            "right",
          ]}}
          rowTone={{summaryRows.map((row) => (row.isTotal ? "info" : undefined))}}
          striped
          stickyHeader
          style={{{{ fontSize: 13 }}}}
        />
      </Stack>

      <Text style={{{{ color: theme.text.secondary, fontSize: 12 }}}}>
        Total unique PVs ({{formatCount(total.uniquePvs)}}) is a union across ecosystems. Error
        breakdowns count main-context PackageVersions that are parents of PRF findings
        ({{formatCount({missing})}} parent UUIDs not found in main context are excluded).
        Call graph error analysis below covers PRF parent PVs with
        spec.resolution_errors.call_graph exists (same count as the summary table's PVs with
        Call Graph Errors).
      </Text>

      <Stack gap={{12}}>
        <Text style={{{{ color: theme.text.secondary, fontSize: 13, fontWeight: 600 }}}}>
          Error analysis by ecosystem
        </Text>
        {{ECOSYSTEMS.map((eco) => (
          <EcosystemErrorSection
            key={{eco}}
            ecosystem={{eco}}
            data={{ecosystemErrors[eco]}}
          />
        ))}}
      </Stack>
    </Stack>
  );
}}
"""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Cursor canvas TSX from PRF analysis JSON."
    )
    parser.add_argument("json_path", type=Path, help="Analysis JSON from run_analysis.py")
    parser.add_argument(
        "--canvas-dir",
        type=Path,
        default=None,
        help="Cursor canvases directory (default: CURSOR_CANVAS_DIR or auto-detect).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Fallback output directory when canvas dir is unavailable.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    json_path = args.json_path
    if not json_path.is_file():
        print(f"JSON not found: {json_path}", file=sys.stderr)
        return 1

    data = json.loads(json_path.read_text(encoding="utf-8"))
    tenant = data["tenant"]
    slug = tenant.replace("_", "-")
    filename = f"{slug}-prf-approximation-main.canvas.tsx"

    canvas_dir = resolve_canvas_dir(args.canvas_dir)
    if canvas_dir is not None:
        out_path = canvas_dir / filename
    elif args.output_dir is not None:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        out_path = args.output_dir / filename
    else:
        fallback = json_path.parent
        out_path = fallback / filename
        print(
            "Canvas dir not found; writing beside JSON. "
            "Pass --canvas-dir or set CURSOR_CANVAS_DIR for Cursor preview.",
            file=sys.stderr,
        )

    out_path.write_text(render_canvas(data), encoding="utf-8")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

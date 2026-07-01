#!/usr/bin/env python3
"""Generate cumulative weekly new-vs-resolved canvas TSX from analysis JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from paths import resolve_canvas_dir


def js_string(value: str) -> str:
    return json.dumps(value)


def js_numbers(values: list[int]) -> str:
    return json.dumps(values)


def component_name(namespace: str) -> str:
    slug = namespace.replace("_", "-")
    parts = [part for part in slug.split("-") if part]
    return "".join(part.capitalize() for part in parts) + "CumulativeWeeklyTrend"


def render_canvas(data: dict) -> str:
    namespace = data["namespace"]
    component = component_name(namespace)
    categories = json.dumps(data["categories"])
    cumulative_new = js_numbers(data["cumulative_new"])
    cumulative_resolved = js_numbers(data["cumulative_resolved"])
    gap_trend = js_string(data["gap_trend"])
    gap_start = data["gap_start"]
    gap_mid = data["gap_mid"]
    gap_end = data["gap_end"]
    gap_mid_label = js_string(data["gap_mid_label"])
    gap_end_label = js_string(data["gap_end_label"])
    finding_criteria = js_string(data["finding_criteria"])
    period_caption = js_string(data["period_caption"])
    last_complete_week = js_string(data["gap_end_label"])

    return f"""import {{
  colorPalette,
  H1,
  Stack,
  Text,
  useHostTheme,
}} from "cursor/canvas";

const categories = {categories};
const cumulativeNew = {cumulative_new};
const cumulativeResolved = {cumulative_resolved};
const namespace = {js_string(namespace)};
const gapTrend = {gap_trend};
const gapStart = {gap_start};
const gapMid = {gap_mid};
const gapEnd = {gap_end};
const findingCriteria = {finding_criteria};

function formatAxis(value: number): string {{
  if (value >= 1000) {{
    return `${{Math.round(value / 1000)}}k`;
  }}
  return String(value);
}}

function CumulativeLineChart({{
  categories: cats,
  newData,
  resolvedData,
}}: {{
  categories: string[];
  newData: number[];
  resolvedData: number[];
}}) {{
  const theme = useHostTheme();
  const textColor = theme.palette.foreground;
  const width = 900;
  const height = 430;
  const margin = {{ top: 36, right: 24, bottom: 88, left: 64 }};
  const plotW = width - margin.left - margin.right;
  const plotH = height - margin.top - margin.bottom;
  const maxVal = Math.max(...newData, ...resolvedData, 1);
  const newColor = theme.diff.stripRemoved;
  const resolvedColor = colorPalette.green;
  const gridColor = theme.stroke.tertiary;
  const baseline = margin.top + plotH;

  const xAt = (i: number) => margin.left + (i / Math.max(cats.length - 1, 1)) * plotW;
  const yAt = (v: number) => margin.top + plotH - (v / maxVal) * plotH;

  const toLinePoints = (data: number[]) =>
    data.map((v, i) => `${{xAt(i)}},${{yAt(v)}}`).join(" ");

  const toAreaPath = (data: number[]) => {{
    const pts = data.map((v, i) => `${{xAt(i)}},${{yAt(v)}}`);
    return `M ${{xAt(0)}},${{baseline}} L ${{pts.join(" L ")}} L ${{xAt(data.length - 1)}},${{baseline}} Z`;
  }};

  const yTicks = 5;
  const tickValues = Array.from({{ length: yTicks + 1 }}, (_, i) => (maxVal / yTicks) * i);

  return (
    <svg
      width={{width}}
      height={{height}}
      style={{{{ display: "block", background: theme.bg.editor, borderRadius: 8 }}}}
    >
      <rect x={{0}} y={{0}} width={{width}} height={{height}} fill={{theme.bg.editor}} rx={{8}} />

      {{tickValues.map((tick) => {{
        const y = yAt(tick);
        return (
          <g key={{tick}}>
            <line
              x1={{margin.left}}
              y1={{y}}
              x2={{margin.left + plotW}}
              y2={{y}}
              stroke={{gridColor}}
              strokeWidth={{1}}
            />
            <text
              x={{margin.left - 8}}
              y={{y + 4}}
              textAnchor="end"
              fill={{textColor}}
              fontSize={{11}}
            >
              {{formatAxis(tick)}}
            </text>
          </g>
        );
      }})}}

      <path d={{toAreaPath(resolvedData)}} fill={{resolvedColor}} fillOpacity={{0.22}} stroke="none" />
      <path d={{toAreaPath(newData)}} fill={{newColor}} fillOpacity={{0.22}} stroke="none" />

      <polyline
        points={{toLinePoints(resolvedData)}}
        fill="none"
        stroke={{resolvedColor}}
        strokeWidth={{2.5}}
      />
      <polyline
        points={{toLinePoints(newData)}}
        fill="none"
        stroke={{newColor}}
        strokeWidth={{2.5}}
      />

      {{cats.map((cat, i) => (
        <text
          key={{`${{cat}}-${{i}}`}}
          x={{xAt(i)}}
          y={{height - 52}}
          textAnchor="middle"
          fill={{textColor}}
          fontSize={{10}}
        >
          {{cat}}
        </text>
      ))}}

      <text x={{margin.left}} y={{18}} fill={{textColor}} fontSize={{12}}>
        Cumulative event count
      </text>

      <g transform={{`translate(${{width / 2 - 175}}, ${{height - 24}})`}}>
        <rect x={{0}} y={{-8}} width={{14}} height={{3}} fill={{newColor}} rx={{1}} />
        <text x={{20}} y={{-5}} fill={{textColor}} fontSize={{11}}>
          Cumulative New
        </text>
        <rect x={{175}} y={{-8}} width={{14}} height={{3}} fill={{resolvedColor}} rx={{1}} />
        <text x={{195}} y={{-5}} fill={{textColor}} fontSize={{11}}>
          Cumulative Resolved
        </text>
      </g>
    </svg>
  );
}}

export default function {component}() {{
  const theme = useHostTheme();
  const textColor = theme.palette.foreground;

  return (
    <Stack
      gap={{16}}
      style={{{{ padding: 24, maxWidth: 940, background: theme.bg.editor, color: textColor }}}}
    >
      <Stack gap={{6}}>
        <H1 style={{{{ color: textColor }}}}>Cumulative New vs Resolved Reachable Vulnerabilities</H1>
        <Text style={{{{ color: textColor }}}}>
          {{namespace}} · main context (incl. child namespaces)
        </Text>
        <Text style={{{{ color: textColor, fontSize: 12, opacity: 0.85 }}}}>
          Source: FindingLog · CREATE &amp; DELETE · {{findingCriteria}} · {period_caption}
          · weekly cumulative event counts (through week of {last_complete_week}) · complete weeks only
        </Text>
      </Stack>

      <CumulativeLineChart
        categories={{categories}}
        newData={{cumulativeNew}}
        resolvedData={{cumulativeResolved}}
      />

      <Stack gap={{4}}>
        <Text weight="medium" style={{{{ color: textColor }}}}>
          Cumulative gap (New − Resolved)
        </Text>
        <Text style={{{{ color: textColor, fontSize: 13, opacity: 0.9 }}}}>
          Start: {{gapStart.toLocaleString()}} · Mid ({gap_mid_label}): {{gapMid.toLocaleString()}} ·
          End ({gap_end_label}): {{gapEnd.toLocaleString()}} — gap is {{gapTrend}}
        </Text>
        <Text style={{{{ color: textColor, fontSize: 13, opacity: 0.9 }}}}>
          Y-axis: running total of FindingLog events · X-axis: week start (UTC)
        </Text>
      </Stack>
    </Stack>
  );
}}
"""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Cursor canvas TSX from new-vs-resolved analysis JSON."
    )
    parser.add_argument(
        "json_path", type=Path, help="Analysis JSON from run_analysis.py"
    )
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
    slug = data["namespace"].replace("_", "-")
    filename = f"{slug}-cumulative-weekly-past-90d.canvas.tsx"

    canvas_dir = resolve_canvas_dir(args.canvas_dir)
    if canvas_dir is not None:
        out_path = canvas_dir / filename
    elif args.output_dir is not None:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        out_path = args.output_dir / filename
    else:
        out_path = json_path.parent / filename
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

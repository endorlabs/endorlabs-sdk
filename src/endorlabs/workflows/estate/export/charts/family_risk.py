"""Risk-ranked dependency family charts (consumer-sorted version bars)."""

from __future__ import annotations

import html
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from endorlabs.utils.logging_config import get_resource_logger
from endorlabs.workflows.estate.analyze.risk.cardinality import (
    _collect_usage_for_package,
    _usage_rows_from_corpus_session,
)
from endorlabs.workflows.estate.analyze.risk.consumer_counts import (
    collect_consumer_counts_by_version,
)
from endorlabs.workflows.estate.analyze.risk.scoring import (
    aggregate_families,
    aggregate_family_findings_by_version,
    dm_package_name_for_key,
    rank_packages,
    resolve_scorer,
)
from endorlabs.workflows.estate.collect.findings import (
    DEFAULT_FINDING_CATEGORIES,
    main_context_label,
)

if TYPE_CHECKING:
    from endorlabs import Client

logger = get_resource_logger(__name__)

RISK_FAMILY_CHART_SCHEMA = "endor.risk_family_chart.v1"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def load_findings_jsonl(path: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if isinstance(row, dict):
            findings.append(row)
    return findings


def _usage_by_version_from_rows(usage_rows: list[dict[str, Any]]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for row in usage_rows:
        version = str(row.get("package_version") or "")
        if not version:
            continue
        totals[version] = totals.get(version, 0) + int(row.get("usage_count") or 0)
    return totals


def _consumers_for_family(
    client: Client | None,
    estate_root: str,
    family_name: str,
    *,
    corpus_session: Path | None,
    page_size: int,
    max_pages: int | None,
) -> dict[str, int]:
    if corpus_session is not None:
        from endorlabs.workflows.estate.collect.dependency_metadata import (
            aggregate_consumers_by_version,
            load_dependency_metadata_records,
        )

        return aggregate_consumers_by_version(
            load_dependency_metadata_records(corpus_session),
            family_name,
        )
    if client is None:
        return {}
    return collect_consumer_counts_by_version(
        client,
        estate_root,
        family_name,
        page_size=page_size,
        max_pages=max_pages,
    )


def _usage_for_family(
    client: Client | None,
    estate_root: str,
    family_name: str,
    *,
    corpus_session: Path | None,
    page_size: int,
    max_pages: int | None,
) -> dict[str, int]:
    if corpus_session is not None:
        rows = _usage_rows_from_corpus_session(corpus_session, estate_root, family_name)
        return _usage_by_version_from_rows(rows)
    if client is None:
        return {}
    rows = _collect_usage_for_package(
        client,
        estate_root,
        family_name,
        page_size=page_size,
        max_pages=max_pages,
    )
    return _usage_by_version_from_rows(rows)


def _join_family_versions(
    *,
    family_name: str,
    consumers_by_version: dict[str, int],
    usage_by_version: dict[str, int],
    version_risk: dict[str, Any],
    max_risk_score: float,
) -> list[dict[str, Any]]:
    all_versions = set(consumers_by_version) | set(usage_by_version) | set(version_risk)
    rows: list[dict[str, Any]] = []
    for version in all_versions:
        risk = version_risk.get(version)
        consumer_count = consumers_by_version.get(version, 0)
        usage_count = usage_by_version.get(version, 0)
        risk_score = float(getattr(risk, "risk_score", 0.0) or 0.0) if risk else 0.0
        findings_critical = (
            int(getattr(risk, "findings_critical", 0) or 0) if risk else 0
        )
        findings_high = int(getattr(risk, "findings_high", 0) or 0) if risk else 0
        findings_total = int(getattr(risk, "findings_total", 0) or 0) if risk else 0
        intensity = (risk_score / max_risk_score) if max_risk_score > 0 else 0.0
        rows.append(
            {
                "version": version,
                "consumer_count": consumer_count,
                "usage_count": usage_count,
                "findings_critical": findings_critical,
                "findings_high": findings_high,
                "findings_total": findings_total,
                "risk_score": risk_score,
                "risk_intensity": round(intensity, 4),
            }
        )
    rows.sort(
        key=lambda item: (
            -item["consumer_count"],
            -item["risk_score"],
            item["version"],
        )
    )
    return rows


def build_family_risk_chart(
    findings: list[dict[str, Any]],
    estate_root: str,
    *,
    top_n: int = 10,
    scorer_name: str = "critical_high_count",
    client: Client | None = None,
    corpus_session: Path | None = None,
    page_size: int = 500,
    max_pages: int | None = None,
    max_versions_per_family: int = 25,
) -> dict[str, Any]:
    """Build chart payload: top families by risk, versions sorted by consumer count."""
    resolved_scorer = resolve_scorer(scorer_name)
    family_summaries = aggregate_families(findings, resolved_scorer)
    ranked = rank_packages(family_summaries)[: max(top_n, 0)]

    families_payload: list[dict[str, Any]] = []
    for index, summary in enumerate(ranked, start=1):
        family_name = summary.package_name
        dm_name = dm_package_name_for_key(family_name)
        version_risk = aggregate_family_findings_by_version(
            findings,
            family_name=family_name,
            scorer=resolved_scorer,
        )
        max_version_risk = max(
            (item.risk_score for item in version_risk.values()),
            default=0.0,
        )
        consumers = _consumers_for_family(
            client,
            estate_root,
            dm_name,
            corpus_session=corpus_session,
            page_size=page_size,
            max_pages=max_pages,
        )
        usage = _usage_for_family(
            client,
            estate_root,
            family_name,
            corpus_session=corpus_session,
            page_size=page_size,
            max_pages=max_pages,
        )
        versions = _join_family_versions(
            family_name=family_name,
            consumers_by_version=consumers,
            usage_by_version=usage,
            version_risk=version_risk,
            max_risk_score=max_version_risk,
        )
        if max_versions_per_family > 0:
            versions = versions[:max_versions_per_family]

        families_payload.append(
            {
                "rank": index,
                "family_name": family_name,
                "dm_package_name": dm_name,
                "risk_score": summary.risk_score,
                "findings_critical": summary.findings_critical,
                "findings_high": summary.findings_high,
                "findings_total": summary.findings_total,
                "version_cardinality": len(consumers) or len(usage),
                "versions": versions,
            }
        )

    return {
        "schema": RISK_FAMILY_CHART_SCHEMA,
        "estate_root": estate_root,
        "context_filter": main_context_label(),
        "finding_categories": list(DEFAULT_FINDING_CATEGORIES),
        "scorer": scorer_name,
        "top_n": top_n,
        "generated_at": _utc_now(),
        "families": families_payload,
    }


def render_family_risk_chart_html(document: dict[str, Any]) -> str:
    """Render a Jackson-style horizontal bar chart (consumer width, risk color)."""
    estate = html.escape(str(document.get("estate_root") or ""))
    generated = html.escape(str(document.get("generated_at") or ""))
    families = document.get("families")
    if not isinstance(families, list):
        families = []

    sections: list[str] = []
    for family in families:
        if not isinstance(family, dict):
            continue
        name = html.escape(str(family.get("family_name") or ""))
        rank = family.get("rank")
        risk_score = family.get("risk_score")
        critical = family.get("findings_critical")
        high = family.get("findings_high")
        cardinality = family.get("version_cardinality")
        versions = family.get("versions")
        if not isinstance(versions, list) or not versions:
            continue
        max_consumers = max(
            int(row.get("consumer_count") or 0)
            for row in versions
            if isinstance(row, dict)
        )
        if max_consumers <= 0:
            max_consumers = 1

        bars: list[str] = []
        for row in versions:
            if not isinstance(row, dict):
                continue
            version = html.escape(str(row.get("version") or ""))
            consumers = int(row.get("consumer_count") or 0)
            risk = float(row.get("risk_score") or 0.0)
            crit = int(row.get("findings_critical") or 0)
            hi = int(row.get("findings_high") or 0)
            intensity = float(row.get("risk_intensity") or 0.0)
            width_pct = max(2.0, 100.0 * consumers / max_consumers)
            red = min(255, int(120 + 135 * intensity))
            green = max(40, int(180 - 140 * intensity))
            blue = max(40, int(200 - 160 * intensity))
            bars.append(
                f"""
                <div class="bar-row">
                  <div class="bar-label">{version}</div>
                  <div class="bar-track">
                    <div class="bar-fill" style="width:{width_pct:.1f}%;background:rgb({red},{green},{blue})"></div>
                  </div>
                  <div class="bar-meta">{consumers} consumers · risk {risk:.0f} · C{crit}/H{hi}</div>
                </div>
                """
            )

        sections.append(
            f"""
            <section class="family">
              <header>
                <h2>#{rank} {name}</h2>
                <p class="summary">
                  Risk {risk_score} · Critical {critical} · High {high}
                  · {cardinality} versions · sorted by consumer count
                </p>
              </header>
              <div class="bars">{"".join(bars)}</div>
            </section>
            """
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Risk-ranked dependency families — {estate}</title>
  <style>
    body {{
      font-family: "Segoe UI", system-ui, sans-serif;
      margin: 24px;
      background: #0f1117;
      color: #e8eaed;
    }}
    h1 {{ font-size: 1.4rem; margin-bottom: 0.25rem; }}
    .subtitle {{ color: #9aa0a6; margin-bottom: 24px; }}
    .family {{
      background: #171923;
      border: 1px solid #2a2f3a;
      border-radius: 10px;
      padding: 16px 18px;
      margin-bottom: 20px;
    }}
    .family h2 {{ margin: 0 0 6px; font-size: 1.05rem; }}
    .summary {{ margin: 0 0 14px; color: #9aa0a6; font-size: 0.9rem; }}
    .bar-row {{
      display: grid;
      grid-template-columns: 160px 1fr 220px;
      gap: 10px;
      align-items: center;
      margin-bottom: 8px;
      font-size: 0.85rem;
    }}
    .bar-label {{ font-family: Consolas, monospace; }}
    .bar-track {{
      background: #252a36;
      border-radius: 4px;
      height: 22px;
      overflow: hidden;
    }}
    .bar-fill {{
      height: 100%;
      border-radius: 4px;
      min-width: 4px;
    }}
    .bar-meta {{ color: #b0b7c3; text-align: right; }}
  </style>
</head>
<body>
  <h1>Risk-ranked dependency families</h1>
  <p class="subtitle">{estate} · main context SCA/vulnerability · generated {generated}</p>
  {"".join(sections)}
</body>
</html>
"""


def export_family_risk_chart(
    client: Client | None,
    estate_root: str,
    findings: list[dict[str, Any]],
    *,
    top_n: int = 10,
    scorer_name: str = "critical_high_count",
    corpus_session: Path | None = None,
    json_output: Path | None = None,
    html_output: Path | None = None,
    page_size: int = 500,
    max_pages: int | None = None,
    max_versions_per_family: int = 25,
) -> dict[str, Any]:
    """Build and optionally write family risk chart artifacts."""
    document = build_family_risk_chart(
        findings,
        estate_root,
        top_n=top_n,
        scorer_name=scorer_name,
        client=client,
        corpus_session=corpus_session,
        page_size=page_size,
        max_pages=max_pages,
        max_versions_per_family=max_versions_per_family,
    )
    if json_output is not None:
        json_output.parent.mkdir(parents=True, exist_ok=True)
        json_output.write_text(
            json.dumps(document, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )
    if html_output is not None:
        html_output.parent.mkdir(parents=True, exist_ok=True)
        html_output.write_text(
            render_family_risk_chart_html(document),
            encoding="utf-8",
        )
    return document

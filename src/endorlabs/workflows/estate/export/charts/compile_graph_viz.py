"""HTML panels for compile-dependency graph workspace IR artifacts."""

from __future__ import annotations

import html
import json
import re
from collections import defaultdict, deque
from pathlib import Path

from endorlabs.utils.path_safety import safe_write_text
from endorlabs.workflows.estate.contracts.ir_artifacts import (
    CLUSTERING_GRAPH_IR,
    COMMUNITY_DETECTION_IR,
    COMMUNITY_PROFILES_IR,
    GRAPH_METRICS_IR,
    PRODUCER_RANKINGS_IR,
)
from endorlabs.workflows.estate.workspace.paths import ir_path

TOP_IMPORTERS = 45
TOP_PRODUCERS = 28
_COLLAPSED_KEY_RE = re.compile(r"^__collapsed_(.+)__$")
COMPILE_GRAPH_VIZ_SCHEMA = "endor.compile_graph_viz.v1"


def short_name(
    name: str, limit: int = 52, collapse_prefixes: tuple[str, ...] = ()
) -> str:
    if name.startswith("https://github.com/"):
        name = "gh/" + name[len("https://github.com/") :]
    for prefix in collapse_prefixes:
        if name.startswith(prefix):
            stem = prefix.rstrip("_")
            name = f"{stem}…" + name[len(prefix) :][:28]
            break
    return name if len(name) <= limit else name[: limit - 1] + "…"


def producer_key(name: str, collapse_prefixes: tuple[str, ...]) -> str:
    for prefix in collapse_prefixes:
        if name.startswith(prefix):
            return f"__collapsed_{prefix.rstrip('_')}__"
    return name


def collapsed_label(pk: str) -> str | None:
    match = _COLLAPSED_KEY_RE.match(pk)
    if not match:
        return None
    return f"{match.group(1)}_* (collapsed)"


def weak_components(node_ids: set[int], edges: list[tuple[int, int]]) -> list[set[int]]:
    und: dict[int, set[int]] = defaultdict(set)
    for nid in node_ids:
        und[nid]
    for source, target in edges:
        if source in node_ids and target in node_ids:
            und[source].add(target)
            und[target].add(source)
    seen: set[int] = set()
    comps: list[set[int]] = []
    for start in node_ids:
        if start in seen:
            continue
        comp: set[int] = set()
        queue: deque[int] = deque([start])
        while queue:
            node = queue.popleft()
            if node in comp:
                continue
            comp.add(node)
            seen.add(node)
            for neighbor in und[node]:
                if neighbor not in comp:
                    queue.append(neighbor)
        comps.append(comp)
    return comps


def farthest_geodesic_path_from(start: int, adj: dict[int, list[dict]]) -> list[int]:
    """Longest shortest-path (BFS geodesic)."""
    dist = {start: 0}
    parent: dict[int, int | None] = {start: None}
    queue: deque[int] = deque([start])
    while queue:
        node = queue.popleft()
        for edge in adj.get(node, []):
            target = int(edge["producer"])
            if target not in dist:
                dist[target] = dist[node] + 1
                parent[target] = node
                queue.append(target)
    if len(dist) == 1:
        return [start]
    far = max(dist, key=lambda key: dist[key])
    path: list[int] = []
    current: int | None = far
    while current is not None:
        path.append(current)
        current = parent[current]
    path.reverse()
    return path


def load_clustering_graph(
    workspace_root: Path,
) -> tuple[dict[int, dict], list[dict], list[tuple[int, int]]]:
    clustering_path = ir_path(workspace_root, CLUSTERING_GRAPH_IR)
    if not clustering_path.is_file():
        msg = f"Missing {clustering_path.name}; run analyze graph step first"
        raise FileNotFoundError(msg)
    clustering = json.loads(clustering_path.read_text(encoding="utf-8"))
    nodes_by_id = {int(node["id"]): node for node in clustering["nodes"]}
    edge_rows = clustering["edges"]
    pairs = [
        (int(edge["importer"]), int(edge["producer"]))
        for edge in edge_rows
        if int(edge["importer"]) in nodes_by_id and int(edge["producer"]) in nodes_by_id
    ]
    return nodes_by_id, edge_rows, pairs


def pick_path_start(
    nodes_by_id: dict[int, dict],
    edge_pairs: list[tuple[int, int]],
    main: set[int],
    path_start: str | None,
) -> int:
    if path_start:
        for node in nodes_by_id.values():
            node_id = int(node["id"])
            if node_id in main and path_start in node["name"]:
                return node_id
    out_deg: dict[int, int] = defaultdict(int)
    for source, _target in edge_pairs:
        if source in main:
            out_deg[source] += 1
    if not out_deg:
        return next(iter(main))
    return max(out_deg, key=lambda key: (out_deg[key], -key))


def is_binary_node(name: str, collapse_prefixes: tuple[str, ...]) -> bool:
    if any(name.startswith(prefix) for prefix in collapse_prefixes):
        return True
    return name.endswith(".zip") or name.startswith("pkg:")


def build_dashboard_section(
    nodes_by_id: dict[int, dict],
    edge_pairs: list[tuple[int, int]],
    rankings: dict,
    metrics: dict | None,
    communities: dict | None,
    community_detection: dict | None,
    collapse_prefixes: tuple[str, ...],
) -> str:
    id_set = set(nodes_by_id)
    comps = [
        component
        for component in weak_components(id_set, edge_pairs)
        if len(component) > 1
    ]
    comps.sort(key=len, reverse=True)
    isolated = sum(
        1 for component in weak_components(id_set, edge_pairs) if len(component) == 1
    )

    rank_rows = (rankings.get("rankings") or [])[:12]
    pub_bars = []
    max_in = (
        max((row.get("inbound_import_count") or 1) for row in rank_rows)
        if rank_rows
        else 1
    )
    for row in rank_rows:
        width = max(2, int(100 * (row.get("inbound_import_count") or 0) / max_in))
        pub_bars.append(
            f'<div class="bar-row graph-bar-row" title="{html.escape(str(row.get("name") or ""))}">'
            f'<span class="bar-label">{html.escape(short_name(str(row.get("name") or ""), 36, collapse_prefixes))}</span>'
            f'<span class="bar-track"><span class="bar-fill pub" style="width:{width}%"></span></span>'
            f'<span class="bar-val">{row.get("inbound_import_count")}</span></div>'
        )

    out_deg: dict[int, int] = defaultdict(int)
    for source, _target in edge_pairs:
        out_deg[source] += 1
    top_con = sorted(out_deg.items(), key=lambda item: (-item[1], item[0]))[:12]
    max_out = top_con[0][1] if top_con else 1
    con_bars = []
    for node_id, degree in top_con:
        node = nodes_by_id[node_id]
        width = max(2, int(100 * degree / max_out))
        con_bars.append(
            f'<div class="bar-row graph-bar-row" title="{html.escape(node["name"])}">'
            f'<span class="bar-label">{html.escape(short_name(node["name"], 36, collapse_prefixes))}</span>'
            f'<span class="bar-track"><span class="bar-fill con" style="width:{width}%"></span></span>'
            f'<span class="bar-val">{degree}</span></div>'
        )

    comp_tiles = "".join(
        f'<div class="tile"><strong>{len(component)}</strong><span>nodes</span></div>'
        for component in comps[:11]
    )

    comm_rows = ""
    if communities:
        multi = [
            row
            for row in communities.get("communities") or []
            if row.get("node_count", 0) > 1
        ]
        multi.sort(key=lambda row: -row.get("node_count", 0))
        for row in multi[:5]:
            namespaces = row.get("dominant_namespaces") or []
            ns_txt = ", ".join(f"{item[0]} ({item[1]})" for item in namespaces[:2])
            linking = row.get("top_linking_packages") or []
            pkg = linking[0][0].split(":")[-1][:40] if linking else "—"
            comm_rows += (
                f"<tr><td>{row.get('node_count')}</td><td>{row.get('edge_count')}</td>"
                f"<td>{html.escape(ns_txt)}</td><td><code>{html.escape(pkg)}</code></td></tr>"
            )

    graph = rankings
    wcc = (metrics or {}).get("components") or {}
    scc = (metrics or {}).get("scc") or {}
    kcore = (metrics or {}).get("k_core") or {}
    detection_hint = ""
    if community_detection:
        detection_hint = (
            f" · detection: {community_detection.get('method')} "
            f"resolution={community_detection.get('resolution')} "
            f"edge_weight={community_detection.get('edge_weight_source')} "
            f"vertex_weight={community_detection.get('vertex_weight_source')}"
        )

    return f"""
    <section id="panel-dashboard" class="panel active">
      <div class="stat-grid">
        <div class="stat"><b>{graph.get("total_nodes", "—")}</b><span>graph nodes</span></div>
        <div class="stat"><b>{sum(len(component) for component in comps)}</b><span>connected</span></div>
        <div class="stat"><b>{isolated}</b><span>isolated (hidden in graph views)</span></div>
        <div class="stat"><b>{len(comps)}</b><span>disconnected islands</span></div>
        <div class="stat"><b>{wcc.get("weakly_connected_count", "—")}</b><span>weak components</span></div>
        <div class="stat"><b>{kcore.get("max_k", "—")}</b><span>k-core max</span></div>
      </div>
      <div class="columns-2">
        <div><h3>Most reused internal libraries</h3>{"".join(pub_bars)}</div>
        <div><h3>Repos importing the most libraries</h3>{"".join(con_bars)}</div>
      </div>
      <h3>Disconnected islands (by size in bipartite view)</h3>
      <div class="tiles">{comp_tiles}</div>
      <h3>Repo groups (shared compile dependencies)</h3>
      <table class="data"><thead><tr><th>Nodes</th><th>Edges</th><th>Org namespaces</th><th>Shared library</th></tr></thead>
      <tbody>{comm_rows or "<tr><td colspan=4>—</td></tr>"}</tbody></table>
      <p class="hint">Circular internal dependencies: {scc.get("has_cycles")} · producers with importers: {graph.get("producers_with_importers")}{detection_hint}</p>
    </section>
    """


def build_bipartite_svg(
    nodes_by_id: dict[int, dict],
    edge_rows: list[dict],
    main: set[int],
    collapse_prefixes: tuple[str, ...],
) -> str:
    pair_edges: dict[tuple[int, str], dict] = {}
    out_deg: dict[int, int] = defaultdict(int)
    in_deg: dict[str, int] = defaultdict(int)

    for edge in edge_rows:
        importer, producer = int(edge["importer"]), int(edge["producer"])
        if importer not in main or producer not in main:
            continue
        pub = producer_key(nodes_by_id[producer]["name"], collapse_prefixes)
        key = (importer, pub)
        if key not in pair_edges:
            pair_edges[key] = {
                "count": 0,
                "linking_package": str(edge.get("linking_package_name") or ""),
            }
        pair_edges[key]["count"] += 1
        out_deg[importer] += 1
        in_deg[pub] += 1

    importers = sorted(
        [node_id for node_id in main if out_deg[node_id] > 0],
        key=lambda node_id: (-out_deg[node_id], node_id),
    )[:TOP_IMPORTERS]
    pub_keys = sorted(in_deg.keys(), key=lambda key: (-in_deg[key], key))[
        :TOP_PRODUCERS
    ]

    con_index = {node_id: index for index, node_id in enumerate(importers)}
    pub_index = {key: index for index, key in enumerate(pub_keys)}

    edges_draw: list[tuple[int, str, int]] = []
    for (importer, pub), meta in pair_edges.items():
        if importer in con_index and pub in pub_index:
            edges_draw.append((importer, pub, meta["count"]))
    edges_draw.sort(key=lambda item: -item[2])

    row_h = 22
    left_x, right_x = 320, 720
    margin_top = 36
    n_rows = max(len(importers), len(pub_keys), 1)
    height = margin_top + n_rows * row_h + 40
    width = 900

    collapse_note = (
        f", {len(collapse_prefixes)} prefix(es) collapsed" if collapse_prefixes else ""
    )
    lines: list[str] = [
        f'<svg class="bipartite" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">',
        '<text x="12" y="22" class="svg-title">Importers (out-degree)</text>',
        f'<text x="530" y="22" class="svg-title">Producers (in-degree{collapse_note})</text>',
    ]

    for node_id in importers:
        y = margin_top + con_index[node_id] * row_h
        label = html.escape(
            short_name(nodes_by_id[node_id]["name"], 38, collapse_prefixes)
        )
        lines.append(f'<text x="8" y="{y + 4}" class="node-label left">{label}</text>')
        lines.append(
            f'<text x="300" y="{y + 4}" class="deg-label">{out_deg[node_id]}</text>'
        )
        lines.append(f'<circle cx="{left_x}" cy="{y}" r="4" class="dot con"/>')

    for pub in pub_keys:
        y = margin_top + pub_index[pub] * row_h
        collapsed = collapsed_label(pub)
        label = collapsed or short_name(pub, 38, collapse_prefixes)
        lines.append(
            f'<text x="{right_x + 12}" y="{y + 4}" class="node-label right">'
            f"{html.escape(label)}</text>"
        )
        lines.append(
            f'<text x="{right_x - 28}" y="{y + 4}" class="deg-label">{in_deg[pub]}</text>'
        )
        lines.append(f'<circle cx="{right_x}" cy="{y}" r="4" class="dot pub"/>')

    max_cnt = max((count for _, _, count in edges_draw), default=1)
    for importer, pub, count in edges_draw[:120]:
        y1 = margin_top + con_index[importer] * row_h
        y2 = margin_top + pub_index[pub] * row_h
        opacity = 0.15 + 0.55 * (count / max_cnt)
        lines.append(
            f'<line x1="{left_x}" y1="{y1}" x2="{right_x}" y2="{y2}" '
            f'stroke="rgba(120,170,220,{opacity:.2f})" stroke-width="{0.5 + 2 * count / max_cnt:.1f}"/>'
        )

    lines.append("</svg>")
    legend = (
        f"<p class='hint'>Largest weak component ({len(main)} nodes): top {len(importers)} importers × "
        f"top {len(pub_keys)} producers · {len(edges_draw)} bundled edges drawn "
        f"(cap 120 strongest)</p>"
    )
    return f'<section id="panel-bipartite" class="panel">{legend}{"".join(lines)}</section>'


def build_path_section(
    nodes_by_id: dict[int, dict],
    edge_rows: list[dict],
    main: set[int],
    edge_pairs: list[tuple[int, int]],
    path_start: str | None,
    collapse_prefixes: tuple[str, ...],
) -> str:
    adj: dict[int, list[dict]] = defaultdict(list)
    for edge in edge_rows:
        adj[int(edge["importer"])].append(edge)

    start = pick_path_start(nodes_by_id, edge_pairs, main, path_start)
    path_ids = farthest_geodesic_path_from(start, adj)
    start_label = short_name(nodes_by_id[start]["name"], 44, collapse_prefixes)
    cards = []
    for index, node_id in enumerate(path_ids):
        name = html.escape(
            short_name(nodes_by_id[node_id]["name"], 44, collapse_prefixes)
        )
        reg = (
            "binary"
            if is_binary_node(nodes_by_id[node_id]["name"], collapse_prefixes)
            else "git"
        )
        cards.append(
            f'<div class="path-card {reg}"><span class="step">{index}</span>{name}</div>'
        )
        if index < len(path_ids) - 1:
            cards.append('<div class="path-arrow">→</div>')

    seed_hint = (
        f"matching <code>{html.escape(path_start)}</code>"
        if path_start
        else f"from top importer <code>{html.escape(start_label)}</code>"
    )
    return f"""
    <section id="panel-path" class="panel">
      <p class="hint">Longest geodesic compile-import chain {seed_hint} ({len(path_ids) - 1} hops)</p>
      <div class="path-flow">{"".join(cards)}</div>
    </section>
    """


def render_compile_graph_panels_html(
    workspace_root: Path,
    *,
    collapse_prefixes: tuple[str, ...] = (),
) -> tuple[str, str]:
    """Return (dashboard_panel, bipartite_panel) HTML fragments."""
    nodes_by_id, edge_rows, edge_pairs = load_clustering_graph(workspace_root)
    rankings = json.loads(
        ir_path(workspace_root, PRODUCER_RANKINGS_IR).read_text(encoding="utf-8")
    )
    metrics_path = ir_path(workspace_root, GRAPH_METRICS_IR)
    metrics = (
        json.loads(metrics_path.read_text(encoding="utf-8"))
        if metrics_path.is_file()
        else None
    )
    comm_path = ir_path(workspace_root, COMMUNITY_PROFILES_IR)
    communities = (
        json.loads(comm_path.read_text(encoding="utf-8"))
        if comm_path.is_file()
        else None
    )
    detection_path = ir_path(workspace_root, COMMUNITY_DETECTION_IR)
    community_detection = (
        json.loads(detection_path.read_text(encoding="utf-8"))
        if detection_path.is_file()
        else None
    )

    comps = [
        component
        for component in weak_components(set(nodes_by_id), edge_pairs)
        if len(component) > 1
    ]
    comps.sort(key=len, reverse=True)
    main = comps[0] if comps else set()

    dashboard = build_dashboard_section(
        nodes_by_id,
        edge_pairs,
        rankings,
        metrics,
        communities,
        community_detection,
        collapse_prefixes,
    )
    bipartite = build_bipartite_svg(nodes_by_id, edge_rows, main, collapse_prefixes)
    return dashboard, bipartite


def render_compile_graph_viz_html(
    workspace_root: Path,
    *,
    namespace_label: str | None = None,
    collapse_prefixes: tuple[str, ...] = (),
) -> str:
    """Build standalone HTML from on-disk compile-graph IR artifacts."""
    dashboard, bipartite = render_compile_graph_panels_html(
        workspace_root, collapse_prefixes=collapse_prefixes
    )

    ns_label = html.escape(namespace_label or workspace_root.name)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Compile dependency graph — {ns_label}</title>
  <style>
    :root {{
      --bg: #0f1419; --panel: #161d27; --text: #e7ecf1; --muted: #8a9bab;
      --accent: #4f8cff; --con: #56b6c2; --pub: #f0a020; --border: #2a3441;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: system-ui, sans-serif; background: var(--bg); color: var(--text); }}
    header {{ padding: 12px 16px; border-bottom: 1px solid var(--border); }}
    h1 {{ margin: 0 0 4px; font-size: 1rem; }}
    .sub {{ color: var(--muted); font-size: 0.8rem; margin: 0; }}
    nav {{ display: flex; gap: 8px; padding: 10px 16px; border-bottom: 1px solid var(--border); }}
    nav button {{
      background: var(--panel); border: 1px solid var(--border); color: var(--text);
      padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 0.85rem;
    }}
    nav button.active {{ background: var(--accent); border-color: var(--accent); color: #fff; }}
    main {{ padding: 16px; max-width: 960px; margin: 0 auto; }}
    .panel {{ display: none; }}
    .panel.active {{ display: block; }}
    .stat-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 10px; margin-bottom: 20px; }}
    .stat {{ background: var(--panel); padding: 12px; border-radius: 8px; border: 1px solid var(--border); }}
    .stat b {{ display: block; font-size: 1.25rem; }}
    .stat span {{ font-size: 0.72rem; color: var(--muted); }}
    .columns-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
    @media (max-width: 700px) {{ .columns-2 {{ grid-template-columns: 1fr; }} }}
    h3 {{ font-size: 0.85rem; color: var(--muted); margin: 0 0 10px; }}
    .bar-row {{ display: grid; grid-template-columns: 140px 1fr 36px; gap: 8px; align-items: center; margin-bottom: 6px; font-size: 0.75rem; }}
    .bar-track {{ background: #1a222d; height: 8px; border-radius: 4px; overflow: hidden; }}
    .bar-fill.pub {{ background: var(--pub); display: block; height: 100%; }}
    .bar-fill.con {{ background: var(--con); display: block; height: 100%; }}
    .bar-val {{ text-align: right; color: var(--muted); }}
    .tiles {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px; }}
    .tile {{ background: var(--panel); border: 1px solid var(--border); border-radius: 8px; padding: 10px 14px; text-align: center; }}
    .tile strong {{ display: block; font-size: 1.1rem; }}
    .tile span {{ font-size: 0.7rem; color: var(--muted); }}
    table.data {{ width: 100%; border-collapse: collapse; font-size: 0.78rem; }}
    table.data th, table.data td {{ border: 1px solid var(--border); padding: 6px 8px; text-align: left; }}
    table.data th {{ background: var(--panel); color: var(--muted); }}
    .hint {{ color: var(--muted); font-size: 0.78rem; }}
    .bipartite {{ width: 100%; max-width: 900px; background: var(--panel); border-radius: 8px; border: 1px solid var(--border); }}
    .svg-title {{ fill: var(--muted); font-size: 11px; }}
    .node-label {{ fill: var(--text); font-size: 10px; }}
    .deg-label {{ fill: var(--muted); font-size: 9px; text-anchor: end; }}
    .dot.con {{ fill: var(--con); }}
    .dot.pub {{ fill: var(--pub); }}
    .path-flow {{ display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }}
    .path-card {{ background: var(--panel); border: 1px solid var(--border); border-radius: 6px; padding: 8px 10px; font-size: 0.72rem; max-width: 200px; }}
    .path-card.git {{ border-left: 3px solid var(--accent); }}
    .path-card.binary {{ border-left: 3px solid var(--pub); }}
    .path-card .step {{ display: block; color: var(--muted); font-size: 0.65rem; }}
    .path-arrow {{ color: var(--muted); font-size: 1.2rem; }}
  </style>
</head>
<body>
  <header>
    <h1>Compile-dependency graph ({ns_label})</h1>
    <p class="sub">{COMPILE_GRAPH_VIZ_SCHEMA} · session artifacts · isolates omitted from graph panels</p>
  </header>
  <nav>
    <button type="button" class="tab active" data-tab="dashboard">Dashboard</button>
    <button type="button" class="tab" data-tab="bipartite">Bipartite hubs</button>
  </nav>
  <main>
    {dashboard}
    {bipartite}
  </main>
  <script>
    document.querySelectorAll(".tab").forEach(btn => {{
      btn.addEventListener("click", () => {{
        document.querySelectorAll(".tab").forEach(b => b.classList.remove("active"));
        document.querySelectorAll(".panel").forEach(p => p.classList.remove("active"));
        btn.classList.add("active");
        document.getElementById("panel-" + btn.dataset.tab).classList.add("active");
      }});
    }});
  </script>
</body>
</html>
"""


def export_compile_graph_viz(
    workspace_root: Path,
    output_path: Path,
    *,
    namespace_label: str | None = None,
    collapse_prefixes: tuple[str, ...] = (),
) -> Path:
    """Write compile-graph HTML dashboard to ``output_path``."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    document = render_compile_graph_viz_html(
        workspace_root,
        namespace_label=namespace_label,
        collapse_prefixes=collapse_prefixes,
    )
    # Prefer workspace root as the containment base when the dashboard lives
    # under it; otherwise contain to the output file's parent directory.
    try:
        output_path.resolve().relative_to(workspace_root.resolve())
        base_dir = workspace_root
    except ValueError:
        base_dir = output_path.parent
    safe_write_text(base_dir, output_path, document)
    return output_path

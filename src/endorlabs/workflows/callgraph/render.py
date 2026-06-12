"""Markdown rendering for decoded call graphs."""

from __future__ import annotations

import textwrap

from endorlabs.resources.call_graph_data_proto import CallGraphInfo, CallSiteInfo


def _short_type_key(key: str) -> str:
    """Shorten a type key for display."""
    if key.startswith("/[") and "]" in key:
        inner = key[2 : key.index("]")]
        parts = inner.split(":")
        module_path = parts[-1] if len(parts) >= 3 else inner
        suffix = key[key.index("]") + 1 :].rstrip("/")
        return f"{module_path}{suffix}" if suffix else module_path
    return key


def _build_call_tree(info: CallGraphInfo) -> str:
    """Build an ASCII call tree rooted at entry-point modules."""
    adj: dict[int, list[tuple[int, list[CallSiteInfo]]]] = {}
    for edge in info.call_edges:
        adj.setdefault(edge.source_id, []).append((edge.target_id, edge.callsites))

    all_targets = {edge.target_id for edge in info.call_edges}
    roots: list[int] = [
        m.method_id
        for t in info.internal_types
        for m in t.methods
        if m.method_id not in all_targets
    ]
    if not roots:
        roots = [
            m.method_id
            for t in info.internal_types
            for m in t.methods
            if m.uri.endswith("/()")
        ]

    lines: list[str] = []
    visited: set[int] = set()

    def _walk(mid: int, prefix: str, is_last: bool, depth: int) -> None:
        if depth > 15:
            return
        connector = "\u2514\u2500\u2500 " if is_last else "\u251c\u2500\u2500 "
        label = info.callable_label(mid)
        c = info._callable_index.get(mid)
        line_info = ""
        if c and c.first_line is not None:
            if c.last_line is not None:
                line_info = f"  [L{c.first_line}-{c.last_line}]"
            else:
                line_info = f"  [L{c.first_line}]"
        lines.append(f"{prefix}{connector}{label}{line_info}")
        if mid in visited:
            new_prefix = prefix + ("    " if is_last else "\u2502   ")
            lines.append(f"{new_prefix}(cycle -- see above)")
            return
        visited.add(mid)
        children = adj.get(mid, [])
        new_prefix = prefix + ("    " if is_last else "\u2502   ")
        for i, (child_id, _sites) in enumerate(children):
            _walk(child_id, new_prefix, i == len(children) - 1, depth + 1)

    for i, root_id in enumerate(sorted(set(roots))):
        if i > 0:
            lines.append("")
        label = info.callable_label(root_id)
        c = info._callable_index.get(root_id)
        line_info = ""
        if c and c.first_line is not None:
            if c.last_line is not None:
                line_info = f"  [L{c.first_line}-{c.last_line}]"
            else:
                line_info = f"  [L{c.first_line}]"
        lines.append(f"{label}{line_info}")
        visited.add(root_id)
        children = adj.get(root_id, [])
        for j, (child_id, _) in enumerate(children):
            _walk(child_id, "", j == len(children) - 1, 1)

    return "\n".join(lines) if lines else "(no call tree could be reconstructed)"


def build_call_tree(info: CallGraphInfo) -> str:
    """Public helper that renders a call tree from decoded call graph info."""
    return _build_call_tree(info)


def _infer_profile(info: CallGraphInfo) -> str:
    """Attempt to infer what the application does from the call graph."""
    lines: list[str] = []
    lines.append(f"- **Language**: {info.language}")

    dep_names: set[str] = set()
    for t in info.external_types:
        key = _short_type_key(t.key)
        if "/" in key:
            dep_names.add(key.split("/")[0].split(":")[0])
        else:
            dep_names.add(key.split(":")[0])

    if dep_names:
        lines.append(
            f"- **Dependencies referenced in call graph**: "
            f"{', '.join(sorted(dep_names))}"
        )

    patterns: list[str] = []
    all_uris = [m.uri for t in info.internal_types for m in t.methods]
    uri_text = " ".join(all_uris).lower()
    if any(d in dep_names for d in ("express", "koa", "fastify", "hapi")):
        patterns.append("Web server (Node.js)")
    if any(d in dep_names for d in ("flask", "django", "fastapi", "starlette")):
        patterns.append("Web server (Python)")
    if "jsonwebtoken" in dep_names or "jwt" in uri_text:
        patterns.append("JWT authentication")
    if "bcrypt" in dep_names or "argon2" in dep_names:
        patterns.append("Password hashing")
    if any(d in dep_names for d in ("mongoose", "sequelize", "typeorm", "prisma")):
        patterns.append("Database ORM")
    if patterns:
        lines.append(f"- **Detected patterns**: {', '.join(patterns)}")

    module_names = [_short_type_key(t.key) for t in info.internal_types]
    lines.append(f"- **Application modules**: {', '.join(sorted(module_names))}")
    total_funcs = sum(len(t.methods) for t in info.internal_types)
    total_dep_funcs = sum(len(t.methods) for t in info.external_types)
    lines.append(f"- **First-party functions**: {total_funcs}")
    lines.append(f"- **Third-party function stubs**: {total_dep_funcs}")
    lines.append(f"- **Cross-module call edges**: {len(info.call_edges)}")
    return "\n".join(lines) + "\n"


def render_callgraph_analysis(info: CallGraphInfo) -> str:
    """Render a full Markdown analysis document for a decoded call graph.

    Args:
        info: Decoded :class:`CallGraphInfo`.

    Returns:
        Complete Markdown string.
    """
    sections: list[str] = []

    sections.append(f"# Call Graph Analysis: `{info.package_name}`\n")
    sections.append(
        textwrap.dedent(f"""\
        | Field | Value |
        |-------|-------|
        | UUID | `{info.uuid}` |
        | Namespace | `{info.namespace}` |
        | Parent (PackageVersion) UUID | `{info.parent_uuid}` |
        | Scan created | {info.create_time_iso} |
        | Scan updated | {info.update_time_iso} |
        | Language | {info.language} |
        | Callgraph version | {info.version} |
        | Internal types (modules) | {len(info.internal_types)} |
        | External types (deps) | {len(info.external_types)} |
        | Cross-module call edges | {len(info.call_edges)} |
        | Total callables | {len(info._callable_index)} |
        """)
    )

    sections.append(
        "> Proto schema: `spec/internal/plugin/v1/call_graph.proto` "
        "(endorlabs/monorepo). Inner message is `CallGraph` with CHA "
        "(types+methods), call_sites (edges), lang_or_rt, and version fields.\n"
    )

    # First-party modules
    sections.append("## First-Party Modules (CHA.internal_types)\n")
    for t in sorted(info.internal_types, key=lambda x: x.key):
        short = _short_type_key(t.key)
        src = t.source_file or "(unknown)"
        sections.append(f"### `{short}`\n")
        sections.append(f"- **Source file**: `{src}`")
        sections.append(f"- **Access**: {t.access} | **Class type**: {t.class_type}")
        sections.append(f"- **Methods**: {len(t.methods)}\n")
        if t.methods:
            sections.append("| ID | Function | Lines | Access | Defined |")
            sections.append("|----|----------|-------|--------|---------|")
            for m in sorted(t.methods, key=lambda x: x.method_id):
                fn_name = m.uri
                if "]/" in fn_name:
                    fn_name = fn_name.rsplit("]/", 1)[-1] or "(module scope)"
                lines_str = ""
                if m.first_line is not None and m.last_line is not None:
                    lines_str = f"L{m.first_line}-{m.last_line}"
                elif m.first_line is not None:
                    lines_str = f"L{m.first_line}"
                sections.append(
                    f"| {m.method_id} | `{fn_name}` | {lines_str} "
                    f"| {m.access} | {m.defined} |"
                )
        sections.append("")

    # External types
    sections.append("## Third-Party Dependencies (CHA.external_types)\n")
    for t in sorted(info.external_types, key=lambda x: x.key):
        short = _short_type_key(t.key)
        sections.append(f"### `{short}`\n")
        if t.methods:
            sections.append("| ID | Function | Access |")
            sections.append("|----|----------|--------|")
            for m in sorted(t.methods, key=lambda x: x.method_id):
                fn_name = m.uri
                if "]/" in fn_name:
                    fn_name = fn_name.rsplit("]/", 1)[-1] or "(module scope)"
                sections.append(f"| {m.method_id} | `{fn_name}` | {m.access} |")
        sections.append("")

    # Call tree
    sections.append("## Reconstructed Call Tree\n")
    sections.append(
        "The tree below shows the caller-to-callee relationships starting from\n"
        "entry-point functions (those not called by any other function).\n"
    )
    tree = _build_call_tree(info)
    sections.append("```")
    sections.append(tree)
    sections.append("```\n")

    # Edge table
    sections.append("## Cross-Module Call Edges (CallGraph.call_sites)\n")
    sections.append("| # | Source | Target | Call Type | Receiver |")
    sections.append("|---|--------|--------|-----------|----------|")
    for i, edge in enumerate(info.call_edges, 1):
        src_label = info.callable_short(edge.source_id)
        tgt_label = info.callable_short(edge.target_id)
        types_set = {s.call_type for s in edge.callsites}
        receivers = [r for s in edge.callsites for r in s.receiver]
        type_str = ", ".join(sorted(types_set)) if types_set else "-"
        recv_str = ", ".join(f"`{r}`" for r in receivers[:3]) if receivers else "-"
        sections.append(
            f"| {i} | `{src_label}` | `{tgt_label}` | {type_str} | {recv_str} |"
        )
    sections.append("")

    # Source files
    sections.append("## Source Files\n")
    files = sorted({t.source_file for t in info.internal_types if t.source_file})
    if files:
        sections.extend(f"- `{f}`" for f in files)
    else:
        sections.append("(no source files recorded)")
    sections.append("")

    sections.append("## Application Profile (inferred)\n")
    sections.append(_infer_profile(info))

    sections.append(
        "> **Limitations**: No dataflow analysis (call edges only). "
        "Anonymous function names are positional (line:column). "
        "Third-party stubs are shallow (exported entry points only). "
        "No HTTP route annotations.\n"
    )

    return "\n".join(sections)

"""Markdown summaries for Model Sync PR workflow (upstream API + resource deltas).

**Upstream section:** compares OpenAPI operation metadata (current file vs git).

**Resource section (default):** only **diffs** vs the baseline JSON from git
(``--git-ref``, default ``HEAD``) — added/removed resources, ``supported_ops`` /
mutable / immutable paths, and create/update payload property *changes*, rendered
as a **tree** (``(+)`` / ``(-)`` / ``(~)``) for CI summaries.

**Full inventory (opt-in):** pass ``--include-resource-inventory`` with
``--print-resource`` (or ``--write-github-output --resource-only``) to emit the
large per-resource snapshot (facade descriptions, mutable/immutable paths, and
payload property types + API descriptions). Use when you need the full picture,
not a change list.

When counts are all zero, **Maintainer readout** subsections explain what that means.
If only ``provenance.json`` moved, use ``--provenance-only`` / the workflow provenance
step for a field-level diff.

Runnable locally after `model_sync.py` (for PR summaries and maintainer triage).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

DEFAULT_OPERATION_METADATA = Path(
    "workspace/model-sync/custom_mapping/mapping/operation_path_metadata.json"
)
DEFAULT_FACADE = Path("workspace/model-sync/custom_mapping/facade_contract.json")
DEFAULT_PAYLOAD = Path(
    "workspace/model-sync/custom_mapping/mapping/payload_schemas.json"
)
DEFAULT_PROVENANCE = Path("workspace/model-sync/custom_mapping/provenance.json")


def load_json_file(path: Path) -> dict[str, Any]:
    """Load JSON object from disk; return {} on missing or invalid."""
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def git_show_json(git_ref: str, path: Path) -> dict[str, Any]:
    """Load JSON object from `git show <ref>:path`."""
    try:
        raw = subprocess.check_output(  # noqa: S603
            ["git", "show", f"{git_ref}:{path.as_posix()}"],  # noqa: S607
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _operations_list(data: dict[str, Any]) -> list[dict[str, Any]]:
    ops = data.get("operations")
    if not isinstance(ops, list):
        return []
    return [x for x in ops if isinstance(x, dict)]


def _endpoint_key(op: dict[str, Any]) -> str | None:
    method = op.get("method")
    path = op.get("path")
    if isinstance(method, str) and isinstance(path, str):
        return f"{method.upper()} {path}"
    return None


def _group_key(op: dict[str, Any]) -> str:
    tags = op.get("tags")
    if isinstance(tags, list) and tags and isinstance(tags[0], str):
        return tags[0]
    return "_untagged"


def _endpoints_by_tag(operations: list[dict[str, Any]]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for op in operations:
        ek = _endpoint_key(op)
        if not ek:
            continue
        g = _group_key(op)
        out.setdefault(g, set()).add(ek)
    return out


def _endpoints_set(operations: list[dict[str, Any]]) -> set[str]:
    return {ek for op in operations if (ek := _endpoint_key(op))}


def _index_op_by_endpoint(
    operations: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for op in operations:
        ek = _endpoint_key(op)
        if ek:
            out[ek] = op
    return out


def _op_signature_tuple(op: dict[str, Any]) -> tuple[str, str, str]:
    oid = op.get("operation_id")
    oid_s = oid if isinstance(oid, str) else ""
    rr = op.get("request_refs")
    rs = (
        ",".join(sorted(x for x in rr if isinstance(x, str)))
        if isinstance(rr, list)
        else ""
    )
    resp = op.get("response_refs")
    resp_s = (
        ",".join(sorted(x for x in resp if isinstance(x, str)))
        if isinstance(resp, list)
        else ""
    )
    return (oid_s, rs, resp_s)


def _short_schema_label(schema: dict[str, Any]) -> str:
    ref = schema.get("$ref")
    if isinstance(ref, str):
        tail = ref.split("/")[-1]
        return f"$ref:{tail}" if len(tail) <= 64 else f"$ref:{tail[:61]}..."
    t = schema.get("type")
    if isinstance(t, str):
        return f"type:{t}"
    if isinstance(t, list):
        return f"type:{','.join(str(x) for x in t)}"
    return "schema"


def _truncate_desc(text: str | None, max_len: int = 220) -> str:
    if not isinstance(text, str):
        return ""
    s = " ".join(text.split())
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."


def _field_line_for_schema(path: str, schema: dict[str, Any]) -> str:
    """Emit path, type/ref, and API description (docstring source)."""
    type_s = _short_schema_label(schema)
    raw_desc = schema.get("description") if isinstance(schema, dict) else None
    desc = _truncate_desc(raw_desc if isinstance(raw_desc, str) else None)
    ro = " [readOnly]" if schema.get("readOnly") is True else ""
    title = schema.get("title")
    title_note = ""
    if isinstance(title, str) and title.strip():
        tshort = _truncate_desc(title, 80)
        if tshort != desc[: len(tshort)]:
            title_note = f" title={tshort!r}"
    if desc:
        return f"{path}: {type_s}{ro}{title_note} | {desc}"
    return f"{path}: {type_s}{ro}{title_note}"


def _iter_property_rows(
    props: dict[str, Any],
    prefix: str,
    depth: int,
    max_depth: int,
) -> list[str]:
    """Flatten OpenAPI payload properties to labeled lines (names, types, comments)."""
    rows: list[str] = []
    if not isinstance(props, dict) or depth > max_depth:
        return rows
    for key in sorted(props.keys()):
        if not isinstance(key, str):
            continue
        full = f"{prefix}.{key}" if prefix else key
        val = props[key]
        if not isinstance(val, dict):
            continue
        rows.append(_field_line_for_schema(full, val))
        if depth >= max_depth:
            continue
        if val.get("type") == "object" and isinstance(val.get("properties"), dict):
            rows.extend(
                _iter_property_rows(val["properties"], full, depth + 1, max_depth)
            )
        elif val.get("type") == "array" and isinstance(val.get("items"), dict):
            items = val["items"]
            if isinstance(items.get("properties"), dict):
                rows.extend(
                    _iter_property_rows(
                        items["properties"], f"{full}[]", depth + 1, max_depth
                    )
                )
    return rows


def _lines_dot_path_list(label: str, paths: list[Any], max_items: int) -> list[str]:
    out = [f"{label}:"]
    n = 0
    for p in paths:
        if not isinstance(p, str):
            continue
        out.append(f"  - {p}")
        n += 1
        if n >= max_items:
            rest = len([x for x in paths if isinstance(x, str)]) - n
            if rest > 0:
                out.append(f"  ... ({rest} more)")
            break
    return out


def _format_facade_detail_lines(
    item: dict[str, Any],
    *,
    max_field_lines: int,
) -> list[str]:
    """Facade contract fields that drive SDK models and docstrings."""
    lines: list[str] = []
    desc = item.get("description")
    if isinstance(desc, str) and desc.strip():
        lines.append("Resource description (facade → class docstring source):")
        lines.append("  " + _truncate_desc(desc, 500))
    for key in ("resource_name", "model_class", "model_class_import_path", "scope"):
        v = item.get(key)
        if v is not None and v != "":
            lines.append(f"{key}: {v}")
    m = item.get("mutable_fields")
    if isinstance(m, list) and m:
        lines.extend(
            _lines_dot_path_list("mutable_fields (update)", m, max_field_lines)
        )
    im = item.get("immutable_fields")
    if isinstance(im, list) and im:
        lines.extend(
            _lines_dot_path_list(
                "immutable_fields (read-only in API)", im, max_field_lines
            )
        )
    ident = item.get("identity_filter_fields")
    if isinstance(ident, list) and ident:
        lines.extend(
            _lines_dot_path_list("identity_filter_fields", ident, max_field_lines)
        )
    fmap = item.get("filter_kwarg_map")
    if isinstance(fmap, dict) and fmap:
        lines.append("filter_kwarg_map (JSON):")
        lines.append("  " + _truncate_desc(json.dumps(fmap, sort_keys=True), 400))
    return lines


def _format_payload_inventory_lines(
    payload_item: dict[str, Any],
    *,
    max_defs_per_kind: int,
    max_props_per_def: int,
    max_depth: int,
) -> list[str]:
    """Create/update payload defs: property names, types/refs, API descriptions."""
    lines: list[str] = []
    for kind in ("create", "update"):
        defs = payload_item.get(f"{kind}_payload_definitions", {})
        if not isinstance(defs, dict) or not defs:
            continue
        def_names = sorted(defs.keys())[:max_defs_per_kind]
        for def_name in def_names:
            body = defs.get(def_name)
            if not isinstance(body, dict):
                continue
            lines.append(f"[{kind}] {def_name}")
            sd = body.get("description")
            if isinstance(sd, str) and sd.strip():
                lines.append(
                    "  schema description (payload / Field description source): "
                    + _truncate_desc(sd, 300)
                )
            req = body.get("required")
            if isinstance(req, list) and req:
                rq = [str(x) for x in req if isinstance(x, str)]
                lines.append(f"  required: {', '.join(rq)}")
            props = body.get("properties")
            if isinstance(props, dict):
                rows = _iter_property_rows(props, "", 0, max_depth)
                shown = rows[:max_props_per_def]
                lines.extend(f"  {row}" for row in shown)
                if len(rows) > max_props_per_def:
                    lines.append(f"  ... ({len(rows) - len(shown)} more fields)")
            lines.append("")
    return lines


def _property_fingerprint(prop: Any) -> str:
    if not isinstance(prop, dict):
        return json.dumps(prop, sort_keys=True)
    return json.dumps(prop, sort_keys=True)


def _tag_group_deltas(
    old_by_tag: dict[str, set[str]],
    new_by_tag: dict[str, set[str]],
    shared_tags: list[str],
) -> list[str]:
    tag_deltas: list[str] = []
    for tag in shared_tags:
        add_eps = sorted(new_by_tag[tag] - old_by_tag[tag])
        del_eps = sorted(old_by_tag[tag] - new_by_tag[tag])
        if add_eps or del_eps:
            frags: list[str] = []
            if add_eps:
                frags.append(f"+{len(add_eps)} endpoints")
            if del_eps:
                frags.append(f"-{len(del_eps)} endpoints")
            tag_deltas.append(f"- {tag}: " + ", ".join(frags))
    return tag_deltas


def _signature_drift_lines(
    old_ix: dict[str, dict[str, Any]],
    new_ix: dict[str, dict[str, Any]],
) -> list[str]:
    sig_drift: list[str] = []
    for ek in sorted(set(old_ix) & set(new_ix)):
        if _op_signature_tuple(old_ix[ek]) != _op_signature_tuple(new_ix[ek]):
            o0, o1, o2 = _op_signature_tuple(old_ix[ek])
            n0, n1, n2 = _op_signature_tuple(new_ix[ek])
            sig_drift.append(
                f"- {ek}: op_id `{o0}` -> `{n0}`; "
                f"req_refs `{o1[:48]}` -> `{n1[:48]}`; "
                f"resp_refs `{o2[:48]}` -> `{n2[:48]}`"
            )
    return sig_drift


def _fmt_scalar_for_summary(key: str, val: Any, max_len: int = 96) -> str:
    if val is None:
        return "null"
    if isinstance(val, str):
        if key == "spec_sha256" and len(val) >= 16:
            return f"{val[:12]}… (len={len(val)})"
        if len(val) > max_len:
            return val[: max_len - 3] + "..."
        return val
    s = json.dumps(val, sort_keys=True)
    return s if len(s) <= max_len else s[: max_len - 3] + "..."


def render_provenance_delta_markdown(
    old_data: dict[str, Any],
    new_data: dict[str, Any],
    *,
    baseline_ref: str = "HEAD",
) -> list[str]:
    """Field-level diff for provenance.json (excluded from sync branch)."""
    lines: list[str] = []
    lines.append("### Provenance delta (excluded from model-sync branch)")
    lines.append(
        "- **Compared:** working tree after generation vs "
        f"`git show {baseline_ref}:workspace/model-sync/custom_mapping/provenance.json`"
    )
    scalar_keys = (
        "endorctl_version",
        "generated_at_utc",
        "spec_sha256",
        "spec_path",
    )
    for key in scalar_keys:
        o = old_data.get(key)
        n = new_data.get(key)
        if o == n:
            lines.append(
                f"- `{key}`: **unchanged** — `{_fmt_scalar_for_summary(key, n)}`"
            )
        else:
            lines.append(
                f"- `{key}`: **changed** — `{_fmt_scalar_for_summary(key, o)}` → "
                f"`{_fmt_scalar_for_summary(key, n)}`"
            )
    old_tc = old_data.get("toolchain")
    new_tc = new_data.get("toolchain")
    if old_tc != new_tc:
        lines.append(
            "- `toolchain`: **changed** (nested object; paths often differ per runner)"
        )
        lines.append(f"  - before: `{_fmt_scalar_for_summary('toolchain', old_tc)}`")
        lines.append(f"  - after: `{_fmt_scalar_for_summary('toolchain', new_tc)}`")
    else:
        lines.append("- `toolchain`: **unchanged**")
    lines.append("")
    lines.append("#### Maintainer readout")
    lines.append(
        "- **Typical case:** Only `generated_at_utc` (and maybe `spec_path`) moves — "
        "the OpenAPI **hash** and generated SDK files already match `main`."
    )
    lines.append("  Nothing to merge from this run.")
    return lines


def render_upstream_delta_markdown(
    old_data: dict[str, Any],
    new_data: dict[str, Any],
    *,
    baseline_ref: str = "HEAD",
    max_tag_delta_lines: int = 80,
    max_endpoint_samples: int = 40,
    max_signature_drift: int = 40,
) -> list[str]:
    """Build markdown lines for upstream delta from operation_path_metadata."""
    old_ops = _operations_list(old_data)
    new_ops = _operations_list(new_data)

    old_count = old_data.get("operation_count")
    new_count = new_data.get("operation_count")
    if not isinstance(old_count, int):
        old_count = len(old_ops)
    if not isinstance(new_count, int):
        new_count = len(new_ops)

    old_endpoints = _endpoints_set(old_ops)
    new_endpoints = _endpoints_set(new_ops)

    old_by_tag = _endpoints_by_tag(old_ops)
    new_by_tag = _endpoints_by_tag(new_ops)
    old_tag_names = set(old_by_tag)
    new_tag_names = set(new_by_tag)
    added_tags = sorted(new_tag_names - old_tag_names)
    removed_tags = sorted(old_tag_names - new_tag_names)
    shared_tags = sorted(old_tag_names & new_tag_names)

    tag_deltas = _tag_group_deltas(old_by_tag, new_by_tag, shared_tags)

    added_endpoints = sorted(new_endpoints - old_endpoints)
    removed_endpoints = sorted(old_endpoints - new_endpoints)

    old_ix = _index_op_by_endpoint(old_ops)
    new_ix = _index_op_by_endpoint(new_ops)
    sig_drift = _signature_drift_lines(old_ix, new_ix)

    lines: list[str] = []
    lines.append("### Upstream API Delta")
    lines.append(
        f"- Unique path+method endpoints (git {baseline_ref}): {len(old_endpoints)}"
    )
    lines.append(f"- Unique path+method endpoints (current run): {len(new_endpoints)}")
    lines.append(f"- Operation tag groups (git {baseline_ref}): {len(old_tag_names)}")
    lines.append(f"- Operation tag groups (current run): {len(new_tag_names)}")
    lines.append(f"- Added tag groups: {len(added_tags)}")
    lines.append(f"- Removed tag groups: {len(removed_tags)}")
    lines.append(f"- Tag groups with endpoint-set deltas: {len(tag_deltas)}")
    lines.append(f"- Added endpoint signatures: {len(added_endpoints)}")
    lines.append(f"- Removed endpoint signatures: {len(removed_endpoints)}")
    lines.append(f"- Total operation entries (git {baseline_ref}): {old_count}")
    lines.append(f"- Total operation entries (current run): {new_count}")

    if added_tags:
        lines.append(f"- New tag groups (sample): {', '.join(added_tags[:20])}")
    if removed_tags:
        lines.append(f"- Removed tag groups (sample): {', '.join(removed_tags[:20])}")

    if tag_deltas:
        lines.append("<details><summary>Per-tag endpoint delta samples</summary>")
        lines.append("")
        lines.append("```text")
        lines.extend(tag_deltas[:max_tag_delta_lines])
        lines.append("```")
        lines.append("</details>")

    if added_endpoints or removed_endpoints:
        lines.append("<details><summary>Endpoint signature delta samples</summary>")
        lines.append("")
        lines.append("```text")
        lines.extend(f"+ {e}" for e in added_endpoints[:max_endpoint_samples])
        lines.extend(f"- {e}" for e in removed_endpoints[:max_endpoint_samples])
        lines.append("```")
        lines.append("</details>")

    if sig_drift:
        lines.append(
            "<details><summary>Same path+method: operation metadata drift</summary>"
        )
        lines.append("")
        lines.append("```text")
        lines.extend(sig_drift[:max_signature_drift])
        lines.append("```")
        lines.append("</details>")

    no_net_delta = (
        bool(old_ops)
        and bool(new_ops)
        and not added_tags
        and not removed_tags
        and not tag_deltas
        and not added_endpoints
        and not removed_endpoints
        and not sig_drift
    )
    if no_net_delta:
        lines.append("")
        lines.append("#### Maintainer readout")
        lines.append(
            "- **What changed in the API catalog:** Nothing vs "
            f"`git {baseline_ref}` — on-disk `operation_path_metadata.json` matches "
            "the committed file."
        )
        lines.append(
            "  Same path+method set, tag groups, and operation metadata as baseline."
        )
        lines.append(
            "- **Why the workflow still ran:** Dispatch can fire on `spec_changed` / "
            "`version_changed` while **main already embeds** that spec output."
        )
        lines.append("  Idempotent regeneration.")
        lines.append(
            "- **If you expected API drift:** Compare **Outcome Matrix** OpenAPI "
            "SHA256 to `provenance.json` `spec_sha256` after this job."
        )
        lines.append(
            "  If hashes align, the spec is already reflected in tracked artifacts."
        )

    return lines


def _resources_index(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    resources = data.get("resources")
    if not isinstance(resources, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for item in resources:
        if isinstance(item, dict):
            key = item.get("attr_name")
            if isinstance(key, str):
                result[key] = item
    return result


def _payload_lines_for_definitions(
    name: str,
    kind: str,
    def_name: str,
    old_def: dict[str, Any],
    new_def: dict[str, Any],
) -> list[str]:
    out: list[str] = []
    old_props = old_def.get("properties", {})
    new_props = new_def.get("properties", {})
    if not isinstance(old_props, dict):
        old_props = {}
    if not isinstance(new_props, dict):
        new_props = {}
    old_req = (
        set(old_def.get("required", []))
        if isinstance(old_def.get("required", []), list)
        else set()
    )
    new_req = (
        set(new_def.get("required", []))
        if isinstance(new_def.get("required", []), list)
        else set()
    )
    add_props = sorted(set(new_props) - set(old_props))
    del_props = sorted(set(old_props) - set(new_props))
    add_req = sorted(new_req - old_req)
    del_req = sorted(old_req - new_req)
    if add_props or del_props or add_req or del_req:
        frag2: list[str] = []
        if add_props:
            frag2.append(f"+attrs={','.join(add_props[:8])}")
        if del_props:
            frag2.append(f"-attrs={','.join(del_props[:8])}")
        if add_req:
            frag2.append(f"+required={','.join(add_req[:8])}")
        if del_req:
            frag2.append(f"-required={','.join(del_req[:8])}")
        out.append(f"- {name} {kind} {def_name}: " + "; ".join(frag2))

    shared_props = sorted(set(old_props) & set(new_props))
    for prop_name in shared_props:
        raw_old = old_props.get(prop_name)
        raw_new = new_props.get(prop_name)
        if not isinstance(raw_old, dict) or not isinstance(raw_new, dict):
            continue
        fp_old = _property_fingerprint(raw_old)
        fp_new = _property_fingerprint(raw_new)
        if fp_old == fp_new:
            continue
        label_old = _short_schema_label(raw_old)
        label_new = _short_schema_label(raw_new)
        out.append(
            f"- {name} {kind} {def_name} prop `{prop_name}`: {label_old} -> {label_new}"
        )
    return out


def _tree_branch() -> str:
    """Prefix for child lines in workflow summary tree output."""
    return "|- "


def _field_type_and_desc(schema: dict[str, Any]) -> tuple[str, str]:
    """Return bracketed type label and truncated API description for a schema dict."""
    type_s = _short_schema_label(schema)
    raw_desc = schema.get("description") if isinstance(schema, dict) else None
    desc = _truncate_desc(raw_desc if isinstance(raw_desc, str) else None)
    return type_s, desc


def _facade_tree_lines(
    old_item: dict[str, Any],
    new_item: dict[str, Any],
) -> list[str]:
    """Tree lines for façade supported_ops and mutable/immutable field deltas."""
    bp = _tree_branch()
    out: list[str] = []
    old_ops = set(old_item.get("supported_ops", []))
    new_ops = set(new_item.get("supported_ops", []))
    add_ops = sorted(x for x in (new_ops - old_ops) if isinstance(x, str))
    del_ops = sorted(x for x in (old_ops - new_ops) if isinstance(x, str))
    out.extend(f"{bp}(+) supported_ops: {op}" for op in add_ops)
    out.extend(f"{bp}(-) supported_ops: {op}" for op in del_ops)

    old_mut = set(old_item.get("mutable_fields", []))
    new_mut = set(new_item.get("mutable_fields", []))
    old_imm = set(old_item.get("immutable_fields", []))
    new_imm = set(new_item.get("immutable_fields", []))
    mut_add = sorted(x for x in (new_mut - old_mut) if isinstance(x, str))
    mut_del = sorted(x for x in (old_mut - new_mut) if isinstance(x, str))
    imm_add = sorted(x for x in (new_imm - old_imm) if isinstance(x, str))
    imm_del = sorted(x for x in (old_imm - new_imm) if isinstance(x, str))
    out.extend(f"{bp}(+) mutable_fields: {p}" for p in mut_add)
    out.extend(f"{bp}(-) mutable_fields: {p}" for p in mut_del)
    out.extend(f"{bp}(+) immutable_fields: {p}" for p in imm_add)
    out.extend(f"{bp}(-) immutable_fields: {p}" for p in imm_del)
    return out


def _norm_payload_props_and_required(
    body: dict[str, Any],
) -> tuple[dict[str, Any], set[str]]:
    props = body.get("properties", {})
    if not isinstance(props, dict):
        props = {}
    req_raw = body.get("required", [])
    req = set(req_raw) if isinstance(req_raw, list) else set()
    return props, req


def _payload_tree_desc_tail(desc_old: str, desc_new: str) -> str:
    if not desc_old and not desc_new:
        return ""
    if desc_old and desc_new:
        if desc_old != desc_new:
            return f": {desc_old} → {desc_new}"
        return ""
    if desc_new:
        return f": {desc_new}"
    return f": {desc_old}"


def _payload_tree_add_remove_prop_lines(
    bp: str,
    ctx: str,
    prop_names: list[str],
    props: dict[str, Any],
    sign: str,
) -> list[str]:
    """Emit one tree line per added (+) or removed (-) payload property."""
    prop_lines: list[str] = []
    for prop_name in prop_names:
        raw = props.get(prop_name)
        if not isinstance(raw, dict):
            continue
        type_s, desc = _field_type_and_desc(raw)
        tail = f": {desc}" if desc else ""
        prop_lines.append(f"{bp}({sign}) {ctx} {prop_name} [{type_s}]{tail}")
    return prop_lines


def _payload_tree_shared_shape_lines(
    bp: str,
    ctx: str,
    old_props: dict[str, Any],
    new_props: dict[str, Any],
    shared_props: list[str],
) -> list[str]:
    out: list[str] = []
    for prop_name in shared_props:
        raw_old = old_props.get(prop_name)
        raw_new = new_props.get(prop_name)
        if not isinstance(raw_old, dict) or not isinstance(raw_new, dict):
            continue
        if _property_fingerprint(raw_old) == _property_fingerprint(raw_new):
            continue
        label_old = _short_schema_label(raw_old)
        label_new = _short_schema_label(raw_new)
        _, desc_old = _field_type_and_desc(raw_old)
        _, desc_new = _field_type_and_desc(raw_new)
        desc_tail = _payload_tree_desc_tail(desc_old, desc_new)
        out.append(f"{bp}(~) {ctx} {prop_name}: {label_old} → {label_new}{desc_tail}")
    return out


def _payload_tree_lines_for_definitions(
    kind: str,
    def_name: str,
    old_def: dict[str, Any],
    new_def: dict[str, Any],
) -> list[str]:
    """Tree lines for create/update payload definition deltas (types + descriptions)."""
    bp = _tree_branch()
    ctx = f"{kind} {def_name}"
    old_props, old_req = _norm_payload_props_and_required(old_def)
    new_props, new_req = _norm_payload_props_and_required(new_def)

    add_props = sorted(set(new_props) - set(old_props))
    del_props = sorted(set(old_props) - set(new_props))
    add_req = sorted(x for x in (new_req - old_req) if isinstance(x, str))
    del_req = sorted(x for x in (old_req - new_req) if isinstance(x, str))

    out: list[str] = []
    out.extend(_payload_tree_add_remove_prop_lines(bp, ctx, add_props, new_props, "+"))
    out.extend(_payload_tree_add_remove_prop_lines(bp, ctx, del_props, old_props, "-"))

    out.extend(f"{bp}(+) {ctx} required: {r}" for r in add_req)
    out.extend(f"{bp}(-) {ctx} required: {r}" for r in del_req)

    shared_props = sorted(set(old_props) & set(new_props))
    out.extend(
        _payload_tree_shared_shape_lines(bp, ctx, old_props, new_props, shared_props)
    )
    return out


def _payload_tree_lines_for_resource(
    old_payload_item: dict[str, Any],
    new_payload_item: dict[str, Any],
) -> list[str]:
    lines: list[str] = []
    for kind in ("create", "update"):
        old_defs = old_payload_item.get(f"{kind}_payload_definitions", {})
        new_defs = new_payload_item.get(f"{kind}_payload_definitions", {})
        if not isinstance(old_defs, dict) or not isinstance(new_defs, dict):
            continue
        def_names = sorted(set(old_defs) | set(new_defs))
        for def_name in def_names:
            raw_o = old_defs.get(def_name)
            raw_n = new_defs.get(def_name)
            old_def = raw_o if isinstance(raw_o, dict) else {}
            new_def = raw_n if isinstance(raw_n, dict) else {}
            lines.extend(
                _payload_tree_lines_for_definitions(kind, def_name, old_def, new_def)
            )
    return lines


def _build_resource_delta_tree_lines(
    old_r: dict[str, dict[str, Any]],
    new_r: dict[str, dict[str, Any]],
    old_p: dict[str, dict[str, Any]],
    new_p: dict[str, dict[str, Any]],
    *,
    max_tree_lines: int = 400,
) -> list[str]:
    """Assemble tree text lines for changed resources only (deterministic order)."""
    old_names = set(old_r)
    new_names = set(new_r)
    added = sorted(new_names - old_names)
    removed = sorted(old_names - new_names)
    shared = sorted(old_names & new_names)

    blocks: list[str] = []
    bp = _tree_branch()

    for name in added:
        blocks.append(name)
        blocks.append(f"{bp}(+) resource [added to SDK façade]")

    for name in removed:
        blocks.append(name)
        blocks.append(f"{bp}(-) resource [removed from SDK façade]")

    for name in shared:
        old_item = old_r[name]
        new_item = new_r[name]
        child_lines: list[str] = []
        child_lines.extend(_facade_tree_lines(old_item, new_item))
        old_payload_item = old_p.get(name, {})
        new_payload_item = new_p.get(name, {})
        if isinstance(old_payload_item, dict) and isinstance(new_payload_item, dict):
            child_lines.extend(
                _payload_tree_lines_for_resource(old_payload_item, new_payload_item)
            )
        if not child_lines:
            continue
        blocks.append(name)
        blocks.extend(child_lines)

    if len(blocks) > max_tree_lines:
        omitted = len(blocks) - max_tree_lines + 1
        trunc = f"{bp}… (truncated: {omitted} more lines omitted)"
        return [*blocks[: max_tree_lines - 1], trunc]
    return blocks


def _shared_facade_diff_lines(
    name: str,
    old_item: dict[str, Any],
    new_item: dict[str, Any],
) -> tuple[list[str], list[str]]:
    """Return (operation_delta_lines, field_delta_lines) for one resource."""
    op_out: list[str] = []
    field_out: list[str] = []
    old_ops = set(old_item.get("supported_ops", []))
    new_ops = set(new_item.get("supported_ops", []))
    add_ops = sorted(new_ops - old_ops)
    del_ops = sorted(old_ops - new_ops)
    if add_ops or del_ops:
        fragments: list[str] = []
        if add_ops:
            fragments.append(f"+ops={','.join(add_ops)}")
        if del_ops:
            fragments.append(f"-ops={','.join(del_ops)}")
        op_out.append(f"- {name}: " + "; ".join(fragments))

    old_mut = set(old_item.get("mutable_fields", []))
    new_mut = set(new_item.get("mutable_fields", []))
    old_imm = set(old_item.get("immutable_fields", []))
    new_imm = set(new_item.get("immutable_fields", []))
    mut_add = sorted(new_mut - old_mut)
    mut_del = sorted(old_mut - new_mut)
    imm_add = sorted(new_imm - old_imm)
    imm_del = sorted(old_imm - new_imm)
    if mut_add or mut_del or imm_add or imm_del:
        frag: list[str] = []
        if mut_add:
            frag.append(f"+mutable={','.join(mut_add[:8])}")
        if mut_del:
            frag.append(f"-mutable={','.join(mut_del[:8])}")
        if imm_add:
            frag.append(f"+immutable={','.join(imm_add[:8])}")
        if imm_del:
            frag.append(f"-immutable={','.join(imm_del[:8])}")
        field_out.append(f"- {name}: " + "; ".join(frag))
    return op_out, field_out


def _payload_delta_lines_for_resource(
    name: str,
    old_payload_item: dict[str, Any],
    new_payload_item: dict[str, Any],
) -> list[str]:
    lines: list[str] = []
    for kind in ("create", "update"):
        old_defs = old_payload_item.get(f"{kind}_payload_definitions", {})
        new_defs = new_payload_item.get(f"{kind}_payload_definitions", {})
        if not isinstance(old_defs, dict) or not isinstance(new_defs, dict):
            continue
        def_names = sorted(set(old_defs) | set(new_defs))
        for def_name in def_names:
            raw_o = old_defs.get(def_name)
            raw_n = new_defs.get(def_name)
            old_def = raw_o if isinstance(raw_o, dict) else {}
            new_def = raw_n if isinstance(raw_n, dict) else {}
            lines.extend(
                _payload_lines_for_definitions(name, kind, def_name, old_def, new_def)
            )
    return lines


def _group_lines_by_resource(lines: list[str]) -> dict[str, list[str]]:
    """Group summary lines by resource attr_name token."""
    grouped: dict[str, list[str]] = {}
    for line in lines:
        if not isinstance(line, str) or not line.startswith("- "):
            continue
        content = line[2:].strip()
        resource = content.split(" ", 1)[0].strip().rstrip(":")
        if not resource:
            continue
        grouped.setdefault(resource, []).append(line)
    return grouped


def build_upstream_delta_structured(
    old_data: dict[str, Any],
    new_data: dict[str, Any],
) -> dict[str, Any]:
    """Return machine-readable upstream delta payload for CI gating."""
    old_ops = _operations_list(old_data)
    new_ops = _operations_list(new_data)
    old_endpoints = _endpoints_set(old_ops)
    new_endpoints = _endpoints_set(new_ops)
    old_by_tag = _endpoints_by_tag(old_ops)
    new_by_tag = _endpoints_by_tag(new_ops)
    old_tag_names = set(old_by_tag)
    new_tag_names = set(new_by_tag)
    added_tags = sorted(new_tag_names - old_tag_names)
    removed_tags = sorted(old_tag_names - new_tag_names)
    shared_tags = sorted(old_tag_names & new_tag_names)
    tag_deltas = _tag_group_deltas(old_by_tag, new_by_tag, shared_tags)
    added_endpoints = sorted(new_endpoints - old_endpoints)
    removed_endpoints = sorted(old_endpoints - new_endpoints)
    old_ix = _index_op_by_endpoint(old_ops)
    new_ix = _index_op_by_endpoint(new_ops)
    signature_drift = _signature_drift_lines(old_ix, new_ix)
    has_delta = bool(
        added_tags
        or removed_tags
        or tag_deltas
        or added_endpoints
        or removed_endpoints
        or signature_drift
    )
    return {
        "has_upstream_delta": has_delta,
        "added_tags": added_tags,
        "removed_tags": removed_tags,
        "tag_deltas": tag_deltas,
        "added_endpoints": added_endpoints,
        "removed_endpoints": removed_endpoints,
        "signature_drift": signature_drift,
    }


def build_resource_delta_structured(
    old_facade: dict[str, Any],
    new_facade: dict[str, Any],
    old_payload: dict[str, Any],
    new_payload: dict[str, Any],
) -> dict[str, Any]:
    """Return machine-readable resource delta payload for CI gating."""
    old_r = _resources_index(old_facade)
    new_r = _resources_index(new_facade)
    old_p = _resources_index(old_payload)
    new_p = _resources_index(new_payload)

    old_names = set(old_r)
    new_names = set(new_r)
    added = sorted(new_names - old_names)
    removed = sorted(old_names - new_names)
    shared = sorted(old_names & new_names)

    op_changes: list[str] = []
    field_changes: list[str] = []
    payload_changes: list[str] = []
    for name in shared:
        o_lines, f_lines = _shared_facade_diff_lines(name, old_r[name], new_r[name])
        op_changes.extend(o_lines)
        field_changes.extend(f_lines)
        old_payload_item = old_p.get(name, {})
        new_payload_item = new_p.get(name, {})
        if isinstance(old_payload_item, dict) and isinstance(new_payload_item, dict):
            payload_changes.extend(
                _payload_delta_lines_for_resource(
                    name, old_payload_item, new_payload_item
                )
            )

    op_by_resource = _group_lines_by_resource(op_changes)
    field_by_resource = _group_lines_by_resource(field_changes)
    payload_by_resource = _group_lines_by_resource(payload_changes)
    changed_resources = sorted(
        set(added)
        | set(removed)
        | set(op_by_resource)
        | set(field_by_resource)
        | set(payload_by_resource)
    )
    return {
        "has_resource_delta": bool(changed_resources),
        "added_resources": added,
        "removed_resources": removed,
        "changed_resources": changed_resources,
        "resource_op_changes": op_by_resource,
        "resource_field_changes": field_by_resource,
        "resource_payload_changes": payload_by_resource,
    }


def _append_resource_field_inventory(
    lines: list[str],
    new_r: dict[str, dict[str, Any]],
    new_p: dict[str, dict[str, Any]],
    *,
    max_resources: int = 40,
    max_facade_field_lines: int = 48,
    max_defs_per_kind: int = 8,
    max_props_per_def: int = 64,
    max_payload_depth: int = 4,
) -> None:
    """Append per-resource facade + payload field inventory."""
    lines.append(f"- SDK facade resources (current run, attr_name): {len(new_r)}")
    if not new_r:
        lines.append("- (No resources in facade_contract payload.)")
        return
    lines.append(
        "<details><summary>Per-resource fields (facade + payload schemas: types & API "
        "descriptions used for docstrings)</summary>"
    )
    lines.append("")
    names_sorted = sorted(new_r.keys())
    for i, name in enumerate(names_sorted):
        if i >= max_resources:
            lines.append("")
            lines.append(
                f"*…{len(names_sorted) - max_resources} more resources omitted "
                "(raise caps in workflow if needed).*"
            )
            break
        item = new_r[name]
        lines.append(f"<details><summary>{name} (facade attr_name)</summary>")
        lines.append("")
        lines.append("```text")
        ops = item.get("supported_ops", [])
        if isinstance(ops, list):
            ops_s = ", ".join(sorted(x for x in ops if isinstance(x, str)))
            lines.append(f"supported_ops: {ops_s}")
        lines.append("")
        lines.extend(
            _format_facade_detail_lines(item, max_field_lines=max_facade_field_lines)
        )
        lines.append("")
        payload_item = new_p.get(name, {})
        if isinstance(payload_item, dict) and payload_item:
            lines.append("--- payload_schemas (create/update bodies) ---")
            lines.extend(
                _format_payload_inventory_lines(
                    payload_item,
                    max_defs_per_kind=max_defs_per_kind,
                    max_props_per_def=max_props_per_def,
                    max_depth=max_payload_depth,
                )
            )
        else:
            lines.append("(no payload_schemas entry for this resource)")
        lines.append("```")
        lines.append("</details>")
        lines.append("")
    lines.append("</details>")


def render_resource_delta_markdown(
    old_facade: dict[str, Any],
    new_facade: dict[str, Any],
    old_payload: dict[str, Any],
    new_payload: dict[str, Any],
    *,
    baseline_ref: str = "HEAD",
    include_resource_inventory: bool = False,
    max_list_lines: int = 80,
    max_payload_lines: int = 120,
    max_tree_lines: int = 400,
) -> list[str]:
    """Build markdown: tree diffs vs baseline; optionally full per-resource inventory.

    Default output is a **tree view** of changed resources and fields only
    (facade ``supported_ops`` / mutable / immutable paths and create/update payload
    properties). Section headings are emitted by the workflow; this function returns
    body lines (tree in a ``text`` code fence, or inventory expanders).
    """
    effective_tree_cap = min(max_tree_lines, max_list_lines + max_payload_lines)

    old_r = _resources_index(old_facade)
    new_r = _resources_index(new_facade)
    old_p = _resources_index(old_payload)
    new_p = _resources_index(new_payload)

    old_names = set(old_r)
    new_names = set(new_r)
    added = sorted(new_names - old_names)
    removed = sorted(old_names - new_names)
    shared = sorted(old_names & new_names)

    op_changes: list[str] = []
    field_changes: list[str] = []
    payload_changes: list[str] = []

    for name in shared:
        old_item = old_r[name]
        new_item = new_r[name]
        o_lines, f_lines = _shared_facade_diff_lines(name, old_item, new_item)
        op_changes.extend(o_lines)
        field_changes.extend(f_lines)

        old_payload_item = old_p.get(name, {})
        new_payload_item = new_p.get(name, {})
        if not isinstance(old_payload_item, dict) or not isinstance(
            new_payload_item, dict
        ):
            continue

        payload_changes.extend(
            _payload_delta_lines_for_resource(name, old_payload_item, new_payload_item)
        )

    lines: list[str] = []
    tree_lines = _build_resource_delta_tree_lines(
        old_r, new_r, old_p, new_p, max_tree_lines=effective_tree_cap
    )

    if tree_lines:
        lines.append("```text")
        lines.extend(tree_lines)
        lines.append("```")
    else:
        lines.append(
            "*No resource façade or payload deltas vs baseline "
            f"``git {baseline_ref}``.*"
        )

    if include_resource_inventory:
        lines.append("")
        lines.append("#### Full field inventory (opt-in)")
        lines.append(
            "Run ``uv run python devtools/model_sync_pr_deltas.py --print-resource "
            "--include-resource-inventory`` for the full snapshot."
        )
        _append_resource_field_inventory(lines, new_r, new_p)

    no_res_delta = (
        bool(old_r)
        and bool(new_r)
        and not added
        and not removed
        and not op_changes
        and not field_changes
        and not payload_changes
    )
    if no_res_delta:
        lines.append("")
        lines.append("#### Maintainer readout")
        lines.append(
            "- **What changed in facade/payload JSON:** Nothing vs "
            f"`git {baseline_ref}` — same resources, `supported_ops`, "
            "mutable/immutable field sets, and create/update payload shapes."
        )
        lines.append(
            "- **So why did git status show workspace changes?** Usually "
            "`provenance.json` only (timestamps/paths); it is reset before branch push."
        )
        lines.append(
            "  **Provenance delta** appears in this summary when that file was dirty."
        )

    return lines


def append_github_output_markdown(key: str, lines: list[str]) -> None:
    """Write a heredoc block to GITHUB_OUTPUT for composite output."""
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with open(output_path, "a", encoding="utf-8") as fh:
        fh.write(f"{key}<<EOF\n")
        fh.write("\n".join(lines))
        fh.write("\nEOF\n")


def append_github_output_text(key: str, text: str) -> None:
    """Write a text block to GITHUB_OUTPUT."""
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with open(output_path, "a", encoding="utf-8") as fh:
        fh.write(f"{key}<<EOF\n")
        fh.write(text)
        fh.write("\nEOF\n")


def _write_stdout(text: str) -> None:
    sys.stdout.write(text)
    if not text.endswith("\n"):
        sys.stdout.write("\n")


def main(argv: list[str] | None = None) -> int:  # noqa: C901
    """Parse CLI args and print or write delta markdown."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--git-ref",
        default="HEAD",
        help=(
            "Git ref for baseline JSON (default HEAD). "
            "Ignored when --auto-baseline is set."
        ),
    )
    parser.add_argument(
        "--auto-baseline",
        action="store_true",
        help=(
            "Resolve baseline via origin/main, origin/master, main, master, else HEAD "
            "(overrides --git-ref)"
        ),
    )
    parser.add_argument(
        "--operation-metadata",
        type=Path,
        default=DEFAULT_OPERATION_METADATA,
        help="Path to operation_path_metadata.json",
    )
    parser.add_argument(
        "--facade",
        type=Path,
        default=DEFAULT_FACADE,
        help="Path to facade_contract.json",
    )
    parser.add_argument(
        "--payload",
        type=Path,
        default=DEFAULT_PAYLOAD,
        help="Path to payload_schemas.json",
    )
    parser.add_argument(
        "--provenance",
        type=Path,
        default=DEFAULT_PROVENANCE,
        help="Path to provenance.json",
    )
    parser.add_argument(
        "--print-upstream",
        action="store_true",
        help="Print upstream delta markdown to stdout",
    )
    parser.add_argument(
        "--print-resource",
        action="store_true",
        help="Print resource section (default: diffs vs --git-ref only)",
    )
    parser.add_argument(
        "--include-resource-inventory",
        action="store_true",
        help="Include large per-resource facade+payload snapshot (not a diff list)",
    )
    parser.add_argument(
        "--print-provenance",
        action="store_true",
        help="Print provenance.json field delta vs --git-ref",
    )
    parser.add_argument(
        "--print-summary",
        action="store_true",
        help="Print compact delta summary vs baseline (upstream/resources/provenance)",
    )
    parser.add_argument(
        "--print-all-markdown",
        action="store_true",
        help="Print full upstream, resource, and provenance markdown sections",
    )
    parser.add_argument(
        "--write-github-output",
        action="store_true",
        help="Append summary_markdown to GITHUB_OUTPUT (use with one of *-only flags)",
    )
    wf = parser.add_mutually_exclusive_group()
    wf.add_argument(
        "--upstream-only",
        action="store_true",
        help="With --write-github-output: write only upstream delta",
    )
    wf.add_argument(
        "--resource-only",
        action="store_true",
        help="With --write-github-output: write only resource delta",
    )
    wf.add_argument(
        "--provenance-only",
        action="store_true",
        help="With --write-github-output: write only provenance delta",
    )
    wf.add_argument(
        "--upstream-json-only",
        action="store_true",
        help="With --write-github-output: write only upstream structured JSON",
    )
    wf.add_argument(
        "--resource-json-only",
        action="store_true",
        help="With --write-github-output: write only resource structured JSON",
    )
    args = parser.parse_args(argv)

    if args.write_github_output and not (
        args.upstream_only
        or args.resource_only
        or args.provenance_only
        or args.upstream_json_only
        or args.resource_json_only
    ):
        parser.error(
            "--write-github-output requires --upstream-only, --resource-only, or "
            "--provenance-only, --upstream-json-only, --resource-json-only"
        )

    if (
        not args.print_upstream
        and not args.print_resource
        and not args.print_provenance
        and not args.write_github_output
        and not args.print_summary
        and not args.print_all_markdown
    ):
        parser.error(
            "Specify at least one of --print-upstream, --print-resource, "
            "--print-provenance, --print-summary, --print-all-markdown, "
            "--write-github-output"
        )

    repo_root = Path(__file__).resolve().parents[1]
    from sync.baseline_ref import resolve_auto_baseline_ref

    effective_ref = (
        resolve_auto_baseline_ref(repo_root) if args.auto_baseline else args.git_ref
    )

    if args.print_summary:
        from sync.delta_summary import render_compact_delta_summary_lines

        _write_stdout(
            "\n".join(
                render_compact_delta_summary_lines(
                    git_ref=effective_ref,
                    repo_root=repo_root,
                    operation_metadata=args.operation_metadata,
                    facade=args.facade,
                    payload=args.payload,
                    provenance=args.provenance,
                )
            )
        )

    if args.print_all_markdown:
        old_meta = git_show_json(effective_ref, args.operation_metadata)
        new_meta = load_json_file(args.operation_metadata)
        _write_stdout("## Upstream\n")
        _write_stdout(
            "\n".join(
                render_upstream_delta_markdown(
                    old_meta, new_meta, baseline_ref=effective_ref
                )
            )
        )
        _write_stdout("\n\n## Resources\n")
        old_facade = git_show_json(effective_ref, args.facade)
        new_facade = load_json_file(args.facade)
        old_payload = git_show_json(effective_ref, args.payload)
        new_payload = load_json_file(args.payload)
        _write_stdout(
            "\n".join(
                render_resource_delta_markdown(
                    old_facade,
                    new_facade,
                    old_payload,
                    new_payload,
                    baseline_ref=effective_ref,
                    include_resource_inventory=args.include_resource_inventory,
                )
            )
        )
        _write_stdout("\n\n## Provenance\n")
        old_prov = git_show_json(effective_ref, args.provenance)
        new_prov = load_json_file(args.provenance)
        _write_stdout(
            "\n".join(
                render_provenance_delta_markdown(
                    old_prov, new_prov, baseline_ref=effective_ref
                )
            )
        )

    run_upstream = args.print_upstream or (
        args.write_github_output and (args.upstream_only or args.upstream_json_only)
    )
    run_resource = args.print_resource or (
        args.write_github_output and (args.resource_only or args.resource_json_only)
    )
    run_provenance = args.print_provenance or (
        args.write_github_output and args.provenance_only
    )

    if run_upstream:
        old_meta = git_show_json(effective_ref, args.operation_metadata)
        new_meta = load_json_file(args.operation_metadata)
        up_lines = render_upstream_delta_markdown(
            old_meta, new_meta, baseline_ref=effective_ref
        )
        if args.print_upstream:
            _write_stdout("\n".join(up_lines))
        if args.write_github_output and args.upstream_only:
            append_github_output_markdown("summary_markdown", up_lines)
        if args.write_github_output and args.upstream_json_only:
            up_json = build_upstream_delta_structured(old_meta, new_meta)
            append_github_output_text("delta_json", json.dumps(up_json, sort_keys=True))

    if run_resource:
        old_facade = git_show_json(effective_ref, args.facade)
        new_facade = load_json_file(args.facade)
        old_payload = git_show_json(effective_ref, args.payload)
        new_payload = load_json_file(args.payload)
        res_lines = render_resource_delta_markdown(
            old_facade,
            new_facade,
            old_payload,
            new_payload,
            baseline_ref=effective_ref,
            include_resource_inventory=args.include_resource_inventory,
        )
        if args.print_resource:
            _write_stdout("\n".join(res_lines))
        if args.write_github_output and args.resource_only:
            append_github_output_markdown("summary_markdown", res_lines)
        if args.write_github_output and args.resource_json_only:
            res_json = build_resource_delta_structured(
                old_facade, new_facade, old_payload, new_payload
            )
            append_github_output_text(
                "delta_json", json.dumps(res_json, sort_keys=True)
            )

    if run_provenance:
        old_prov = git_show_json(effective_ref, args.provenance)
        new_prov = load_json_file(args.provenance)
        prov_lines = render_provenance_delta_markdown(
            old_prov, new_prov, baseline_ref=effective_ref
        )
        if args.print_provenance:
            _write_stdout("\n".join(prov_lines))
        if args.write_github_output and args.provenance_only:
            append_github_output_markdown("summary_markdown", prov_lines)

    return 0


if __name__ == "__main__":
    sys.exit(main())

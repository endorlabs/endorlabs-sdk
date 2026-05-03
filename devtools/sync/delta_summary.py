"""Compact model-sync delta summary for CLI and model_sync_pr_deltas."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


def _ensure_scripts_on_path() -> None:
    """Allow importing ``model_sync_pr_deltas`` from the ``sync`` package."""
    scripts = Path(__file__).resolve().parent.parent
    s = str(scripts)
    if s not in sys.path:
        sys.path.insert(0, s)


def _default_paths(repo_root: Path) -> tuple[Path, Path, Path, Path]:
    base = repo_root / "workspace" / "model-sync" / "custom_mapping"
    return (
        base / "mapping" / "operation_path_metadata.json",
        base / "facade_contract.json",
        base / "mapping" / "payload_schemas.json",
        base / "provenance.json",
    )


def _git_path(repo_root: Path, path: Path) -> Path:
    """Path relative to repo root for ``git show ref:path`` (POSIX segments)."""
    try:
        return path.relative_to(repo_root.resolve())
    except ValueError:
        return path


def _resolved_under_repo(repo_root: Path, path: Path) -> Path:
    """Absolute path to artifact (default args are repo-relative)."""
    return path.resolve() if path.is_absolute() else (repo_root / path).resolve()


def provenance_meaningful_delta(old: dict[str, Any], new: dict[str, Any]) -> bool:
    """True if spec hash or endorctl version differs (ignore timestamps-only churn)."""
    for key in ("spec_sha256", "endorctl_version"):
        if old.get(key) != new.get(key):
            return True
    return False


def render_compact_delta_summary_lines(
    *,
    git_ref: str,
    repo_root: Path,
    operation_metadata: Path | None = None,
    facade: Path | None = None,
    payload: Path | None = None,
    provenance: Path | None = None,
) -> list[str]:
    """Build short markdown lines for terminal / job summary."""
    _ensure_scripts_on_path()
    import model_sync_pr_deltas as msd

    op_path, facade_path, payload_path, prov_path = _default_paths(repo_root)
    if operation_metadata is not None:
        op_path = operation_metadata
    if facade is not None:
        facade_path = facade
    if payload is not None:
        payload_path = payload
    if provenance is not None:
        prov_path = provenance

    op_path = _resolved_under_repo(repo_root, op_path)
    facade_path = _resolved_under_repo(repo_root, facade_path)
    payload_path = _resolved_under_repo(repo_root, payload_path)
    prov_path = _resolved_under_repo(repo_root, prov_path)

    old_meta = msd.git_show_json(git_ref, _git_path(repo_root, op_path))
    new_meta = msd.load_json_file(op_path)
    up = msd.build_upstream_delta_structured(old_meta, new_meta)

    old_facade = msd.git_show_json(git_ref, _git_path(repo_root, facade_path))
    new_facade = msd.load_json_file(facade_path)
    old_payload = msd.git_show_json(git_ref, _git_path(repo_root, payload_path))
    new_payload = msd.load_json_file(payload_path)
    res = msd.build_resource_delta_structured(
        old_facade, new_facade, old_payload, new_payload
    )

    old_prov = msd.git_show_json(git_ref, _git_path(repo_root, prov_path))
    new_prov = msd.load_json_file(prov_path)
    prov_changed = provenance_meaningful_delta(old_prov, new_prov)

    lines: list[str] = []
    lines.append(f"## Delta summary (vs `git {git_ref}`)")
    lines.append("")
    if up["has_upstream_delta"]:
        lines.append(
            "- **Upstream (OpenAPI operations):** changed "
            f"(+{len(up['added_endpoints'])} / -{len(up['removed_endpoints'])} endpoints; "
            f"+{len(up['added_tags'])} / -{len(up['removed_tags'])} tag groups)"
        )
    else:
        lines.append("- **Upstream (OpenAPI operations):** no catalog delta vs baseline")
    if res["has_resource_delta"]:
        lines.append(
            "- **Resources / payloads:** changed "
            f"(+{len(res['added_resources'])} / -{len(res['removed_resources'])} resources; "
            f"{len(res['changed_resources'])} resource names touched)"
        )
    else:
        lines.append("- **Resources / payloads:** no facade/payload delta vs baseline")
    if prov_changed:
        lines.append(
            "- **Provenance:** `spec_sha256` or `endorctl_version` differs vs baseline"
        )
    else:
        lines.append(
            "- **Provenance:** no spec/tooling delta vs baseline (timestamps may still differ)"
        )
    lines.append("")
    lines.append(
        "Full detail: `uv run python devtools/model_sync_pr_deltas.py "
        f"--git-ref {git_ref} --print-all-markdown` "
        "(or `--auto-baseline --print-all-markdown` for the same baseline pick)"
    )
    return lines


def render_compact_delta_summary_text(**kwargs: Any) -> str:
    """Single string for logging."""
    return "\n".join(render_compact_delta_summary_lines(**kwargs))

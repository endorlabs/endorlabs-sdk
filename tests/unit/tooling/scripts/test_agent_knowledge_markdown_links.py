"""Validate relative markdown links in the shipped agent knowledge bundle."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SHIPPED_ROOT = REPO_ROOT / "src" / "endorlabs" / "agent_knowledge"
LINK_RE = re.compile(r"\]\(([^)]+)\)")
SKIP_PREFIXES = ("http://", "https://", "mailto:", "#")


def _iter_invalid_relative_links(base: Path) -> list[tuple[Path, str, str]]:
    """Return relative links that escape shipped root or resolve off-disk."""
    invalid: list[tuple[Path, str, str]] = []
    shipped_resolved = base.resolve()
    for md_path in sorted(base.rglob("*.md")):
        text = md_path.read_text(encoding="utf-8")
        for raw_target in LINK_RE.findall(text):
            target = raw_target.split("#", 1)[0].strip()
            if not target or target.startswith(SKIP_PREFIXES):
                continue
            resolved = (md_path.parent / target).resolve()
            try:
                resolved.relative_to(shipped_resolved)
            except ValueError:
                invalid.append(
                    (
                        md_path.relative_to(REPO_ROOT),
                        target,
                        "escapes shipped agent_knowledge root",
                    )
                )
                continue
            if not resolved.exists():
                invalid.append(
                    (
                        md_path.relative_to(REPO_ROOT),
                        target,
                        "target missing on disk",
                    )
                )
    return invalid


def test_shipped_agent_knowledge_relative_links_stay_in_bundle() -> None:
    invalid = _iter_invalid_relative_links(SHIPPED_ROOT)
    if invalid:
        lines = "\n".join(
            f"  {path}: {target} ({reason})" for path, target, reason in invalid[:20]
        )
        extra = ""
        if len(invalid) > 20:
            extra = f"\n  ... and {len(invalid) - 20} more"
        pytest.fail(
            f"Invalid relative markdown links in shipped bundle:\n{lines}{extra}"
        )

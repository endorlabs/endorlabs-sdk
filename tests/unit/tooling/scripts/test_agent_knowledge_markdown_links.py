"""Validate relative markdown links in the shipped agent knowledge bundle."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
SHIPPED_ROOT = REPO_ROOT / "src" / "endorlabs" / "agent_knowledge"
LINK_RE = re.compile(r"\]\(([^)]+)\)")
SKIP_PREFIXES = ("http://", "https://", "mailto:", "#")


def _iter_broken_relative_links(base: Path) -> list[tuple[Path, str]]:
    broken: list[tuple[Path, str]] = []
    for md_path in sorted(base.rglob("*.md")):
        text = md_path.read_text(encoding="utf-8")
        for raw_target in LINK_RE.findall(text):
            target = raw_target.split("#", 1)[0].strip()
            if not target or target.startswith(SKIP_PREFIXES):
                continue
            resolved = (md_path.parent / target).resolve()
            if not resolved.exists():
                broken.append((md_path.relative_to(REPO_ROOT), target))
    return broken


def test_shipped_agent_knowledge_relative_links_resolve() -> None:
    broken = _iter_broken_relative_links(SHIPPED_ROOT)
    if broken:
        lines = "\n".join(f"  {path}: {target}" for path, target in broken[:20])
        extra = ""
        if len(broken) > 20:
            extra = f"\n  ... and {len(broken) - 20} more"
        pytest.fail(
            f"Broken relative markdown links in shipped bundle:\n{lines}{extra}"
        )

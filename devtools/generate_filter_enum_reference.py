"""Generate filter enum snippet reference from model-sync StrEnum classes."""

from __future__ import annotations

import sys
from pathlib import Path

from sync.path_safety import find_repo_root


def main() -> int:
    repo = find_repo_root(start=Path(__file__).resolve().parent)
    from doc_facade_helpers import render_filter_enum_snippets_md

    out = repo / "docs" / "generated-reference" / "filter-enum-snippets.md"
    out.write_text(render_filter_enum_snippets_md(), encoding="utf-8")
    print(f"Wrote {out.relative_to(repo)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

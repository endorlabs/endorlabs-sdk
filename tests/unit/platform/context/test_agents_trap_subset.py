"""Root AGENTS.md trap-id allowlist must be a subset of canonical critical traps."""

from __future__ import annotations

import re
from pathlib import Path

import endorlabs

_REPO_ROOT = Path(__file__).resolve().parents[4]
_AGENTS_MD = _REPO_ROOT / "AGENTS.md"
_TRAP_IDS_RE = re.compile(
    r"<!--\s*trap-ids:\s*([a-z0-9_,\-\s]+)\s*-->",
    re.IGNORECASE,
)
_HEADING_ID_RE = re.compile(r"^##\s+([a-z0-9][a-z0-9\-]+)\s*$", re.MULTILINE)


def _parse_agents_trap_ids(text: str) -> set[str]:
    match = _TRAP_IDS_RE.search(text)
    assert match is not None, "AGENTS.md missing <!-- trap-ids: ... --> allowlist"
    return {part.strip() for part in match.group(1).split(",") if part.strip()}


def _parse_critical_trap_ids(text: str) -> set[str]:
    return set(_HEADING_ID_RE.findall(text))


def test_agents_trap_ids_subset_of_critical_validation_traps() -> None:
    """Repo-root AGENTS trap allowlist ⊆ shipped critical-validation-traps headings."""
    agents_ids = _parse_agents_trap_ids(_AGENTS_MD.read_text(encoding="utf-8"))
    assert agents_ids, "AGENTS.md trap-ids allowlist must be non-empty"

    critical_path = (
        endorlabs.agent_knowledge_dir() / "reference" / "critical-validation-traps.md"
    )
    assert critical_path.is_file()
    critical_ids = _parse_critical_trap_ids(critical_path.read_text(encoding="utf-8"))
    assert critical_ids, "critical-validation-traps.md must define ## trap ids"

    missing = sorted(agents_ids - critical_ids)
    assert not missing, f"AGENTS trap ids missing from critical traps: {missing}"

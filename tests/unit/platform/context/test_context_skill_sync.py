"""Unit tests for skill mirror sync helpers."""

from __future__ import annotations

from pathlib import Path

from endorlabs.context import _sync


def test_resolve_skill_sync_targets_supports_explicit_targets() -> None:
    """Explicit targets should resolve without repository heuristics."""
    assert _sync._resolve_skill_sync_targets(target="cursor") == ("cursor",)
    assert _sync._resolve_skill_sync_targets(target="both") == (
        "cursor",
        "claude",
    )


def test_sync_agent_skills_mirrors_tree_and_prunes_stale(tmp_path: Path) -> None:
    """Skill sync should mirror current files and delete removed ones."""
    source_dir = tmp_path / "skills-src"
    repo_root = tmp_path / "repo"
    target_dir = repo_root / ".cursor" / "skills"
    source_file = source_dir / "demo-skill" / "SKILL.md"
    nested_file = source_dir / "demo-skill" / "guide.md"

    source_file.parent.mkdir(parents=True, exist_ok=True)
    repo_root.mkdir()
    source_file.write_text("# Demo\n", encoding="utf-8")
    nested_file.write_text("details\n", encoding="utf-8")

    stale_file = target_dir / "obsolete" / "old.md"
    stale_file.parent.mkdir(parents=True, exist_ok=True)
    stale_file.write_text("stale\n", encoding="utf-8")

    synced = _sync.sync_agent_skills(
        repo_root=repo_root,
        target="cursor",
        source_dir=source_dir,
    )

    assert synced == {"cursor": target_dir}
    assert (target_dir / "demo-skill" / "SKILL.md").read_text(encoding="utf-8") == (
        "# Demo\n"
    )
    assert (target_dir / "demo-skill" / "guide.md").read_text(encoding="utf-8") == (
        "details\n"
    )
    assert not stale_file.exists()

"""Unit tests for the custom SAST rule manager helper."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import yaml


def _load_sast_rule_manager() -> ModuleType:
    root = Path(__file__).resolve().parents[4]
    cursor_path = (
        root
        / ".cursor"
        / "skills"
        / "custom-sast-rules"
        / "scripts"
        / "sast_rule_manager.py"
    )
    skills_src_path = (
        root / "agent-skills" / "custom-sast-rules" / "scripts" / "sast_rule_manager.py"
    )
    script_path = cursor_path if cursor_path.is_file() else skills_src_path
    spec = importlib.util.spec_from_file_location(
        "sast_rule_manager_for_test", script_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cmd_import_preserves_compound_rule_structure(tmp_path: Path) -> None:
    manager = _load_sast_rule_manager()
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "compound.yml").write_text(
        """rules:
  - id: parser-backed-demo
    message: "Parser backed demo"
    severity: ERROR
    languages: [java]
    paths:
      include:
        - "**/*.java"
    metadata:
      category: security
      description: Demo parser-backed rule
      display-name: Parser backed demo
      endor-category: vulnerability
      rule-origin-note: unit-test
      endor-tags: [demo]
      technology: [java]
    pattern-either:
      - patterns:
          - pattern-inside: |
              String $JWK = $S;
              ...
              JWK.parse($JWK);
          - metavariable-regex:
              metavariable: $S
              regex: '.*kty.*'
""",
        encoding="utf-8",
    )

    client = MagicMock()
    client.SemgrepRule.list.return_value = []
    client.SemgrepRule.create.return_value = MagicMock(uuid="new-rule-uuid")

    manager.cmd_import(
        client=client,
        namespace="tenant.ns",
        rules_dir=rules_dir,
        force=False,
        dry_run=False,
    )

    client.SemgrepRule.create.assert_called_once()
    payload = client.SemgrepRule.create.call_args.kwargs["payload"]
    assert payload.spec is not None
    assert payload.spec.rule is not None
    rule_dump = payload.spec.rule.model_dump(exclude_none=True)
    assert "pattern-either" in rule_dump
    assert payload.spec.rule.paths is not None
    assert payload.spec.rule.paths.include == ["**/*.java"]
    assert payload.spec.rule.metadata is not None
    assert rule_dump["metadata"]["display-name"] == "Parser backed demo"


def test_cmd_import_update_preserves_compound_rule_structure(tmp_path: Path) -> None:
    manager = _load_sast_rule_manager()
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "compound.yml").write_text(
        """rules:
  - id: parser-backed-demo
    message: "Parser backed demo"
    severity: ERROR
    languages: [csharp]
    paths:
      include:
        - "**/*.cs"
    metadata:
      category: security
      description: Demo parser-backed rule
      display-name: Parser backed demo
      endor-category: vulnerability
      rule-origin-note: unit-test
      endor-tags: [demo]
      technology: [csharp]
    pattern-either:
      - patterns:
          - pattern-inside: |
              var $JWK = $S;
              ...
              var $KEY = new JsonWebKey($JWK);
          - metavariable-regex:
              metavariable: $S
              regex: '.*kty.*'
""",
        encoding="utf-8",
    )

    client = MagicMock()
    existing = MagicMock(uuid="existing-rule-uuid")
    client.SemgrepRule.list.return_value = [existing]

    manager.cmd_import(
        client=client,
        namespace="tenant.ns",
        rules_dir=rules_dir,
        force=True,
        dry_run=False,
    )

    client.SemgrepRule.update.assert_called_once()
    payload = client.SemgrepRule.update.call_args.kwargs["payload"]
    assert payload.spec is not None
    assert payload.spec.rule is not None
    rule_dump = payload.spec.rule.model_dump(exclude_none=True)
    assert "pattern-either" in rule_dump
    assert payload.spec.rule.paths is not None
    assert payload.spec.rule.paths.include == ["**/*.cs"]
    assert payload.spec.rule.metadata is not None
    assert rule_dump["metadata"]["display-name"] == "Parser backed demo"


def test_cmd_import_warns_and_drops_unknown_metadata(tmp_path: Path) -> None:
    manager = _load_sast_rule_manager()
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "drop-unknown.yml").write_text(
        """rules:
  - id: drop-unknown
    message: "Drop unknown metadata"
    severity: ERROR
    languages: [generic]
    pattern: "jwt"
    metadata:
      category: security
      description: test
      unknown-key: should-drop
""",
        encoding="utf-8",
    )

    client = MagicMock()
    client.SemgrepRule.list.return_value = []
    client.SemgrepRule.create.return_value = MagicMock(uuid="new-rule-uuid")

    manager.cmd_import(
        client=client,
        namespace="tenant.ns",
        rules_dir=rules_dir,
        force=False,
        dry_run=False,
    )

    payload = client.SemgrepRule.create.call_args.kwargs["payload"]
    assert payload.spec is not None
    assert payload.spec.yaml is not None
    assert "unknown-key" not in payload.spec.yaml


def test_cmd_import_drops_parser_unsupported_short_description(tmp_path: Path) -> None:
    manager = _load_sast_rule_manager()
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    (rules_dir / "drop-short-description.yml").write_text(
        """rules:
  - id: drop-short-description
    message: "Drop parser-unsupported metadata"
    severity: ERROR
    languages: [generic]
    pattern: "jwk"
    metadata:
      category: security
      short-description: parser should reject this
      description: test
""",
        encoding="utf-8",
    )

    client = MagicMock()
    client.SemgrepRule.list.return_value = []
    client.SemgrepRule.create.return_value = MagicMock(uuid="new-rule-uuid")

    manager.cmd_import(
        client=client,
        namespace="tenant.ns",
        rules_dir=rules_dir,
        force=False,
        dry_run=False,
    )

    payload = client.SemgrepRule.create.call_args.kwargs["payload"]
    assert payload.spec is not None
    assert payload.spec.yaml is not None
    parsed = yaml.safe_load(payload.spec.yaml)
    rules = parsed.get("rules", [])
    assert isinstance(rules, list)
    metadata = rules[0].get("metadata", {})
    assert "short-description" not in metadata

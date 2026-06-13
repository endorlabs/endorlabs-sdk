"""Parametrized wire deserialization tests for consumer resource models."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES_ROOT = REPO_ROOT / "tests" / "fixtures" / "models"
FIXTURE_NAME = "list_row_min.json"


def _kind_from_module(module: str) -> str:
    parts = module.split("_")
    return "".join(p[:1].upper() + p[1:] for p in parts)


def _model_class(module: str, kind: str):
    mod = importlib.import_module(f"endorlabs.resources.{module}")
    return getattr(mod, kind, None) or getattr(mod, kind.replace("V1", ""), None)


def _fixture_cases() -> list[tuple[str, str, Path]]:
    cases: list[tuple[str, str, Path]] = []
    for path in sorted(FIXTURES_ROOT.glob(f"*/{FIXTURE_NAME}")):
        module = path.parent.name
        kind = _kind_from_module(module)
        cases.append((module, kind, path))
    return cases


@pytest.mark.parametrize(("module", "kind", "fixture_path"), _fixture_cases())
def test_wire_list_row_min_deserializes(
    module: str, kind: str, fixture_path: Path
) -> None:
    """Golden list-row fixtures must construct without validation errors."""
    model_cls = _model_class(module, kind)
    assert model_cls is not None, f"No model class for {module}.{kind}"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    from endorlabs.resources.consumer.wire_compat import deserialize_list_row

    instance = deserialize_list_row(model_cls, payload)
    assert instance is not None

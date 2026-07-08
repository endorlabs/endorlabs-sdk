"""Tests for collect benchmark helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock

from endorlabs.core.whoami import WhoamiResult

_REPO_ROOT = Path(__file__).resolve().parents[5]
_BENCHMARK_PATH = _REPO_ROOT / "devtools" / "estate_collect_benchmark.py"
_spec = importlib.util.spec_from_file_location(
    "estate_collect_benchmark",
    _BENCHMARK_PATH,
)
benchmark = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(benchmark)


def test_session_user_slug_from_whoami_result() -> None:
    client = MagicMock()
    client.whoami.return_value = WhoamiResult(identity="User.Name@corp.com")
    assert benchmark._session_user_slug(client) == "user.name"

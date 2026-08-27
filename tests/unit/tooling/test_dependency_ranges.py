"""Guard: published library deps declare ranges, not exact pins."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_PYPROJECT = _REPO_ROOT / "pyproject.toml"

# Exact pin (==) is wrong at the library-manifest boundary.
_EXACT_PIN = re.compile(r"==")


def _tomllib():
    import tomllib

    return tomllib


def _load_project() -> dict:
    data = _tomllib().loads(_PYPROJECT.read_text(encoding="utf-8"))
    return data["project"]


@pytest.mark.parametrize(
    "bucket",
    [
        "dependencies",
        "optional-dependencies.analytics",
    ],
)
def test_runtime_deps_use_compatible_ranges(bucket: str) -> None:
    project = _load_project()
    if bucket == "dependencies":
        specs = project["dependencies"]
    else:
        specs = project["optional-dependencies"]["analytics"]

    assert specs, f"expected non-empty {bucket}"
    for spec in specs:
        assert not _EXACT_PIN.search(spec), (
            f"{bucket} must not use exact pins; got {spec!r}. "
            "Declare a compatible range (e.g. pydantic>=2.11,<3); pin in uv.lock."
        )
        assert ">=" in spec and "<" in spec, (
            f"{bucket} entry {spec!r} should use a lower and upper bound"
        )


def test_consumer_coinstall_floors_documented() -> None:
    """Acceptance floors from the ADX ranges workstream stay installable."""
    deps = _load_project()["dependencies"]
    by_name = {s.split(">", 1)[0].split("=", 1)[0].lower(): s for s in deps}
    assert "pydantic" in by_name
    assert "httpx" in by_name
    # pydantic==2.11 and httpx==0.27 must remain inside the declared ranges.
    assert by_name["pydantic"].startswith("pydantic>="), by_name["pydantic"]
    assert by_name["httpx"].startswith("httpx>="), by_name["httpx"]
    pydantic_floor = by_name["pydantic"].split(">=", 1)[1].split(",", 1)[0]
    httpx_floor = by_name["httpx"].split(">=", 1)[1].split(",", 1)[0]
    assert tuple(int(p) for p in pydantic_floor.split(".")) <= (2, 11)
    assert tuple(int(p) for p in httpx_floor.split(".")) <= (0, 27)

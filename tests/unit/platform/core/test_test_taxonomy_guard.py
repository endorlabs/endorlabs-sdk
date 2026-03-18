"""Guards the domain-driven test taxonomy layout."""

from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def test_domain_buckets_exist_and_have_tests() -> None:
    root = _repo_root()
    required_dirs = [
        root / "tests" / "unit" / "client",
        root / "tests" / "unit" / "workflows",
        root / "tests" / "unit" / "platform",
        root / "tests" / "unit" / "tooling",
        root / "tests" / "integration" / "client",
        root / "tests" / "integration" / "resources",
        root / "tests" / "integration" / "workflows",
    ]
    for directory in required_dirs:
        assert directory.exists(), f"Missing test taxonomy directory: {directory}"
        assert any(directory.rglob("test_*.py")), f"No tests found under: {directory}"

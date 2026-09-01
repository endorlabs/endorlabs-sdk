#!/usr/bin/env python3
"""Verify a built wheel matches shipped MANIFEST paths and import contracts.

Usage:
    uv build
    uv run python devtools/ship/verify_wheel_contents.py
    uv run python devtools/ship/verify_wheel_contents.py --wheel dist/endorlabs-0.7.2-py3-none-any.whl
    uv run python devtools/ship/verify_wheel_contents.py --expect-version 0.7.2
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import textwrap
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BUNDLE_ROOT = ROOT / "src" / "endorlabs" / "agent_knowledge"
MANIFEST_PATH = BUNDLE_ROOT / "MANIFEST.json"
ANALYZE_ROOT = ROOT / "src" / "endorlabs" / "workflows" / "estate" / "analyze"
ESTATE_ROOT = ROOT / "src" / "endorlabs" / "workflows" / "estate"

# Shipped markdown subtrees force-included via pyproject hatch config.
AGENT_KNOWLEDGE_FORCE_INCLUDE = (
    "rules",
    "contracts",
    "skills",
    "templates",
    "reference",
    "workflows",
)


def _run(cmd: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


def find_wheel(dist_dir: Path, wheel: Path | None) -> Path:
    """Return explicit wheel path or newest endorlabs wheel under dist_dir."""
    if wheel is not None:
        if not wheel.is_file():
            msg = f"wheel not found: {wheel}"
            raise FileNotFoundError(msg)
        return wheel
    wheels = sorted(dist_dir.glob("endorlabs-*.whl"))
    if not wheels:
        msg = f"no endorlabs wheel found under {dist_dir}"
        raise FileNotFoundError(msg)
    return wheels[-1]


def load_manifest(manifest_path: Path = MANIFEST_PATH) -> dict[str, Any]:
    """Load committed agent knowledge MANIFEST.json."""
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def manifest_shipped_relative_paths(manifest: dict[str, Any]) -> list[str]:
    """Return MANIFEST catalog paths that must exist inside the installed wheel."""
    paths: list[str] = []
    for key in ("skills", "rules", "contracts"):
        entries = manifest.get(key)
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if isinstance(entry, dict) and isinstance(entry.get("path"), str):
                paths.append(entry["path"])
    for name in ("INDEX.md", "AGENTS.md", "MANIFEST.json"):
        paths.append(name)
    return sorted(set(paths))


def wheel_contains_path(wheel_names: set[str], rel: str) -> bool:
    """Return True when rel path exists in the wheel agent_knowledge tree."""
    rel_posix = rel.replace("\\", "/").lstrip("/")
    target = f"endorlabs/agent_knowledge/{rel_posix}"
    return target in wheel_names


def verify_wheel_archive_paths(wheel_path: Path, manifest: dict[str, Any]) -> list[str]:
    """Check wheel zip lists every MANIFEST catalog path (pre-install fast path)."""
    errors: list[str] = []
    with zipfile.ZipFile(wheel_path) as archive:
        names = set(archive.namelist())
    if not any(name.startswith("endorlabs/workflows/estate/analyze/") for name in names):
        errors.append(
            "wheel missing endorlabs/workflows/estate/analyze/ "
            "(estate package import will fail)"
        )
    for rel in manifest_shipped_relative_paths(manifest):
        if not wheel_contains_path(names, rel):
            errors.append(f"wheel missing agent_knowledge/{rel}")
    for subdir in AGENT_KNOWLEDGE_FORCE_INCLUDE:
        prefix = f"endorlabs/agent_knowledge/{subdir}/"
        if not any(name.startswith(prefix) for name in names):
            errors.append(f"wheel missing agent_knowledge/{subdir}/ subtree")
    return errors


def python_dirs_requiring_init(package_root: Path) -> list[Path]:
    """Return subdirs that contain .py modules and need __init__.py."""
    required: set[Path] = {package_root}
    for path in package_root.rglob("*.py"):
        if path.name == "__init__.py":
            continue
        required.add(path.parent)
    return sorted(required)


def verify_package_init_files(package_root: Path, label: str) -> list[str]:
    """Ensure every module directory under package_root ships as a Python package."""
    errors: list[str] = []
    for directory in python_dirs_requiring_init(package_root):
        init_path = directory / "__init__.py"
        if not init_path.is_file():
            try:
                rel = init_path.relative_to(ROOT).as_posix()
            except ValueError:
                rel = init_path.as_posix()
            errors.append(f"missing {label} package marker: {rel}")
    return errors


def verify_analyze_init_files(analyze_root: Path = ANALYZE_ROOT) -> list[str]:
    """Ensure every analyze module directory ships as a Python package."""
    return verify_package_init_files(analyze_root, "analyze")


def verify_estate_init_files(estate_root: Path = ESTATE_ROOT) -> list[str]:
    """Ensure every estate workflow module directory ships as a Python package."""
    return verify_package_init_files(estate_root, "estate")


def verify_manifest_paths_on_disk(
    manifest: dict[str, Any],
    bundle_root: Path = BUNDLE_ROOT,
) -> list[str]:
    """Ensure MANIFEST catalog paths exist in the committed source bundle."""
    errors: list[str] = []
    for rel in manifest_shipped_relative_paths(manifest):
        path = bundle_root / rel
        if not path.is_file():
            errors.append(f"source bundle missing file: {rel}")
    for subdir in AGENT_KNOWLEDGE_FORCE_INCLUDE:
        if not (bundle_root / subdir).is_dir():
            errors.append(f"source bundle missing directory: {subdir}/")
    return errors


def installed_wheel_smoke_script() -> str:
    """Return Python source run inside an isolated venv with the wheel installed."""
    return textwrap.dedent(
        """
        import importlib
        import importlib.metadata
        import sys

        import endorlabs
        from endorlabs import Client  # noqa: F401
        from endorlabs.agent_knowledge import (
            agent_knowledge_bootstrap_paths,
            agent_knowledge_dir,
            agent_knowledge_manifest,
        )

        expect = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else None
        version = endorlabs.__version__
        if not version:
            raise SystemExit("empty endorlabs.__version__")
        if expect and version != expect:
            raise SystemExit(
                f"version mismatch: installed {version!r} != expected {expect!r}"
            )

        from importlib.resources import files

        pkg = files("endorlabs")
        if not (pkg / "py.typed").is_file():
            raise SystemExit("missing py.typed in wheel")
        if not (pkg / "client_surface.pyi").is_file():
            raise SystemExit("missing client_surface.pyi in wheel")

        import endorlabs.workflows.estate  # noqa: F401

        manifest = agent_knowledge_manifest()
        bundle = agent_knowledge_dir()
        for key in ("skills", "rules", "contracts"):
            for entry in manifest.get(key, []):
                rel = entry.get("path")
                if not isinstance(rel, str):
                    continue
                path = bundle / rel
                if not path.is_file():
                    raise SystemExit(f"missing manifest path in wheel: {rel}")

        for path in agent_knowledge_bootstrap_paths():
            if not path.is_file():
                raise SystemExit(
                    f"missing bootstrap path in wheel: {path.relative_to(bundle)}"
                )

        sdk_version = manifest.get("sdk_version")
        if isinstance(sdk_version, str) and sdk_version != version:
            raise SystemExit(
                f"MANIFEST sdk_version {sdk_version!r} != installed {version!r}"
            )

        entry_points = importlib.metadata.entry_points(group="console_scripts")
        for ep in sorted(entry_points, key=lambda row: row.name):
            if not ep.name.startswith("endor-"):
                continue
            importlib.import_module(ep.module)

        print(version)
        """
    ).strip()


def verify_installed_wheel(
    wheel_path: Path,
    *,
    expect_version: str | None = None,
    python_executable: str | None = None,
) -> tuple[str, list[str]]:
    """Install wheel in temp venv and run import/bootstrap smoke checks."""
    archive_errors = verify_wheel_archive_paths(wheel_path, load_manifest())
    if archive_errors:
        return "", archive_errors

    interpreter = python_executable or sys.executable
    with tempfile.TemporaryDirectory(prefix="endorlabs-wheel-verify-") as tmp:
        venv_dir = Path(tmp) / "venv"
        _run([interpreter, "-m", "venv", str(venv_dir)])
        if sys.platform == "win32":
            python = venv_dir / "Scripts" / "python.exe"
        else:
            python = venv_dir / "bin" / "python"

        _run([str(python), "-m", "pip", "install", str(wheel_path.resolve())])
        script = installed_wheel_smoke_script()
        cmd = [str(python), "-c", script]
        if expect_version is not None:
            cmd.append(expect_version)
        try:
            proc = _run(cmd)
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or str(exc)).strip()
            return "", [detail or "installed wheel smoke checks failed"]
        version = proc.stdout.strip()
        if not version:
            return "", ["installed wheel smoke checks returned empty version"]
        return version, []


def verify_source_packaging_invariants() -> list[str]:
    """Fast checks against committed source (no wheel build)."""
    errors: list[str] = []
    manifest = load_manifest()
    errors.extend(verify_manifest_paths_on_disk(manifest))
    errors.extend(verify_estate_init_files())
    codegen_dir = str(ROOT / "devtools" / "codegen")
    if codegen_dir not in sys.path:
        sys.path.insert(0, codegen_dir)
    from agent_knowledge_catalog import (  # noqa: PLC0415
        lint_shipped_agent_knowledge_links,
        verify_manifest_sdk_version,
    )

    sdk_err = verify_manifest_sdk_version(MANIFEST_PATH, pyproject_path=ROOT / "pyproject.toml")
    if sdk_err is not None:
        errors.append(sdk_err)
    errors.extend(lint_shipped_agent_knowledge_links(BUNDLE_ROOT))
    return errors


def run_verify(
    *,
    wheel: Path | None = None,
    dist_dir: Path | None = None,
    expect_version: str | None = None,
    skip_install: bool = False,
) -> int:
    """Run source invariants and optional installed-wheel smoke verification."""
    errors = verify_source_packaging_invariants()
    if errors:
        for msg in errors:
            print(f"ERROR: {msg}", file=sys.stderr)
        return 1

    if skip_install:
        print("source packaging invariants ok (install smoke skipped)")
        return 0

    wheel_path = find_wheel(dist_dir or (ROOT / "dist"), wheel)
    print(f"verifying wheel: {wheel_path.name}")
    version, install_errors = verify_installed_wheel(
        wheel_path,
        expect_version=expect_version,
    )
    if install_errors:
        for msg in install_errors:
            print(f"ERROR: {msg}", file=sys.stderr)
        return 1
    print(f"wheel contents ok; endorlabs.__version__={version}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--wheel",
        type=Path,
        default=None,
        help="Path to a built wheel (default: newest dist/endorlabs-*.whl)",
    )
    parser.add_argument(
        "--dist-dir",
        type=Path,
        default=ROOT / "dist",
        help="Directory containing built wheels",
    )
    parser.add_argument(
        "--expect-version",
        default=None,
        help="Fail unless installed endorlabs.__version__ equals this string",
    )
    parser.add_argument(
        "--source-only",
        action="store_true",
        help="Run fast source-tree invariants only (no wheel build/install)",
    )
    args = parser.parse_args(argv)
    return run_verify(
        wheel=args.wheel,
        dist_dir=args.dist_dir,
        expect_version=args.expect_version,
        skip_install=args.source_only,
    )


if __name__ == "__main__":
    raise SystemExit(main())

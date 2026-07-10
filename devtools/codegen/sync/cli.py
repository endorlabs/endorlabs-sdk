"""CLI entrypoint for hard-cutover model-sync automation."""
# ruff: noqa: E501, D103

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import logging
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from .codegen import generate_modules_in_memory, load_profiles
from .contract import (
    build_facade_contract,
    build_operation_path_metadata,
    build_payload_schemas,
    build_registry_parity_report,
    load_resource_scope_overrides,
    render_create_convenience_module,
    render_generated_registry_contract_module,
    validate_contract_artifacts,
)
from .path_safety import find_repo_root, safe_repo_output_path
from .planner import build_plan
from .policy import load_openapi_spec
from .provenance import build_provenance
from .upstream_verify import meta_version_url_from_openapi_url

DEFAULT_SPEC_URL = "https://api.endorlabs.com/download/openapiv2.swagger.json"
LEGACY_OUTPUT_ROOT_REL = Path("workspace") / "model-bakeoff"

logger = logging.getLogger(__name__)


def _repo_root() -> Path:
    return find_repo_root()


def default_spec_path(repo_root: Path | None = None) -> Path:
    root = repo_root or _repo_root()
    return root / ".endorlabs-context" / "platform" / "openapi" / "openapiv2.swagger.json"


def default_custom_profiles_dir(repo_root: Path | None = None) -> Path:
    root = repo_root or _repo_root()
    return root / "devtools" / "codegen" / "model_sync_profiles"


def generated_contract_module_path(repo_root: Path | None = None) -> Path:
    root = repo_root or _repo_root()
    return safe_repo_output_path(
        root, "src", "endorlabs", "generated", "registry_contract.py"
    )


def _datamodel_codegen_available() -> bool:
    return importlib.util.find_spec("datamodel_code_generator") is not None


def _toolchain_inventory() -> dict[str, dict[str, bool]]:
    return {"datamodel-codegen": {"available": _datamodel_codegen_available()}}


def _ensure_devtools_on_path(repo_root: Path) -> None:
    devtools = repo_root / "devtools"
    if str(devtools) not in sys.path:
        sys.path.insert(0, str(devtools))


def _run_upstream_verify_only(args: argparse.Namespace) -> int:
    from .upstream_verify import verify_upstream_matches_committed

    drift = verify_upstream_matches_committed(
        registry_contract_path=generated_contract_module_path(),
        spec_url=args.spec_url,
    )
    if drift:
        for line in drift:
            logger.error("%s", line)
        return 1
    logger.info("Upstream OpenAPI spec matches committed model-sync provenance.")
    return 0


def _run_verify_and_sync_if_stale(args: argparse.Namespace, spec_path: Path) -> int:
    from .upstream_verify import verify_upstream_matches_committed

    drift = verify_upstream_matches_committed(
        registry_contract_path=generated_contract_module_path(),
        spec_url=args.spec_url,
    )
    if not drift:
        logger.info(
            "Committed model-sync provenance matches upstream; skipping regeneration.",
        )
        return 0
    for line in drift:
        logger.warning("%s", line)
    logger.info("Upstream drift detected; running full model sync.")
    if not _fetch_openapi_spec(args.spec_url, spec_path):
        return 1
    code = run_sync(
        profiles_dir=args.custom_profiles_dir,
        generate_stubs=True,
        generate_reference_docs=True,
        spec_url=args.spec_url,
    )
    if code != 0:
        return code
    return 0


def _fetch_openapi_spec(url: str, dest: Path) -> bool:
    """Download OpenAPI JSON to ``dest``. Return True on success."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(url, timeout=120) as resp:  # noqa: S310
            data = resp.read()
        dest.write_bytes(data)
    except (OSError, urllib.error.URLError) as exc:
        logger.error("Failed to download spec from %s: %s", url, exc)
        return False
    logger.info("Wrote spec to %s", dest)
    return True


def _sha256_hex(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run_command(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        command,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )


def _run_optional_generators(
    repo_root: Path,
    *,
    generate_stubs: bool,
    generate_reference_docs: bool,
) -> bool:
    _ensure_devtools_on_path(repo_root)
    ok = True
    if generate_stubs:
        from generate_client_stub import main as generate_client_stub_main

        try:
            generate_client_stub_main()
        except Exception as exc:
            ok = False
            logger.error("generate_client_stub failed: %s", exc)
        else:
            logger.info("generate_client_stub completed.")
    if generate_reference_docs:
        from generate_reference_docs import main as generate_reference_docs_main

        try:
            if generate_reference_docs_main([]) != 0:
                ok = False
                logger.error("generate_reference_docs failed.")
            else:
                logger.info("generate_reference_docs completed.")
        except Exception as exc:
            ok = False
            logger.error("generate_reference_docs failed: %s", exc)
    return ok


def _ensure_package_init(path: Path, doc: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    contents = (doc or "") + "\n" if doc else ""
    path.write_text(contents, encoding="utf-8")


def _write_generated_models(
    repo_root: Path, generated_modules: dict[str, str]
) -> None:
    models_root = safe_repo_output_path(
        repo_root, "src", "endorlabs", "generated", "models"
    )
    if models_root.exists():
        shutil.rmtree(models_root)
    models_root.mkdir(parents=True, exist_ok=True)
    package_init = safe_repo_output_path(
        repo_root, "src", "endorlabs", "generated", "__init__.py"
    )
    _ensure_package_init(
        package_init,
        '"""Generated artifacts consumed by runtime registry adapter."""',
    )
    _ensure_package_init(
        models_root / "__init__.py",
        '"""Generated model modules from model-sync."""',
    )
    for rel_path, source in sorted(generated_modules.items()):
        dest = safe_repo_output_path(
            repo_root, "src", "endorlabs", "generated", "models", rel_path
        )
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(source, encoding="utf-8")
    for package_dir in sorted(path for path in models_root.rglob("*") if path.is_dir()):
        _ensure_package_init(package_dir / "__init__.py")


def run_sync(
    *,
    profiles_dir: Path,
    generate_stubs: bool,
    generate_reference_docs: bool,
    spec_url: str = DEFAULT_SPEC_URL,
    repo_root: Path | None = None,
) -> int:
    """Run canonical model-sync generation and write committed ship artifacts only."""
    root = repo_root or _repo_root()
    spec_path = default_spec_path(root)
    if not spec_path.exists():
        logger.error("Spec file not found: %s", spec_path)
        return 1

    legacy_output = root / LEGACY_OUTPUT_ROOT_REL
    if legacy_output.exists():
        shutil.rmtree(legacy_output)
        logger.info("Removed legacy multi-approach output at %s", legacy_output)

    toolchain = _toolchain_inventory()
    if not toolchain["datamodel-codegen"]["available"]:
        logger.error(
            "datamodel-code-generator package is required "
            "(install dev dependencies with uv sync)."
        )
        return 1

    spec = load_openapi_spec(spec_path)
    load_profiles(profiles_dir)
    try:
        spec_for_provenance = spec_path.resolve().relative_to(root.resolve())
    except ValueError:
        spec_for_provenance = spec_path
    provenance = build_provenance(
        spec_for_provenance,
        toolchain,
        meta_version_url=meta_version_url_from_openapi_url(spec_url),
    )

    plan = build_plan(spec)
    operation_path_metadata = build_operation_path_metadata(spec)
    payload_schemas = build_payload_schemas(
        spec=spec,
        operation_metadata=operation_path_metadata,
    )
    facade_contract = build_facade_contract(
        mapping_entries=plan.entries,
        payload_schemas=payload_schemas,
        operation_metadata=operation_path_metadata,
        scope_overrides=load_resource_scope_overrides(profiles_dir),
    )
    registry_parity_report = build_registry_parity_report(
        mapping_entries=plan.entries,
        facade_contract=facade_contract,
    )
    contract_errors = validate_contract_artifacts(
        facade_contract=facade_contract,
        registry_parity_report=registry_parity_report,
        operation_path_metadata=operation_path_metadata,
        payload_schemas=payload_schemas,
    )
    if contract_errors:
        for error in contract_errors:
            logger.error("model-sync contract validation failed: %s", error)
        logger.error(
            "Contract validation triage: inspect src/endorlabs/generated/"
            "registry_contract.py and validate_contract_artifacts output; "
            "see docs/contributing/docs-drift-workflow.md"
        )
        return 1

    try:
        generated_modules = generate_modules_in_memory(plan.schema_shards)
    except Exception as exc:
        logger.error("model-sync codegen failed: %s", exc)
        return 1
    logger.info(
        "model-sync: generated %s model module(s) in memory",
        len(generated_modules),
    )

    generated_contract_content = render_generated_registry_contract_module(
        facade_contract=facade_contract,
        provenance=provenance,
    )
    contract_path = generated_contract_module_path(root)
    create_convenience_path = safe_repo_output_path(
        root, "src", "endorlabs", "generated", "create_convenience.py"
    )
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    package_init = safe_repo_output_path(
        root, "src", "endorlabs", "generated", "__init__.py"
    )
    _ensure_package_init(
        package_init,
        '"""Generated artifacts consumed by runtime registry adapter."""',
    )
    contract_path.write_text(generated_contract_content, encoding="utf-8")
    create_convenience_path.write_text(
        render_create_convenience_module(facade_contract=facade_contract),
        encoding="utf-8",
    )
    format_result = _run_command(
        [
            sys.executable,
            "-m",
            "ruff",
            "format",
            str(contract_path),
            str(create_convenience_path),
        ],
        root,
    )
    if format_result.returncode != 0:
        logger.error(
            "failed to format generated runtime contract module: %s",
            (format_result.stderr or format_result.stdout).strip(),
        )
        return 1

    _write_generated_models(root, generated_modules)

    optional_ok = _run_optional_generators(
        root,
        generate_stubs=generate_stubs,
        generate_reference_docs=generate_reference_docs,
    )
    if not optional_ok:
        return 1
    logger.info("Model sync completed (ship surface under src/endorlabs/generated/)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--spec-url",
        default=DEFAULT_SPEC_URL,
        help="URL for --fetch-spec (default: public Endor Labs OpenAPI download)",
    )
    parser.add_argument(
        "--fetch-spec",
        action="store_true",
        help="Download OpenAPI JSON to the canonical context path before running sync",
    )
    parser.add_argument(
        "--spec-hash-only",
        action="store_true",
        help=(
            "Print SHA-256 of the canonical OpenAPI spec path and exit "
            "(runs --fetch-spec first if set)"
        ),
    )
    parser.add_argument(
        "--custom-profiles-dir",
        type=Path,
        default=None,
        help="Directory containing model_sync_profiles JSON (default: devtools/codegen/model_sync_profiles)",
    )
    parser.add_argument("--generate-stubs", action="store_true")
    parser.add_argument("--generate-reference-docs", action="store_true")
    parser.add_argument("--inventory-only", action="store_true")
    parser.add_argument(
        "--verify-upstream-only",
        action="store_true",
        help=(
            "Download OpenAPI + query meta/version; fail if committed registry_contract "
            "provenance is stale vs upstream (no code generation)"
        ),
    )
    parser.add_argument(
        "--verify-and-sync-if-stale",
        action="store_true",
        help=(
            "If upstream differs from committed provenance, fetch OpenAPI and run full "
            "model sync (implies --fetch-spec, --generate-stubs, --generate-reference-docs)"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.verify_upstream_only and args.verify_and_sync_if_stale:
        parser.error(
            "--verify-upstream-only and --verify-and-sync-if-stale are mutually exclusive"
        )

    repo_root = _repo_root()
    if args.custom_profiles_dir is None:
        args.custom_profiles_dir = default_custom_profiles_dir(repo_root)
    spec_path = default_spec_path(repo_root)

    if args.inventory_only:
        logger.info("Toolchain inventory: %s", _toolchain_inventory())
        return 0

    if args.verify_upstream_only:
        return _run_upstream_verify_only(args)

    if args.verify_and_sync_if_stale:
        return _run_verify_and_sync_if_stale(args, spec_path)

    if args.fetch_spec and not _fetch_openapi_spec(args.spec_url, spec_path):
        return 1

    if args.spec_hash_only:
        if not spec_path.is_file():
            logger.error("Spec file not found: %s", spec_path)
            return 1
        print(_sha256_hex(spec_path))  # noqa: T201
        return 0

    code = run_sync(
        profiles_dir=args.custom_profiles_dir,
        generate_stubs=args.generate_stubs,
        generate_reference_docs=args.generate_reference_docs,
        spec_url=args.spec_url,
        repo_root=repo_root,
    )
    if code != 0:
        return code

    return 0

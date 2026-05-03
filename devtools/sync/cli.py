"""CLI entrypoint for hard-cutover model-sync automation."""
# ruff: noqa: E501, D103

from __future__ import annotations

import argparse
import hashlib
import logging
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from .codegen import generate_modules, load_profiles
from .contract import (
    build_facade_contract,
    build_operation_path_metadata,
    build_payload_schemas,
    build_registry_parity_report,
    build_runtime_index_metadata,
    render_generated_registry_contract_module,
    validate_contract_artifacts,
)
from .planner import build_plan, write_mapping_metadata
from .policy import load_openapi_spec
from .provenance import build_artifacts_manifest, build_provenance, write_json

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SPEC_PATH = REPO_ROOT / ".endorlabs-context" / "openapiv2.swagger.json"
DEFAULT_SPEC_URL = "https://api.endorlabs.com/download/openapiv2.swagger.json"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "workspace" / "model-sync"
DEFAULT_CUSTOM_PROFILES_DIR = REPO_ROOT / "devtools" / "model_sync_profiles"
LEGACY_OUTPUT_ROOT = REPO_ROOT / "workspace" / "model-bakeoff"
GENERATED_CONTRACT_MODULE_PATH = (
    REPO_ROOT / "src" / "endorlabs" / "generated" / "registry_contract.py"
)
GENERATED_PACKAGE_INIT_PATH = REPO_ROOT / "src" / "endorlabs" / "generated" / "__init__.py"
GENERATED_RUNTIME_MODELS_ROOT = REPO_ROOT / "src" / "endorlabs" / "generated" / "models"
logger = logging.getLogger(__name__)


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
    resolved = list(command)
    executable = shutil.which(resolved[0])
    if executable is not None:
        resolved[0] = executable
    return subprocess.run(  # noqa: S603
        resolved,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )


def _run_optional_generators(
    generate_stubs: bool,
    generate_reference_docs: bool,
) -> bool:
    ok = True
    if generate_stubs:
        result = _run_command([sys.executable, "devtools/generate_client_stub.py"], REPO_ROOT)
        if result.returncode != 0:
            ok = False
            logger.error("generate_client_stub failed: %s", (result.stderr or result.stdout).strip())
        else:
            logger.info("generate_client_stub completed.")
    if generate_reference_docs:
        result = _run_command([sys.executable, "devtools/generate_reference_docs.py"], REPO_ROOT)
        if result.returncode != 0:
            ok = False
            logger.error(
                "generate_reference_docs failed: %s", (result.stderr or result.stdout).strip()
            )
        else:
            logger.info("generate_reference_docs completed.")
    return ok


def _ensure_package_init(path: Path, doc: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    contents = (doc or "") + "\n" if doc else ""
    path.write_text(contents, encoding="utf-8")


def _mirror_generated_models_to_runtime(model_output: Path) -> None:
    generated_source = model_output / "generated"
    if not generated_source.exists():
        return
    if GENERATED_RUNTIME_MODELS_ROOT.exists():
        shutil.rmtree(GENERATED_RUNTIME_MODELS_ROOT)
    GENERATED_RUNTIME_MODELS_ROOT.mkdir(parents=True, exist_ok=True)
    for file_path in sorted(generated_source.rglob("*.py")):
        rel = file_path.relative_to(generated_source)
        dest = GENERATED_RUNTIME_MODELS_ROOT / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, dest)
    _ensure_package_init(
        GENERATED_PACKAGE_INIT_PATH,
        '"""Generated artifacts consumed by runtime registry adapter."""',
    )
    _ensure_package_init(
        GENERATED_RUNTIME_MODELS_ROOT / "__init__.py",
        '"""Generated model modules mirrored from model-sync output."""',
    )
    for package_dir in sorted(path for path in GENERATED_RUNTIME_MODELS_ROOT.rglob("*") if path.is_dir()):
        _ensure_package_init(package_dir / "__init__.py")


def run_sync(
    *,
    spec_path: Path,
    output_root: Path,
    profiles_dir: Path,
    generate_stubs: bool,
    generate_reference_docs: bool,
) -> int:
    """Run canonical model-sync generation and metadata emission."""
    if not spec_path.exists():
        logger.error("Spec file not found: %s", spec_path)
        return 1
    if LEGACY_OUTPUT_ROOT.exists():
        shutil.rmtree(LEGACY_OUTPUT_ROOT)
        logger.info("Removed legacy multi-approach output at %s", LEGACY_OUTPUT_ROOT)

    toolchain = {
        "datamodel-codegen": {
            "available": shutil.which("datamodel-codegen") is not None,
        }
    }
    write_json(output_root / "toolchain_inventory.json", toolchain)
    if not toolchain["datamodel-codegen"]["available"]:
        logger.error("datamodel-codegen is required in PATH.")
        return 1

    spec = load_openapi_spec(spec_path)
    profiles = load_profiles(profiles_dir)
    try:
        spec_for_provenance = spec_path.resolve().relative_to(REPO_ROOT.resolve())
    except ValueError:
        spec_for_provenance = spec_path
    provenance = build_provenance(spec_for_provenance, toolchain)
    model_output = output_root / "custom_mapping"
    if model_output.exists():
        shutil.rmtree(model_output)
    (model_output / "mapping").mkdir(parents=True, exist_ok=True)
    write_json(model_output / "provenance.json", provenance)

    plan = build_plan(spec)
    write_mapping_metadata(plan.entries, model_output / "mapping" / "entity_mapping.json", profiles)
    operation_path_metadata = build_operation_path_metadata(spec)
    write_json(
        model_output / "mapping" / "operation_path_metadata.json",
        operation_path_metadata,
    )
    payload_schemas = build_payload_schemas(
        spec=spec,
        operation_metadata=operation_path_metadata,
    )
    write_json(model_output / "mapping" / "payload_schemas.json", payload_schemas)
    facade_contract = build_facade_contract(
        mapping_entries=plan.entries,
        payload_schemas=payload_schemas,
    )
    write_json(model_output / "facade_contract.json", facade_contract)
    runtime_index = build_runtime_index_metadata(facade_contract)
    write_json(model_output / "mapping" / "runtime_index.json", runtime_index)
    generated_contract_content = render_generated_registry_contract_module(
        facade_contract=facade_contract,
        provenance=provenance,
    )
    GENERATED_PACKAGE_INIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not GENERATED_PACKAGE_INIT_PATH.exists():
        GENERATED_PACKAGE_INIT_PATH.write_text(
            '"""Generated artifacts consumed by runtime registry adapter."""\n',
            encoding="utf-8",
        )
    GENERATED_CONTRACT_MODULE_PATH.write_text(generated_contract_content, encoding="utf-8")
    format_result = _run_command(
        [sys.executable, "-m", "ruff", "format", str(GENERATED_CONTRACT_MODULE_PATH)],
        REPO_ROOT,
    )
    if format_result.returncode != 0:
        logger.error(
            "failed to format generated runtime contract module: %s",
            (format_result.stderr or format_result.stdout).strip(),
        )
        return 1
    registry_parity_report = build_registry_parity_report(
        mapping_entries=plan.entries,
        facade_contract=facade_contract,
    )
    write_json(
        model_output / "mapping" / "registry_parity_report.json",
        registry_parity_report,
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
            "Contract validation triage: inspect "
            "workspace/model-sync/custom_mapping/mapping/registry_parity_report.json "
            "and workspace/model-sync/custom_mapping/facade_contract.json; see "
            "docs/rules-of-engagement/docs-drift-workflow.md"
        )
        return 1
    ok, message, commands = generate_modules(
        repo_root=REPO_ROOT,
        model_output=model_output,
        schema_shards=plan.schema_shards,
        provenance=provenance,
    )
    logger.info("model-sync: %s", message)
    if not ok:
        return 1
    _mirror_generated_models_to_runtime(model_output)

    write_json(output_root / "commands.json", {"commands": commands})
    manifest = build_artifacts_manifest(model_output, excluded_paths={"provenance.json"})
    write_json(model_output / "artifacts_manifest.json", manifest)

    optional_ok = _run_optional_generators(generate_stubs, generate_reference_docs)
    if not optional_ok:
        return 1
    logger.info("Model sync completed at %s", model_output)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec-path", type=Path, default=DEFAULT_SPEC_PATH)
    parser.add_argument(
        "--spec-url",
        default=DEFAULT_SPEC_URL,
        help="URL for --fetch-spec (default: public Endor Labs OpenAPI download)",
    )
    parser.add_argument(
        "--fetch-spec",
        action="store_true",
        help="Download OpenAPI JSON to --spec-path before running sync",
    )
    parser.add_argument(
        "--spec-hash-only",
        action="store_true",
        help="Print SHA-256 of --spec-path and exit (runs --fetch-spec first if set)",
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--custom-profiles-dir", type=Path, default=DEFAULT_CUSTOM_PROFILES_DIR)
    parser.add_argument("--generate-stubs", action="store_true")
    parser.add_argument("--generate-reference-docs", action="store_true")
    parser.add_argument("--inventory-only", action="store_true")
    parser.add_argument(
        "--delta-summary",
        action="store_true",
        help="After a successful sync, print a compact delta vs git baseline",
    )
    parser.add_argument(
        "--delta-git-ref",
        default="",
        help="Baseline ref for --delta-summary (default: auto origin/main..master)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.inventory_only:
        toolchain = {
            "datamodel-codegen": {
                "available": shutil.which("datamodel-codegen") is not None,
            }
        }
        write_json(args.output_root / "toolchain_inventory.json", toolchain)
        return 0

    spec_path = args.spec_path.expanduser().resolve()

    if args.fetch_spec:
        if not _fetch_openapi_spec(args.spec_url, spec_path):
            return 1

    if args.spec_hash_only:
        if not spec_path.is_file():
            logger.error("Spec file not found: %s", spec_path)
            return 1
        print(_sha256_hex(spec_path))
        return 0

    code = run_sync(
        spec_path=spec_path,
        output_root=args.output_root,
        profiles_dir=args.custom_profiles_dir,
        generate_stubs=args.generate_stubs,
        generate_reference_docs=args.generate_reference_docs,
    )
    if code != 0:
        return code

    if args.delta_summary:
        from .baseline_ref import resolve_auto_baseline_ref
        from .delta_summary import render_compact_delta_summary_lines

        ref = (args.delta_git_ref or "").strip() or resolve_auto_baseline_ref(REPO_ROOT)
        summary_text = "\n".join(
            render_compact_delta_summary_lines(git_ref=ref, repo_root=REPO_ROOT)
        )
        print(summary_text)

    return 0

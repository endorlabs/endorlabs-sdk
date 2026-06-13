#!/usr/bin/env python3
"""Verify consumer resource modules have wire list-row fixtures."""

from __future__ import annotations

import argparse
import importlib
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RESOURCES_DIR = REPO_ROOT / "src" / "endorlabs" / "resources"
FIXTURES_ROOT = REPO_ROOT / "tests" / "fixtures" / "models"
FIXTURE_NAME = "list_row_min.json"

REGISTRY_DIRECT_ATTRS = {
    "IdentityProvider": "identity_provider",
    "PackageFirewallLog": "package_firewall_log",
    "Query": "query",
    "QuerySimilarPackages": "query_similar_packages",
    "SavedQuery": "saved_query",
}


def _kind_from_module(module: str) -> str:
    parts = module.split("_")
    return "".join(p[:1].upper() + p[1:] for p in parts)


def _module_for_attr(attr_name: str) -> str | None:
    if attr_name in REGISTRY_DIRECT_ATTRS:
        module = REGISTRY_DIRECT_ATTRS[attr_name]
        return module if (RESOURCES_DIR / f"{module}.py").is_file() else None
    snake = re.sub(r"(?<!^)(?=[A-Z])", "_", attr_name).lower()
    path = RESOURCES_DIR / f"{snake}.py"
    return snake if path.is_file() else None


def _is_consumer_module(module: str) -> bool:
    path = RESOURCES_DIR / f"{module}.py"
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    return "ConsumerResourceMixin" in text and (
        "generated.models" in text or "Endorv1" in text
    )


def consumer_modules_from_registry() -> list[str]:
    from endorlabs.generated.registry_contract import RUNTIME_REGISTRY_CONTRACT

    modules: list[str] = []
    seen: set[str] = set()
    for item in RUNTIME_REGISTRY_CONTRACT.get("resources", []):
        attr_name = str(item.get("attr_name", ""))
        module = _module_for_attr(attr_name)
        if module is None or module in seen:
            continue
        seen.add(module)
        if _is_consumer_module(module):
            modules.append(module)
    if "dependency_metadata" not in seen and _is_consumer_module("dependency_metadata"):
        modules.append("dependency_metadata")
    return sorted(modules)


def fixture_path(module: str) -> Path:
    return FIXTURES_ROOT / module / FIXTURE_NAME


def _stub_payload(module: str) -> dict:
    payload: dict = {
        "uuid": "000000000000000000000001",
        "meta": {"name": f"wire-{module}"},
        "tenant_meta": {"namespace": "tenant.example"},
    }
    if module in {"finding", "finding_log", "scan_result", "package_version", "dependency_metadata"}:
        payload["context"] = {"id": "ctx-1", "type": "CONTEXT_TYPE_MAIN"}
    return payload


def write_missing_fixtures(modules: list[str] | None = None) -> int:
    """Create list_row_min.json for consumer modules that lack a fixture."""
    targets = modules if modules is not None else consumer_modules_from_registry()
    created = 0
    for module in targets:
        path = fixture_path(module)
        if path.is_file():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(_stub_payload(module), indent=2) + "\n", encoding="utf-8")
        created += 1
    return created


def verify(*, strict_deserialize: bool = False) -> list[str]:
    """Return human-readable errors; empty list means OK."""
    errors: list[str] = []
    for module in consumer_modules_from_registry():
        path = fixture_path(module)
        if not path.is_file():
            errors.append(f"missing wire fixture: {path.relative_to(REPO_ROOT)}")
            continue
        if not strict_deserialize:
            continue
        kind = _kind_from_module(module)
        mod = importlib.import_module(f"endorlabs.resources.{module}")
        model_cls = getattr(mod, kind, None)
        if model_cls is None:
            errors.append(f"no model class {kind} in endorlabs.resources.{module}")
            continue
        from endorlabs.resources.consumer.wire_compat import deserialize_list_row

        payload = json.loads(path.read_text(encoding="utf-8"))
        try:
            deserialize_list_row(model_cls, payload)
        except Exception as exc:
            errors.append(f"fixture {path.relative_to(REPO_ROOT)} failed deserialize: {exc}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write-fixtures",
        action="store_true",
        help=f"Create missing {FIXTURE_NAME} under tests/fixtures/models/{{module}}/",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 when a consumer module lacks a wire fixture",
    )
    parser.add_argument(
        "--strict-deserialize",
        action="store_true",
        help="With --check, also construct each fixture through deserialize_list_row",
    )
    args = parser.parse_args(argv)

    if args.write_fixtures:
        n = write_missing_fixtures()
        print(f"Created {n} fixture(s) under tests/fixtures/models/")

    if args.check:
        errors = verify(strict_deserialize=args.strict_deserialize)
        if errors:
            for err in errors:
                print(err, file=sys.stderr)
            return 1
        print("consumer wire fixtures OK")

    if not args.write_fixtures and not args.check:
        for module in consumer_modules_from_registry():
            rel = fixture_path(module).relative_to(REPO_ROOT)
            status = "ok" if fixture_path(module).is_file() else "MISSING"
            print(f"{module}: {rel} [{status}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

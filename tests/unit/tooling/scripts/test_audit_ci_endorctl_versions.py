"""Unit tests for CI endorctl version audit helpers."""

from __future__ import annotations

import importlib
from datetime import UTC, datetime, timedelta
from types import ModuleType


def _load_module() -> ModuleType:
    return importlib.import_module(
        "endorlabs.workflows.reports.analyze.ci_endorctl_audit"
    )


def test_normalize_endorctl_version_strips_prefix() -> None:
    module = _load_module()

    assert module.normalize_endorctl_version("endorctl version v1.7.980") == "1.7.980"
    assert module.normalize_endorctl_version("v1.7.1037") == "1.7.1037"
    assert module.normalize_endorctl_version("1.7.980") == "1.7.980"
    assert module.normalize_endorctl_version(None) == "unknown"


def test_classify_latest_scan_requires_cli_and_recent() -> None:
    module = _load_module()
    cutoff = datetime.now(tz=UTC) - timedelta(days=7)
    recent = (datetime.now(tz=UTC) - timedelta(days=1)).isoformat()

    cli_scan = {
        "meta": {"create_time": recent},
        "spec": {
            "environment": {
                "config": {"RunBySystem": False},
                "endorctl_version": "endorctl version v1.7.980",
            }
        },
    }
    cloud_scan = {
        "meta": {"create_time": recent},
        "spec": {
            "environment": {
                "config": {"RunBySystem": True},
                "endorctl_version": "endorctl version v1.7.1037",
            }
        },
    }

    audit = module.classify_latest_scan(cli_scan, cutoff=cutoff)
    assert audit is not None
    assert audit["execution"] == "CLI"
    assert audit["endorctl_version"] == "1.7.980"

    assert module.classify_latest_scan(cloud_scan, cutoff=cutoff) is None
    assert module.classify_latest_scan(None, cutoff=cutoff) is None


def test_version_matches_accepts_normalized_forms() -> None:
    module = _load_module()

    assert module.version_matches("1.7.980", "1.7.980")
    assert module.version_matches("1.7.980-rc1", "1.7.980")
    assert not module.version_matches("1.7.1037", "1.7.980")

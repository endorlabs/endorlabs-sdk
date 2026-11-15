"""Unit tests for acquire_reachability_context (no filesystem / no live API)."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock

from endorlabs.resources.call_graph_data import CallGraphDecoded
from endorlabs.workflows.reachability.context import (
    ReachabilityContextRequest,
    acquire_reachability_context,
    write_reachability_context,
)
from endorlabs.workflows.reachability.resolve import ReachabilitySubject


def _subject(**overrides: Any) -> ReachabilitySubject:
    base: dict[str, Any] = {
        "tenant": "example-tenant",
        "namespace": "example-tenant.child",
        "finding_uuid": "f-1",
        "project_uuid": "proj-1",
        "importer_pv_uuid": "imp-pv",
        "importer_pv_name": "app@1",
        "target_dependency_uuid": "dep-1",
        "target_dependency_package_name": "org.pkg:dep",
        "oss_namespace": "oss",
        "oss_package_version_uuid": "oss-pv",
        "oss_package_name": "org.pkg:dep@1.0",
        "extra_key": "GHSA-test",
    }
    base.update(overrides)
    return ReachabilitySubject(**base)


def test_acquire_partial_when_callgraphs_missing(
    monkeypatch: Any,
) -> None:
    client = MagicMock()
    subject = _subject()
    finding = {
        "uuid": "f-1",
        "spec": {
            "extra_key": "GHSA-test",
            "finding_tags": [],
            "reachable_paths": [],
            "finding_metadata": {"vulnerability": {}},
        },
    }

    monkeypatch.setattr(
        "endorlabs.workflows.reachability.context.resolve_from_finding",
        lambda *_a, **_k: (subject, finding, None),
    )
    monkeypatch.setattr(
        "endorlabs.workflows.reachability.context._fetch_decoded_callgraph",
        lambda *_a, **_k: None,
    )

    req = ReachabilityContextRequest(
        tenant="example-tenant",
        namespace="example-tenant.child",
        finding_uuid="f-1",
    )
    result = acquire_reachability_context(client, req)

    assert result.status == "partial"
    assert not result.ok
    assert len(result.warnings) >= 1
    assert result.payload["customer_callgraph"] is None
    assert result.payload["oss_callgraph"] is None
    assert result.payload["stitching"] is None
    client.close.assert_not_called()


def test_acquire_success_with_decoded_graphs(monkeypatch: Any) -> None:
    client = MagicMock()
    subject = _subject()
    finding = {
        "uuid": "f-1",
        "spec": {
            "extra_key": "GHSA-test",
            "finding_tags": [],
            "reachable_paths": [],
            "finding_metadata": {"vulnerability": {}},
        },
    }
    decoded = CallGraphDecoded(
        summary={"uuid": "cg-1"},
        callables=[{"method_id": 1, "uri": "u"}],
        edges=[],
        envelope={},
    )

    monkeypatch.setattr(
        "endorlabs.workflows.reachability.context.resolve_from_finding",
        lambda *_a, **_k: (subject, finding, None),
    )
    monkeypatch.setattr(
        "endorlabs.workflows.reachability.context._fetch_decoded_callgraph",
        Mock(return_value=decoded),
    )

    req = ReachabilityContextRequest(
        tenant="example-tenant",
        namespace="example-tenant.child",
        finding_uuid="f-1",
    )
    result = acquire_reachability_context(client, req)

    assert result.status == "success"
    assert result.ok
    assert result.warnings == []
    assert result.payload["customer_callgraph"] is not None
    assert result.payload["oss_callgraph"] is not None


def test_write_reachability_context_no_network(tmp_path: Path) -> None:
    from endorlabs.workflows.reachability.context import ReachabilityContextResult

    result = ReachabilityContextResult(
        status="success",
        message="ok",
        payload={"subject": {"namespace": "example-tenant"}, "warnings": []},
    )
    out = write_reachability_context(result, tmp_path)
    assert out.name == "reachability_context.json"
    assert out.is_file()

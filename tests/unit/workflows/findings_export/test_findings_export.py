"""Unit tests for MAIN-context findings export helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from endorlabs.workflows.findings_export.checkpoint import (
    CHECKPOINT_SCHEMA,
    load_checkpoint,
    mark_complete,
    pending_shard_keys,
    save_checkpoint,
)
from endorlabs.workflows.findings_export.cli import main as findings_export_main
from endorlabs.workflows.findings_export.collect import (
    collect_findings_export,
    compose_finding_filter,
)


def test_compose_finding_filter_mandatory_main_and_project() -> None:
    filt = compose_finding_filter("proj-1")
    assert 'context.type=="CONTEXT_TYPE_MAIN"' in filt
    assert 'spec.project_uuid=="proj-1"' in filt


def test_compose_finding_filter_ands_extra() -> None:
    base = compose_finding_filter("proj-1")
    combined = compose_finding_filter("proj-1", "spec.level==FINDING_LEVEL_CRITICAL")
    assert combined.startswith("(")
    assert ") and (" in combined
    assert "FINDING_LEVEL_CRITICAL" in combined
    assert "CONTEXT_TYPE_MAIN" in combined
    assert base in combined or "proj-1" in combined


def _mock_project(*, uuid: str, namespace: str, name: str = "repo") -> MagicMock:
    project = MagicMock()
    project.uuid = uuid
    project.tenant_meta = MagicMock()
    project.tenant_meta.namespace = namespace
    project.meta = MagicMock()
    project.meta.name = name
    project.meta.tags = []
    return project


def test_collect_findings_default_no_mask(tmp_path: Path) -> None:
    client = MagicMock()
    client.Project.list.return_value = [
        _mock_project(uuid="proj-1", namespace="example-tenant.child"),
    ]
    finding = MagicMock()
    finding.model_dump = MagicMock(
        return_value={
            "uuid": "f1",
            "spec": {"project_uuid": "proj-1", "level": "FINDING_LEVEL_HIGH"},
        }
    )
    client.Finding.list.return_value = [finding]

    result = collect_findings_export(
        client,
        namespace="example-tenant.child",
        output_dir=tmp_path,
        max_workers=2,
    )
    assert result.ok
    assert result.row_count == 1
    kwargs = client.Finding.list.call_args.kwargs
    assert "mask" not in kwargs
    assert "CONTEXT_TYPE_MAIN" in kwargs["filter"]
    assert "proj-1" in kwargs["filter"]
    assert kwargs["traverse"] is False
    row = json.loads(Path(result.findings_path).read_text(encoding="utf-8").strip())
    assert row["uuid"] == "f1"
    assert row["spec"]["level"] == "FINDING_LEVEL_HIGH"


def test_collect_findings_optional_mask(tmp_path: Path) -> None:
    client = MagicMock()
    client.Project.list.return_value = [
        _mock_project(uuid="proj-1", namespace="example-tenant.child"),
    ]
    client.Finding.list.return_value = [
        {"uuid": "f1", "spec": {"level": "FINDING_LEVEL_CRITICAL"}},
    ]
    collect_findings_export(
        client,
        namespace="example-tenant.child",
        output_dir=tmp_path,
        max_workers=2,
        extra_filter="spec.level==FINDING_LEVEL_CRITICAL",
        mask="uuid,spec.level",
    )
    kwargs = client.Finding.list.call_args.kwargs
    assert kwargs["mask"] == "uuid,spec.level"
    assert "FINDING_LEVEL_CRITICAL" in kwargs["filter"]
    assert "CONTEXT_TYPE_MAIN" in kwargs["filter"]


def test_collect_findings_root_hosted_uses_traverse(tmp_path: Path) -> None:
    client = MagicMock()
    client.Project.list.return_value = [
        _mock_project(uuid="proj-root", namespace="example-tenant"),
    ]
    client.Finding.list.return_value = []
    result = collect_findings_export(
        client,
        namespace="example-tenant",
        output_dir=tmp_path,
        max_workers=2,
    )
    assert result.status in {"success", "partial"}
    kwargs = client.Finding.list.call_args.kwargs
    assert kwargs["namespace"] == "example-tenant"
    assert kwargs["traverse"] is True
    assert client.Project.list.call_args.kwargs["traverse"] is True


def test_collect_findings_resume_skips_complete(tmp_path: Path) -> None:
    client = MagicMock()
    client.Project.list.return_value = [
        _mock_project(uuid="proj-1", namespace="example-tenant.child"),
        _mock_project(uuid="proj-2", namespace="example-tenant.child", name="other"),
    ]
    client.Finding.list.return_value = [
        {"uuid": "f-new", "spec": {"project_uuid": "proj-2"}},
    ]

    from endorlabs.workflows.findings_export.checkpoint import ShardState

    checkpoint = load_checkpoint(tmp_path, namespace="example-tenant.child")
    checkpoint.shards["proj-1"] = ShardState(status="complete", line_count=3)
    checkpoint.shards["proj-2"] = ShardState(status="pending", line_count=0)
    save_checkpoint(tmp_path, checkpoint)

    findings_path = tmp_path / "findings.jsonl"
    findings_path.write_text(
        json.dumps({"uuid": "f-old", "spec": {"project_uuid": "proj-1"}}) + "\n",
        encoding="utf-8",
    )

    result = collect_findings_export(
        client,
        namespace="example-tenant.child",
        output_dir=tmp_path,
        max_workers=2,
        resume=True,
    )
    assert result.ok
    # Only pending shard listed.
    called_filters = [
        call.kwargs["filter"] for call in client.Finding.list.call_args_list
    ]
    assert len(called_filters) == 1
    assert "proj-2" in called_filters[0]
    assert "proj-1" not in called_filters[0]
    text = findings_path.read_text(encoding="utf-8")
    assert "f-old" in text
    assert "f-new" in text


def test_pending_shard_keys_resume() -> None:
    from endorlabs.workflows.findings_export.checkpoint import (
        NamespaceCheckpoint,
        ShardState,
    )

    cp = NamespaceCheckpoint(namespace="example-tenant.child")
    cp.shards["a"] = ShardState(status="complete", line_count=1)
    cp.shards["b"] = ShardState(status="failed", line_count=0)
    cp.shards["c"] = ShardState(status="pending", line_count=0)
    assert pending_shard_keys(cp, resume=False) == {"a", "b", "c"}
    assert pending_shard_keys(cp, resume=True) == {"b", "c"}


def test_checkpoint_schema_roundtrip(tmp_path: Path) -> None:
    from endorlabs.workflows.findings_export.checkpoint import NamespaceCheckpoint

    cp = NamespaceCheckpoint(namespace="example-tenant.child")
    mark_complete(cp, "proj-1", line_count=5)
    save_checkpoint(tmp_path, cp)
    loaded = load_checkpoint(tmp_path, namespace="example-tenant.child")
    assert loaded.schema == CHECKPOINT_SCHEMA
    assert loaded.shards["proj-1"].status == "complete"
    assert loaded.shards["proj-1"].line_count == 5


def test_cli_requires_namespace(monkeypatch: Any) -> None:
    monkeypatch.delenv("ENDOR_NAMESPACE", raising=False)
    with pytest.raises(SystemExit) as exc:
        findings_export_main([])
    assert exc.value.code != 0


def test_cli_help_exits_zero() -> None:
    with pytest.raises(SystemExit) as exc:
        findings_export_main(["--help"])
    assert exc.value.code == 0

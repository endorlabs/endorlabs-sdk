"""Atomic collect manifest for estate workspace pull/resume/validation."""

from __future__ import annotations

import json
import os
import threading
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from endorlabs.utils.path_safety import safe_write_text
from endorlabs.workflows.estate.contracts.resources import (
    COLLECT_RESOURCE_IDS,
    RESOURCE_ARTIFACT_SCHEMAS,
    SHARDED_RESOURCES,
    WORKSPACE_COLLECT_SCHEMA,
    resource_data_relpath,
)
from endorlabs.workflows.estate.workspace.paths import (
    collect_manifest_path,
    resource_path,
)

ResourceStatus = Literal["pending", "partial", "complete", "failed"]
ShardStatus = Literal["pending", "complete", "failed"]

_manifest_locks: dict[str, threading.Lock] = {}
_manifest_locks_guard = threading.Lock()


def _manifest_lock(workspace_root: Path) -> threading.Lock:
    key = str(workspace_root.resolve())
    with _manifest_locks_guard:
        lock = _manifest_locks.get(key)
        if lock is None:
            lock = threading.Lock()
            _manifest_locks[key] = lock
        return lock


def _atomic_replace(tmp: Path, path: Path, *, retries: int = 8) -> None:
    last_err: OSError | None = None
    for attempt in range(retries):
        try:
            os.replace(tmp, path)
            return
        except PermissionError as exc:
            last_err = exc
            if attempt + 1 < retries:
                time.sleep(0.05 * (attempt + 1))
    if last_err is not None:
        raise last_err


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class ShardRecord:
    status: ShardStatus = "pending"
    line_count: int = 0
    expected_count: int | None = None
    error: str | None = None
    retrieved_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"status": self.status, "line_count": self.line_count}
        if self.expected_count is not None:
            out["expected_count"] = self.expected_count
        if self.error:
            out["error"] = self.error
        if self.retrieved_at:
            out["retrieved_at"] = self.retrieved_at
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ShardRecord:
        status = data.get("status")
        if status not in ("pending", "complete", "failed"):
            status = "pending"
        return cls(
            status=status,  # type: ignore[arg-type]
            line_count=int(data.get("line_count") or 0),
            expected_count=data.get("expected_count")
            if isinstance(data.get("expected_count"), int)
            else None,
            error=data.get("error") if isinstance(data.get("error"), str) else None,
            retrieved_at=data.get("retrieved_at")
            if isinstance(data.get("retrieved_at"), str)
            else None,
        )


@dataclass
class ResourceRecord:
    resource_id: str
    path: str
    status: ResourceStatus = "pending"
    line_count: int = 0
    keys: list[str] = field(default_factory=list)
    filter_summary: str | None = None
    shards: dict[str, ShardRecord] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "path": self.path,
            "status": self.status,
            "line_count": self.line_count,
            "artifact_schema": RESOURCE_ARTIFACT_SCHEMAS.get(self.resource_id, ""),
        }
        if self.keys:
            out["keys"] = list(self.keys)
        if self.filter_summary:
            out["filter_summary"] = self.filter_summary
        if self.shards:
            out["shards"] = {k: v.to_dict() for k, v in self.shards.items()}
        if self.error:
            out["error"] = self.error
        return out

    @classmethod
    def from_dict(cls, resource_id: str, data: dict[str, Any]) -> ResourceRecord:
        shards_raw = data.get("shards") or {}
        shards: dict[str, ShardRecord] = {}
        if isinstance(shards_raw, dict):
            for key, val in shards_raw.items():
                if isinstance(val, dict):
                    shards[str(key)] = ShardRecord.from_dict(val)
        status = data.get("status")
        if status not in ("pending", "partial", "complete", "failed"):
            status = "pending"
        keys_raw = data.get("keys") or []
        keys = [str(k) for k in keys_raw] if isinstance(keys_raw, list) else []
        return cls(
            resource_id=resource_id,
            path=str(data.get("path") or resource_data_relpath(resource_id)),
            status=status,  # type: ignore[arg-type]
            line_count=int(data.get("line_count") or 0),
            keys=keys,
            filter_summary=data.get("filter_summary")
            if isinstance(data.get("filter_summary"), str)
            else None,
            shards=shards,
            error=data.get("error") if isinstance(data.get("error"), str) else None,
        )


@dataclass
class CollectManifest:
    namespace: str
    created_at: str
    resources: dict[str, ResourceRecord] = field(default_factory=dict)

    @classmethod
    def new(cls, namespace: str) -> CollectManifest:
        resources = {
            rid: ResourceRecord(
                resource_id=rid,
                path=resource_data_relpath(rid),
            )
            for rid in sorted(COLLECT_RESOURCE_IDS)
        }
        return cls(namespace=namespace, created_at=_utc_now(), resources=resources)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": WORKSPACE_COLLECT_SCHEMA,
            "namespace": self.namespace,
            "created_at": self.created_at,
            "updated_at": _utc_now(),
            "resources": {
                rid: rec.to_dict() for rid, rec in sorted(self.resources.items())
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CollectManifest:
        resources_raw = data.get("resources") or {}
        resources: dict[str, ResourceRecord] = {}
        if isinstance(resources_raw, dict):
            for rid, val in resources_raw.items():
                if isinstance(val, dict):
                    resources[str(rid)] = ResourceRecord.from_dict(str(rid), val)
        for rid in COLLECT_RESOURCE_IDS:
            if rid not in resources:
                resources[rid] = ResourceRecord(
                    resource_id=rid,
                    path=resource_data_relpath(rid),
                )
        return cls(
            namespace=str(data.get("namespace") or ""),
            created_at=str(data.get("created_at") or _utc_now()),
            resources=resources,
        )


def load_collect_manifest(workspace_root: Path) -> CollectManifest | None:
    path = collect_manifest_path(workspace_root)
    if not path.is_file():
        return None
    return CollectManifest.from_dict(json.loads(path.read_text(encoding="utf-8")))


def save_collect_manifest(workspace_root: Path, manifest: CollectManifest) -> Path:
    with _manifest_lock(workspace_root):
        path = collect_manifest_path(workspace_root)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        payload = json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False) + "\n"
        safe_write_text(workspace_root, tmp, payload)
        _atomic_replace(tmp, path)
    return path


def create_or_load_manifest(workspace_root: Path, namespace: str) -> CollectManifest:
    existing = load_collect_manifest(workspace_root)
    if existing is not None:
        return existing
    manifest = CollectManifest.new(namespace)
    save_collect_manifest(workspace_root, manifest)
    return manifest


def reset_manifest_for_overwrite(
    workspace_root: Path, namespace: str
) -> CollectManifest:
    manifest = CollectManifest.new(namespace)
    save_collect_manifest(workspace_root, manifest)
    return manifest


def pending_shard_keys(
    manifest: CollectManifest,
    resource_id: str,
    *,
    resume: bool,
) -> list[str]:
    rec = manifest.resources[resource_id]
    if not resume:
        return list(rec.shards.keys())
    return [key for key, shard in rec.shards.items() if shard.status != "complete"]


def init_shards(
    manifest: CollectManifest, resource_id: str, shard_keys: list[str]
) -> None:
    rec = manifest.resources[resource_id]
    for key in shard_keys:
        if key not in rec.shards:
            rec.shards[key] = ShardRecord()


def mark_shard_complete(
    manifest: CollectManifest,
    resource_id: str,
    shard_key: str,
    *,
    line_count: int,
    expected_count: int | None = None,
) -> None:
    rec = manifest.resources[resource_id]
    shard = rec.shards.setdefault(shard_key, ShardRecord())
    shard.status = "complete"
    shard.line_count = line_count
    shard.expected_count = expected_count
    shard.retrieved_at = _utc_now()
    shard.error = None
    rec.line_count = sum(s.line_count for s in rec.shards.values())


def mark_shard_failed(
    manifest: CollectManifest,
    resource_id: str,
    shard_key: str,
    error: str,
) -> None:
    rec = manifest.resources[resource_id]
    shard = rec.shards.setdefault(shard_key, ShardRecord())
    shard.status = "failed"
    shard.error = error


def finalize_resource(
    manifest: CollectManifest,
    resource_id: str,
    *,
    status: ResourceStatus,
    line_count: int | None = None,
    keys: list[str] | None = None,
    filter_summary: str | None = None,
) -> None:
    rec = manifest.resources[resource_id]
    rec.status = status
    if line_count is not None:
        rec.line_count = line_count
    if keys is not None:
        rec.keys = keys
    if filter_summary is not None:
        rec.filter_summary = filter_summary


def _load_jsonl_keys(path: Path, key_field: str) -> set[str]:
    keys: set[str] = set()
    if not path.is_file():
        return keys
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        val = row.get(key_field)
        if val:
            keys.add(str(val))
    return keys


def _count_jsonl_lines(path: Path) -> int:
    if not path.is_file():
        return 0
    return sum(
        1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    )


def _shard_line_counts(path: Path, shard_key_field: str) -> Counter[str]:
    counts: Counter[str] = Counter()
    if not path.is_file():
        return counts
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        key = row.get(shard_key_field)
        if key:
            counts[str(key)] += 1
    return counts


class ValidationError(Exception):
    """Collect manifest does not match on-disk JSONL artifacts."""


def validate_workspace_collect(
    workspace_root: Path,
    manifest: CollectManifest | None = None,
) -> None:
    """Verify manifest keys and line counts match JSONL files (1:1)."""
    manifest = manifest or load_collect_manifest(workspace_root)
    if manifest is None:
        msg = f"Missing collect manifest at {collect_manifest_path(workspace_root)}"
        raise ValidationError(msg)

    project_path = resource_path(workspace_root, "project")
    project_uuids = _load_jsonl_keys(project_path, "uuid")
    project_rec = manifest.resources["project"]
    if project_rec.status == "complete":
        manifest_keys = set(project_rec.keys)
        if manifest_keys != project_uuids:
            msg = (
                f"project keys mismatch: manifest={len(manifest_keys)} "
                f"file={len(project_uuids)}"
            )
            raise ValidationError(msg)
        file_lines = _count_jsonl_lines(project_path)
        if file_lines != project_rec.line_count:
            msg = f"project line_count mismatch: manifest={project_rec.line_count} file={file_lines}"
            raise ValidationError(msg)

    for resource_id in SHARDED_RESOURCES:
        rec = manifest.resources[resource_id]
        if rec.status not in ("complete", "partial"):
            continue
        path = resource_path(workspace_root, resource_id)
        shard_field = "project_uuid"
        file_counts = _shard_line_counts(path, shard_field)
        if rec.shards:
            shard_keys = set(rec.shards.keys())
            if project_uuids and shard_keys != project_uuids:
                missing = project_uuids - shard_keys
                extra = shard_keys - project_uuids
                if missing or extra:
                    msg = (
                        f"{resource_id} shard keys mismatch: "
                        f"missing={len(missing)} extra={len(extra)}"
                    )
                    raise ValidationError(msg)
            for key, shard in rec.shards.items():
                if (
                    shard.status == "complete"
                    and file_counts.get(key, 0) != shard.line_count
                ):
                    msg = (
                        f"{resource_id} shard {key}: manifest line_count="
                        f"{shard.line_count} file={file_counts.get(key, 0)}"
                    )
                    raise ValidationError(msg)
        file_lines = _count_jsonl_lines(path)
        if rec.status == "complete" and file_lines != rec.line_count:
            msg = (
                f"{resource_id} line_count mismatch: "
                f"manifest={rec.line_count} file={file_lines}"
            )
            raise ValidationError(msg)

    pv_rec = manifest.resources["package_version"]
    if pv_rec.status == "complete":
        pv_path = resource_path(workspace_root, "package_version")
        file_lines = _count_jsonl_lines(pv_path)
        if file_lines != pv_rec.line_count:
            msg = (
                f"package_version line_count mismatch: "
                f"manifest={pv_rec.line_count} file={file_lines}"
            )
            raise ValidationError(msg)

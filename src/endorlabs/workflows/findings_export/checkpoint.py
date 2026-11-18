"""Thin per-namespace checkpoint for findings-export resume."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, cast

CHECKPOINT_SCHEMA = "endor.findings_export.checkpoint.v2"
CHECKPOINT_FILENAME = "checkpoint.json"

ShardStatus = Literal["pending", "complete", "failed"]


@dataclass
class ShardState:
    """Per-project shard status inside a namespace checkpoint."""

    status: ShardStatus = "pending"
    line_count: int = 0
    error: str | None = None


@dataclass
class NamespaceCheckpoint:
    """Resume state for one namespace findings export run."""

    namespace: str
    schema: str = CHECKPOINT_SCHEMA
    extra_filter: str | None = None
    mask: str | None = None
    shards: dict[str, ShardState] = field(default_factory=dict[str, ShardState])

    def to_dict(self) -> dict[str, Any]:
        """Serialize checkpoint for JSON persistence."""
        return {
            "schema": self.schema,
            "namespace": self.namespace,
            "extra_filter": self.extra_filter,
            "mask": self.mask,
            "shards": {
                key: {
                    "status": state.status,
                    "line_count": state.line_count,
                    "error": state.error,
                }
                for key, state in self.shards.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NamespaceCheckpoint:
        """Deserialize a checkpoint dict from disk."""
        shards: dict[str, ShardState] = {}
        raw_shards_obj = data.get("shards")
        raw_shards: dict[str, Any] = (
            cast("dict[str, Any]", raw_shards_obj)
            if isinstance(raw_shards_obj, dict)
            else {}
        )
        for key, value in raw_shards.items():
            if not isinstance(value, dict):
                continue
            value_map = cast("dict[str, Any]", value)
            status_raw = str(value_map.get("status") or "pending")
            status: ShardStatus = (
                cast("ShardStatus", status_raw)
                if status_raw in {"pending", "complete", "failed"}
                else "pending"
            )
            err = value_map.get("error")
            shards[str(key)] = ShardState(
                status=status,
                line_count=int(value_map.get("line_count") or 0),
                error=str(err) if err is not None else None,
            )
        filter_raw = data.get("extra_filter")
        mask_raw = data.get("mask")
        return cls(
            namespace=str(data.get("namespace") or ""),
            schema=str(data.get("schema") or CHECKPOINT_SCHEMA),
            extra_filter=str(filter_raw) if filter_raw is not None else None,
            mask=str(mask_raw) if mask_raw is not None else None,
            shards=shards,
        )


def checkpoint_path(output_dir: Path) -> Path:
    """Return the checkpoint.json path under *output_dir*."""
    return output_dir / CHECKPOINT_FILENAME


def load_checkpoint(output_dir: Path, *, namespace: str) -> NamespaceCheckpoint:
    """Load checkpoint from disk or return an empty one for *namespace*.

    Corrupt JSON or namespace mismatch yields a fresh empty checkpoint
    (callers must not treat that as reusable completion).
    """
    path = checkpoint_path(output_dir)
    if not path.is_file():
        return NamespaceCheckpoint(namespace=namespace)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return NamespaceCheckpoint(namespace=namespace)
    if not isinstance(data, dict):
        return NamespaceCheckpoint(namespace=namespace)
    loaded = NamespaceCheckpoint.from_dict(data)
    if loaded.namespace and loaded.namespace != namespace:
        return NamespaceCheckpoint(namespace=namespace)
    loaded.namespace = namespace
    return loaded


def save_checkpoint(output_dir: Path, checkpoint: NamespaceCheckpoint) -> None:
    """Persist *checkpoint* atomically as checkpoint.json under *output_dir*."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = checkpoint_path(output_dir)
    tmp = path.with_suffix(".json.tmp")
    payload = json.dumps(checkpoint.to_dict(), indent=2, ensure_ascii=True) + "\n"
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(path)


def identity_matches(
    checkpoint: NamespaceCheckpoint,
    *,
    namespace: str,
    extra_filter: str | None,
    mask: str | None,
) -> bool:
    """True when checkpoint semantic inputs match the requested export."""
    if checkpoint.namespace != namespace:
        return False
    if (checkpoint.extra_filter or None) != (extra_filter or None):
        return False
    return (checkpoint.mask or None) == (mask or None)


def invalidate_complete_without_artifact(
    checkpoint: NamespaceCheckpoint,
    *,
    artifact_path: Path,
) -> None:
    """Demote completed shards when the output artifact is missing/empty."""
    if artifact_path.is_file() and artifact_path.stat().st_size > 0:
        return
    for key, state in list(checkpoint.shards.items()):
        if state.status == "complete":
            checkpoint.shards[key] = ShardState(
                status="pending",
                line_count=0,
                error="artifact missing or empty; completion invalidated",
            )


def init_shards(checkpoint: NamespaceCheckpoint, shard_keys: list[str]) -> None:
    """Ensure every *shard_keys* entry exists (pending if new)."""
    for key in shard_keys:
        if key not in checkpoint.shards:
            checkpoint.shards[key] = ShardState()


def pending_shard_keys(checkpoint: NamespaceCheckpoint, *, resume: bool) -> set[str]:
    """Return shard keys still needing work (all keys when not resuming)."""
    if not resume:
        return set(checkpoint.shards)
    return {
        key for key, state in checkpoint.shards.items() if state.status != "complete"
    }


def mark_complete(
    checkpoint: NamespaceCheckpoint, shard_key: str, *, line_count: int
) -> None:
    """Mark *shard_key* complete with *line_count* finding rows."""
    checkpoint.shards[shard_key] = ShardState(status="complete", line_count=line_count)


def mark_failed(checkpoint: NamespaceCheckpoint, shard_key: str, error: str) -> None:
    """Mark *shard_key* failed with *error* detail."""
    prev = checkpoint.shards.get(shard_key)
    line_count = prev.line_count if prev else 0
    checkpoint.shards[shard_key] = ShardState(
        status="failed", line_count=line_count, error=error
    )

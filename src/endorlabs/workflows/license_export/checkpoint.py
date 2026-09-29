"""Thin per-namespace checkpoint for license-export inventory resume."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, cast

CHECKPOINT_SCHEMA = "endor.license_export.checkpoint.v1"
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
    """Resume state for one namespace inventory run."""

    namespace: str
    schema: str = CHECKPOINT_SCHEMA
    shards: dict[str, ShardState] = field(default_factory=dict[str, ShardState])

    def to_dict(self) -> dict[str, Any]:
        """Serialize checkpoint for JSON persistence."""
        return {
            "schema": self.schema,
            "namespace": self.namespace,
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
        return cls(
            namespace=str(data.get("namespace") or ""),
            schema=str(data.get("schema") or CHECKPOINT_SCHEMA),
            shards=shards,
        )


def checkpoint_path(output_dir: Path) -> Path:
    """Return the checkpoint.json path under *output_dir*."""
    return output_dir / CHECKPOINT_FILENAME


def load_checkpoint(output_dir: Path, *, namespace: str) -> NamespaceCheckpoint:
    """Load checkpoint from disk or return an empty one for *namespace*."""
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
    """Persist *checkpoint* as checkpoint.json under *output_dir*."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = checkpoint_path(output_dir)
    path.write_text(
        json.dumps(checkpoint.to_dict(), indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
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
    """Mark *shard_key* complete with *line_count* inventory rows."""
    checkpoint.shards[shard_key] = ShardState(status="complete", line_count=line_count)


def mark_failed(checkpoint: NamespaceCheckpoint, shard_key: str, error: str) -> None:
    """Mark *shard_key* failed with *error* detail."""
    prev = checkpoint.shards.get(shard_key)
    line_count = prev.line_count if prev else 0
    checkpoint.shards[shard_key] = ShardState(
        status="failed", line_count=line_count, error=error
    )

"""Keyed JSONL upsert store with atomic rewrite."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any, cast


def row_key(row: Mapping[str, Any], key_fields: Sequence[str]) -> tuple[str, ...]:
    """Build a composite string key from *row* using *key_fields*."""
    return tuple(str(row.get(field) or "") for field in key_fields)


def load_jsonl_rows(path: Path) -> list[dict[str, Any]]:
    """Load JSON object rows from a JSONL file (skips blank/bad lines)."""
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                rows.append(cast("dict[str, Any]", data))
    return rows


class JsonlKeyedStore:
    """In-memory keyed view of a JSONL file with atomic upsert persistence.

    Rows are keyed by one or more fields. Upserts replace existing keys and
    append new ones; ``flush`` rewrites the file via temp + ``os.replace``.
    """

    def __init__(self, path: Path | str, key_fields: Sequence[str]) -> None:
        super().__init__()
        if not key_fields:
            raise ValueError("key_fields must be non-empty")
        self.path = Path(path)
        self.key_fields = tuple(key_fields)
        self._by_key: dict[tuple[str, ...], dict[str, Any]] = {}
        self._order: list[tuple[str, ...]] = []
        self.reload()

    def reload(self) -> None:
        """Reload rows from disk into the in-memory index."""
        self._by_key.clear()
        self._order.clear()
        for row in load_jsonl_rows(self.path):
            key = row_key(row, self.key_fields)
            if not all(key):
                continue
            if key not in self._by_key:
                self._order.append(key)
            self._by_key[key] = row

    def get(self, *key_parts: str) -> dict[str, Any] | None:
        """Return the row for *key_parts*, or None."""
        return self._by_key.get(tuple(str(p) for p in key_parts))

    def __contains__(self, key_parts: tuple[str, ...] | list[str]) -> bool:
        """Return True if a row exists for *key_parts*."""
        return tuple(str(p) for p in key_parts) in self._by_key

    def __len__(self) -> int:
        """Return the number of keyed rows."""
        return len(self._by_key)

    def rows(self) -> list[dict[str, Any]]:
        """Return rows in insertion/upsert order."""
        return [self._by_key[k] for k in self._order if k in self._by_key]

    def as_dict(self) -> dict[tuple[str, ...], dict[str, Any]]:
        """Return a shallow copy of the key → row map."""
        return dict(self._by_key)

    def upsert(self, row: Mapping[str, Any]) -> tuple[str, ...]:
        """Insert or replace *row* by primary key; return the key."""
        key = row_key(row, self.key_fields)
        if not all(key):
            raise ValueError(
                f"upsert row missing key field(s) {self.key_fields!r}: {dict(row)!r}"
            )
        data = dict(row)
        if key not in self._by_key:
            self._order.append(key)
        self._by_key[key] = data
        return key

    def upsert_many(self, rows: Iterable[Mapping[str, Any]]) -> int:
        """Upsert each row; return count processed."""
        count = 0
        for row in rows:
            self.upsert(row)
            count += 1
        return count

    def clear(self) -> None:
        """Drop all in-memory rows (does not touch disk until flush)."""
        self._by_key.clear()
        self._order.clear()

    def flush(self) -> None:
        """Atomically rewrite the JSONL file from the in-memory index."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.",
            suffix=".tmp",
            dir=str(self.path.parent),
        )
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                for key in self._order:
                    row = self._by_key.get(key)
                    if row is None:
                        continue
                    handle.write(json.dumps(row, ensure_ascii=False, default=str))
                    handle.write("\n")
            os.replace(tmp_path, self.path)
        except Exception:
            if tmp_path.is_file():
                tmp_path.unlink(missing_ok=True)
            raise

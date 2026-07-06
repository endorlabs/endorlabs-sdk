"""Flatten nested Query reference list rows (ewok normalize_query_results parity)."""

from __future__ import annotations

from typing import Any, cast


def _wire_dict(obj: Any) -> dict[str, Any]:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return cast("dict[str, Any]", obj)
    if hasattr(obj, "model_dump"):
        return cast("dict[str, Any]", obj.model_dump(mode="json", warnings=False))
    return {}


def normalize_reference_rows(objects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Hoist the first list object from each ``meta.references[*].list`` block.

    When a reference returns a single masked row, field paths like
    ``references.Finding.spec.level`` are easier to consume after hoisting
    ``references.Finding.list.objects[0]`` onto the reference block.
    """
    normalized: list[dict[str, Any]] = []
    for row in objects:
        item = dict(row)
        meta = _wire_dict(item.get("meta"))
        refs = _wire_dict(meta.get("references"))
        if not refs:
            normalized.append(item)
            continue
        refs_out: dict[str, Any] = {}
        for ref_key, block in refs.items():
            block_dict = _wire_dict(block)
            lst = _wire_dict(block_dict.get("list"))
            objects_block = lst.get("objects")
            if isinstance(objects_block, list) and objects_block:
                first = _wire_dict(objects_block[0])
                merged = dict(block_dict)
                merged.update(first)
                refs_out[ref_key] = merged
            else:
                refs_out[ref_key] = block_dict
        meta_out = dict(meta)
        meta_out["references"] = refs_out
        item["meta"] = meta_out
        normalized.append(item)
    return normalized

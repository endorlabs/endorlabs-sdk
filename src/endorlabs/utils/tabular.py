"""Generic tabular export for SDK resources (flat rows, CSV, optional pandas).

Any ``list()`` / ``list_iter()`` result—Pydantic models, masked dict rows, or
mappings—can be flattened and written for spreadsheets or DataFrames.

Example::

    from endorlabs.utils.tabular import export_records, write_table

    rows = client.Finding.list(namespace="tenant", traverse=True)
    table = export_records(rows, include=("uuid", "meta", "spec"))
    write_table(table, "findings.csv")

    # Optional: pip install 'endorlabs[tabular]'
    # df = table.to_dataframe()
"""

from __future__ import annotations

import csv
import json
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel

_TABULAR_INSTALL_HINT = (
    "Install tabular extras for DataFrame/Parquet support: "
    "pip install 'endorlabs[tabular]'"
)


def normalize_record(item: Any) -> dict[str, Any]:
    """Convert a supported record type to a plain ``dict``.

    Supports Pydantic models, dataclasses, and mappings.
    """
    if isinstance(item, BaseModel):
        return item.model_dump(mode="json", warnings=False)
    if is_dataclass(item) and not isinstance(item, type):
        return asdict(item)
    if isinstance(item, Mapping):
        return dict(item)
    msg = f"Unsupported record type: {type(item).__name__}"
    raise TypeError(msg)


def _serialize_leaf(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple, dict)):
        return json.dumps(value, default=str)
    return str(value)


def flatten_mapping(
    data: Mapping[str, Any],
    *,
    sep: str = ".",
    max_depth: int | None = None,
    parent_key: str = "",
    depth: int = 0,
) -> dict[str, Any]:
    """Flatten a nested mapping into single-level keys joined by *sep*."""
    items: dict[str, Any] = {}
    for key, value in data.items():
        new_key = f"{parent_key}{sep}{key}" if parent_key else str(key)
        if (
            isinstance(value, Mapping)
            and value
            and (max_depth is None or depth < max_depth)
        ):
            items.update(
                flatten_mapping(
                    value,
                    sep=sep,
                    max_depth=max_depth,
                    parent_key=new_key,
                    depth=depth + 1,
                )
            )
        else:
            items[new_key] = _serialize_leaf(value)
    return items


def _key_matches(key: str, patterns: Sequence[str]) -> bool:
    return any(key == pattern or key.startswith(f"{pattern}.") for pattern in patterns)


def _apply_row_filters(
    row: dict[str, Any],
    *,
    include: Sequence[str] | None,
    exclude: Sequence[str] | None,
    rename: Mapping[str, str] | None,
) -> dict[str, Any]:
    filtered = row
    if include:
        filtered = {k: v for k, v in row.items() if _key_matches(k, include)}
    if exclude:
        filtered = {k: v for k, v in filtered.items() if not _key_matches(k, exclude)}
    if rename:
        return {rename.get(k, k): v for k, v in filtered.items()}
    return filtered


def _resolve_extra(
    record: Any,
    extra: Mapping[str, Any] | Callable[[Any], Mapping[str, Any]] | None,
) -> Mapping[str, Any]:
    if extra is None:
        return {}
    if callable(extra):
        resolved = extra(record)
        return resolved if isinstance(resolved, Mapping) else {}
    return extra


def _record_to_row(
    record: Any,
    *,
    include: Sequence[str] | None,
    exclude: Sequence[str] | None,
    rename: Mapping[str, str] | None,
    sep: str,
    max_depth: int | None,
    extra: Mapping[str, Any] | Callable[[Any], Mapping[str, Any]] | None,
) -> dict[str, Any]:
    normalized = normalize_record(record)
    row = flatten_mapping(normalized, sep=sep, max_depth=max_depth)
    row = _apply_row_filters(row, include=include, exclude=exclude, rename=rename)
    row_extras = _resolve_extra(record, extra)
    if row_extras:
        row = {**row, **dict(row_extras)}
    return row


def column_names(
    rows: Sequence[Mapping[str, Any]],
    *,
    columns: Sequence[str] | None = None,
) -> list[str]:
    """Return stable column order (explicit *columns* or first-seen keys)."""
    if columns is not None:
        return list(columns)
    seen: dict[str, None] = {}
    for row in rows:
        for key in row:
            if key not in seen:
                seen[key] = None
    return list(seen.keys())


@dataclass
class TabularExport:
    """Flattened resource rows plus column order for CSV / DataFrame export."""

    rows: list[dict[str, Any]] = field(default_factory=list)
    columns: list[str] = field(default_factory=list)

    @property
    def row_count(self) -> int:
        """Number of flattened rows in this export."""
        return len(self.rows)

    def to_dataframe(self, *, columns: Sequence[str] | None = None) -> Any:
        """Build a pandas ``DataFrame`` (requires ``endorlabs[tabular]``)."""
        try:
            import pandas as pd  # pyright: ignore[reportMissingTypeStubs]
        except ImportError as e:
            raise ImportError(_TABULAR_INSTALL_HINT) from e

        frame = pd.DataFrame(self.rows)
        if columns is not None:
            present = [col for col in columns if col in frame.columns]
            return frame[present] if present else frame
        if self.columns:
            present = [col for col in self.columns if col in frame.columns]
            if present:
                return frame[present]
        return frame

    def write_csv(
        self,
        path: str | Path,
        *,
        columns: Sequence[str] | None = None,
    ) -> None:
        """Write rows to a UTF-8 CSV file (stdlib; no pandas required)."""
        write_csv(self.rows, path, columns=columns or self.columns or None)


def export_records(
    records: Iterable[Any],
    *,
    include: Sequence[str] | None = None,
    exclude: Sequence[str] | None = None,
    rename: Mapping[str, str] | None = None,
    sep: str = ".",
    max_depth: int | None = None,
    extra: Mapping[str, Any] | Callable[[Any], Mapping[str, Any]] | None = None,
    columns: Sequence[str] | None = None,
) -> TabularExport:
    """Flatten resource records into a :class:`TabularExport`."""
    rows = [
        _record_to_row(
            record,
            include=include,
            exclude=exclude,
            rename=rename,
            sep=sep,
            max_depth=max_depth,
            extra=extra,
        )
        for record in records
    ]
    return TabularExport(rows=rows, columns=column_names(rows, columns=columns))


def records_to_rows(
    records: Iterable[Any],
    *,
    include: Sequence[str] | None = None,
    exclude: Sequence[str] | None = None,
    rename: Mapping[str, str] | None = None,
    sep: str = ".",
    max_depth: int | None = None,
    extra: Mapping[str, Any] | Callable[[Any], Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Flatten records to row dicts (wrapper around :func:`export_records`)."""
    return export_records(
        records,
        include=include,
        exclude=exclude,
        rename=rename,
        sep=sep,
        max_depth=max_depth,
        extra=extra,
    ).rows


def write_csv(
    rows: Sequence[Mapping[str, Any]],
    path: str | Path,
    *,
    columns: Sequence[str] | None = None,
) -> None:
    """Write flattened rows to a UTF-8 CSV file."""
    path = Path(path)
    fieldnames = column_names(rows, columns=columns)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def write_table(
    table: TabularExport | Sequence[Mapping[str, Any]],
    path: str | Path,
    *,
    columns: Sequence[str] | None = None,
) -> None:
    """Write rows or a :class:`TabularExport` to CSV or Parquet."""
    path = Path(path)
    suffix = path.suffix.lower()
    if isinstance(table, TabularExport):
        rows = table.rows
        default_columns = table.columns or None
    else:
        rows = list(table)
        default_columns = None
    cols = columns if columns is not None else default_columns
    if suffix == ".csv":
        write_csv(rows, path, columns=cols)
        return
    if suffix == ".parquet":
        frame = (
            table.to_dataframe(columns=cols)
            if isinstance(table, TabularExport)
            else to_dataframe([dict(row) for row in rows], columns=cols)
        )
        frame.to_parquet(path, index=False)
        return
    msg = f"Unsupported output extension (use .csv or .parquet): {path}"
    raise ValueError(msg)


def to_dataframe(
    rows: list[dict[str, Any]],
    *,
    columns: Sequence[str] | None = None,
) -> Any:
    """Build a pandas ``DataFrame`` from flattened rows (requires pandas)."""
    export = TabularExport(
        rows=rows,
        columns=column_names(rows, columns=columns),
    )
    return export.to_dataframe(columns=columns)


def write_rows(rows: list[dict[str, Any]], path: str | Path) -> None:
    """Write flattened rows to *path* (``.csv`` or ``.parquet``)."""
    write_table(rows, path)

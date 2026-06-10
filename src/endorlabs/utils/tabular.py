"""Backward-compatible re-exports for estate cardinality tabular helpers.

Canonical path: ``endorlabs.workflows.estate.analyze.cardinality.tabular``.
"""

from endorlabs.workflows.estate.analyze.cardinality.tabular import (
    TabularExport,
    column_names,
    export_records,
    flatten_mapping,
    normalize_record,
    records_to_rows,
    to_dataframe,
    write_csv,
    write_rows,
    write_table,
)

__all__ = [
    "TabularExport",
    "column_names",
    "export_records",
    "flatten_mapping",
    "normalize_record",
    "records_to_rows",
    "to_dataframe",
    "write_csv",
    "write_rows",
    "write_table",
]

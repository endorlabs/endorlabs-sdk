"""Re-export shim — moved to :mod:`endorlabs.workflows.tabular` (layer-neutral).

``TabularExport`` has no cardinality-specific behavior; it now lives outside
``endorlabs.workflows.estate`` so non-estate workflows (e.g.
``endorlabs.workflows.findings``) can import it without tripping the
cross-layer import guard. Import from :mod:`endorlabs.workflows.tabular`
directly in new code — this module is kept only for backward compatibility.
"""

from __future__ import annotations

from endorlabs.workflows.tabular import (
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

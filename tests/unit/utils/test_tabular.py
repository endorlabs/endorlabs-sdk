"""Unit tests for tabular export utilities."""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from pydantic import BaseModel

from endorlabs.utils.tabular import (
    TabularExport,
    column_names,
    export_records,
    flatten_mapping,
    normalize_record,
    records_to_rows,
    write_csv,
    write_table,
)


class _SampleModel(BaseModel):
    uuid: str
    meta: dict[str, str]


@dataclass
class _SampleDataclass:
    name: str
    count: int


def test_normalize_record_from_pydantic() -> None:
    model = _SampleModel(uuid="u1", meta={"name": "n1"})
    out = normalize_record(model)
    assert out == {"uuid": "u1", "meta": {"name": "n1"}}


def test_normalize_record_from_dataclass() -> None:
    out = normalize_record(_SampleDataclass(name="x", count=3))
    assert out == {"name": "x", "count": 3}


def test_normalize_record_unsupported_raises() -> None:
    with pytest.raises(TypeError, match="Unsupported record type"):
        normalize_record(42)


def test_flatten_mapping_nested() -> None:
    flat = flatten_mapping(
        {"spec": {"dependency_data": {"package_name": "pkg", "tags": [1, 2]}}}
    )
    assert flat["spec.dependency_data.package_name"] == "pkg"
    assert flat["spec.dependency_data.tags"] == "[1, 2]"


def test_export_records_include_rename_and_callable_extra() -> None:
    table = export_records(
        [{"spec": {"a": 1}, "uuid": "u"}],
        include=["spec"],
        rename={"spec.a": "a_val"},
        extra=lambda _rec: {"source": "test"},
    )
    assert table.rows == [{"a_val": 1, "source": "test"}]
    assert table.columns == ["a_val", "source"]


def test_records_to_rows_matches_export_records() -> None:
    records = [{"uuid": "u"}]
    assert (
        records_to_rows(records, extra={"estate_root": "tenant"})
        == export_records(records, extra={"estate_root": "tenant"}).rows
    )


def test_column_names_stable_first_seen() -> None:
    rows = [{"b": 2, "a": 1}, {"c": 3, "a": 0}]
    assert column_names(rows) == ["b", "a", "c"]


def test_write_csv_without_pandas(tmp_path: object) -> None:
    path = tmp_path / "rows.csv"
    write_csv([{"a": 1, "b": 2}, {"a": 3}], path)
    text = path.read_text(encoding="utf-8")
    assert text == "a,b\n1,2\n3,\n"


def test_tabular_export_write_csv(tmp_path: object) -> None:
    path = tmp_path / "out.csv"
    table = TabularExport(rows=[{"x": 1}], columns=["x"])
    table.write_csv(path)
    assert path.read_text(encoding="utf-8") == "x\n1\n"


def test_write_table_bad_extension() -> None:
    with pytest.raises(ValueError, match="Unsupported output extension"):
        write_table([{"a": 1}], "rows.json")


def test_to_dataframe_with_pandas() -> None:
    pytest.importorskip("pandas")
    table = TabularExport(rows=[{"a": 1}, {"a": 2}])
    frame = table.to_dataframe()
    assert len(frame) == 2

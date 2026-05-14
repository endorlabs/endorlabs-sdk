"""Tests for list field-mask detection on ListParameters."""

from __future__ import annotations

import pytest

from endorlabs.core.types import ListParameters, list_parameters_has_nonempty_field_mask


@pytest.mark.parametrize(
    ("lp", "expected"),
    [
        (None, False),
        (ListParameters(), False),
        (ListParameters(mask=None), False),
        (ListParameters(mask=""), False),
        (ListParameters(mask="   "), False),
        (ListParameters(mask="uuid"), True),
        (ListParameters(mask=" meta.name "), True),
    ],
)
def test_list_parameters_has_nonempty_field_mask(
    lp: ListParameters | None, expected: bool
) -> None:
    assert list_parameters_has_nonempty_field_mask(lp) is expected

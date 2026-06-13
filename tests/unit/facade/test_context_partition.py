"""Tests for scan-plane partition filter helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from endorlabs import F
from endorlabs.facade.context_partition import (
    MAIN_CONTEXT_TYPE,
    context_partition_filter,
    main_context_filter,
)


def _ctx(*, type: str | None, id: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(type=type, id=id)


def test_context_partition_filter_type_only() -> None:
    filt = context_partition_filter(_ctx(type=MAIN_CONTEXT_TYPE))
    assert filt == '(context.type=="CONTEXT_TYPE_MAIN")'


def test_context_partition_filter_type_and_id() -> None:
    filt = context_partition_filter(_ctx(type="CONTEXT_TYPE_CI_RUN", id="pr-1"))
    assert '(context.type=="CONTEXT_TYPE_CI_RUN")' in filt
    assert '(context.id=="pr-1")' in filt


def test_context_partition_filter_with_extra_string() -> None:
    filt = context_partition_filter(
        _ctx(type=MAIN_CONTEXT_TYPE),
        extra='spec.level=="FINDING_LEVEL_CRITICAL"',
    )
    assert filt.startswith("((context.type==")
    assert 'spec.level=="FINDING_LEVEL_CRITICAL"' in filt


def test_context_partition_filter_with_f_expression() -> None:
    filt = context_partition_filter(
        _ctx(type=MAIN_CONTEXT_TYPE),
        extra=F("spec.level") == "FINDING_LEVEL_CRITICAL",
    )
    assert "FINDING_LEVEL_CRITICAL" in filt


def test_context_partition_filter_missing_type_raises() -> None:
    with pytest.raises(ValueError, match=r"context\.type"):
        context_partition_filter(_ctx(type=None))


def test_main_context_filter_without_extra() -> None:
    assert main_context_filter() == 'context.type=="CONTEXT_TYPE_MAIN"'


def test_main_context_filter_with_extra() -> None:
    filt = main_context_filter('spec.project_uuid=="abc"')
    assert '(context.type=="CONTEXT_TYPE_MAIN")' in filt
    assert 'spec.project_uuid=="abc"' in filt

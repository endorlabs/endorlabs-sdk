"""Unit tests for SemgrepRule metadata inventory workflow."""

from __future__ import annotations

from unittest.mock import Mock

from endorlabs.workflows.semgrep.inventory import build_inventory


def _rule(*, name: str, origin: str, meta: dict[str, str]) -> Mock:
    rule = Mock()
    rule.uuid = f"uuid-{name}"
    rule.meta.name = name
    rule.spec.defined_by = origin
    native = Mock()
    native.metadata.model_dump.return_value = meta
    rule.spec.rule = native
    return rule


def test_build_inventory_unlimited_not_truncated() -> None:
    client = Mock()
    client.SemgrepRule.list.return_value = [
        _rule(name="r1", origin="tenant", meta={"category": "security"}),
    ]

    inv = build_inventory(client, "tenant.ns", max_pages=0, page_size=500)

    assert inv["total_rules"] == 1
    assert inv["list_truncated"] is False
    assert client.SemgrepRule.list.call_args.kwargs["max_pages"] is None


def test_build_inventory_flags_truncation_at_capacity() -> None:
    client = Mock()
    client.SemgrepRule.list.return_value = [
        _rule(name=f"r{i}", origin="tenant", meta={}) for i in range(100)
    ]

    inv = build_inventory(client, "tenant.ns", max_pages=1, page_size=100)

    assert inv["total_rules"] == 100
    assert inv["list_truncated"] is True

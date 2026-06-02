"""Unit tests for grouped list helpers."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from endorlabs.core.types import ListParameters
from endorlabs.workflows.analytics.group_list import (
    count_from_wire,
    grouped_count_list_parameters,
    grouped_count_list_parameters_for_importer_package_version,
    grouped_count_list_parameters_for_project,
    iter_group_buckets,
)


def test_grouped_count_list_parameters_never_traverse() -> None:
    assert grouped_count_list_parameters(page_size=100).traverse is False


def test_grouped_count_list_parameters_for_project_filter() -> None:
    params = grouped_count_list_parameters_for_project(
        page_size=50,
        project_uuid="abc-123",
    )
    assert params.traverse is False
    assert params.filter == 'spec.importer_data.project_uuid=="abc-123"'


def test_grouped_count_list_parameters_for_importer_package_version_filter() -> None:
    params = grouped_count_list_parameters_for_importer_package_version(
        page_size=50,
        package_version_uuid="pv-123",
    )
    assert params.traverse is False
    assert params.filter == 'spec.importer_data.package_version_uuid=="pv-123"'


def test_count_from_wire() -> None:
    assert count_from_wire({"count": 42}) == 42
    assert count_from_wire(None) == 0


def test_iter_group_buckets_single_page() -> None:
    group_key = json.dumps(
        [{"key": "spec.dependency_data.package_name", "value": "pkg"}]
    )
    page = {
        "group_response": {
            "groups": {
                group_key: {"aggregation_count": {"count": 5}},
            }
        }
    }
    client = MagicMock()
    ops = client.DependencyMetadata._ops
    ops._build_params.return_value = {}
    ops.client.get.return_value.json.return_value = page

    buckets = list(
        iter_group_buckets(
            client,
            "tenant.child",
            ListParameters(traverse=False),
        )
    )
    assert len(buckets) == 1
    assert buckets[0][1]["aggregation_count"]["count"] == 5
    url = ops.client.get.call_args[0][0]
    assert url == "v1/namespaces/tenant.child/dependency-metadata"

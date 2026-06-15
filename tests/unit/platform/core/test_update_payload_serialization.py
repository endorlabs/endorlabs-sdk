"""Regression: union-typed update payloads must serialize nested models."""

from __future__ import annotations

from unittest.mock import MagicMock

from endorlabs.operations import BaseResourceOperations
from endorlabs.resources.finding import (
    Finding,
    FindingMetaUpdate,
    FindingSpec,
    FindingTags,
    UpdateFindingPayload,
)


def test_sparse_update_preserves_nested_union_payload_fields() -> None:
    """UpdateFindingPayload uses dict|BaseModel unions; dump must not drop tags."""
    ops = BaseResourceOperations(MagicMock(), "findings", Finding)
    payload = UpdateFindingPayload(
        meta=FindingMetaUpdate(tags=["label-a"]),
        spec=FindingSpec(finding_tags=[FindingTags.TEST.value]),
    )
    body = ops._to_request_body(
        payload, ["meta.tags", "spec.finding_tags"], "finding-uuid"
    )
    assert body["meta"]["tags"] == ["label-a"]
    assert body["spec"]["finding_tags"] == ["FINDING_TAGS_TEST"]

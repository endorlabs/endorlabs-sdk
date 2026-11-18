"""SDK-008 config change plan drafts (no writes)."""

from __future__ import annotations

from endorlabs.workflows.platform.change_plans import draft_update_plan


def test_draft_ready_with_mask_and_patch() -> None:
    plan = draft_update_plan(
        kind="scan_profile",
        namespace="example-tenant",
        resource_uuid="aaaaaaaaaaaaaaaaaaaaaaaa",
        patch={"spec.foo": "bar"},
        update_mask=["spec.foo"],
        current={"spec.foo": "old"},
    )
    assert plan.status == "ready"
    assert plan.rejections == []
    assert plan.review_diff["spec.foo"]["before"] == "old"
    assert "Planning only" in plan.notes[0]


def test_draft_rejects_missing_revision_when_required() -> None:
    plan = draft_update_plan(
        kind="policy",
        namespace="example-tenant",
        resource_uuid="bbbbbbbbbbbbbbbbbbbbbbbb",
        patch={"spec.enabled": True},
        require_revision=True,
    )
    assert plan.status == "rejected"
    assert any("expected_revision" in r for r in plan.rejections)

"""Reviewable configuration / policy change plans (SDK-008).

Planning is never permission to apply. Drafts perform no writes. Unsupported
preconditions are explicit rather than optimistic concurrency claims.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

PlanKind = Literal[
    "policy",
    "policy_template",
    "scan_profile",
    "snooze",
]
PlanStatus = Literal["draft", "rejected", "ready"]


def _empty_dict() -> dict[str, Any]:
    return {}


def _empty_str_list() -> list[str]:
    return []


@dataclass
class ConfigChangePlan:
    """Pure draft for a configuration mutation (no network / no apply)."""

    kind: PlanKind
    status: PlanStatus
    namespace: str
    resource_uuid: str | None = None
    expected_revision: str | None = None
    update_mask: list[str] = field(default_factory=_empty_str_list)
    patch: dict[str, Any] = field(default_factory=_empty_dict)
    review_diff: dict[str, Any] = field(default_factory=_empty_dict)
    rejections: list[str] = field(default_factory=_empty_str_list)
    notes: list[str] = field(default_factory=_empty_str_list)


def draft_update_plan(
    *,
    kind: PlanKind,
    namespace: str,
    resource_uuid: str,
    patch: dict[str, Any],
    update_mask: list[str] | None = None,
    expected_revision: str | None = None,
    current: dict[str, Any] | None = None,
    require_revision: bool = False,
) -> ConfigChangePlan:
    """Build a reviewable update plan without performing writes.

    When ``require_revision`` is True and ``expected_revision`` is missing,
    the plan is ``rejected`` (precondition unavailable) rather than claiming
    unconditional apply safety.
    """
    mask = list(update_mask or sorted(patch.keys()))
    rejections: list[str] = []
    notes = [
        "Planning only — apply requires a separate grant and explicit call.",
    ]
    if require_revision and not expected_revision:
        rejections.append(
            "expected_revision required but unavailable; "
            "optimistic concurrency not claimed"
        )
    if not mask:
        rejections.append("update_mask is empty")
    if not patch:
        rejections.append("patch is empty")

    review_diff: dict[str, Any] = {}
    if current is not None:
        for key in mask:
            review_diff[key] = {
                "before": current.get(key),
                "after": patch.get(key),
            }
    else:
        notes.append("current resource not supplied; review_diff is patch-only")
        for key in mask:
            review_diff[key] = {"before": None, "after": patch.get(key)}

    status: PlanStatus = "rejected" if rejections else "ready"
    return ConfigChangePlan(
        kind=kind,
        status=status,
        namespace=namespace,
        resource_uuid=resource_uuid,
        expected_revision=expected_revision,
        update_mask=mask,
        patch=dict(patch),
        review_diff=review_diff,
        rejections=rejections,
        notes=notes,
    )

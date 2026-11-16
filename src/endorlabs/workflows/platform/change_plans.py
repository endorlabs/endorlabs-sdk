"""Reviewable configuration / policy change plans (SDK-008).

Planning is never permission to apply. Drafts perform no writes. Unsupported
preconditions are explicit rather than optimistic concurrency claims.
Rejections are driven from registry metadata when available.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, cast

PlanKind = Literal[
    "policy",
    "policy_template",
    "scan_profile",
    "snooze",
]
PlanStatus = Literal["draft", "rejected", "ready"]

_KIND_TO_ATTR: dict[PlanKind, str] = {
    "policy": "Policy",
    "policy_template": "PolicyTemplate",
    "scan_profile": "ScanProfile",
    "snooze": "ExceptionPolicy",
}


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


def _nested_get(obj: dict[str, Any], dotted: str) -> Any:
    cur: Any = obj
    for part in dotted.split("."):
        if not isinstance(cur, dict):
            return None
        typed = cast("dict[str, Any]", cur)
        cur = typed.get(part)
    return cur


def _registry_rejections(kind: PlanKind, mask: list[str]) -> list[str]:
    """Reject when registry says update is unavailable or mask is invalid."""
    rejections: list[str] = []
    try:
        from endorlabs.registry import RESOURCE_REGISTRY

        attr = _KIND_TO_ATTR[kind]
        entry = next((e for e in RESOURCE_REGISTRY if e.attr_name == attr), None)
    except Exception:
        entry = None
    if entry is None:
        rejections.append(
            f"registry metadata unavailable for {kind}; "
            "cannot validate update mask or operations"
        )
        return rejections
    raw_ops = getattr(entry, "supported_ops", ()) or ()
    ops: frozenset[str] = frozenset(str(op) for op in raw_ops)
    if "update" not in ops:
        rejections.append(f"update operation unavailable for {kind}")
    raw_ro = getattr(entry, "create_convenience_read_only_spec_fields", ()) or ()
    read_only: set[str] = {str(item) for item in raw_ro}
    for field_path in mask:
        leaf = field_path.split(".")[-1]
        if leaf in read_only or field_path in read_only:
            rejections.append(f"field not mutable: {field_path}")
    return rejections


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
    unconditional apply safety. Registry-backed checks reject unavailable
    updates and read-only fields. ``ready`` only when all checks pass.
    """
    mask = list(update_mask or sorted(patch.keys()))
    rejections: list[str] = []
    notes = [
        "Planning only — apply requires a separate grant and explicit call.",
    ]
    if not namespace or not str(namespace).strip():
        rejections.append("namespace is required")
    if require_revision and not expected_revision:
        rejections.append(
            "expected_revision required but unavailable; "
            "optimistic concurrency not claimed"
        )
    if not mask:
        rejections.append("update_mask is empty")
    if not patch:
        rejections.append("patch is empty")
    rejections.extend(_registry_rejections(kind, mask))

    if expected_revision and current is not None:
        current_rev = (
            _nested_get(current, "meta.update_time")
            or _nested_get(current, "meta.revision")
            or current.get("update_time")
            or current.get("revision")
        )
        if current_rev is not None and str(current_rev) != str(expected_revision):
            rejections.append(
                "expected_revision does not match current resource revision"
            )

    review_diff: dict[str, Any] = {}
    if current is not None:
        for key in mask:
            if key in current:
                before: Any = current.get(key)
            elif "." in key:
                before = _nested_get(current, key)
            else:
                before = None
            review_diff[key] = {
                "before": before,
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

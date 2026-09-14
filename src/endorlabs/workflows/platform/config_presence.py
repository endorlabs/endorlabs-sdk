"""Read-side onboarding config-presence probes (boolean / guided matrix).

Complements ``platform_setup`` create helpers. Does not mutate tenant state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, cast

from endorlabs.core.exceptions import NotFoundError
from endorlabs.filters.main_context import MAIN_CONTEXT_LIST_FILTER
from endorlabs.workflows.common import WorkflowResult
from endorlabs.workflows.projects.discovery import resolve_project_candidate
from endorlabs.workflows.projects.inventory import (
    REGISTRATION_SOURCE_CLI,
    REGISTRATION_SOURCE_CLOUD,
    is_mixed_registration_execution,
    latest_scan_execution_label,
    registration_source_label,
)
from endorlabs.workflows.reports.analyze.license_entitlements import (
    FEATURE_AI_SAST,
    FEATURE_ENDOR_PATCHING,
    FEATURE_SAST,
    FEATURE_SCA,
    FEATURE_SECRETS,
    fetch_license_feature_types,
)
from endorlabs.workflows.wire_access import nested_dict, nested_str

if TYPE_CHECKING:
    from endorlabs import Client

CI_CONTEXT_LIST_FILTER = 'context.type=="CONTEXT_TYPE_CI_RUN"'
MAIN_FULL_SCAN_FILTER = (
    f'({MAIN_CONTEXT_LIST_FILTER}) and (spec.type=="TYPE_ALL_SCANS")'
)

# Out-of-box SemgrepRule origins (see workflows.semgrep.rules). Custom = not these.
PLATFORM_SEMGREP_DEFINED_BY = frozenset({"Endor Labs", "3rd-Party"})
CUSTOM_SEMGREP_RULE_FILTER = (
    'spec.defined_by!="Endor Labs" and spec.defined_by!="3rd-Party"'
)
# Policy has no spec.defined_by in OpenAPI; platform-seeded rows use these creators.
PLATFORM_POLICY_CREATED_BY = frozenset({"apiserver@endor.ai@x509", "Endor Labs"})
CUSTOM_POLICY_FILTER = (
    'meta.created_by!="apiserver@endor.ai@x509" and meta.created_by!="Endor Labs"'
)


def _empty_dict() -> dict[str, Any]:
    return {}


def _empty_str_list() -> list[str]:
    return []


@dataclass
class CheckResult:
    """One presence / guided check outcome."""

    id: str
    tier: str
    present: bool | None = None
    status: str = "pass"
    evidence: dict[str, Any] = field(default_factory=_empty_dict)
    hint: str = ""


def _empty_checks() -> list[CheckResult]:
    return []


@dataclass
class ConfigPresenceResult(WorkflowResult):
    """Tenant (+ optional project) config-presence matrix."""

    tenant: str = ""
    project_uuid: str | None = None
    project_namespace: str | None = None
    checks: list[CheckResult] = field(default_factory=_empty_checks)
    deferred: list[str] = field(default_factory=_empty_str_list)
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize for JSON artifacts."""
        return {
            "status": self.status,
            "message": self.message,
            "errors": list(self.errors),
            "tenant": self.tenant,
            "project_uuid": self.project_uuid,
            "project_namespace": self.project_namespace,
            "generated_at": self.generated_at,
            "checks": [
                {
                    "id": c.id,
                    "tier": c.tier,
                    "present": c.present,
                    "status": c.status,
                    "evidence": c.evidence,
                    "hint": c.hint,
                }
                for c in self.checks
            ],
            "deferred": list(self.deferred),
        }


def _safe_count(
    client: Client,
    kind: str,
    *,
    namespace: str,
    traverse: bool = False,
    filter: str | None = None,
) -> tuple[int | None, str | None]:
    facade = getattr(client, kind, None)
    if facade is None:
        return None, f"facade {kind} missing"
    try:
        kwargs: dict[str, Any] = {"namespace": namespace, "traverse": traverse}
        if filter is not None:
            kwargs["filter"] = filter
        return int(facade.count(**kwargs)), None
    except Exception as exc:
        return None, f"{kind}.count: {type(exc).__name__}: {exc}"


def _spec_dict(obj: Any) -> dict[str, Any]:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return nested_dict(cast("dict[str, Any]", obj), "spec")
    spec = getattr(obj, "spec", None)
    if spec is None:
        return {}
    if hasattr(spec, "model_dump"):
        dumped = spec.model_dump(mode="json")
        if isinstance(dumped, dict):
            return cast("dict[str, Any]", dumped)
        return {}
    return {}


def _bool_check(
    check_id: str,
    *,
    present: bool | None,
    evidence: dict[str, Any] | None = None,
    hint: str = "",
    error: str | None = None,
) -> CheckResult:
    if error:
        return CheckResult(
            id=check_id,
            tier="A",
            present=None,
            status="error",
            evidence=evidence or {"error": error},
            hint=hint,
        )
    return CheckResult(
        id=check_id,
        tier="A",
        present=bool(present),
        status="pass" if present else "fail",
        evidence=evidence or {},
        hint=hint,
    )


def _guided(
    check_id: str,
    *,
    status: str,
    present: bool | None = None,
    evidence: dict[str, Any] | None = None,
    hint: str = "",
) -> CheckResult:
    return CheckResult(
        id=check_id,
        tier="B",
        present=present,
        status=status,
        evidence=evidence or {},
        hint=hint,
    )


_DEFERRED_IDS = [
    "defer.github_app_org_selection",
    "defer.branch_protection_required_checks",
    "defer.ci_workflow_yaml",
    "defer.policy_content_strategy",
    "defer.idp_claim_business_mapping",
    "defer.aisast_baseline_quality",
    "defer.success_criteria_denominator",
    "defer.intended_cli_vs_app_model",
]


def probe_tenant_presence(
    client: Client,
    tenant: str,
) -> list[CheckResult]:
    """Tier A (+ selected Tier B) checks at tenant root namespace."""
    checks: list[CheckResult] = []

    for kind, check_id in (
        ("Installation", "tenant.has_installation"),
        ("ScanProfile", "tenant.has_scan_profile"),
        ("AuthorizationPolicy", "tenant.has_authorization_policy"),
        ("IdentityProvider", "tenant.has_identity_provider"),
        ("NotificationTarget", "tenant.has_notification_target"),
    ):
        count, err = _safe_count(client, kind, namespace=tenant, traverse=True)
        checks.append(
            _bool_check(
                check_id,
                present=(count or 0) > 0 if count is not None else None,
                evidence={"count": count},
                error=err,
            )
        )

    # Custom Policy / SemgrepRule only — exclude platform / 3rd-party out-of-box rows.
    custom_specs: list[tuple[str, str, str, dict[str, Any]]] = [
        (
            "Policy",
            "tenant.has_custom_policy",
            CUSTOM_POLICY_FILTER,
            {
                "excludes_created_by": sorted(PLATFORM_POLICY_CREATED_BY),
                "note": (
                    "Policy has no spec.defined_by; custom ≈ not platform-seeded "
                    "meta.created_by."
                ),
            },
        ),
        (
            "SemgrepRule",
            "tenant.has_custom_semgrep_rule",
            CUSTOM_SEMGREP_RULE_FILTER,
            {
                "excludes_defined_by": sorted(PLATFORM_SEMGREP_DEFINED_BY),
            },
        ),
    ]
    for kind, check_id, filt, extra in custom_specs:
        count, err = _safe_count(
            client, kind, namespace=tenant, traverse=True, filter=filt
        )
        evidence: dict[str, Any] = {"count": count, "filter": filt, **extra}
        checks.append(
            _bool_check(
                check_id,
                present=(count or 0) > 0 if count is not None else None,
                evidence=evidence,
                error=err,
                hint=(
                    "Ask SE whether tenant-authored policies/rules are in scope."
                    if count == 0
                    else ""
                ),
            )
        )

    # Child namespaces: list under tenant without counting the root itself.
    try:
        children = client.Namespace.list(namespace=tenant, traverse=False, max_pages=1)
        child_n = 0
        for ns in children:
            name = ""
            if hasattr(ns, "meta") and ns.meta is not None:
                name = str(getattr(ns.meta, "name", "") or "")
            elif isinstance(ns, dict):
                name = nested_str(ns, "meta", "name")
            if name.startswith(f"{tenant}."):
                child_n += 1
        checks.append(
            _bool_check(
                "tenant.has_child_namespace",
                present=child_n > 0,
                evidence={"child_count": child_n, "listed": len(children)},
            )
        )
    except Exception as exc:
        checks.append(
            _bool_check(
                "tenant.has_child_namespace",
                present=None,
                error=f"Namespace.list: {type(exc).__name__}: {exc}",
            )
        )

    # Default scan profile
    try:
        profiles = client.ScanProfile.list(namespace=tenant, traverse=True, max_pages=1)
        default_n = 0
        for p in profiles:
            spec = _spec_dict(p)
            if spec.get("is_default"):
                default_n += 1
        checks.append(
            _bool_check(
                "tenant.has_default_scan_profile",
                present=default_n > 0,
                evidence={"default_count": default_n, "listed": len(profiles)},
            )
        )
    except Exception as exc:
        checks.append(
            _bool_check(
                "tenant.has_default_scan_profile",
                present=None,
                error=f"ScanProfile.list: {type(exc).__name__}: {exc}",
            )
        )

    features = fetch_license_feature_types(client, tenant)
    feat_map = {
        "tenant.license_entitles_sca": FEATURE_SCA,
        "tenant.license_entitles_sast": FEATURE_SAST,
        "tenant.license_entitles_ai_sast": FEATURE_AI_SAST,
        "tenant.license_entitles_secrets": FEATURE_SECRETS,
        "tenant.license_entitles_patches": FEATURE_ENDOR_PATCHING,
    }
    for check_id, feat in feat_map.items():
        if features is None:
            checks.append(
                _bool_check(
                    check_id,
                    present=None,
                    evidence={"features": None},
                    error="EndorLicense list empty or failed",
                )
            )
        else:
            checks.append(
                _bool_check(
                    check_id,
                    present=feat in features,
                    evidence={"feature": feat, "active_features": sorted(features)},
                )
            )

    # SystemConfig package firewall presence
    try:
        configs = client.SystemConfig.list(namespace=tenant, max_pages=1)
        has_pfw = False
        for row in configs:
            spec = _spec_dict(row)
            if spec.get("package_firewall") is not None:
                has_pfw = True
                break
        checks.append(
            _bool_check(
                "tenant.has_system_config_package_firewall",
                present=has_pfw,
                evidence={"system_config_rows": len(configs)},
            )
        )
    except Exception as exc:
        checks.append(
            _bool_check(
                "tenant.has_system_config_package_firewall",
                present=None,
                error=f"SystemConfig.list: {type(exc).__name__}: {exc}",
            )
        )

    # Tier B: AuthPolicy form heuristics
    try:
        from endorlabs.workflows.auth.authorization_policy import (
            list_authorization_policies,
        )
        from endorlabs.workflows.auth.authorization_policy_form import (
            audit_authorization_policy_forms,
        )

        raw = list_authorization_policies(
            client, namespace=tenant, traverse=True, max_pages=1
        )
        findings = audit_authorization_policy_forms(raw)
        checks.append(
            _guided(
                "guided.auth_policy_form_issues",
                status="warn" if findings else "pass",
                present=len(findings) > 0,
                evidence={"form_finding_count": len(findings)},
                hint=(
                    "Ask SE to review AuthPolicy claim/namespace form heuristics."
                    if findings
                    else ""
                ),
            )
        )
    except Exception as exc:
        checks.append(
            _guided(
                "guided.auth_policy_form_issues",
                status="error",
                evidence={"error": f"{type(exc).__name__}: {exc}"},
                hint="Ask SE if AuthorizationPolicy list is permitted for this tenant.",
            )
        )

    # Tier B: API key expiry (best-effort)
    try:
        from endorlabs.workflows.auth.credential_expiry import (
            classify_expiration,
            parse_expiration_time,
        )

        keys = client.APIKey.list(namespace=tenant, max_pages=1)
        statuses: list[str] = []
        for key in keys:
            spec = _spec_dict(key)
            exp = parse_expiration_time(spec.get("expiration_time"))
            label, _days = classify_expiration(exp, within_days=30)
            statuses.append(str(label))
        near = any(s in {"expiring_soon", "expired"} for s in statuses)
        checks.append(
            _guided(
                "guided.api_key_expiry",
                status="warn" if near else "pass",
                present=near,
                evidence={"key_count": len(keys), "classifications": statuses[:20]},
                hint=("Ask SE about rotating API keys nearing expiry." if near else ""),
            )
        )
    except Exception as exc:
        checks.append(
            _guided(
                "guided.api_key_expiry",
                status="error",
                evidence={"error": f"{type(exc).__name__}: {exc}"},
                hint="APIKey list may require elevated privileges.",
            )
        )

    return checks


def probe_project_presence(
    client: Client,
    project: Any,
    *,
    tenant: str | None = None,
    lookback_days: int = 30,
) -> list[CheckResult]:
    """Tier A (+ selected Tier B) checks for one Project row."""
    checks: list[CheckResult] = []
    ns = getattr(project, "namespace", None) or nested_str(
        project if isinstance(project, dict) else {}, "tenant_meta", "namespace"
    )
    vector_ns = tenant or (str(ns).split(".", 1)[0] if ns else "")

    is_sbom = bool(client.Project.is_sbom(project))
    is_app = bool(client.Project.is_app(project))
    is_cli = bool(client.Project.is_cli(project))
    # Classification flags: present is the label; status is always pass when known.
    for cid, val in (
        ("project.is_sbom", is_sbom),
        ("project.is_app", is_app),
        ("project.is_cli", is_cli),
    ):
        checks.append(
            CheckResult(
                id=cid,
                tier="A",
                present=val,
                status="pass",
                evidence={"classification": True},
            )
        )

    spec = _spec_dict(project)
    profile_uuid = spec.get("scan_profile_uuid") or nested_str(
        project if isinstance(project, dict) else {}, "spec", "scan_profile_uuid"
    )
    # model may expose scan_profile_uuid on spec attr
    if not profile_uuid and hasattr(project, "spec") and project.spec is not None:
        profile_uuid = getattr(project.spec, "scan_profile_uuid", None)
    checks.append(
        _bool_check(
            "project.has_scan_profile",
            present=bool(profile_uuid),
            evidence={"scan_profile_uuid": profile_uuid},
        )
    )

    git: dict[str, Any] = {}
    raw_git = spec.get("git")
    if isinstance(raw_git, dict):
        git = cast("dict[str, Any]", raw_git)
    if not git and hasattr(project, "spec") and project.spec is not None:
        git_obj = getattr(project.spec, "git", None)
        if git_obj is not None and hasattr(git_obj, "model_dump"):
            dumped = git_obj.model_dump(mode="json")
            if isinstance(dumped, dict):
                git = cast("dict[str, Any]", dumped)
        elif isinstance(git_obj, dict):
            git = cast("dict[str, Any]", git_obj)
    invalid = bool(git.get("invalid_installation"))
    if is_app:
        checks.append(
            _bool_check(
                "project.installation_valid",
                present=not invalid,
                evidence={"invalid_installation": invalid},
            )
        )
    else:
        checks.append(
            CheckResult(
                id="project.installation_valid",
                tier="A",
                present=True,
                status="pass",
                evidence={"applicable": False, "skipped": "not_app_registered"},
            )
        )

    # Resolve scan profile flags (project namespace, then tenant root).
    enable_ai = None
    enable_pr = None
    resolvable = False
    profile_get_error: str | None = None
    if profile_uuid and ns:
        namespaces_to_try = [str(ns)]
        if tenant and str(tenant) != str(ns):
            namespaces_to_try.append(str(tenant))
        for try_ns in namespaces_to_try:
            try:
                profile = client.ScanProfile.get(str(profile_uuid), namespace=try_ns)
                resolvable = True
                pspec = _spec_dict(profile)
                enable_ai = bool(pspec.get("enable_ai_sast_scan"))
                enable_pr = bool(pspec.get("enable_automated_pr_scans"))
                profile_get_error = None
                break
            except NotFoundError as exc:
                profile_get_error = f"ScanProfile.get: {type(exc).__name__}: {exc}"
                continue
            except Exception as exc:
                profile_get_error = f"ScanProfile.get: {type(exc).__name__}: {exc}"
                break
    if profile_uuid:
        if resolvable:
            checks.append(
                _bool_check(
                    "project.scan_profile_resolvable",
                    present=True,
                    evidence={"scan_profile_uuid": profile_uuid},
                )
            )
        elif profile_get_error:
            checks.append(
                _bool_check(
                    "project.scan_profile_resolvable",
                    present=False,
                    error=profile_get_error,
                )
            )
        else:
            checks.append(
                _bool_check(
                    "project.scan_profile_resolvable",
                    present=False,
                    evidence={"scan_profile_uuid": profile_uuid},
                )
            )
        checks.append(
            _bool_check(
                "project.scan_profile_enable_ai_sast",
                present=bool(enable_ai) if enable_ai is not None else False,
                evidence={"enable_ai_sast_scan": enable_ai},
            )
        )
        checks.append(
            _bool_check(
                "project.scan_profile_enable_pr_scans",
                present=bool(enable_pr) if enable_pr is not None else False,
                evidence={"enable_automated_pr_scans": enable_pr},
            )
        )
    else:
        for cid in (
            "project.scan_profile_resolvable",
            "project.scan_profile_enable_ai_sast",
            "project.scan_profile_enable_pr_scans",
        ):
            checks.append(
                _bool_check(
                    cid,
                    present=False,
                    evidence={"skipped": "no_scan_profile_uuid"},
                )
            )

    # Scan activity lookback via count filters
    from_date = (datetime.now(UTC) - timedelta(days=lookback_days)).strftime(
        "%Y-%m-%dT00:00:00Z"
    )
    for check_id, filt in (
        ("project.has_main_full_scan", MAIN_FULL_SCAN_FILTER),
        ("project.has_ci_scan", CI_CONTEXT_LIST_FILTER),
    ):
        try:
            n = client.ScanResult.count(
                parent=project,
                filter=filt,
                from_date=from_date,
            )
            checks.append(
                _bool_check(
                    check_id,
                    present=n > 0,
                    evidence={"count": n, "from_date": from_date, "filter": filt},
                )
            )
        except Exception as exc:
            # Fallback: list_by_project one page and filter client-side
            try:
                scans = client.ScanResult.list_by_project(project, max_pages=1)
                hit = 0
                for s in scans:
                    ctx = getattr(getattr(s, "context", None), "type", None)
                    stype = None
                    sspec = getattr(s, "spec", None)
                    if sspec is not None:
                        stype = getattr(sspec, "type", None)
                    if (
                        check_id == "project.has_ci_scan"
                        and ctx == "CONTEXT_TYPE_CI_RUN"
                    ):
                        hit += 1
                    if (
                        check_id == "project.has_main_full_scan"
                        and ctx == ("CONTEXT_TYPE_MAIN")
                        and stype == "TYPE_ALL_SCANS"
                    ):
                        hit += 1
                checks.append(
                    _bool_check(
                        check_id,
                        present=hit > 0,
                        evidence={
                            "count": hit,
                            "fallback": "list_by_project",
                            "count_error": f"{type(exc).__name__}: {exc}",
                        },
                    )
                )
            except Exception as exc2:
                checks.append(
                    _bool_check(
                        check_id,
                        present=None,
                        error=f"{type(exc2).__name__}: {exc2}",
                    )
                )

    # AI-SAST findings
    try:
        n = client.Finding.count(
            parent=project,
            filter=(
                'spec.finding_categories contains ["FINDING_CATEGORY_SAST"] '
                'and spec.finding_tags contains ["FINDING_TAGS_AI"]'
            ),
        )
        checks.append(
            _bool_check(
                "project.has_ai_sast_finding",
                present=n > 0,
                evidence={"count": n},
            )
        )
    except Exception as exc:
        try:
            rows = client.Finding.list_by_project(
                project,
                filter=(
                    'spec.finding_categories contains ["FINDING_CATEGORY_SAST"] '
                    'and spec.finding_tags contains ["FINDING_TAGS_AI"]'
                ),
                max_pages=1,
            )
            checks.append(
                _bool_check(
                    "project.has_ai_sast_finding",
                    present=len(rows) > 0,
                    evidence={
                        "count": len(rows),
                        "fallback": "list_by_project",
                        "count_error": f"{type(exc).__name__}: {exc}",
                    },
                )
            )
        except Exception as exc2:
            checks.append(
                _bool_check(
                    "project.has_ai_sast_finding",
                    present=None,
                    error=f"{type(exc2).__name__}: {exc2}",
                )
            )

    # Latest execution (labels: present is the value; status always pass when known)
    try:
        label = latest_scan_execution_label(client, project)
        for cid, present in (
            (
                "project.latest_scan_execution_cloud",
                label == REGISTRATION_SOURCE_CLOUD,
            ),
            (
                "project.latest_scan_execution_cli",
                label == REGISTRATION_SOURCE_CLI,
            ),
        ):
            checks.append(
                CheckResult(
                    id=cid,
                    tier="A",
                    present=present,
                    status="pass",
                    evidence={"latest_scan_execution": label},
                )
            )
        reg = registration_source_label(client, project)
        mixed = is_mixed_registration_execution(reg, label)
        checks.append(
            _guided(
                "guided.mixed_registration_execution",
                status="warn" if mixed else "pass",
                present=mixed,
                evidence={
                    "registration": reg,
                    "latest_scan_execution": label,
                },
                hint=(
                    "Ask SE whether mixed Cloud registration + CLI execution is intended."
                    if mixed
                    else ""
                ),
            )
        )
        # Cadence guided: both MAIN and CI present in lookback?
        main_ok = next(
            (c.present for c in checks if c.id == "project.has_main_full_scan"),
            None,
        )
        ci_ok = next((c.present for c in checks if c.id == "project.has_ci_scan"), None)
        if main_ok and ci_ok:
            cadence_status = "pass"
            hint = ""
        elif main_ok or ci_ok:
            cadence_status = "warn"
            hint = "Ask SE about missing MAIN full or CI scan activity in lookback."
        else:
            cadence_status = "fail"
            hint = "Ask SE: no MAIN full or CI scans in lookback window."
        checks.append(
            _guided(
                "guided.main_ci_cadence",
                status=cadence_status,
                present=bool(main_ok and ci_ok),
                evidence={
                    "has_main_full_scan": main_ok,
                    "has_ci_scan": ci_ok,
                    "lookback_days": lookback_days,
                },
                hint=hint,
            )
        )
    except Exception as exc:
        checks.append(
            _guided(
                "guided.mixed_registration_execution",
                status="error",
                evidence={"error": f"{type(exc).__name__}: {exc}"},
            )
        )

    # RepositoryVersion AI-SAST status
    try:
        versions = client.RepositoryVersion.list(parent=project, max_pages=1)
        statuses: list[str] = []
        for v in versions:
            vspec = _spec_dict(v)
            st = vspec.get("aisast_status")
            if st is not None:
                statuses.append(str(st))
        ok = any("SUCCESS" in s.upper() for s in statuses)
        checks.append(
            _guided(
                "guided.aisast_repo_version_status",
                status="pass" if ok else ("warn" if statuses else "fail"),
                present=ok if statuses else False,
                evidence={
                    "aisast_statuses": statuses[:10],
                    "version_count": len(versions),
                },
                hint=(
                    ""
                    if ok
                    else "Ask SE about AI-SAST RepositoryVersion status / baseline."
                ),
            )
        )
    except Exception as exc:
        checks.append(
            _guided(
                "guided.aisast_repo_version_status",
                status="error",
                evidence={"error": f"{type(exc).__name__}: {exc}"},
            )
        )

    # Vector store indexed (repo metadata casing)
    try:
        from endorlabs.workflows.vector_search.query import (
            probe_store_indexed_for_project,
        )

        repo = ""
        if hasattr(project, "meta") and project.meta is not None:
            repo = str(getattr(project.meta, "name", "") or "")
        candidates = [r for r in (repo, repo.lower()) if r]
        stores = [
            s
            for s in client.VectorStore.list(namespace=vector_ns, max_pages=1)
            if getattr(getattr(s, "meta", None), "name", None) == "function_summary"
        ]
        indexed = False
        chosen = None
        if stores and candidates:
            for cand in candidates:
                probe = probe_store_indexed_for_project(client, stores[0], cand)
                if probe.get("indexed"):
                    indexed = True
                    chosen = cand
                    break
        checks.append(
            _guided(
                "guided.vector_store_indexed",
                status="pass" if indexed else "warn",
                present=indexed,
                evidence={"repo": chosen or (candidates[0] if candidates else None)},
                hint=(
                    ""
                    if indexed
                    else "Ask SE whether AI-SAST vector indexing completed for this repo."
                ),
            )
        )
    except Exception as exc:
        checks.append(
            _guided(
                "guided.vector_store_indexed",
                status="error",
                evidence={"error": f"{type(exc).__name__}: {exc}"},
            )
        )

    # PR profile vs installation — presence of both flags only (consistency warn)
    checks.append(
        _guided(
            "guided.scan_profile_pr_vs_installation",
            status="pass" if enable_pr else "warn",
            present=bool(enable_pr),
            evidence={
                "enable_automated_pr_scans": enable_pr,
                "is_app": is_app,
            },
            hint=(
                ""
                if enable_pr
                else "Ask SE: enable automated PR scans on ScanProfile and/or Installation."
            ),
        )
    )

    return checks


def run_config_presence(
    client: Client,
    tenant: str,
    *,
    project: Any | None = None,
    project_uuid: str | None = None,
    lookback_days: int = 30,
) -> ConfigPresenceResult:
    """Probe tenant config presence and optionally one project."""
    result = ConfigPresenceResult(
        tenant=tenant,
        generated_at=datetime.now(UTC).isoformat(),
        deferred=list(_DEFERRED_IDS),
    )
    errors: list[str] = []

    try:
        result.checks.extend(probe_tenant_presence(client, tenant))
    except Exception as exc:
        errors.append(f"tenant probe: {type(exc).__name__}: {exc}")

    proj = project
    if proj is None and project_uuid:
        try:
            proj = resolve_project_candidate(client, project_uuid, namespace=tenant)
        except Exception as exc:
            errors.append(f"Project.resolve: {type(exc).__name__}: {exc}")

    if proj is not None:
        result.project_uuid = getattr(proj, "uuid", None) or project_uuid
        result.project_namespace = getattr(proj, "namespace", None)
        try:
            result.checks.extend(
                probe_project_presence(
                    client,
                    proj,
                    tenant=tenant,
                    lookback_days=lookback_days,
                )
            )
        except Exception as exc:
            errors.append(f"project probe: {type(exc).__name__}: {exc}")

    result.errors = errors
    fails = sum(1 for c in result.checks if c.status == "fail")
    warns = sum(1 for c in result.checks if c.status == "warn")
    errs = sum(1 for c in result.checks if c.status == "error")
    if not result.checks and (errors or errs):
        result.status = "error"
    elif fails or errs or errors:
        result.status = "partial"
    else:
        result.status = "success"
    result.message = (
        f"config-presence tenant={tenant} checks={len(result.checks)} "
        f"fail={fails} warn={warns} error={errs}"
    )
    return result

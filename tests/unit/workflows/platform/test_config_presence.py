"""Unit tests for platform config-presence probes (mocked Client)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

from endorlabs.core.exceptions import NotFoundError
from endorlabs.workflows.platform.config_presence import (
    CheckResult,
    ConfigPresenceResult,
    probe_project_presence,
    probe_tenant_presence,
    run_config_presence,
)
from endorlabs.workflows.projects.inventory import REGISTRATION_SOURCE_CLI
from endorlabs.workflows.reports.analyze.license_entitlements import (
    FEATURE_AI_SAST,
    FEATURE_ENDOR_PATCHING,
    FEATURE_SAST,
    FEATURE_SCA,
    FEATURE_SECRETS,
)


def _dump(payload: dict[str, Any]) -> Any:
    def _inner(**_kwargs: Any) -> dict[str, Any]:
        return payload

    return _inner


def _license_row(*features: str) -> Any:
    infos = [SimpleNamespace(type=f, expiration_time=None) for f in features]
    return SimpleNamespace(
        spec=SimpleNamespace(license_info=infos, excluded_feature_types=[])
    )


def _all_license_features() -> Any:
    return _license_row(
        FEATURE_SCA,
        FEATURE_SAST,
        FEATURE_AI_SAST,
        FEATURE_SECRETS,
        FEATURE_ENDOR_PATCHING,
    )


def _project(
    *,
    uuid: str = "aaaaaaaaaaaaaaaaaaaaaaaa",
    namespace: str = "example-tenant",
    app: bool = True,
    profile_uuid: str | None = "bbbbbbbbbbbbbbbbbbbbbbbb",
) -> Any:
    git = SimpleNamespace(
        external_installation_id="inst-1" if app else None,
        invalid_installation=False,
    )
    spec = SimpleNamespace(
        scan_profile_uuid=profile_uuid,
        git=git,
        sbom=None,
        model_dump=_dump(
            {
                "scan_profile_uuid": profile_uuid,
                "git": {
                    "external_installation_id": "inst-1" if app else None,
                    "invalid_installation": False,
                },
                "sbom": None,
            }
        ),
    )
    return SimpleNamespace(
        uuid=uuid,
        namespace=namespace,
        meta=SimpleNamespace(name="https://github.com/org/repo.git"),
        spec=spec,
    )


def _stub_tenant_counts(client: MagicMock, *, identity_provider: int = 1) -> None:
    client.Installation.count.return_value = 2
    client.ScanProfile.count.return_value = 1
    client.AuthorizationPolicy.count.return_value = 1
    client.IdentityProvider.count.return_value = identity_provider
    client.Policy.count.return_value = 3
    client.NotificationTarget.count.return_value = 1
    client.SemgrepRule.count.return_value = 1
    client.Namespace.list.return_value = [
        SimpleNamespace(meta=SimpleNamespace(name="example-tenant.child"))
    ]
    client.ScanProfile.list.return_value = [
        SimpleNamespace(
            spec=SimpleNamespace(
                is_default=True, model_dump=_dump({"is_default": True})
            )
        )
    ]
    client.SystemConfig.list.return_value = [
        SimpleNamespace(
            spec=SimpleNamespace(
                package_firewall={"x": 1},
                model_dump=_dump({"package_firewall": {"x": 1}}),
            )
        )
    ]
    client.EndorLicense.list.return_value = [_all_license_features()]
    client.APIKey.list.return_value = []
    client.AuthorizationPolicy.list = MagicMock(return_value=[])


def test_probe_tenant_custom_policy_and_semgrep_filters() -> None:
    client = MagicMock()
    _stub_tenant_counts(client)

    checks = probe_tenant_presence(client, "example-tenant")
    by_id = {c.id: c for c in checks}
    assert "tenant.has_custom_policy" in by_id
    assert "tenant.has_custom_semgrep_rule" in by_id
    assert "tenant.has_policy" not in by_id
    assert "tenant.has_semgrep_rule" not in by_id

    policy_kwargs = [
        call.kwargs for call in client.Policy.count.call_args_list if call.kwargs
    ]
    semgrep_kwargs = [
        call.kwargs for call in client.SemgrepRule.count.call_args_list if call.kwargs
    ]
    assert any("meta.created_by" in str(k.get("filter", "")) for k in policy_kwargs), (
        policy_kwargs
    )
    assert any(
        "spec.defined_by" in str(k.get("filter", ""))
        and "3rd-Party" in str(k.get("filter", ""))
        for k in semgrep_kwargs
    ), semgrep_kwargs
    assert by_id["tenant.has_custom_policy"].present is True
    assert by_id["tenant.has_custom_semgrep_rule"].present is True


def test_probe_tenant_presence_counts() -> None:
    client = MagicMock()
    _stub_tenant_counts(client, identity_provider=0)

    checks = probe_tenant_presence(client, "example-tenant")
    by_id = {c.id: c for c in checks}
    assert by_id["tenant.has_installation"].present is True
    assert by_id["tenant.has_identity_provider"].present is False
    assert by_id["tenant.has_child_namespace"].present is True
    assert by_id["tenant.has_default_scan_profile"].present is True


def test_probe_project_presence_app_with_profile() -> None:
    client = MagicMock()
    client.Project.is_sbom.return_value = False
    client.Project.is_app.return_value = True
    client.Project.is_cli.return_value = False
    client.ScanProfile.get.return_value = SimpleNamespace(
        spec=SimpleNamespace(
            enable_ai_sast_scan=True,
            enable_automated_pr_scans=True,
            model_dump=_dump(
                {
                    "enable_ai_sast_scan": True,
                    "enable_automated_pr_scans": True,
                }
            ),
        )
    )
    client.ScanResult.count.side_effect = [2, 1]
    client.Finding.count.return_value = 5
    client.ScanResult.list_by_project.return_value = [
        {
            "spec": {"environment": {"config": {"RunBySystem": True}}},
        }
    ]
    client.RepositoryVersion.list.return_value = [
        SimpleNamespace(
            spec=SimpleNamespace(
                aisast_status="AISAST_STATUS_SUCCESS",
                model_dump=_dump({"aisast_status": "AISAST_STATUS_SUCCESS"}),
            )
        )
    ]
    client.VectorStore.list.return_value = []

    checks = probe_project_presence(client, _project(app=True), tenant="example-tenant")
    by_id = {c.id: c for c in checks}
    assert by_id["project.is_app"].present is True
    assert by_id["project.has_scan_profile"].present is True
    assert by_id["project.scan_profile_enable_ai_sast"].present is True
    assert by_id["project.has_main_full_scan"].present is True
    assert by_id["project.latest_scan_execution_cloud"].present is True


def test_run_config_presence_includes_deferred() -> None:
    client = MagicMock()
    for name in (
        "Installation",
        "ScanProfile",
        "AuthorizationPolicy",
        "IdentityProvider",
        "Policy",
        "NotificationTarget",
        "SemgrepRule",
    ):
        getattr(client, name).count.return_value = 0
    client.Namespace.list.return_value = []
    client.ScanProfile.list.return_value = []
    client.SystemConfig.list.return_value = []
    client.EndorLicense.list.return_value = []
    client.APIKey.list.return_value = []

    result = run_config_presence(client, "example-tenant")
    assert result.tenant == "example-tenant"
    assert result.deferred
    assert any(d.startswith("defer.") for d in result.deferred)
    assert result.to_dict()["checks"]


def test_run_status_partial_on_tier_a_fail() -> None:
    client = MagicMock()
    _stub_tenant_counts(client, identity_provider=0)

    result = run_config_presence(client, "example-tenant")
    assert result.status == "partial"
    assert "fail=" in result.message
    assert any(c.status == "fail" for c in result.checks)


def test_run_status_success_with_warns_only() -> None:
    client = MagicMock()
    _stub_tenant_counts(client, identity_provider=1)
    soon = (datetime.now(UTC) + timedelta(days=7)).isoformat().replace("+00:00", "Z")
    client.APIKey.list.return_value = [
        SimpleNamespace(
            spec=SimpleNamespace(
                expiration_time=soon,
                model_dump=_dump({"expiration_time": soon}),
            )
        )
    ]

    result = run_config_presence(client, "example-tenant")
    assert any(c.status == "warn" for c in result.checks)
    assert not any(c.status in {"fail", "error"} for c in result.checks)
    assert result.status == "success"


def test_execution_labels_are_not_fails() -> None:
    client = MagicMock()
    client.Project.is_sbom.return_value = False
    client.Project.is_app.return_value = True
    client.Project.is_cli.return_value = False
    client.ScanProfile.get.return_value = SimpleNamespace(
        spec=SimpleNamespace(
            enable_ai_sast_scan=False,
            enable_automated_pr_scans=False,
            model_dump=_dump(
                {
                    "enable_ai_sast_scan": False,
                    "enable_automated_pr_scans": False,
                }
            ),
        )
    )
    client.ScanResult.count.side_effect = [1, 1]
    client.Finding.count.return_value = 0
    client.ScanResult.list_by_project.return_value = [
        {"spec": {"environment": {"config": {"RunBySystem": False}}}},
    ]
    client.RepositoryVersion.list.return_value = [
        SimpleNamespace(
            spec=SimpleNamespace(
                aisast_status="AISAST_STATUS_SUCCESS",
                model_dump=_dump({"aisast_status": "AISAST_STATUS_SUCCESS"}),
            )
        )
    ]
    client.VectorStore.list.return_value = []

    checks = probe_project_presence(client, _project(app=True), tenant="example-tenant")
    by_id = {c.id: c for c in checks}
    cloud = by_id["project.latest_scan_execution_cloud"]
    cli = by_id["project.latest_scan_execution_cli"]
    assert cloud.present is False
    assert cloud.status == "pass"
    assert cli.present is True
    assert cli.status == "pass"
    assert cli.evidence.get("latest_scan_execution") == REGISTRATION_SOURCE_CLI


def test_is_cli_uses_facade() -> None:
    client = MagicMock()
    client.Project.is_sbom.return_value = False
    client.Project.is_app.return_value = False
    client.Project.is_cli.return_value = True
    client.ScanResult.count.side_effect = [0, 0]
    client.Finding.count.return_value = 0
    client.ScanResult.list_by_project.return_value = []
    client.RepositoryVersion.list.return_value = []
    client.VectorStore.list.return_value = []

    checks = probe_project_presence(
        client, _project(app=False, profile_uuid=None), tenant="example-tenant"
    )
    by_id = {c.id: c for c in checks}
    assert by_id["project.is_cli"].present is True
    client.Project.is_cli.assert_called()


def test_child_namespace_requires_prefix() -> None:
    client = MagicMock()
    _stub_tenant_counts(client)
    client.Namespace.list.return_value = [
        SimpleNamespace(meta=SimpleNamespace(name="example-tenant")),
        SimpleNamespace(meta=SimpleNamespace(name="other-tenant.child")),
    ]
    checks = probe_tenant_presence(client, "example-tenant")
    by_id = {c.id: c for c in checks}
    assert by_id["tenant.has_child_namespace"].present is False

    client.Namespace.list.return_value = [
        SimpleNamespace(meta=SimpleNamespace(name="example-tenant.child")),
    ]
    checks2 = probe_tenant_presence(client, "example-tenant")
    assert {c.id: c for c in checks2}["tenant.has_child_namespace"].present is True


def test_run_resolves_project_via_discovery() -> None:
    client = MagicMock()
    _stub_tenant_counts(client)
    child = _project(namespace="example-tenant.child")
    client.Project.get.side_effect = NotFoundError("not in tenant root")

    with patch(
        "endorlabs.workflows.platform.config_presence.resolve_project_candidate",
        return_value=child,
    ) as resolve:
        with patch(
            "endorlabs.workflows.platform.config_presence.probe_project_presence",
            return_value=[],
        ):
            result = run_config_presence(
                client,
                "example-tenant",
                project_uuid="aaaaaaaaaaaaaaaaaaaaaaaa",
            )

    resolve.assert_called_once()
    assert result.project_namespace == "example-tenant.child"
    assert result.project_uuid == "aaaaaaaaaaaaaaaaaaaaaaaa"
    client.Project.get.assert_not_called()


def test_scan_profile_get_falls_back_to_tenant() -> None:
    client = MagicMock()
    client.Project.is_sbom.return_value = False
    client.Project.is_app.return_value = True
    client.Project.is_cli.return_value = False
    profile = SimpleNamespace(
        spec=SimpleNamespace(
            enable_ai_sast_scan=True,
            enable_automated_pr_scans=True,
            model_dump=_dump(
                {
                    "enable_ai_sast_scan": True,
                    "enable_automated_pr_scans": True,
                }
            ),
        )
    )

    def _get(_uuid: str, *, namespace: str) -> Any:
        if namespace == "example-tenant.child":
            raise NotFoundError("missing in child")
        if namespace == "example-tenant":
            return profile
        raise AssertionError(f"unexpected namespace {namespace}")

    client.ScanProfile.get.side_effect = _get
    client.ScanResult.count.side_effect = [1, 1]
    client.Finding.count.return_value = 0
    client.ScanResult.list_by_project.return_value = [
        {"spec": {"environment": {"config": {"RunBySystem": True}}}},
    ]
    client.RepositoryVersion.list.return_value = []
    client.VectorStore.list.return_value = []

    project = _project(namespace="example-tenant.child")
    checks = probe_project_presence(client, project, tenant="example-tenant")
    by_id = {c.id: c for c in checks}
    assert by_id["project.scan_profile_resolvable"].present is True
    assert by_id["project.scan_profile_enable_ai_sast"].present is True
    assert by_id["project.scan_profile_resolvable"].status == "pass"


def test_cli_exit_code_partial(tmp_path: Path) -> None:
    from endorlabs.workflows.platform import cli as presence_cli

    partial = ConfigPresenceResult(
        tenant="example-tenant",
        status="partial",
        message="fail=1",
        checks=[
            CheckResult(
                id="tenant.has_identity_provider",
                tier="A",
                present=False,
                status="fail",
            )
        ],
    )
    success = ConfigPresenceResult(
        tenant="example-tenant",
        status="success",
        message="fail=0",
        checks=[
            CheckResult(
                id="tenant.has_installation", tier="A", present=True, status="pass"
            )
        ],
    )

    with (
        patch.object(presence_cli.endorlabs, "Client"),
        patch.object(presence_cli, "run_config_presence", return_value=partial),
        patch.object(presence_cli, "_default_output_dir", return_value=tmp_path),
    ):
        assert presence_cli.main(["-n", "example-tenant"]) == 1

    with (
        patch.object(presence_cli.endorlabs, "Client"),
        patch.object(presence_cli, "run_config_presence", return_value=success),
        patch.object(presence_cli, "_default_output_dir", return_value=tmp_path),
    ):
        assert presence_cli.main(["-n", "example-tenant"]) == 0

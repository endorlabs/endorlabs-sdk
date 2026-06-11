"""Tests for the resource-oriented Client facade (TDD).

Verifies delegation, namespace resolution, and convenience kwargs
for endorlabs.Client and client.Namespace. Aligns with facade UX
(import endorlabs; client = endorlabs.Client(...)) and registry-driven architecture.

Delegation is asserted by mocking the facade's _ops (BaseResourceOperations)
methods (list, get, create, update, delete, list_iter) (noqa: SLF001).
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

import endorlabs
from endorlabs.api_client import APIClient
from endorlabs.client_surface import Client
from endorlabs.core.exceptions import AmbiguousError, NotFoundError, ValidationError
from endorlabs.facade import ScanLogsFacade
from tests.conftest import (
    TEST_MAX_PAGES,
    TEST_NAMESPACE_DEFAULT,
    TEST_PAGE_SIZE,
)


def test_client_uses_endorctl_config_when_env_unset(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Client() falls back to ENDOR_NAMESPACE in ~/.endorctl/config.yaml."""
    config_dir = tmp_path / ".endorctl"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text(
        "ENDOR_NAMESPACE: config.tenant.namespace\n", encoding="utf-8"
    )
    monkeypatch.setattr("endorlabs.utils.endorctl_config.Path.home", lambda: tmp_path)
    monkeypatch.delenv("ENDOR_NAMESPACE", raising=False)
    monkeypatch.delenv("ENDOR_CONFIG_PATH", raising=False)
    mock = Mock(spec=APIClient)
    client = endorlabs.Client(api_client=mock)
    mock_list = Mock(return_value=[])
    client.Namespace._ops.list = mock_list
    client.Namespace.list(max_pages=TEST_MAX_PAGES)
    args, _ = mock_list.call_args
    assert args[0] == "config.tenant.namespace"


def test_client_env_namespace_overrides_endorctl_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """ENDOR_NAMESPACE env wins over endorctl config file."""
    config_dir = tmp_path / ".endorctl"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text(
        "ENDOR_NAMESPACE: config.tenant\n", encoding="utf-8"
    )
    monkeypatch.setattr("endorlabs.utils.endorctl_config.Path.home", lambda: tmp_path)
    monkeypatch.setenv("ENDOR_NAMESPACE", "env.tenant")
    mock = Mock(spec=APIClient)
    client = endorlabs.Client(api_client=mock)
    mock_list = Mock(return_value=[])
    client.Namespace._ops.list = mock_list
    client.Namespace.list(max_pages=TEST_MAX_PAGES)
    args, _ = mock_list.call_args
    assert args[0] == "env.tenant"


def test_client_logs_endorctl_config_fallback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Client init logs when namespace comes from endorctl config."""
    import logging

    config_dir = tmp_path / ".endorctl"
    config_dir.mkdir()
    config_file = config_dir / "config.yaml"
    config_file.write_text("ENDOR_NAMESPACE: config.tenant\n", encoding="utf-8")
    monkeypatch.setattr("endorlabs.utils.endorctl_config.Path.home", lambda: tmp_path)
    monkeypatch.delenv("ENDOR_NAMESPACE", raising=False)
    caplog.set_level(logging.INFO, logger="endorlabs.client_surface")
    endorlabs.Client(api_client=Mock(spec=APIClient))
    assert "Default namespace from endorctl config" in caplog.text
    assert str(config_file) in caplog.text


def test_client_uses_endor_namespace_env_when_tenant_omitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Client() without tenant uses ENDOR_NAMESPACE from the environment."""
    monkeypatch.setenv("ENDOR_NAMESPACE", "env.tenant.namespace")
    mock = Mock(spec=APIClient)
    client = endorlabs.Client(api_client=mock)
    mock_list = Mock(return_value=[])
    client.Namespace._ops.list = mock_list
    client.Namespace.list(max_pages=TEST_MAX_PAGES)
    args, _ = mock_list.call_args
    assert args[0] == "env.tenant.namespace"


def test_client_explicit_tenant_overrides_endor_namespace_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Explicit tenant= wins over ENDOR_NAMESPACE."""
    monkeypatch.setenv("ENDOR_NAMESPACE", "env.tenant.namespace")
    mock = Mock(spec=APIClient)
    client = endorlabs.Client(api_client=mock, tenant="explicit.tenant")
    mock_list = Mock(return_value=[])
    client.Namespace._ops.list = mock_list
    client.Namespace.list(max_pages=TEST_MAX_PAGES)
    args, _ = mock_list.call_args
    assert args[0] == "explicit.tenant"


def test_client_requires_namespace_or_tenant_for_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When tenant is None and namespace is not passed to list(), raise ValueError."""
    monkeypatch.delenv("ENDOR_NAMESPACE", raising=False)
    monkeypatch.delenv("ENDOR_CONFIG_PATH", raising=False)
    monkeypatch.setattr(
        "endorlabs.utils.endorctl_config.read_endorctl_namespace",
        lambda: None,
    )
    client = endorlabs.Client(api_client=Mock(spec=APIClient), tenant=None)
    client.Namespace._ops.list = Mock(return_value=[])
    with pytest.raises(ValidationError, match="namespace"):
        client.Namespace.list()
    client.Namespace._ops.list.assert_not_called()


def test_client_namespace_list_uses_default_tenant(
    client_with_mock_transport: Client,
) -> None:
    """list(traverse=True, max_pages=1) delegates with tenant, traverse, max_pages."""
    client = client_with_mock_transport
    mock_list = Mock(return_value=[])
    client.Namespace._ops.list = mock_list
    result = client.Namespace.list(
        traverse=True, concurrent=False, max_pages=TEST_MAX_PAGES
    )
    assert result == []
    mock_list.assert_called_once()
    args, _ = mock_list.call_args
    assert args[0] == TEST_NAMESPACE_DEFAULT
    assert args[1] is not None
    assert args[1].traverse is True
    assert args[2] == TEST_MAX_PAGES


def test_client_namespace_list_override_namespace(
    client_with_mock_transport: Client,
) -> None:
    """client.Namespace.list(namespace='bar') uses 'bar' instead of default tenant."""
    client = client_with_mock_transport
    mock_list = Mock(return_value=[])
    client.Namespace._ops.list = mock_list
    client.Namespace.list(namespace="bar", max_pages=TEST_MAX_PAGES)
    args, _ = mock_list.call_args
    assert args[0] == "bar"
    assert args[2] == TEST_MAX_PAGES


def test_client_creates_apiclient_when_not_passed() -> None:
    """Client(tenant=...) without api_client creates an APIClient internally."""
    with patch("endorlabs.client_surface.APIClient") as mock_apiclient_class:
        mock_apiclient_class.return_value = Mock(spec=APIClient)
        client = endorlabs.Client(tenant=TEST_NAMESPACE_DEFAULT)
        client.Namespace._ops.list = Mock(return_value=[])
        _ = client.Namespace.list(max_pages=TEST_MAX_PAGES)
        mock_apiclient_class.assert_called_once()
    assert mock_apiclient_class.return_value is not None


def test_client_explicit_transport_params_forwarded_to_apiclient() -> None:
    """Client(timeout=30, content_type=..., etc.) forwards params to APIClient."""
    with patch("endorlabs.client_surface.APIClient") as mock_apiclient_class:
        mock_apiclient_class.return_value = Mock(spec=APIClient)
        endorlabs.Client(
            tenant=TEST_NAMESPACE_DEFAULT,
            timeout=30.0,
            content_type="application/json",
            accept_encoding=None,
            max_retries=2,
            base_url="https://custom.example.com",
        )
        mock_apiclient_class.assert_called_once()
        call_kwargs = mock_apiclient_class.call_args[1]
        assert call_kwargs["timeout"] == 30.0
        assert call_kwargs["content_type"] == "application/json"
        assert call_kwargs["accept_encoding"] is None
        assert call_kwargs["max_retries"] == 2
        assert call_kwargs["base_url"] == "https://custom.example.com"


def test_client_namespace_list_convenience_kwargs(
    client_with_mock_transport: Client,
) -> None:
    """list(traverse, page_size, max_pages) builds ListParams; max_pages passed."""
    client = client_with_mock_transport
    mock_list = Mock(return_value=[])
    client.Namespace._ops.list = mock_list
    client.Namespace.list(
        traverse=True,
        concurrent=False,
        page_size=TEST_PAGE_SIZE,
        max_pages=TEST_MAX_PAGES,
    )
    args, _ = mock_list.call_args
    lp = args[1]
    assert lp is not None
    assert lp.traverse is True
    assert lp.page_size == TEST_PAGE_SIZE
    assert args[2] == TEST_MAX_PAGES


def test_client_projects_present_and_delegates(
    client_with_mock_transport: Client,
) -> None:
    """client.Project is present and list(traverse=True, max_pages=1) delegates."""
    client = client_with_mock_transport
    mock_list = Mock(return_value=[])
    client.Project._ops.list = mock_list
    result = client.Project.list(
        traverse=True, concurrent=False, max_pages=TEST_MAX_PAGES
    )
    assert result == []
    mock_list.assert_called_once()
    args, _ = mock_list.call_args
    assert args[0] == TEST_NAMESPACE_DEFAULT
    assert args[1] is not None
    assert args[1].traverse is True
    assert args[2] == TEST_MAX_PAGES


def test_client_exposes_all_registry_resources(
    client_with_mock_transport: Client,
) -> None:
    """Client exposes exactly the resources defined in RESOURCE_REGISTRY."""
    from endorlabs.facade import ResourceFacade
    from endorlabs.registry import RESOURCE_REGISTRY

    client = client_with_mock_transport
    for entry in RESOURCE_REGISTRY:
        assert hasattr(client, entry.attr_name), f"Missing attribute: {entry.attr_name}"
        facade = getattr(client, entry.attr_name)
        assert isinstance(facade, ResourceFacade), (
            f"{entry.attr_name} is not a ResourceFacade"
        )
        assert facade.scope == entry.scope, (
            f"{entry.attr_name}: scope {facade.scope!r} != {entry.scope!r}"
        )
        assert hasattr(facade, "list")
        assert hasattr(facade, "list_iter")
        assert hasattr(facade, "lookup")
        assert hasattr(facade, "get")


def test_registry_supported_ops_not_implemented_contract(
    client_with_mock_transport: Client,
) -> None:
    """Unsupported registry operations should raise NotImplementedError."""
    from endorlabs.registry import RESOURCE_REGISTRY

    client = client_with_mock_transport
    for entry in RESOURCE_REGISTRY:
        facade = getattr(client, entry.attr_name)
        namespace = "oss" if entry.scope == "oss" else TEST_NAMESPACE_DEFAULT

        if "list" not in entry.supported_ops:
            with pytest.raises(NotImplementedError, match="support list"):
                facade.list(namespace=namespace, max_pages=TEST_MAX_PAGES)
            with pytest.raises(NotImplementedError, match="support list_iter"):
                list(facade.list_iter(namespace=namespace, max_pages=TEST_MAX_PAGES))
            with pytest.raises(NotImplementedError, match="support lookup"):
                facade.lookup(namespace=namespace, max_pages=TEST_MAX_PAGES)

        if "get" not in entry.supported_ops:
            with pytest.raises(NotImplementedError, match="support get"):
                facade.get("unit-uuid", namespace=namespace)

        if "create" not in entry.supported_ops:
            with pytest.raises(NotImplementedError, match="support create"):
                facade.create(payload=Mock(), namespace=namespace)

        if "update" not in entry.supported_ops:
            with pytest.raises(NotImplementedError, match="support update"):
                facade.update(
                    "unit-uuid",
                    payload=Mock(),
                    update_mask="meta.description",
                    namespace=namespace,
                )

        if "delete" not in entry.supported_ops:
            with pytest.raises(NotImplementedError, match="support delete"):
                facade.delete("unit-uuid", namespace=namespace)


class TestBuildFacade:
    """_build_facade factory produces the correct facade scope per registry entry."""

    def test_tenant_scope_facade_has_none_scope(
        self, client_with_mock_transport: Client
    ) -> None:
        from endorlabs.registry import RESOURCE_REGISTRY

        for entry in RESOURCE_REGISTRY:
            if entry.scope is None:
                facade = getattr(client_with_mock_transport, entry.attr_name)
                assert facade.scope is None, entry.attr_name
                break
        else:
            pytest.skip("No tenant-scoped resource in registry")


def test_authentication_log_facade_get_uses_tenant_namespace(
    client_with_mock_transport: Client,
) -> None:
    """AuthenticationLog get resolves through tenant namespace in SDK."""
    client = client_with_mock_transport
    client.AuthenticationLog._ops.get = Mock(return_value=Mock(uuid="log-123"))
    result = client.AuthenticationLog.get("log-123")
    assert result.uuid == "log-123"
    client.AuthenticationLog._ops.get.assert_called_once()
    args, _ = client.AuthenticationLog._ops.get.call_args
    assert args[0] == TEST_NAMESPACE_DEFAULT
    assert args[1] == "log-123"


def test_malware_facade_get_uses_oss_namespace(
    client_with_mock_transport: Client,
) -> None:
    """OSS-scoped get(id) always uses the oss namespace path."""
    client = client_with_mock_transport
    client.Malware._ops.get = Mock(
        return_value=Mock(uuid="mal-456", tenant_meta=Mock(namespace="oss"))
    )
    result = client.Malware.get("mal-456")
    assert result.uuid == "mal-456"
    client.Malware._ops.get.assert_called_once()
    args, _ = client.Malware._ops.get.call_args
    assert args[0] == "oss"
    assert args[1] == "mal-456"


def test_malware_facade_list_uses_oss_namespace(
    client_with_mock_transport: Client,
) -> None:
    """OSS-scoped list() always uses the oss namespace path."""
    client = client_with_mock_transport
    client.Malware._ops.list = Mock(return_value=[])
    client.Malware.list(max_pages=TEST_MAX_PAGES)
    client.Malware._ops.list.assert_called_once()
    args, _ = client.Malware._ops.list.call_args
    assert args[0] == "oss"


def test_dependency_metadata_facade_get_uses_tenant_namespace(
    client_with_mock_transport: Client,
) -> None:
    """DependencyMetadata get uses the customer namespace path, not oss."""
    client = client_with_mock_transport
    client.DependencyMetadata._ops.get = Mock(
        return_value=Mock(
            uuid="dep-456", tenant_meta=Mock(namespace=TEST_NAMESPACE_DEFAULT)
        )
    )
    result = client.DependencyMetadata.get("dep-456", namespace="tenant.child")
    assert result.uuid == "dep-456"
    client.DependencyMetadata._ops.get.assert_called_once()
    args, _ = client.DependencyMetadata._ops.get.call_args
    assert args[0] == "tenant.child"
    assert args[1] == "dep-456"


def test_dependency_metadata_facade_list_uses_tenant_namespace(
    client_with_mock_transport: Client,
) -> None:
    """DependencyMetadata list uses the customer namespace path, not oss."""
    client = client_with_mock_transport
    client.DependencyMetadata._ops.list = Mock(return_value=[])
    client.DependencyMetadata.list(namespace="tenant.child", max_pages=TEST_MAX_PAGES)
    client.DependencyMetadata._ops.list.assert_called_once()
    args, _ = client.DependencyMetadata._ops.list.call_args
    assert args[0] == "tenant.child"


def test_dependency_metadata_registry_scope_is_tenant() -> None:
    """DependencyMetadata is tenant-scoped in the effective registry contract."""
    from endorlabs.registry import RESOURCE_REGISTRY

    entry = next(
        item for item in RESOURCE_REGISTRY if item.attr_name == "DependencyMetadata"
    )
    assert entry.scope is None


def test_vulnerability_facade_list_uses_oss_namespace(
    client_with_mock_transport: Client,
) -> None:
    """OSS-scoped vulnerability list() always uses the oss namespace path."""
    client = client_with_mock_transport
    client.Vulnerability._ops.list = Mock(return_value=[])
    client.Vulnerability.list(max_pages=TEST_MAX_PAGES)
    client.Vulnerability._ops.list.assert_called_once()
    args, _ = client.Vulnerability._ops.list.call_args
    assert args[0] == "oss"


def test_vulnerability_and_malware_registry_scope_is_oss() -> None:
    """Vulnerability and Malware catalog facades are OSS-scoped in the registry."""
    from endorlabs.registry import RESOURCE_REGISTRY

    by_attr = {entry.attr_name: entry for entry in RESOURCE_REGISTRY}
    assert by_attr["Vulnerability"].scope == "oss"
    assert by_attr["Malware"].scope == "oss"
    assert by_attr["QueryVulnerability"].scope == "oss"
    assert by_attr["QueryMalware"].scope == "oss"


def test_query_vulnerability_create_builds_payload_and_uses_oss_namespace(
    client_with_mock_transport: Client,
) -> None:
    """Create-only query_vulnerability uses builder and OSS namespace (catalog plane)."""
    client = client_with_mock_transport
    built_payload = Mock()
    client.QueryVulnerability._build_create_payload_fn = Mock(
        return_value=built_payload
    )
    client.QueryVulnerability._ops.create = Mock(return_value=Mock(uuid="qv-1"))
    client.QueryVulnerability.create(
        name="query-vuln",
        package_version_name="pypi://requests@2.31.0",
    )
    client.QueryVulnerability._build_create_payload_fn.assert_called_once()
    client.QueryVulnerability._ops.create.assert_called_once()
    args, _ = client.QueryVulnerability._ops.create.call_args
    assert args[0] == "oss"
    assert args[1] is built_payload


def test_vector_store_query_create_builds_payload_and_uses_tenant_namespace(
    client_with_mock_transport: Client,
) -> None:
    """Create-only VectorStoreQuery uses builder and client tenant namespace."""
    client = client_with_mock_transport
    built_payload = Mock()
    client.VectorStoreQuery._build_create_payload_fn = Mock(return_value=built_payload)
    client.VectorStoreQuery._ops.create = Mock(return_value=Mock(uuid="vsq-1"))
    client.VectorStoreQuery.create(
        name="nl-query",
        vector_store_uuid="6997574c9482b12a38ffeef3",
        query="functions that sanitize a command injection",
    )
    client.VectorStoreQuery._build_create_payload_fn.assert_called_once()
    client.VectorStoreQuery._ops.create.assert_called_once()
    args, _ = client.VectorStoreQuery._ops.create.call_args
    assert args[0] == TEST_NAMESPACE_DEFAULT
    assert args[1] is built_payload


def test_client_exposes_all_custom_facades(
    client_with_mock_transport: Client,
) -> None:
    """Client exposes exactly the facades defined in CUSTOM_FACADE_REGISTRY."""
    from endorlabs.registry import CUSTOM_FACADE_REGISTRY

    client = client_with_mock_transport
    for entry in CUSTOM_FACADE_REGISTRY:
        assert hasattr(client, entry.attr_name), f"Missing attribute: {entry.attr_name}"
        facade = getattr(client, entry.attr_name)
        assert facade is not None, f"{entry.attr_name} is None"


def test_client_exposes_pr_comment_config_with_endorctl_pascal_case(
    client_with_mock_transport: Client,
) -> None:
    """Client should expose PRCommentConfig using endorctl-style PascalCase."""
    from endorlabs.registry import RESOURCE_REGISTRY

    client = client_with_mock_transport
    assert hasattr(client, "PRCommentConfig")
    entry = next(
        (r for r in RESOURCE_REGISTRY if r.attr_name == "PRCommentConfig"),
        None,
    )
    assert entry is not None
    assert entry.resource_name == "pr-comment-configs"
    assert {"list", "get", "create", "update", "delete"}.issubset(entry.supported_ops)


def test_custom_facade_registry_has_stub_metadata() -> None:
    """Every custom facade entry must define pyi_* fields for stub generation."""
    from endorlabs.registry import CUSTOM_FACADE_REGISTRY

    for entry in CUSTOM_FACADE_REGISTRY:
        assert entry.pyi_facade_class.strip(), f"{entry.attr_name}: pyi_facade_class"
        assert entry.pyi_import_module.strip(), f"{entry.attr_name}: pyi_import_module"
        assert entry.pyi_attr_doc.strip(), f"{entry.attr_name}: pyi_attr_doc"


def test_client_namespace_list_uses_session_logging_only(
    client_with_mock_transport: Client,
) -> None:
    """list() delegates with no logging_level; session logging is set on client."""
    client = client_with_mock_transport
    mock_list = Mock(return_value=[])
    client.Namespace._ops.list = mock_list
    client.Namespace.list(max_pages=TEST_MAX_PAGES)
    mock_list.assert_called_once()
    args, kwargs = mock_list.call_args
    assert len(args) == 3
    assert "logging_level" not in kwargs


def test_client_scan_logs_facade_present_and_delegates(
    client_with_mock_transport: Client,
) -> None:
    """client.ScanLogs present; get_logs delegates to get_scan_result_logs."""
    client = client_with_mock_transport
    assert hasattr(client, "ScanLogs")
    assert isinstance(client.ScanLogs, ScanLogsFacade)
    with patch(
        "endorlabs.resources.scan_log_request.get_scan_result_logs",
        return_value=[],
    ) as mock_get_logs:
        result = client.ScanLogs.get_logs("scan-result-uuid-123")
        assert result == []
        mock_get_logs.assert_called_once()
        args, kwargs = mock_get_logs.call_args
        assert args[0] is client._client
        assert args[1] == TEST_NAMESPACE_DEFAULT
        assert args[2] == "scan-result-uuid-123"
        assert kwargs.get("max_entries") == 100


def test_get_with_uuid_string_uses_default_namespace(
    client_with_mock_transport: Client,
) -> None:
    """get(uuid) delegates with client default namespace."""
    client = client_with_mock_transport
    client.Project._ops.get = Mock(return_value=Mock(uuid="proj-123"))
    _ = client.Project.get("proj-123")
    args, _ = client.Project._ops.get.call_args
    assert args[0] == TEST_NAMESPACE_DEFAULT
    assert args[1] == "proj-123"


def test_get_with_resource_object_uses_resource_namespace(
    client_with_mock_transport: Client,
) -> None:
    """get(resource) uses resource.tenant_meta.namespace (context anchoring)."""
    client = client_with_mock_transport
    resource_ns = "tenant.engineering"
    resource = Mock(uuid="proj-456", tenant_meta=Mock(namespace=resource_ns))
    client.Project._ops.get = Mock(return_value=resource)
    _ = client.Project.get(resource)
    args, _ = client.Project._ops.get.call_args
    assert args[0] == resource_ns
    assert args[1] == "proj-456"


def test_delete_with_uuid_string_uses_default_namespace(
    client_with_mock_transport: Client,
) -> None:
    """delete(uuid) delegates with client default namespace."""
    client = client_with_mock_transport
    client.Project._ops.delete = Mock(return_value=True)
    result = client.Project.delete("proj-789")
    assert result is True
    args, _ = client.Project._ops.delete.call_args
    assert args[0] == TEST_NAMESPACE_DEFAULT
    assert args[1] == "proj-789"


def test_delete_with_resource_object_uses_resource_namespace(
    client_with_mock_transport: Client,
) -> None:
    """delete(resource) uses resource.tenant_meta.namespace (context anchoring)."""
    client = client_with_mock_transport
    resource_ns = "tenant.other-team"
    resource = Mock(uuid="proj-abc", tenant_meta=Mock(namespace=resource_ns))
    client.Project._ops.delete = Mock(return_value=True)
    result = client.Project.delete(resource)
    assert result is True
    args, _ = client.Project._ops.delete.call_args
    assert args[0] == resource_ns
    assert args[1] == "proj-abc"


def test_update_with_resource_object_and_no_payload_uses_resource_as_payload(
    client_with_mock_transport: Client,
) -> None:
    """update(resource, update_mask=...) uses resource namespace and payload."""
    client = client_with_mock_transport
    resource_ns = "tenant.eng"
    resource = Mock(uuid="proj-def", tenant_meta=Mock(namespace=resource_ns))
    client.Project._ops.update = Mock(return_value=resource)
    _ = client.Project.update(resource, update_mask="meta.description")
    args, _ = client.Project._ops.update.call_args
    assert args[0] == resource_ns
    assert args[1] == "proj-def"
    assert args[2] is resource
    assert args[3] == ["meta.description"]


def test_update_with_uuid_requires_payload(
    client_with_mock_transport: Client,
) -> None:
    """update(uuid, payload=None, update_mask=...) raises TypeError."""
    client = client_with_mock_transport
    client.Project._ops.update = Mock()
    with pytest.raises(TypeError, match="payload is required"):
        client.Project.update("proj-uuid", update_mask="meta.description")
    client.Project._ops.update.assert_not_called()


def test_update_with_field_kwargs_requires_resource_instance(
    client_with_mock_transport: Client,
) -> None:
    """update(uuid, meta_description=...) raises TypeError; need resource instance."""
    client = client_with_mock_transport
    client.Project._ops.update = Mock()
    with pytest.raises(TypeError, match="resource instance"):
        client.Project.update("proj-uuid", meta_description="new desc")
    client.Project._ops.update.assert_not_called()


def test_update_requires_update_mask(
    client_with_mock_transport: Client,
) -> None:
    """update(id_or_resource) with no update_mask and no kwargs raises TypeError."""
    client = client_with_mock_transport
    resource = Mock(uuid="proj-xyz", tenant_meta=Mock(namespace="tenant.ns"))
    client.Project._ops.update = Mock()
    with pytest.raises(TypeError, match=r"update_mask|kwargs"):
        client.Project.update(resource)
    client.Project._ops.update.assert_not_called()


def test_update_with_kwargs_derives_mask_and_calls_update(
    client_with_mock_transport: Client,
) -> None:
    """update(resource, meta_description=...) derives update_mask and builds payload."""
    from endorlabs.models.base import TenantMeta as BaseTenantMeta
    from endorlabs.resources.project import (
        Project,
        ProjectMeta,
        ProjectSpec,
    )

    client = client_with_mock_transport
    resource_ns = "tenant.eng"
    resource = Project(
        uuid="proj-kw",
        meta=ProjectMeta(name="test-project"),
        spec=ProjectSpec(),
        tenant_meta=BaseTenantMeta(namespace=resource_ns),
    )
    returned = Project(
        uuid="proj-kw",
        meta=ProjectMeta(name="test-project", description="new desc"),
        spec=ProjectSpec(),
        tenant_meta=BaseTenantMeta(namespace=resource_ns),
    )
    client.Project._ops.update = Mock(return_value=returned)
    _ = client.Project.update(resource, meta_description="new desc")
    client.Project._ops.update.assert_called_once()
    args, _ = client.Project._ops.update.call_args
    assert args[0] == resource_ns
    assert args[1] == "proj-kw"
    assert args[2].meta.description == "new desc"
    assert args[3] == ["meta.description"]


def test_create_with_explicit_params_merges_into_kwargs(
    client_with_mock_transport: Client,
) -> None:
    """create(name=..., description=..., namespace_uuid=...) merges into kwargs."""
    client = client_with_mock_transport
    built_payload = Mock()
    client.Project._build_create_payload_fn = Mock(return_value=built_payload)
    client.Project._ops.create = Mock(return_value=Mock(uuid="new-proj"))
    client.Project.create(
        name="my-project",
        description="A project",
        namespace_uuid="ns-uuid-123",
    )
    client.Project._build_create_payload_fn.assert_called_once()
    call_kwargs = client.Project._build_create_payload_fn.call_args[1]
    assert call_kwargs["name"] == "my-project"
    assert call_kwargs["description"] == "A project"
    assert call_kwargs["namespace_uuid"] == "ns-uuid-123"
    client.Project._ops.create.assert_called_once()
    assert client.Project._ops.create.call_args[0][1] is built_payload


def test_create_explicit_param_overrides_kwarg(
    client_with_mock_transport: Client,
) -> None:
    """Explicit name= overrides same key in kwargs when not None."""
    client = client_with_mock_transport
    built_payload = Mock()
    client.Project._build_create_payload_fn = Mock(return_value=built_payload)
    client.Project._ops.create = Mock(return_value=Mock(uuid="new-proj"))
    client.Project.create(
        name="explicit-name",
        description="from-kwargs",
        namespace_uuid="ns-1",
    )
    call_kwargs = client.Project._build_create_payload_fn.call_args[1]
    assert call_kwargs["name"] == "explicit-name"
    assert call_kwargs["description"] == "from-kwargs"
    assert call_kwargs["namespace_uuid"] == "ns-1"


def test_update_with_explicit_meta_params_merges_into_kwargs(
    client_with_mock_transport: Client,
) -> None:
    """update(resource, meta_description=..., meta_tags=...) merges into kwargs."""
    from endorlabs.models.base import TenantMeta as BaseTenantMeta
    from endorlabs.resources.project import (
        Project,
        ProjectMeta,
        ProjectSpec,
    )

    client = client_with_mock_transport
    resource_ns = "tenant.eng"
    resource = Project(
        uuid="proj-explicit",
        meta=ProjectMeta(name="test", description="old"),
        spec=ProjectSpec(),
        tenant_meta=BaseTenantMeta(namespace=resource_ns),
    )
    returned = Project(
        uuid="proj-explicit",
        meta=ProjectMeta(name="test", description="new desc", tags=["t1"]),
        spec=ProjectSpec(),
        tenant_meta=BaseTenantMeta(namespace=resource_ns),
    )
    client.Project._ops.update = Mock(return_value=returned)
    client.Project.update(
        resource,
        meta_description="new desc",
        meta_tags=["t1"],
    )
    client.Project._ops.update.assert_called_once()
    args, _ = client.Project._ops.update.call_args
    assert args[2].meta.description == "new desc"
    assert args[2].meta.tags == ["t1"]
    assert args[3] == ["meta.description", "meta.tags"]


def test_delete_ignore_missing_false_raises_not_found(
    client_with_mock_transport: Client,
) -> None:
    """delete(uuid, ignore_missing=False) raises NotFoundError on 404."""
    client = client_with_mock_transport
    client.Project._ops.delete = Mock(side_effect=NotFoundError("Resource not found"))
    with pytest.raises(NotFoundError, match="Resource not found"):
        client.Project.delete("proj-missing")
    client.Project._ops.delete.assert_called_once()


def test_delete_ignore_missing_true_returns_false_on_not_found(
    client_with_mock_transport: Client,
) -> None:
    """delete(uuid, ignore_missing=True) catches NotFoundError and returns False."""
    client = client_with_mock_transport
    client.Project._ops.delete = Mock(side_effect=NotFoundError("Resource not found"))
    result = client.Project.delete("proj-missing", ignore_missing=True)
    assert result is False
    client.Project._ops.delete.assert_called_once()


def test_delete_ignore_missing_true_returns_true_on_success(
    client_with_mock_transport: Client,
) -> None:
    """delete(uuid, ignore_missing=True) returns True when delete succeeds."""
    client = client_with_mock_transport
    client.Project._ops.delete = Mock(return_value=True)
    result = client.Project.delete("proj-ok", ignore_missing=True)
    assert result is True
    client.Project._ops.delete.assert_called_once()


def test_list_iter_returns_iterator_and_delegates(
    client_with_mock_transport: Client,
) -> None:
    """list_iter(max_pages=1) returns an iterator and delegates to _ops.list_iter."""
    client = client_with_mock_transport
    client.Project._ops.list_iter = Mock(return_value=iter([Mock(uuid="p1")]))
    it = client.Project.list_iter(max_pages=TEST_MAX_PAGES)
    items = list(it)
    assert len(items) == 1
    assert items[0].uuid == "p1"
    client.Project._ops.list_iter.assert_called_once()
    args, _ = client.Project._ops.list_iter.call_args
    assert args[0] == TEST_NAMESPACE_DEFAULT
    assert args[2] == TEST_MAX_PAGES


def test_tag_delegates_to_update_with_meta_tags(
    client_with_mock_transport: Client,
) -> None:
    """tag(resource, tags) calls update with update_mask meta.tags."""
    client = client_with_mock_transport
    resource_ns = "tenant.eng"
    meta = Mock(tags=["old"])
    meta.model_copy = Mock(return_value=Mock(tags=["a", "b"]))
    resource = Mock(
        uuid="proj-tag",
        tenant_meta=Mock(namespace=resource_ns),
        meta=meta,
    )
    resource.model_copy = Mock(return_value=Mock(meta=Mock(tags=["a", "b"])))
    client.Project._ops.update = Mock(return_value=resource)
    client.Project.tag(resource, ["a", "b"])
    client.Project._ops.update.assert_called_once()
    args, _ = client.Project._ops.update.call_args
    assert args[0] == resource_ns
    assert args[1] == "proj-tag"
    assert args[3] == ["meta.tags"]


def test_untag_delegates_to_update_with_meta_tags(
    client_with_mock_transport: Client,
) -> None:
    """untag(resource, keys) calls update with meta.tags after removing keys."""
    client = client_with_mock_transport
    resource_ns = "tenant.eng"
    meta = Mock(tags=["a", "b", "c"])
    meta.model_copy = Mock(return_value=Mock(tags=["a", "c"]))
    resource = Mock(
        uuid="proj-untag",
        tenant_meta=Mock(namespace=resource_ns),
        meta=meta,
    )
    resource.model_copy = Mock(return_value=Mock(meta=Mock(tags=["a", "c"])))
    client.Project._ops.update = Mock(return_value=resource)
    client.Project.untag(resource, ["b"])
    client.Project._ops.update.assert_called_once()
    args, _ = client.Project._ops.update.call_args
    assert args[3] == ["meta.tags"]


def test_tag_raises_when_resource_has_no_tags_support(
    client_with_mock_transport: Client,
) -> None:
    """tag() on a facade without tags support raises NotImplementedError."""
    client = client_with_mock_transport
    # scan_workflow has supported_ops=list/get/delete only (no update), so no tags_paths
    with pytest.raises(NotImplementedError, match="does not support tag"):
        client.ScanWorkflow.tag("some-uuid", ["x"])


def test_untag_raises_when_resource_has_no_tags_support(
    client_with_mock_transport: Client,
) -> None:
    """untag() on a facade without tags support raises NotImplementedError."""
    client = client_with_mock_transport
    # scan_workflow has no update support, so no tags_paths
    with pytest.raises(NotImplementedError, match="does not support untag"):
        client.ScanWorkflow.untag("some-uuid", ["x"])


def test_tag_raises_when_resource_has_no_meta(
    client_with_mock_transport: Client,
) -> None:
    """tag() raises ValueError when the resolved resource has no meta."""
    client = client_with_mock_transport
    resource = Mock(uuid="no-meta", tenant_meta=Mock(namespace="t.ns"), meta=None)
    client.Project._ops.update = Mock()
    with pytest.raises(ValidationError, match="no meta"):
        client.Project.tag(resource, ["a"])


def test_untag_raises_when_resource_has_no_meta(
    client_with_mock_transport: Client,
) -> None:
    """untag() raises ValueError when the resolved resource has no meta."""
    client = client_with_mock_transport
    resource = Mock(uuid="no-meta", tenant_meta=Mock(namespace="t.ns"), meta=None)
    client.Project._ops.update = Mock()
    with pytest.raises(ValidationError, match="no meta"):
        client.Project.untag(resource, ["a"])


def test_list_with_explicit_filter_for_resource_without_filter_map(
    client_with_mock_transport: Client,
) -> None:
    """list(filter='...', max_pages=1) passes filter through when no identity map."""
    client = client_with_mock_transport
    mock_list = Mock(return_value=[])
    client.APIKey._ops.list = mock_list
    client.APIKey.list(
        filter="meta.name == 'my-key'",
        max_pages=TEST_MAX_PAGES,
    )
    mock_list.assert_called_once()
    args, _ = mock_list.call_args
    lp = args[1]
    assert lp is not None
    assert lp.filter == "meta.name == 'my-key'"


def test_list_with_high_utility_kwargs_passes_archive_page_id_pr_uuid_list_all(
    client_with_mock_transport: Client,
) -> None:
    """Pass archive, page_id, pr_uuid to ListParameters; list_all is True (default)."""
    client = client_with_mock_transport
    mock_list = Mock(return_value=[])
    client.Namespace._ops.list = mock_list
    client.Namespace.list(
        archive=True,
        page_id="p1",
        pr_uuid="pr-1",
        max_pages=TEST_MAX_PAGES,
    )
    mock_list.assert_called_once()
    args, _ = mock_list.call_args
    lp = args[1]
    assert lp is not None
    assert lp.archive is True
    assert lp.page_id == "p1"
    assert lp.pr_uuid == "pr-1"
    assert lp.list_all is None  # default; server decides


def test_list_explicit_kwargs_override_list_params(
    client_with_mock_transport: Client,
) -> None:
    """Explicit kwargs override when both list_params and kwargs passed."""
    from endorlabs.core.types import ListParameters

    client = client_with_mock_transport
    mock_list = Mock(return_value=[])
    client.Namespace._ops.list = mock_list
    client.Namespace.list(
        list_params=ListParameters(filter="from_list_params"),
        filter="from_explicit",
        max_pages=TEST_MAX_PAGES,
    )
    mock_list.assert_called_once()
    args, _ = mock_list.call_args
    lp = args[1]
    assert lp is not None
    assert lp.filter == "from_explicit"


def test_lookup_returns_single_item(
    client_with_mock_transport: Client,
) -> None:
    """lookup(name='only') returns the single item when list returns one."""
    client = client_with_mock_transport
    single = Mock(
        uuid="proj-1",
        tenant_meta=Mock(namespace=TEST_NAMESPACE_DEFAULT),
    )
    mock_list = Mock(return_value=[single])
    client.Project._ops.list = mock_list
    result = client.Project.lookup(name="only", max_pages=2)
    assert result is single
    mock_list.assert_called_once()
    args, _ = mock_list.call_args
    assert args[2] == 2


def test_lookup_raises_not_found_when_zero(
    client_with_mock_transport: Client,
) -> None:
    """lookup(...) raises NotFoundError when list returns no items."""
    client = client_with_mock_transport
    client.Project._ops.list = Mock(return_value=[])
    with pytest.raises(NotFoundError, match="No resource matched"):
        client.Project.lookup(name="missing", max_pages=2)


def test_lookup_raises_ambiguous_when_multiple(
    client_with_mock_transport: Client,
) -> None:
    """lookup(...) raises AmbiguousError when list returns more than one."""
    client = client_with_mock_transport
    a = Mock(uuid="proj-a", tenant_meta=Mock(namespace=TEST_NAMESPACE_DEFAULT))
    b = Mock(uuid="proj-b", tenant_meta=Mock(namespace=TEST_NAMESPACE_DEFAULT))
    client.Project._ops.list = Mock(return_value=[a, b])
    with pytest.raises(AmbiguousError, match="Multiple resources"):
        client.Project.lookup(name="dup", max_pages=2)


def test_lookup_calls_list_with_identity_kwargs(
    client_with_mock_transport: Client,
) -> None:
    """lookup(name='x') calls list with name and max_pages=2; filter built from name."""
    client = client_with_mock_transport
    single = Mock(
        uuid="p1",
        tenant_meta=Mock(namespace=TEST_NAMESPACE_DEFAULT),
    )
    mock_list = Mock(return_value=[single])
    client.Project._ops.list = mock_list
    client.Project.lookup(name="backend")
    mock_list.assert_called_once()
    args, _ = mock_list.call_args
    lp = args[1]
    assert lp is not None
    assert lp.filter is not None
    assert "meta.name" in lp.filter
    assert "backend" in lp.filter
    assert args[2] == 2


def test_lookup_raises_value_error_when_mask_kwarg_set(
    client_with_mock_transport: Client,
) -> None:
    """lookup raises before list() when mask= is non-empty (typed resource only)."""
    client = client_with_mock_transport
    mock_list = Mock(return_value=[])
    client.Project._ops.list = mock_list
    with pytest.raises(ValidationError, match="lookup returns a typed resource"):
        client.Project.lookup(mask="uuid", name="x", max_pages=2)
    mock_list.assert_not_called()


def test_lookup_raises_value_error_when_list_params_mask_set(
    client_with_mock_transport: Client,
) -> None:
    """lookup raises when ListParameters.mask is non-empty."""
    from endorlabs.core.types import ListParameters

    client = client_with_mock_transport
    mock_list = Mock(return_value=[])
    client.Project._ops.list = mock_list
    with pytest.raises(ValidationError, match="lookup returns a typed resource"):
        client.Project.lookup(
            list_params=ListParameters(mask="meta.name"),
            name="x",
            max_pages=2,
        )
    mock_list.assert_not_called()


def test_list_with_identity_kwargs_builds_filter_when_in_map(
    client_with_mock_transport: Client,
) -> None:
    """policy has name in list filter map; list(name='x') builds filter from name."""
    client = client_with_mock_transport
    mock_list = Mock(return_value=[])
    client.Policy._ops.list = mock_list
    client.Policy.list(name="my-policy", max_pages=TEST_MAX_PAGES)
    mock_list.assert_called_once()
    args, _ = mock_list.call_args
    lp = args[1]
    assert lp is not None
    assert lp.filter is not None
    assert "meta.name" in lp.filter
    assert "my-policy" in lp.filter


def test_authorization_policy_lookup_builds_filter_from_name(
    client_with_mock_transport: Client,
) -> None:
    """authorization_policy.lookup(name='x') delegates to list with filter from name."""
    client = client_with_mock_transport
    single = Mock(
        uuid="ap-1",
        tenant_meta=Mock(namespace=TEST_NAMESPACE_DEFAULT),
    )
    mock_list = Mock(return_value=[single])
    client.AuthorizationPolicy._ops.list = mock_list
    result = client.AuthorizationPolicy.lookup(name="only-one", max_pages=2)
    assert result is single
    mock_list.assert_called_once()
    args, _ = mock_list.call_args
    lp = args[1]
    assert lp is not None
    assert lp.filter is not None
    assert "meta.name" in lp.filter
    assert "only-one" in lp.filter


def test_list_name_raises_when_not_in_identity_map(
    client_with_mock_transport: Client,
) -> None:
    """scan_workflow has no list identity map; unknown ``name`` raises TypeError."""
    client = client_with_mock_transport
    with pytest.raises(TypeError, match="Invalid list kwargs"):
        client.ScanWorkflow.list(name="some-workflow", max_pages=TEST_MAX_PAGES)


def test_list_with_parent_raises_when_facade_does_not_support_parent(
    client_with_mock_transport: Client,
) -> None:
    """list(parent=...) raises when resource has no parent_kind."""
    client = client_with_mock_transport
    some_resource = Mock(uuid="ns-1", tenant_meta=Mock(namespace="tenant.foo"))
    with pytest.raises(ValidationError, match="does not support list\\(parent="):
        client.Namespace.list(parent=some_resource, max_pages=TEST_MAX_PAGES)


class TestBuildListKwargs:
    """list() and list_iter() use the same internal kwarg-building logic.

    After the _build_list_kwargs extraction, both must produce identical
    ListParameters for the same inputs.
    """

    def test_filter_and_mask_pass_through(
        self, client_with_mock_transport: Client
    ) -> None:
        """Explicit filter and mask appear in ListParameters."""
        client = client_with_mock_transport
        mock_list = Mock(return_value=[])
        client.Project._ops.list = mock_list
        client.Project.list(
            filter='spec.git.http_clone_url=="https://x"',
            mask="meta.name,spec.git",
            max_pages=TEST_MAX_PAGES,
        )
        lp = mock_list.call_args[0][1]
        assert lp is not None
        assert lp.filter == 'spec.git.http_clone_url=="https://x"'
        assert lp.mask == "meta.name,spec.git"

    def test_parent_scoping_adds_parent_uuid_filter(
        self, client_with_mock_transport: Client
    ) -> None:
        """list(parent=resource) uses parent namespace and adds parent_uuid filter."""
        client = client_with_mock_transport
        parent = Mock(uuid="parent-uuid-1", tenant_meta=Mock(namespace="tenant.team"))
        mock_list = Mock(return_value=[])
        client.ScanResult._ops.list = mock_list
        client.ScanResult.list(parent=parent, max_pages=TEST_MAX_PAGES)
        args, _ = mock_list.call_args
        assert args[0] == "tenant.team"  # namespace anchored to parent
        lp = args[1]
        assert lp is not None
        assert "meta.parent_uuid" in lp.filter
        assert "parent-uuid-1" in lp.filter
        assert args[2] == TEST_MAX_PAGES

    def test_identity_kwargs_translated_to_filter(
        self, client_with_mock_transport: Client
    ) -> None:
        """name= kwarg is translated to meta.name filter on supported resources."""
        client = client_with_mock_transport
        mock_list = Mock(return_value=[])
        client.Project._ops.list = mock_list
        client.Project.list(name="my-project", max_pages=TEST_MAX_PAGES)
        lp = mock_list.call_args[0][1]
        assert lp is not None
        assert "meta.name" in lp.filter
        assert "my-project" in lp.filter

    def test_list_and_list_iter_produce_identical_params(
        self, client_with_mock_transport: Client
    ) -> None:
        """list() and list_iter() build the same ListParameters for same inputs."""
        client = client_with_mock_transport
        list_mock = Mock(return_value=[])
        iter_mock = Mock(return_value=iter([]))

        client.Project._ops.list = list_mock
        client.Project._ops.list_iter = iter_mock

        kwargs = {
            "filter": 'meta.tags contains "reviewed"',
            "mask": "meta.name",
            "page_size": 10,
            "max_pages": TEST_MAX_PAGES,
        }
        client.Project.list(**kwargs)
        # Consume the iterator so the mock is actually called
        list(client.Project.list_iter(**kwargs))

        lp_list = list_mock.call_args[0][1]
        lp_iter = iter_mock.call_args[0][1]

        assert lp_list is not None
        assert lp_iter is not None
        assert lp_list.filter == lp_iter.filter
        assert lp_list.mask == lp_iter.mask
        assert lp_list.page_size == lp_iter.page_size


def test_resource_namespace_property_returns_tenant_meta_namespace() -> None:
    """Resource .namespace returns tenant_meta.namespace when set, None otherwise."""
    from endorlabs.models.base import BaseMeta, BaseResource, TenantMeta

    class _ConcreteResource(BaseResource):
        pass

    ns = "tenant.foo.bar"
    meta = BaseMeta()
    tenant_meta = TenantMeta(namespace=ns)
    resource = _ConcreteResource(uuid="r-1", meta=meta, tenant_meta=tenant_meta)
    assert resource.namespace == ns

    resource_none_ns = _ConcreteResource(uuid="r-2", meta=meta, tenant_meta=None)
    assert resource_none_ns.namespace is None


def test_finding_empty_list_warns_at_default_namespace(
    client_with_mock_transport: Client,
) -> None:
    """Empty project-scoped list at tenant root emits a namespace scoping warning."""
    client = client_with_mock_transport
    client.Finding._ops.list = Mock(return_value=[])
    with pytest.warns(UserWarning, match="namespace=project.namespace"):
        client.Finding.list(max_pages=TEST_MAX_PAGES)


def test_finding_empty_list_no_warn_with_child_namespace(
    client_with_mock_transport: Client,
) -> None:
    """Explicit child namespace suppresses the empty-list namespace warning."""
    import warnings

    client = client_with_mock_transport
    client.Finding._ops.list = Mock(return_value=[])
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        client.Finding.list(namespace="tenant.child", max_pages=TEST_MAX_PAGES)
    assert not [w for w in caught if issubclass(w.category, UserWarning)]

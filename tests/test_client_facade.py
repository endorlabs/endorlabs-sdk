"""Tests for the resource-oriented Client facade (TDD).

Verifies delegation, namespace resolution, and convenience kwargs
for endorlabs.Client and client.namespace. Aligns with facade UX
(import endorlabs; client = endorlabs.Client(...)) and registry-driven architecture.

Delegation is asserted by injecting a mock into the facade's _list_fn (noqa: SLF001);
module-boundary mocking would require resolving callables at call time (lazy registry).
"""

from unittest.mock import Mock, patch

import conftest
import pytest

import endorlabs
from endorlabs.api_client import APIClient
from endorlabs.client_surface import Client
from endorlabs.exceptions import AmbiguousError, NotFoundError
from endorlabs.facade import ScanLogsFacade


@pytest.fixture
def client_with_mock_transport() -> Client:
    """Client with mock APIClient and canonical test namespace (typed fixture)."""
    mock = Mock(spec=APIClient)
    client = endorlabs.Client(
        api_client=mock,
        tenant=conftest.TEST_NAMESPACE_DEFAULT,
    )
    return client


def test_client_requires_namespace_or_tenant_for_list() -> None:
    """When tenant is None and namespace is not passed to list(), raise ValueError."""
    client = endorlabs.Client(api_client=Mock(spec=APIClient), tenant=None)
    # Inject mock for delegation; module-boundary mock would need lazy registry.
    client.namespace._list_fn = Mock(return_value=[])
    with pytest.raises(ValueError, match="namespace"):
        client.namespace.list()
    client.namespace._list_fn.assert_not_called()


def test_client_namespace_list_uses_default_tenant(
    client_with_mock_transport: Client,
) -> None:
    """list(traverse=True, max_pages=1) delegates with tenant, traverse, max_pages."""
    client = client_with_mock_transport
    mock_list = Mock(return_value=[])
    client.namespace._list_fn = mock_list
    result = client.namespace.list(traverse=True, max_pages=conftest.TEST_MAX_PAGES)
    assert result == []
    mock_list.assert_called_once()
    args, _ = mock_list.call_args
    assert args[0] is client._client
    assert args[1] == conftest.TEST_NAMESPACE_DEFAULT
    assert args[2] is not None
    assert args[2].traverse is True
    assert args[3] == conftest.TEST_MAX_PAGES


def test_client_namespace_list_override_namespace(
    client_with_mock_transport: Client,
) -> None:
    """client.namespace.list(namespace='bar') uses 'bar' instead of default tenant."""
    client = client_with_mock_transport
    mock_list = Mock(return_value=[])
    client.namespace._list_fn = mock_list
    client.namespace.list(namespace="bar", max_pages=conftest.TEST_MAX_PAGES)
    args, _ = mock_list.call_args
    assert args[1] == "bar"
    assert args[3] == conftest.TEST_MAX_PAGES


def test_client_creates_apiclient_when_not_passed() -> None:
    """Client(tenant=...) without api_client creates an APIClient internally."""
    with patch("endorlabs.client_surface.APIClient") as mock_apiclient_class:
        mock_apiclient_class.return_value = Mock(spec=APIClient)
        client = endorlabs.Client(tenant=conftest.TEST_NAMESPACE_DEFAULT)
        client.namespace._list_fn = Mock(return_value=[])
        _ = client.namespace.list(max_pages=conftest.TEST_MAX_PAGES)
        mock_apiclient_class.assert_called_once()
    assert mock_apiclient_class.return_value is not None


def test_client_explicit_transport_params_forwarded_to_apiclient() -> None:
    """Client(timeout=30, content_type=..., etc.) forwards params to APIClient."""
    with patch("endorlabs.client_surface.APIClient") as mock_apiclient_class:
        mock_apiclient_class.return_value = Mock(spec=APIClient)
        endorlabs.Client(
            tenant=conftest.TEST_NAMESPACE_DEFAULT,
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
    client.namespace._list_fn = mock_list
    client.namespace.list(
        traverse=True,
        page_size=conftest.TEST_PAGE_SIZE,
        max_pages=conftest.TEST_MAX_PAGES,
    )
    args, _ = mock_list.call_args
    lp = args[2]
    assert lp is not None
    assert lp.traverse is True
    assert lp.page_size == conftest.TEST_PAGE_SIZE
    assert args[3] == conftest.TEST_MAX_PAGES


def test_client_projects_present_and_delegates(
    client_with_mock_transport: Client,
) -> None:
    """client.project is present and list(traverse=True, max_pages=1) delegates."""
    client = client_with_mock_transport
    mock_list = Mock(return_value=[])
    client.project._list_fn = mock_list
    result = client.project.list(traverse=True, max_pages=conftest.TEST_MAX_PAGES)
    assert result == []
    mock_list.assert_called_once()
    args, _ = mock_list.call_args
    assert args[0] is client._client
    assert args[1] == conftest.TEST_NAMESPACE_DEFAULT
    assert args[2] is not None
    assert args[2].traverse is True
    assert args[3] == conftest.TEST_MAX_PAGES


def test_client_exposes_all_registry_resources(
    client_with_mock_transport: Client,
) -> None:
    """Client exposes exactly the resources defined in RESOURCE_REGISTRY."""
    from endorlabs.facade import OssResourceFacade, ResourceFacade, SystemResourceFacade
    from endorlabs.registry import RESOURCE_REGISTRY

    client = client_with_mock_transport
    for entry in RESOURCE_REGISTRY:
        assert hasattr(client, entry.attr_name), f"Missing attribute: {entry.attr_name}"
        facade = getattr(client, entry.attr_name)
        if entry.scope == "system":
            assert isinstance(facade, SystemResourceFacade), (
                f"{entry.attr_name} is not a SystemResourceFacade"
            )
            assert hasattr(facade, "get")
        elif entry.scope == "oss":
            assert isinstance(facade, OssResourceFacade), (
                f"{entry.attr_name} is not an OssResourceFacade"
            )
            assert hasattr(facade, "get")
        else:
            assert isinstance(facade, ResourceFacade), (
                f"{entry.attr_name} is not a ResourceFacade"
            )
            assert hasattr(facade, "get") == (entry.get_fn is not None)
        assert hasattr(facade, "list")
        assert hasattr(facade, "list_iter")
        assert hasattr(facade, "lookup")


def test_system_resource_facade_get_with_oss_namespace_delegates(
    client_with_mock_transport: Client,
) -> None:
    """SystemResourceFacade.get(id, namespace='oss') delegates to get_fn with 'oss'."""
    client = client_with_mock_transport
    client.authentication_log._get_fn = Mock(return_value=Mock(uuid="log-123"))
    result = client.authentication_log.get("log-123", namespace="oss")
    assert result.uuid == "log-123"
    client.authentication_log._get_fn.assert_called_once()
    args, _ = client.authentication_log._get_fn.call_args
    assert args[0] is client._client
    assert args[1] == "oss"
    assert args[2] == "log-123"


def test_system_resource_facade_get_with_non_oss_namespace_raises(
    client_with_mock_transport: Client,
) -> None:
    """SystemResourceFacade.get(id) or get(id, namespace=tenant) raises."""
    client = client_with_mock_transport
    with pytest.raises(NotImplementedError, match="oss namespace"):
        client.authentication_log.get("log-123")
    with pytest.raises(NotImplementedError, match="oss namespace"):
        client.authentication_log.get("log-123", namespace="tenant.foo")


def test_oss_resource_facade_get_uses_oss_namespace(
    client_with_mock_transport: Client,
) -> None:
    """OssResourceFacade.get(id) delegates with namespace 'oss' (no param required)."""
    client = client_with_mock_transport
    client.dependency_metadata._get_fn = Mock(
        return_value=Mock(uuid="dep-456", tenant_meta=Mock(namespace="oss"))
    )
    result = client.dependency_metadata.get("dep-456")
    assert result.uuid == "dep-456"
    client.dependency_metadata._get_fn.assert_called_once()
    args, _ = client.dependency_metadata._get_fn.call_args
    assert args[0] is client._client
    assert args[1] == "oss"
    assert args[2] == "dep-456"


def test_oss_resource_facade_list_uses_oss_namespace(
    client_with_mock_transport: Client,
) -> None:
    """OssResourceFacade.list() delegates with namespace 'oss'."""
    client = client_with_mock_transport
    client.dependency_metadata._list_fn = Mock(return_value=[])
    client.dependency_metadata.list(max_pages=conftest.TEST_MAX_PAGES)
    client.dependency_metadata._list_fn.assert_called_once()
    args, _ = client.dependency_metadata._list_fn.call_args
    assert args[0] is client._client
    assert args[1] == "oss"


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


def test_client_namespace_list_uses_session_logging_only(
    client_with_mock_transport: Client,
) -> None:
    """list() delegates with no logging_level; session logging is set on client."""
    client = client_with_mock_transport
    mock_list = Mock(return_value=[])
    client.namespace._list_fn = mock_list
    client.namespace.list(max_pages=conftest.TEST_MAX_PAGES)
    mock_list.assert_called_once()
    args, kwargs = mock_list.call_args
    assert len(args) == 4
    assert "logging_level" not in kwargs


def test_client_scan_logs_facade_present_and_delegates(
    client_with_mock_transport: Client,
) -> None:
    """client.scan_logs present; get_logs delegates to get_scan_result_logs."""
    client = client_with_mock_transport
    assert hasattr(client, "scan_logs")
    assert isinstance(client.scan_logs, ScanLogsFacade)
    with patch(
        "endorlabs.resources.scan_log_request.get_scan_result_logs",
        return_value=[],
    ) as mock_get_logs:
        result = client.scan_logs.get_logs("scan-result-uuid-123")
        assert result == []
        mock_get_logs.assert_called_once()
        args, kwargs = mock_get_logs.call_args
        assert args[0] is client._client
        assert args[1] == conftest.TEST_NAMESPACE_DEFAULT
        assert args[2] == "scan-result-uuid-123"
        assert kwargs.get("max_entries") == 100


def test_get_with_uuid_string_uses_default_namespace(
    client_with_mock_transport: Client,
) -> None:
    """get(uuid) delegates with client default namespace."""
    client = client_with_mock_transport
    client.project._get_fn = Mock(return_value=Mock(uuid="proj-123"))
    _ = client.project.get("proj-123")
    args, _ = client.project._get_fn.call_args
    assert args[0] is client._client
    assert args[1] == conftest.TEST_NAMESPACE_DEFAULT
    assert args[2] == "proj-123"


def test_get_with_resource_object_uses_resource_namespace(
    client_with_mock_transport: Client,
) -> None:
    """get(resource) uses resource.tenant_meta.namespace (context anchoring)."""
    client = client_with_mock_transport
    resource_ns = "tenant.engineering"
    resource = Mock(uuid="proj-456", tenant_meta=Mock(namespace=resource_ns))
    client.project._get_fn = Mock(return_value=resource)
    _ = client.project.get(resource)
    args, _ = client.project._get_fn.call_args
    assert args[0] is client._client
    assert args[1] == resource_ns
    assert args[2] == "proj-456"


def test_delete_with_uuid_string_uses_default_namespace(
    client_with_mock_transport: Client,
) -> None:
    """delete(uuid) delegates with client default namespace."""
    client = client_with_mock_transport
    client.project._delete_fn = Mock(return_value=True)
    result = client.project.delete("proj-789")
    assert result is True
    args, _ = client.project._delete_fn.call_args
    assert args[0] is client._client
    assert args[1] == conftest.TEST_NAMESPACE_DEFAULT
    assert args[2] == "proj-789"


def test_delete_with_resource_object_uses_resource_namespace(
    client_with_mock_transport: Client,
) -> None:
    """delete(resource) uses resource.tenant_meta.namespace (context anchoring)."""
    client = client_with_mock_transport
    resource_ns = "tenant.other-team"
    resource = Mock(uuid="proj-abc", tenant_meta=Mock(namespace=resource_ns))
    client.project._delete_fn = Mock(return_value=True)
    result = client.project.delete(resource)
    assert result is True
    args, _ = client.project._delete_fn.call_args
    assert args[0] is client._client
    assert args[1] == resource_ns
    assert args[2] == "proj-abc"


def test_update_with_resource_object_and_no_payload_uses_resource_as_payload(
    client_with_mock_transport: Client,
) -> None:
    """update(resource, update_mask=...) uses resource namespace and payload."""
    client = client_with_mock_transport
    resource_ns = "tenant.eng"
    resource = Mock(uuid="proj-def", tenant_meta=Mock(namespace=resource_ns))
    client.project._update_fn = Mock(return_value=resource)
    _ = client.project.update(resource, update_mask="meta.description")
    args, _ = client.project._update_fn.call_args
    assert args[0] is client._client
    assert args[1] == resource_ns
    assert args[2] == "proj-def"
    assert args[3] is resource
    assert args[4] == "meta.description"


def test_update_with_uuid_requires_payload(
    client_with_mock_transport: Client,
) -> None:
    """update(uuid, payload=None, update_mask=...) raises TypeError."""
    client = client_with_mock_transport
    client.project._update_fn = Mock()
    with pytest.raises(TypeError, match="payload is required"):
        client.project.update("proj-uuid", update_mask="meta.description")
    client.project._update_fn.assert_not_called()


def test_update_requires_update_mask(
    client_with_mock_transport: Client,
) -> None:
    """update(id_or_resource) with no update_mask and no kwargs raises TypeError."""
    client = client_with_mock_transport
    resource = Mock(uuid="proj-xyz", tenant_meta=Mock(namespace="tenant.ns"))
    client.project._update_fn = Mock()
    with pytest.raises(TypeError, match=r"update_mask|kwargs"):
        client.project.update(resource)
    client.project._update_fn.assert_not_called()


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
    client.project._update_fn = Mock(return_value=returned)
    _ = client.project.update(resource, meta_description="new desc")
    client.project._update_fn.assert_called_once()
    args, _ = client.project._update_fn.call_args
    assert args[0] is client._client
    assert args[1] == resource_ns
    assert args[2] == "proj-kw"
    assert args[3].meta.description == "new desc"
    assert args[4] == "meta.description"


def test_create_with_explicit_params_merges_into_kwargs(
    client_with_mock_transport: Client,
) -> None:
    """create(name=..., description=..., namespace_uuid=...) merges into kwargs."""
    client = client_with_mock_transport
    built_payload = Mock()
    client.project._build_create_payload_fn = Mock(return_value=built_payload)
    client.project._create_fn = Mock(return_value=Mock(uuid="new-proj"))
    client.project.create(
        name="my-project",
        description="A project",
        namespace_uuid="ns-uuid-123",
    )
    client.project._build_create_payload_fn.assert_called_once()
    call_kwargs = client.project._build_create_payload_fn.call_args[1]
    assert call_kwargs["name"] == "my-project"
    assert call_kwargs["description"] == "A project"
    assert call_kwargs["namespace_uuid"] == "ns-uuid-123"
    client.project._create_fn.assert_called_once()
    assert client.project._create_fn.call_args[0][2] is built_payload


def test_create_explicit_param_overrides_kwarg(
    client_with_mock_transport: Client,
) -> None:
    """Explicit name= overrides same key in kwargs when not None."""
    client = client_with_mock_transport
    built_payload = Mock()
    client.project._build_create_payload_fn = Mock(return_value=built_payload)
    client.project._create_fn = Mock(return_value=Mock(uuid="new-proj"))
    client.project.create(
        name="explicit-name",
        description="from-kwargs",
        namespace_uuid="ns-1",
    )
    call_kwargs = client.project._build_create_payload_fn.call_args[1]
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
    client.project._update_fn = Mock(return_value=returned)
    client.project.update(
        resource,
        meta_description="new desc",
        meta_tags=["t1"],
    )
    client.project._update_fn.assert_called_once()
    args, _ = client.project._update_fn.call_args
    assert args[3].meta.description == "new desc"
    assert args[3].meta.tags == ["t1"]
    assert args[4] == "meta.description,meta.tags"


def test_delete_ignore_missing_false_raises_not_found(
    client_with_mock_transport: Client,
) -> None:
    """delete(uuid, ignore_missing=False) raises NotFoundError on 404."""
    client = client_with_mock_transport
    client.project._delete_fn = Mock(side_effect=NotFoundError("Resource not found"))
    with pytest.raises(NotFoundError, match="Resource not found"):
        client.project.delete("proj-missing")
    client.project._delete_fn.assert_called_once()


def test_delete_ignore_missing_true_returns_false_on_not_found(
    client_with_mock_transport: Client,
) -> None:
    """delete(uuid, ignore_missing=True) catches NotFoundError and returns False."""
    client = client_with_mock_transport
    client.project._delete_fn = Mock(side_effect=NotFoundError("Resource not found"))
    result = client.project.delete("proj-missing", ignore_missing=True)
    assert result is False
    client.project._delete_fn.assert_called_once()


def test_delete_ignore_missing_true_returns_true_on_success(
    client_with_mock_transport: Client,
) -> None:
    """delete(uuid, ignore_missing=True) returns True when delete succeeds."""
    client = client_with_mock_transport
    client.project._delete_fn = Mock(return_value=True)
    result = client.project.delete("proj-ok", ignore_missing=True)
    assert result is True
    client.project._delete_fn.assert_called_once()


def test_list_iter_returns_iterator_and_delegates(
    client_with_mock_transport: Client,
) -> None:
    """list_iter(max_pages=1) returns an iterator and delegates to list_iter_fn."""
    client = client_with_mock_transport
    client.project._list_iter_fn = Mock(return_value=iter([Mock(uuid="p1")]))
    it = client.project.list_iter(max_pages=conftest.TEST_MAX_PAGES)
    items = list(it)
    assert len(items) == 1
    assert items[0].uuid == "p1"
    client.project._list_iter_fn.assert_called_once()
    args, _ = client.project._list_iter_fn.call_args
    assert args[0] is client._client
    assert args[1] == conftest.TEST_NAMESPACE_DEFAULT
    assert args[3] == conftest.TEST_MAX_PAGES


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
    client.project._update_fn = Mock(return_value=resource)
    client.project.tag(resource, ["a", "b"])
    client.project._update_fn.assert_called_once()
    args, _ = client.project._update_fn.call_args
    assert args[0] is client._client
    assert args[1] == resource_ns
    assert args[2] == "proj-tag"
    assert args[4] == "meta.tags"


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
    client.project._update_fn = Mock(return_value=resource)
    client.project.untag(resource, ["b"])
    client.project._update_fn.assert_called_once()
    args, _ = client.project._update_fn.call_args
    assert args[4] == "meta.tags"


def test_tag_raises_when_resource_has_no_tags_support(
    client_with_mock_transport: Client,
) -> None:
    """tag() on a facade without tags support raises NotImplementedError."""
    client = client_with_mock_transport
    # api_keys has no update_fn and no tags_paths from registry
    with pytest.raises(NotImplementedError, match="does not support tag"):
        client.api_key.tag("some-uuid", ["x"])


def test_list_with_identity_kwarg_builds_filter(
    client_with_mock_transport: Client,
) -> None:
    """list(name='backend', max_pages=1) passes filter with meta.name clause."""
    client = client_with_mock_transport
    mock_list = Mock(return_value=[])
    client.project._list_fn = mock_list
    client.project.list(name="backend", max_pages=conftest.TEST_MAX_PAGES)
    mock_list.assert_called_once()
    args, _ = mock_list.call_args
    lp = args[2]
    assert lp is not None
    assert lp.filter is not None
    assert "meta.name" in lp.filter
    assert "backend" in lp.filter


def test_list_with_explicit_filter_for_resource_without_filter_map(
    client_with_mock_transport: Client,
) -> None:
    """list(filter='...', max_pages=1) passes filter through when no identity map."""
    client = client_with_mock_transport
    mock_list = Mock(return_value=[])
    client.api_key._list_fn = mock_list
    client.api_key.list(
        filter="meta.name == 'my-key'",
        max_pages=conftest.TEST_MAX_PAGES,
    )
    mock_list.assert_called_once()
    args, _ = mock_list.call_args
    lp = args[2]
    assert lp is not None
    assert lp.filter == "meta.name == 'my-key'"


def test_list_with_high_utility_kwargs_passes_archive_page_id_pr_uuid_list_all(
    client_with_mock_transport: Client,
) -> None:
    """Pass archive, page_id, pr_uuid to ListParameters; list_all is always True (default)."""
    client = client_with_mock_transport
    mock_list = Mock(return_value=[])
    client.namespace._list_fn = mock_list
    client.namespace.list(
        archive=True,
        page_id="p1",
        pr_uuid="pr-1",
        max_pages=conftest.TEST_MAX_PAGES,
    )
    mock_list.assert_called_once()
    args, _ = mock_list.call_args
    lp = args[2]
    assert lp is not None
    assert lp.archive is True
    assert lp.page_id == "p1"
    assert lp.pr_uuid == "pr-1"
    assert lp.list_all is True  # default for list operations


def test_list_explicit_kwargs_override_list_params(
    client_with_mock_transport: Client,
) -> None:
    """Explicit kwargs override when both list_params and kwargs passed."""
    from endorlabs.types import ListParameters

    client = client_with_mock_transport
    mock_list = Mock(return_value=[])
    client.namespace._list_fn = mock_list
    client.namespace.list(
        list_params=ListParameters(filter="from_list_params"),
        filter="from_explicit",
        max_pages=conftest.TEST_MAX_PAGES,
    )
    mock_list.assert_called_once()
    args, _ = mock_list.call_args
    lp = args[2]
    assert lp is not None
    assert lp.filter == "from_explicit"


def test_lookup_returns_single_item(
    client_with_mock_transport: Client,
) -> None:
    """lookup(name='only') returns the single item when list returns one."""
    client = client_with_mock_transport
    single = Mock(
        uuid="proj-1",
        tenant_meta=Mock(namespace=conftest.TEST_NAMESPACE_DEFAULT),
    )
    mock_list = Mock(return_value=[single])
    client.project._list_fn = mock_list
    result = client.project.lookup(name="only", max_pages=2)
    assert result is single
    mock_list.assert_called_once()
    args, _ = mock_list.call_args
    assert args[3] == 2


def test_lookup_raises_not_found_when_zero(
    client_with_mock_transport: Client,
) -> None:
    """lookup(...) raises NotFoundError when list returns no items."""
    client = client_with_mock_transport
    client.project._list_fn = Mock(return_value=[])
    with pytest.raises(NotFoundError, match="No resource matched"):
        client.project.lookup(name="missing", max_pages=2)


def test_lookup_raises_ambiguous_when_multiple(
    client_with_mock_transport: Client,
) -> None:
    """lookup(...) raises AmbiguousError when list returns more than one."""
    client = client_with_mock_transport
    a = Mock(uuid="proj-a", tenant_meta=Mock(namespace=conftest.TEST_NAMESPACE_DEFAULT))
    b = Mock(uuid="proj-b", tenant_meta=Mock(namespace=conftest.TEST_NAMESPACE_DEFAULT))
    client.project._list_fn = Mock(return_value=[a, b])
    with pytest.raises(AmbiguousError, match="Multiple resources"):
        client.project.lookup(name="dup", max_pages=2)


def test_lookup_calls_list_with_identity_kwargs(
    client_with_mock_transport: Client,
) -> None:
    """lookup(name='x') calls list with name and max_pages=2; filter built from name."""
    client = client_with_mock_transport
    single = Mock(
        uuid="p1",
        tenant_meta=Mock(namespace=conftest.TEST_NAMESPACE_DEFAULT),
    )
    mock_list = Mock(return_value=[single])
    client.project._list_fn = mock_list
    client.project.lookup(name="backend")
    mock_list.assert_called_once()
    args, _ = mock_list.call_args
    lp = args[2]
    assert lp is not None
    assert lp.filter is not None
    assert "meta.name" in lp.filter
    assert "backend" in lp.filter
    assert args[3] == 2


def test_list_with_parent_uses_parent_namespace_and_filter(
    client_with_mock_transport: Client,
) -> None:
    """list(parent=project) delegates with parent namespace and parent_uuid filter."""
    client = client_with_mock_transport
    project_ns = "tenant.engineering"
    project_uuid = "proj-parent-123"
    project = Mock(uuid=project_uuid, tenant_meta=Mock(namespace=project_ns))
    mock_list = Mock(return_value=[])
    client.scan_result._list_fn = mock_list
    result = client.scan_result.list(
        parent=project, traverse=True, max_pages=conftest.TEST_MAX_PAGES
    )
    assert result == []
    mock_list.assert_called_once()
    args, _ = mock_list.call_args
    assert args[0] is client._client
    assert args[1] == project_ns
    lp = args[2]
    assert lp is not None
    assert lp.filter is not None
    assert "meta.parent_uuid" in lp.filter
    assert project_uuid in lp.filter
    assert args[3] == conftest.TEST_MAX_PAGES


def test_list_with_parent_raises_when_facade_does_not_support_parent(
    client_with_mock_transport: Client,
) -> None:
    """list(parent=...) raises when resource has no parent_kind."""
    client = client_with_mock_transport
    some_resource = Mock(uuid="ns-1", tenant_meta=Mock(namespace="tenant.foo"))
    with pytest.raises(ValueError, match="does not support list\\(parent="):
        client.namespace.list(parent=some_resource, max_pages=conftest.TEST_MAX_PAGES)


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

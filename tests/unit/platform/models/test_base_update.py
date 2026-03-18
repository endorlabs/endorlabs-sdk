"""Unit tests for BaseResourceOperations.update() behavior.

Tests sparse payload building, immutable-field blocking, unmodeled-attribute
warning, and wire contract (PATCH URL and body shape per API spec).
See plan: base update sparse mask immutable; API-spec consistency.
"""

from unittest.mock import Mock

import pytest
from pydantic import BaseModel, ConfigDict, Field

from endorlabs.core.exceptions import ValidationError as EndorValidationError
from endorlabs.models.base import BaseResource
from endorlabs.operations import BaseResourceOperations
from endorlabs.resources.authorization_policy import AuthorizationPolicy
from endorlabs.resources.finding import Finding
from endorlabs.resources.installation import Installation
from endorlabs.resources.metric import Metric
from endorlabs.resources.package_version import PackageVersion
from endorlabs.resources.project import Project
from endorlabs.resources.semgrep_rule import SemgrepRule


class MinimalPayload(BaseModel):
    """Minimal payload for update tests (uuid only)."""

    uuid: str = Field(..., description="Resource UUID")


class PayloadWithExtra(BaseModel):
    """Payload that allows extra attributes (for unmodeled warning test)."""

    model_config = ConfigDict(extra="allow")

    uuid: str = Field(..., description="Resource UUID")


class TestBuildSparseUpdateObject:
    """Tests for _build_sparse_update_object helper."""

    def test_sparse_object_contains_only_uuid_and_masked_paths(self) -> None:
        """Result has uuid and only the paths in update_mask."""
        client = Mock()
        ops = BaseResourceOperations(client, "findings", MinimalPayload)
        payload_dict = {
            "uuid": "abc-123",
            "tenant_meta": {"namespace": "ns"},
            "meta": {"name": "x", "tags": ["a", "b"]},
            "spec": {"finding_tags": ["T1"], "level": "HIGH"},
            "context": {"type": "main"},
        }
        update_mask = ["meta.tags", "spec.finding_tags"]
        result = ops._build_sparse_update_object(payload_dict, update_mask, "abc-123")
        assert result["uuid"] == "abc-123"
        assert result.get("meta") == {"tags": ["a", "b"]}
        assert result.get("spec") == {"finding_tags": ["T1"]}
        assert "tenant_meta" not in result
        assert "context" not in result
        assert "level" not in result.get("spec", {})

    def test_sparse_uses_resource_uuid_when_missing_in_payload(self) -> None:
        """When payload has no uuid, result uses resource_uuid."""
        client = Mock()
        ops = BaseResourceOperations(client, "findings", MinimalPayload)
        payload_dict = {"meta": {"tags": ["x"]}}
        result = ops._build_sparse_update_object(
            payload_dict, ["meta.tags"], "fallback-uuid"
        )
        assert result["uuid"] == "fallback-uuid"
        assert result["meta"]["tags"] == ["x"]

    def test_sparse_skips_missing_optional_path(self) -> None:
        """Missing path in payload does not crash; path is skipped."""
        client = Mock()
        ops = BaseResourceOperations(client, "findings", MinimalPayload)
        payload_dict = {"uuid": "id-1"}  # no meta, no spec
        result = ops._build_sparse_update_object(
            payload_dict, ["meta.tags", "spec.finding_tags"], "id-1"
        )
        assert result == {"uuid": "id-1"}
        assert "meta" not in result
        assert "spec" not in result

    def test_sparse_empty_mask_returns_only_uuid(self) -> None:
        """Empty update_mask yields only uuid."""
        client = Mock()
        ops = BaseResourceOperations(client, "findings", MinimalPayload)
        payload_dict = {"uuid": "id-1", "meta": {"tags": ["x"]}}
        result = ops._build_sparse_update_object(payload_dict, [], "id-1")
        assert result == {"uuid": "id-1"}


class TestUpdateImmutableBlock:
    """Tests for immutable-field blocking in update()."""

    def test_update_with_immutable_in_mask_raises(self) -> None:
        """When update_mask contains immutable path, raise EndorValidationError."""
        client = Mock()
        client.patch = Mock()
        ops = BaseResourceOperations(client, "findings", Finding)
        payload = MinimalPayload(uuid="finding-uuid")
        with pytest.raises(EndorValidationError) as exc_info:
            ops.update(
                "tenant.ns",
                "finding-uuid",
                payload,
                update_mask=["uuid"],
            )
        assert "immutable" in exc_info.value.message.lower()
        assert "uuid" in exc_info.value.message
        client.patch.assert_not_called()

    def test_update_with_empty_mask_raises_validation_error(self) -> None:
        """Empty update_mask raises EndorValidationError (update_mask is required)."""
        client = Mock()
        client.patch = Mock()
        ops = BaseResourceOperations(client, "findings", MinimalPayload)
        payload = MinimalPayload(uuid="id-1")
        with pytest.raises(EndorValidationError) as exc_info:
            ops.update("tenant.ns", "id-1", payload, update_mask=[])
        assert "update_mask" in exc_info.value.message.lower()
        client.patch.assert_not_called()

    def test_update_with_unmapped_resource_name_fails_fast_on_missing_metadata(
        self,
    ) -> None:
        """Resource missing generated mutability metadata should fail fast."""
        client = Mock()
        client.patch = Mock()
        ops = BaseResourceOperations(client, "dashboard-config", MinimalPayload)
        payload = MinimalPayload(uuid="id-1")
        with pytest.raises(EndorValidationError) as exc_info:
            ops.update(
                "tenant.ns",
                "id-1",
                payload,
                update_mask=["uuid"],
            )
        assert "mutability metadata missing" in exc_info.value.message.lower()
        client.patch.assert_not_called()

    def test_update_metrics_immutable_in_mask_raises(self) -> None:
        """When resource is mapped (e.g. metrics), immutable path in mask raises."""
        client = Mock()
        client.patch = Mock()
        ops = BaseResourceOperations(client, "metrics", Metric)
        payload = MinimalPayload(uuid="metric-uuid")
        with pytest.raises(EndorValidationError) as exc_info:
            ops.update(
                "tenant.ns",
                "metric-uuid",
                payload,
                update_mask=["uuid"],
            )
        assert "immutable" in exc_info.value.message.lower()
        client.patch.assert_not_called()

    def test_update_authorization_policy_immutable_spec_path_raises(self) -> None:
        """Authorization policy: spec.is_support_policy is readOnly per OpenAPI."""
        client = Mock()
        client.patch = Mock()
        ops = BaseResourceOperations(
            client, "authorization-policies", AuthorizationPolicy
        )
        payload = MinimalPayload(uuid="ap-uuid")
        with pytest.raises(EndorValidationError) as exc_info:
            ops.update(
                "tenant.ns",
                "ap-uuid",
                payload,
                update_mask=["spec.is_support_policy"],
            )
        assert "immutable" in exc_info.value.message.lower()
        assert "spec.is_support_policy" in exc_info.value.message
        client.patch.assert_not_called()

    def test_update_installation_immutable_spec_path_raises(self) -> None:
        """Installation: spec.external_name is readOnly per OpenAPI."""
        client = Mock()
        client.patch = Mock()
        ops = BaseResourceOperations(client, "installations", Installation)
        payload = MinimalPayload(uuid="inst-uuid")
        with pytest.raises(EndorValidationError) as exc_info:
            ops.update(
                "tenant.ns",
                "inst-uuid",
                payload,
                update_mask=["spec.external_name"],
            )
        assert "immutable" in exc_info.value.message.lower()
        assert "spec.external_name" in exc_info.value.message
        client.patch.assert_not_called()

    def test_update_package_version_immutable_spec_path_raises(self) -> None:
        """Package version: spec.ecosystem is readOnly per OpenAPI."""
        client = Mock()
        client.patch = Mock()
        ops = BaseResourceOperations(client, "package-versions", PackageVersion)
        payload = MinimalPayload(uuid="pv-uuid")
        with pytest.raises(EndorValidationError) as exc_info:
            ops.update(
                "tenant.ns",
                "pv-uuid",
                payload,
                update_mask=["spec.ecosystem"],
            )
        assert "immutable" in exc_info.value.message.lower()
        assert "spec.ecosystem" in exc_info.value.message
        client.patch.assert_not_called()

    def test_update_semgrep_rule_immutable_spec_path_raises(self) -> None:
        """Semgrep rule: spec.defined_by is readOnly per OpenAPI."""
        client = Mock()
        client.patch = Mock()
        ops = BaseResourceOperations(client, "semgrep-rules", SemgrepRule)
        payload = MinimalPayload(uuid="rule-uuid")
        with pytest.raises(EndorValidationError) as exc_info:
            ops.update(
                "tenant.ns",
                "rule-uuid",
                payload,
                update_mask=["spec.defined_by"],
            )
        assert "immutable" in exc_info.value.message.lower()
        assert "spec.defined_by" in exc_info.value.message
        client.patch.assert_not_called()


class TestUpdateUnmodeledWarning:
    """Tests for unmodeled-attribute warning in update()."""

    def test_update_with_extra_attributes_logs_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """When payload has __pydantic_extra__ set, log a warning."""
        client = Mock()
        client.patch = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {"uuid": "id-1"}
        mock_response.raise_for_status = Mock()
        client.patch.return_value = mock_response
        ops = BaseResourceOperations(client, "findings", PayloadWithExtra)
        payload = PayloadWithExtra(uuid="id-1", future_field="value")
        ops.update("tenant.ns", "id-1", payload, update_mask=["meta.tags"])
        client.patch.assert_called_once()
        assert "Unmodeled" in caplog.text or "unmodeled" in caplog.text.lower()


# Expected top-level keys for PATCH body per API spec (object + optional request)
UPDATE_BODY_OBJECT_KEY = "object"
UPDATE_BODY_REQUEST_KEY = "request"
UPDATE_BODY_REQUEST_UPDATE_MASK_KEY = "update_mask"


class TestUpdateContractSpec:
    """Contract tests: PATCH URL and body shape match API spec."""

    def test_patch_uses_collection_url(self) -> None:
        """PATCH is sent to collection URL (no UUID in path)."""
        client = Mock()
        client.patch = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {"uuid": "finding-uuid"}
        mock_response.raise_for_status = Mock()
        client.patch.return_value = mock_response
        ops = BaseResourceOperations(client, "findings", MinimalPayload)
        payload = MinimalPayload(uuid="finding-uuid")
        tenant_meta_namespace = "tenant.example"
        resource_uuid = "finding-uuid"
        ops.update(
            tenant_meta_namespace,
            resource_uuid,
            payload,
            update_mask=["meta.tags"],
        )
        client.patch.assert_called_once()
        call_args = client.patch.call_args
        url = call_args[0][0]
        assert url == f"v1/namespaces/{tenant_meta_namespace}/findings"
        assert resource_uuid not in url

    def test_patch_body_has_object_and_request_update_mask_when_mask_provided(
        self,
    ) -> None:
        """When update_mask is provided, body has object and request.update_mask."""
        client = Mock()
        client.patch = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {"uuid": "id-1"}
        mock_response.raise_for_status = Mock()
        client.patch.return_value = mock_response
        ops = BaseResourceOperations(client, "findings", MinimalPayload)
        payload = MinimalPayload(uuid="id-1")
        update_mask_list = ["meta.tags", "spec.finding_tags"]
        ops.update("tenant.ns", "id-1", payload, update_mask_list)
        call_args = client.patch.call_args
        json_body = call_args[1]["json"]
        assert UPDATE_BODY_OBJECT_KEY in json_body
        assert json_body[UPDATE_BODY_OBJECT_KEY]["uuid"] == "id-1"
        assert UPDATE_BODY_REQUEST_KEY in json_body
        assert (
            json_body[UPDATE_BODY_REQUEST_KEY][UPDATE_BODY_REQUEST_UPDATE_MASK_KEY]
            == "meta.tags,spec.finding_tags"
        )

    def test_update_with_none_or_empty_mask_raises_validation_error(self) -> None:
        """update() raises EndorValidationError when update_mask is empty (required)."""
        client = Mock()
        client.patch = Mock()
        ops = BaseResourceOperations(client, "findings", MinimalPayload)
        payload = MinimalPayload(uuid="id-1")
        with pytest.raises(EndorValidationError) as exc_info:
            ops.update("tenant.ns", "id-1", payload, update_mask=[])
        assert "update_mask" in exc_info.value.message.lower()
        client.patch.assert_not_called()

    def test_patch_body_always_has_object_and_request_update_mask(self) -> None:
        """PATCH body has object and request.update_mask (update_mask required)."""
        client = Mock()
        client.patch = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {"uuid": "id-1"}
        mock_response.raise_for_status = Mock()
        client.patch.return_value = mock_response
        ops = BaseResourceOperations(client, "findings", MinimalPayload)
        payload = MinimalPayload(uuid="id-1")
        ops.update("tenant.ns", "id-1", payload, update_mask=["meta.tags"])
        call_args = client.patch.call_args
        json_body = call_args[1]["json"]
        assert UPDATE_BODY_OBJECT_KEY in json_body
        assert json_body[UPDATE_BODY_OBJECT_KEY]["uuid"] == "id-1"
        assert UPDATE_BODY_REQUEST_KEY in json_body
        assert (
            json_body[UPDATE_BODY_REQUEST_KEY][UPDATE_BODY_REQUEST_UPDATE_MASK_KEY]
            == "meta.tags"
        )


class TestModelClassmethodsCanonical:
    """Tests for get_mutable_fields_cls/get_immutable_fields_cls and get_tags_update_paths.

    Model is canonical for mutable/immutable fields; get_tags_update_paths
    derives tag paths from the model class.
    """  # noqa: E501

    def test_base_resource_get_mutable_fields_cls_returns_default(self) -> None:
        """BaseResource.get_mutable_fields_cls() returns default mutable list."""
        mutable = BaseResource.get_mutable_fields_cls()
        assert mutable == ["meta.description", "meta.tags"]

    def test_project_get_mutable_fields_cls_includes_processing_status(self) -> None:
        """Project.get_mutable_fields_cls() includes processing_status paths."""
        mutable = Project.get_mutable_fields_cls()
        assert "meta.description" in mutable
        assert "meta.tags" in mutable
        assert "processing_status.scan_state" in mutable
        assert "processing_status.disable_automated_scan" in mutable

    def test_finding_get_mutable_fields_cls_includes_finding_tags(self) -> None:
        """Finding.get_mutable_fields_cls() includes spec.finding_tags and context.tags."""  # noqa: E501
        mutable = Finding.get_mutable_fields_cls()
        assert "meta.tags" in mutable
        assert "spec.finding_tags" in mutable
        assert "context.tags" in mutable

    def test_project_get_immutable_fields_cls_includes_spec_git(self) -> None:
        """Project.get_immutable_fields_cls() includes spec.git."""
        from endorlabs.resources.project import Project

        immutable = Project.get_immutable_fields_cls()
        assert "uuid" in immutable
        assert "meta.name" in immutable
        assert "spec.git" in immutable
        assert "tenant_meta.namespace" in immutable

    def test_get_tags_update_paths_from_model_class(self) -> None:
        """get_tags_update_paths(model_class) returns tag paths from model mutable."""
        from endorlabs.utils.model_validation import get_tags_update_paths

        # Project has meta.tags but not spec.finding_tags
        project_tags = get_tags_update_paths(Project)
        assert "meta.tags" in project_tags
        assert "spec.finding_tags" not in project_tags

        # Finding has both meta.tags and spec.finding_tags
        finding_tags = get_tags_update_paths(Finding)
        assert "meta.tags" in finding_tags
        assert "spec.finding_tags" in finding_tags

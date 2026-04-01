"""Integration tests for PRCommentConfig resource operations."""

from __future__ import annotations

import time
from contextlib import suppress

import pytest

import endorlabs
from endorlabs.resources.pr_comment_config import (
    CreatePRCommentConfigPayload,
    PlatformSource,
    PRCommentConfigMeta,
    PRCommentConfigSpec,
    PRCommentsTemplate,
)
from tests.conftest import TEST_MAX_PAGES


@pytest.mark.integration
class TestPRCommentConfig:
    """Exercise list/get/create/update/delete for PRCommentConfig."""

    @pytest.fixture(autouse=True)
    def setup_fast(self, api_client, namespace) -> None:
        self.client = endorlabs.Client(tenant=namespace, api_client=api_client)
        self.created_uuids: list[str] = []

    def teardown_method(self) -> None:
        for uuid in getattr(self, "created_uuids", []):
            with suppress(Exception):
                self.client.PRCommentConfig.delete(uuid)
        self.created_uuids.clear()

    def test_pr_comment_config_list(self) -> None:
        """LIST should return a list result."""
        result = self.client.PRCommentConfig.list(max_pages=TEST_MAX_PAGES)
        assert isinstance(result, list)

    def test_pr_comment_config_get(self) -> None:
        """GET first item from LIST when available."""
        items = self.client.PRCommentConfig.list(max_pages=TEST_MAX_PAGES)
        if not items:
            pytest.skip("No PRCommentConfig resources in scope.")
        got = self.client.PRCommentConfig.get(items[0].uuid)
        assert got is not None
        assert got.uuid == items[0].uuid

    @pytest.mark.writes
    def test_pr_comment_config_create_update_delete(self) -> None:
        """CREATE/UPDATE/DELETE roundtrip with template payload."""
        ts = int(time.time())
        name = f"sdk-pr-comment-config-{ts}"
        template = (
            "## Endor Labs Findings\\nSummary template from SDK integration test."
        )
        payload = CreatePRCommentConfigPayload(
            meta=PRCommentConfigMeta(
                name=name,
                description="SDK integration test config",
                tags=["test", "pr-comment-config"],
            ),
            spec=PRCommentConfigSpec(
                platform_type=PlatformSource.GITHUB,
                template=PRCommentsTemplate(findings_summary_template=template),
            ),
            propagate=False,
        )

        try:
            created = self.client.PRCommentConfig.create(payload)
        except Exception as exc:
            pytest.skip(
                f"PRCommentConfig create not allowed in this environment: {exc}"
            )

        assert created.meta.name == name
        self.created_uuids.append(created.uuid)

        updated_template = "## Endor Labs Findings (Updated)\\nUpdated template text."
        update_payload = created.model_copy(
            deep=True,
            update={
                "spec": created.spec.model_copy(
                    update={
                        "template": created.spec.template.model_copy(
                            update={"findings_summary_template": updated_template}
                        )
                    }
                )
            },
        )
        updated = self.client.PRCommentConfig.update(
            created.uuid,
            payload=update_payload,
            update_mask="spec.template.findings_summary_template",
        )
        assert updated is not None
        assert updated.spec.template.findings_summary_template == updated_template

        assert self.client.PRCommentConfig.delete(created.uuid) is True
        self.created_uuids.remove(created.uuid)
